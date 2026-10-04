"""
core/workload.py

Aggregate metrics, collision/overload detection.
No I/O, no Streamlit.
"""

from dataclasses import dataclass
from datetime import date

from core.task_manager import Task


@dataclass
class CollisionInfo:
    task: Task
    days_remaining: int
    hours_available_before_deadline: float  # = days_remaining * available_hours_per_day
    is_collision: bool


@dataclass
class WorkloadMetrics:
    total_tasks: int
    total_required_hours: float
    available_hours: float          # max(0, days_to_last_deadline) * available_hours_per_day
    surplus_deficit: float          # available_hours - total_required_hours
    is_overloaded: bool             # surplus_deficit < 0
    collisions: list[CollisionInfo]
    upcoming_deadlines: list[Task]  # all tasks with deadline >= today, sorted ascending


def compute_metrics(
    tasks: list[Task],
    today: date,
    available_hours_per_day: float,
) -> WorkloadMetrics:
    """
    Computes aggregate workload metrics.

    Step 0: Guard for non-positive available hours — returns all-zero metrics (no exception).
    Step 1: Empty tasks list → returns all-zero metrics.
    Step 2: Per-task collision detection.
    Step 3: Global available_hours using last (furthest) deadline.
    Step 4: Upcoming deadlines list (no time-window cap).
    Step 5: Totals and overload flag.
    """
    # Step 0: belt-and-suspenders guard
    if available_hours_per_day <= 0:
        return WorkloadMetrics(
            total_tasks=0,
            total_required_hours=0.0,
            available_hours=0.0,
            surplus_deficit=0.0,
            is_overloaded=False,
            collisions=[],
            upcoming_deadlines=[],
        )

    # Step 1: empty tasks
    if not tasks:
        return WorkloadMetrics(
            total_tasks=0,
            total_required_hours=0.0,
            available_hours=0.0,
            surplus_deficit=0.0,
            is_overloaded=False,
            collisions=[],
            upcoming_deadlines=[],
        )

    # Step 2: collision detection per task
    collisions: list[CollisionInfo] = []
    for task in tasks:
        days_remaining = max(0, (task.deadline - today).days)
        hours_available = days_remaining * available_hours_per_day
        is_collision = hours_available < task.estimated_effort_hours
        collisions.append(
            CollisionInfo(
                task=task,
                days_remaining=days_remaining,
                hours_available_before_deadline=hours_available,
                is_collision=is_collision,
            )
        )

    # Step 3: global available hours (clamped to zero for all-overdue scenario)
    last_deadline = max(t.deadline for t in tasks)
    available_hours = max(0, (last_deadline - today).days) * available_hours_per_day

    # Step 4: upcoming deadlines — all tasks on or after today, sorted ascending
    upcoming_deadlines = sorted(
        [t for t in tasks if t.deadline >= today],
        key=lambda t: t.deadline,
    )

    # Step 5: totals and overload
    total_required_hours = sum(t.estimated_effort_hours for t in tasks)
    surplus_deficit = available_hours - total_required_hours
    is_overloaded = surplus_deficit < 0

    return WorkloadMetrics(
        total_tasks=len(tasks),
        total_required_hours=total_required_hours,
        available_hours=available_hours,
        surplus_deficit=surplus_deficit,
        is_overloaded=is_overloaded,
        collisions=collisions,
        upcoming_deadlines=upcoming_deadlines,
    )
