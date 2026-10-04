"""
tests/test_scheduler.py

Tests for core/scheduler.py — priority scoring and daily plan generation.
"""

import uuid
from datetime import date, timedelta

import pytest

from core.scheduler import compute_scores, generate_plan
from core.task_manager import Task


def make_task(name: str, deadline: date, effort: float, priority: str) -> Task:
    return Task(
        id=uuid.uuid4().hex,
        name=name,
        course="TestCourse",
        deadline=deadline,
        estimated_effort_hours=effort,
        priority=priority,
        description="",
    )


def test_score_formula_single_task():
    """
    One High-priority task with effort 4h, deadline 7 days away.
    Expected score = 3*0.4 + 1.0*0.4 + 1.0*0.2 = 1.8
    Note: score > 1.0 is intentional — priority_weight is the raw integer (3), not normalized.
    """
    today = date.today()
    task = make_task("Big Project", today + timedelta(days=7), 4.0, "High")
    results = compute_scores([task], today)
    assert len(results) == 1
    assert results[0]["score"] == pytest.approx(1.8)
    assert results[0]["priority_weight"] == 3
    assert results[0]["urgency_score_normalized"] == pytest.approx(1.0)
    assert results[0]["effort_normalized"] == pytest.approx(1.0)


def test_score_ordering():
    """
    Three tasks with varying priorities and deadlines.
    Verify that the returned scores reflect the expected relative ordering.
    """
    today = date.today()
    task_high = make_task("High Task", today + timedelta(days=1), 2.0, "High")
    task_med = make_task("Med Task", today + timedelta(days=5), 2.0, "Medium")
    task_low = make_task("Low Task", today + timedelta(days=10), 2.0, "Low")

    results = compute_scores([task_high, task_med, task_low], today)
    score_map = {r["task"].name: r["score"] for r in results}

    assert score_map["High Task"] > score_map["Med Task"]
    assert score_map["Med Task"] > score_map["Low Task"]


def test_urgency_normalization_pinned():
    """
    Pinned multi-task example to verify max-normalization.
    today = date(2024, 11, 1)
    Task A: deadline 2024-11-02 (1 day away), effort 2h, priority Medium → score = 1.3000
    Task B: deadline 2024-11-04 (3 days away), effort 4h, priority High → score = 1.6000
    Task C: deadline 2024-11-08 (7 days away), effort 3h, priority Low → score = 0.6500
    """
    today = date(2024, 11, 1)
    task_a = make_task("Task A", date(2024, 11, 2), 2.0, "Medium")
    task_b = make_task("Task B", date(2024, 11, 4), 4.0, "High")
    task_c = make_task("Task C", date(2024, 11, 8), 3.0, "Low")

    results = compute_scores([task_a, task_b, task_c], today)
    score_map = {r["task"].name: r["score"] for r in results}

    assert score_map["Task B"] == pytest.approx(1.6000, abs=1e-9)
    assert score_map["Task A"] == pytest.approx(1.3000, abs=1e-9)
    assert score_map["Task C"] == pytest.approx(0.6500, abs=1e-9)

    # Sort order: B > A > C
    assert score_map["Task B"] > score_map["Task A"] > score_map["Task C"]


def test_score_deterministic():
    """Two calls with identical inputs must produce identical scores."""
    today = date.today()
    tasks = [
        make_task("T1", today + timedelta(days=3), 2.0, "High"),
        make_task("T2", today + timedelta(days=7), 4.0, "Medium"),
    ]
    results1 = compute_scores(tasks, today)
    results2 = compute_scores(tasks, today)

    for r1, r2 in zip(results1, results2):
        assert r1["score"] == pytest.approx(r2["score"])


def test_plan_respects_daily_limit():
    """No DaySlot should have total hours exceeding available_hours_per_day."""
    today = date.today()
    available = 6.0
    tasks = [
        make_task("T1", today + timedelta(days=5), 8.0, "High"),
        make_task("T2", today + timedelta(days=7), 5.0, "Medium"),
        make_task("T3", today + timedelta(days=10), 3.0, "Low"),
    ]
    result = generate_plan(tasks, today, available)
    for slot in result.day_slots:
        total = sum(a.hours_today for a in slot.allocations)
        assert total <= available + 1e-9, f"Slot {slot.date} has {total}h > {available}h"


def test_plan_covers_all_tasks():
    """Sum of hours_today across all slots must equal total effort of non-overdue tasks."""
    today = date.today()
    available = 6.0
    tasks = [
        make_task("T1", today + timedelta(days=5), 8.0, "High"),
        make_task("T2", today + timedelta(days=7), 5.0, "Medium"),
        make_task("T3", today + timedelta(days=10), 3.0, "Low"),
    ]
    result = generate_plan(tasks, today, available)

    overdue_ids = {t.id for t in result.overdue_tasks}
    expected_hours = sum(t.estimated_effort_hours for t in tasks if t.id not in overdue_ids)
    actual_hours = sum(
        a.hours_today for slot in result.day_slots for a in slot.allocations
    )
    assert actual_hours == pytest.approx(expected_hours)


def test_plan_excludes_overdue():
    """A task with yesterday's deadline must appear in overdue_tasks, not in day_slots."""
    today = date.today()
    overdue_task = make_task("Overdue", today - timedelta(days=1), 3.0, "High")
    future_task = make_task("Future", today + timedelta(days=5), 2.0, "Medium")

    result = generate_plan([overdue_task, future_task], today, 6.0)

    overdue_ids = {t.id for t in result.overdue_tasks}
    assert overdue_task.id in overdue_ids

    all_scheduled_ids = {
        a.task.id for slot in result.day_slots for a in slot.allocations
    }
    assert overdue_task.id not in all_scheduled_ids


def test_plan_flags_deadline_miss():
    """A task with 20h effort, deadline 1 day away, 6h/day → at least one slot has has_deadline_miss=True."""
    today = date.today()
    task = make_task("Big Task", today + timedelta(days=1), 20.0, "High")
    result = generate_plan([task], today, 6.0)

    flagged = [slot for slot in result.day_slots if slot.has_deadline_miss]
    assert len(flagged) >= 1
