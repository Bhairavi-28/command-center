"""
tests/test_workload.py

Tests for core/workload.py — aggregate metrics and collision detection.
"""

import uuid
from datetime import date, timedelta

import pytest

from core.task_manager import Task
from core.workload import compute_metrics


def make_task(
    name: str,
    deadline: date,
    effort: float,
    priority: str = "Medium",
) -> Task:
    return Task(
        id=uuid.uuid4().hex,
        name=name,
        course="TestCourse",
        deadline=deadline,
        estimated_effort_hours=effort,
        priority=priority,
        description="",
    )


def test_collision_detected():
    """10h task, 1 day left, 6h/day → collision."""
    today = date.today()
    task = make_task("Big HW", today + timedelta(days=1), 10.0)
    metrics = compute_metrics([task], today, 6.0)
    assert len(metrics.collisions) == 1
    c = metrics.collisions[0]
    assert c.is_collision is True
    assert c.hours_available_before_deadline == pytest.approx(6.0)


def test_no_collision():
    """5h task, 2 days left, 6h/day → no collision."""
    today = date.today()
    task = make_task("Small HW", today + timedelta(days=2), 5.0)
    metrics = compute_metrics([task], today, 6.0)
    assert len(metrics.collisions) == 1
    c = metrics.collisions[0]
    assert c.is_collision is False


def test_overload_detected():
    """Tasks totaling 30h, 3 days * 6h = 18h available → overloaded."""
    today = date.today()
    tasks = [
        make_task("T1", today + timedelta(days=3), 15.0),
        make_task("T2", today + timedelta(days=3), 15.0),
    ]
    metrics = compute_metrics(tasks, today, 6.0)
    assert metrics.is_overloaded is True
    assert metrics.total_required_hours == pytest.approx(30.0)
    assert metrics.available_hours == pytest.approx(18.0)


def test_no_overload():
    """Tasks totaling 10h, 5 days * 6h = 30h available → not overloaded."""
    today = date.today()
    tasks = [
        make_task("T1", today + timedelta(days=5), 5.0),
        make_task("T2", today + timedelta(days=5), 5.0),
    ]
    metrics = compute_metrics(tasks, today, 6.0)
    assert metrics.is_overloaded is False
    assert metrics.surplus_deficit == pytest.approx(20.0)


def test_empty_task_list_metrics():
    """Zero tasks → all numeric fields 0.0, is_overloaded=False."""
    today = date.today()
    metrics = compute_metrics([], today, 6.0)
    assert metrics.total_tasks == 0
    assert metrics.total_required_hours == pytest.approx(0.0)
    assert metrics.available_hours == pytest.approx(0.0)
    assert metrics.surplus_deficit == pytest.approx(0.0)
    assert metrics.is_overloaded is False
    assert metrics.collisions == []
    assert metrics.upcoming_deadlines == []


def test_all_tasks_overdue_metrics():
    """Task with past deadline → available_hours=0.0, is_overloaded=True."""
    today = date.today()
    task = make_task("Old HW", today - timedelta(days=1), 5.0)
    metrics = compute_metrics([task], today, 6.0)
    assert metrics.available_hours == pytest.approx(0.0)
    assert metrics.is_overloaded is True


def test_zero_hours_per_day_metrics():
    """
    Guard: available_hours_per_day=0 → no exception, all numeric fields 0.0,
    is_overloaded=False, collisions=[], upcoming_deadlines=[].
    """
    today = date.today()
    task = make_task("Valid Task", today + timedelta(days=5), 3.0)
    metrics = compute_metrics([task], today, 0)
    assert metrics.total_tasks == 0
    assert metrics.total_required_hours == pytest.approx(0.0)
    assert metrics.available_hours == pytest.approx(0.0)
    assert metrics.surplus_deficit == pytest.approx(0.0)
    assert metrics.is_overloaded is False
    assert metrics.collisions == []
    assert metrics.upcoming_deadlines == []
