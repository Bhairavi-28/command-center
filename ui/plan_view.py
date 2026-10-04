"""
ui/plan_view.py

Execution plan tab renderer.
All scheduling logic delegated to core/scheduler.py.
"""

from datetime import date

import pandas as pd
import streamlit as st

from core import scheduler, task_manager
from core.scheduler import DaySlot, PlanResult, TaskAllocation


def render_plan_view(path: str) -> None:
    st.header("📅 Execution Plan")

    # Load data
    try:
        tasks, settings = task_manager.load_data(path)
    except ValueError as exc:
        st.error(f"Failed to load tasks: {exc}")
        return

    today = date.today()
    result = scheduler.generate_plan(tasks, today, settings.available_hours_per_day)

    day_slots, overdue_tasks = result  # NamedTuple unpacking

    if not day_slots and not overdue_tasks:
        if not tasks:
            st.info("No tasks yet. Add tasks on the Tasks tab to generate a plan.")
        else:
            st.info(
                "No plan could be generated. "
                "Check that your available hours/day setting is greater than 0."
            )
        return

    st.caption(
        f"Plan generated for {len(day_slots)} day(s) • "
        f"{settings.available_hours_per_day:.1f}h available per day"
    )

    # Track cumulative hours assigned per task to compute Hours Remaining
    hours_assigned: dict[str, float] = {}

    for slot in day_slots:
        label = str(slot.date)
        if slot.has_deadline_miss:
            label += " ⚠ deadline miss"

        with st.expander(label, expanded=(slot.date == today)):
            if slot.has_deadline_miss:
                st.warning("⚠ One or more tasks will miss their deadline on this day.")

            rows = []
            for allocation in slot.allocations:
                task = allocation.task
                # Update running total for this task
                hours_assigned[task.id] = (
                    hours_assigned.get(task.id, 0.0) + allocation.hours_today
                )
                hours_remaining = task.estimated_effort_hours - hours_assigned[task.id]

                rows.append(
                    {
                        "Task": task.name,
                        "Course": task.course,
                        "Hours Today": round(allocation.hours_today, 2),
                        "Hours Remaining": round(max(0.0, hours_remaining), 2),
                        "Deadline": str(task.deadline),
                    }
                )

            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Overdue tasks section
    if overdue_tasks:
        st.divider()
        st.subheader("Overdue Tasks")
        for t in overdue_tasks:
            st.error(f"Overdue: '{t.name}' (due {t.deadline})")
