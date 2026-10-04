"""
core/scheduler.py

Pure-function module for priority scoring and daily execution plan generation.
No I/O, no Streamlit. All functions take plain Python values and return plain Python values.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import NamedTuple

from core.task_manager import Task

logger = logging.getLogger(__name__)

_PRIORITY_WEIGHTS = {"High": 3, "Medium": 2, "Low": 1}


@dataclass
class TaskAllocation:
    task: Task
    hours_today: float


@dataclass
class DaySlot:
    date: date
    allocations: list[TaskAllocation] = field(default_factory=list)
    has_deadline_miss: bool = False


class PlanResult(NamedTuple):
    day_slots: list[DaySlot]
    overdue_tasks: list[Task]


def compute_scores(tasks: list[Task], today: date) -> list[dict]:
    """
    Returns a list of dicts with keys:
        task, score, priority_weight, urgency_score_normalized, effort_normalized

    Score formula (exact):
        score = (priority_weight * 0.4) + (urgency_score_normalized * 0.4) + (effort_normalized * 0.2)

    priority_weight: raw integer (High=3, Medium=2, Low=1) — NOT normalized.
    Scores above 1.0 are valid and expected (e.g., single High task = 1.8).
    """
    if not tasks:
        return []

    # Step 1 & 2: compute raw urgency per task
    urgency_raws = []
    for task in tasks:
        days_until_deadline = max(0, (task.deadline - today).days)
        urgency_raw = 1.0 / (days_until_deadline + 1)
        urgency_raws.append(urgency_raw)

    # Step 3: max-normalize urgency
    max_urgency = max(urgency_raws)
    # Single task or all same deadline → normalized = 1.0 for the maximum(s)
    urgency_normalized = [u / max_urgency for u in urgency_raws]

    # Step 4: effort normalization
    efforts = [task.estimated_effort_hours for task in tasks]
    max_effort = max(efforts)
    effort_normalized = [e / max_effort for e in efforts]

    # Step 5 & 6: assemble result
    results = []
    for i, task in enumerate(tasks):
        pw = _PRIORITY_WEIGHTS.get(task.priority, 2)  # default Medium if unexpected
        un = urgency_normalized[i]
        en = effort_normalized[i]
        score = (pw * 0.4) + (un * 0.4) + (en * 0.2)
        results.append(
            {
                "task": task,
                "score": score,
                "priority_weight": pw,
                "urgency_score_normalized": un,
                "effort_normalized": en,
            }
        )

    return results


def generate_plan(
    tasks: list[Task],
    today: date,
    available_hours_per_day: float,
) -> PlanResult:
    """
    Generates a greedy daily execution plan.

    Guard: available_hours_per_day <= 0 → returns PlanResult([], []) and logs a warning.
    Overdue tasks (deadline < today) are collected in PlanResult.overdue_tasks.
    """
    if available_hours_per_day <= 0:
        logger.warning(
            "generate_plan called with available_hours_per_day=%s; returning empty plan.",
            available_hours_per_day,
        )
        return PlanResult([], [])

    # Separate overdue tasks
    overdue_tasks = [t for t in tasks if t.deadline < today]
    active_tasks = [t for t in tasks if t.deadline >= today]

    if not active_tasks:
        return PlanResult([], overdue_tasks)

    # Sort active tasks descending by score
    scored = compute_scores(active_tasks, today)
    scored_sorted = sorted(scored, key=lambda x: x["score"], reverse=True)
    sorted_tasks = [s["task"] for s in scored_sorted]

    # Greedy allocation
    day_slots: list[DaySlot] = []
    current_day = today
    hours_remaining_today = available_hours_per_day

    # Ensure there is a slot for today even before allocating
    current_slot = DaySlot(date=current_day)

    for task in sorted_tasks:
        hours_left_on_task = task.estimated_effort_hours

        while hours_left_on_task > 0:
            allocated = min(hours_remaining_today, hours_left_on_task)
            current_slot.allocations.append(
                TaskAllocation(task=task, hours_today=allocated)
            )
            hours_remaining_today -= allocated
            hours_left_on_task -= allocated

            # Use <= 0 to handle float rounding
            if hours_remaining_today <= 0:
                day_slots.append(current_slot)
                current_day = current_day + timedelta(days=1)
                hours_remaining_today = available_hours_per_day
                current_slot = DaySlot(date=current_day)

    # Append the last slot if it has any allocations
    if current_slot.allocations:
        day_slots.append(current_slot)

    # Annotate deadline misses
    for slot in day_slots:
        for allocation in slot.allocations:
            if allocation.task.deadline < slot.date:
                slot.has_deadline_miss = True
                break

    return PlanResult(day_slots=day_slots, overdue_tasks=overdue_tasks)
