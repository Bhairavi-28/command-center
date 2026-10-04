"""
ui/tasks.py

Task list display (FR-1.5, FR-3.2) and Add/Edit/Delete form (FR-1.1, FR-1.2, FR-1.3).
All calculations delegated to core/ — no scoring or metric logic here.
"""

import uuid
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import scheduler, task_manager, workload
from core.task_manager import Task


def render_tasks(path: str) -> None:
    st.header("📝 Tasks")

    # --- Load data ---
    try:
        tasks, settings = task_manager.load_data(path)
    except ValueError as exc:
        st.error(f"Failed to load tasks: {exc}")
        return

    today = date.today()
    scored = scheduler.compute_scores(tasks, today)
    metrics = workload.compute_metrics(tasks, today, settings.available_hours_per_day)
    collision_map = {c.task.id: c.is_collision for c in metrics.collisions}

    # --- Task list ---
    st.subheader("All Tasks")

    if not tasks:
        st.info("No tasks yet. Use the form below to add your first task.")
    else:
        # Build scored lookup by task id
        score_map = {s["task"].id: s for s in scored}

        # Render a header row and individual task rows with Edit/Delete buttons
        for task in tasks:
            s = score_map.get(task.id, {})
            score_val = s.get("score", 0.0)
            pw = s.get("priority_weight", 0)
            un = s.get("urgency_score_normalized", 0.0)
            en = s.get("effort_normalized", 0.0)
            has_collision = collision_map.get(task.id, False)

            with st.container():
                cols = st.columns([3, 2, 2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1, 1, 1])
                cols[0].write(f"**{task.name}**")
                cols[1].write(task.course)
                cols[2].write(str(task.deadline))
                cols[3].write(f"{task.estimated_effort_hours}h")
                cols[4].write(task.priority)
                cols[5].write(f"{score_val:.3f}")
                cols[6].write(str(pw))
                cols[7].write(f"{un:.3f}")
                cols[8].write(f"{en:.3f}")
                cols[9].write("⚠" if has_collision else "✓")

                if cols[10].button("Edit", key=f"edit_{task.id}"):
                    st.session_state["editing_task_id"] = task.id
                    st.rerun()

                if cols[11].button("Delete", key=f"del_{task.id}"):
                    try:
                        task_manager.delete_task(task.id, path)
                        st.rerun()
                    except KeyError as exc:
                        st.error(f"Delete failed: {exc}")

        # Show column header legend
        st.caption(
            "Columns: Name | Course | Deadline | Effort | Priority | Score | "
            "Priority Weight | Urgency (norm) | Effort (norm) | Collision"
        )

    st.divider()

    # --- Add / Edit form ---
    editing_task_id: str | None = st.session_state.get("editing_task_id")
    editing_task: Task | None = None

    if editing_task_id:
        editing_task = next((t for t in tasks if t.id == editing_task_id), None)
        if editing_task is None:
            # Task was deleted externally; clear state
            st.session_state.pop("editing_task_id", None)
            editing_task_id = None

    form_title = "Edit Task" if editing_task_id else "Add New Task"
    st.subheader(form_title)

    with st.form(key="task_form", clear_on_submit=True):
        name = st.text_input(
            "Task Name *",
            value=editing_task.name if editing_task else "",
        )
        course = st.text_input(
            "Course / Category *",
            value=editing_task.course if editing_task else "",
        )
        deadline = st.date_input(
            "Deadline *",
            value=editing_task.deadline if editing_task else today + timedelta(days=7),
            min_value=today,
        )
        effort = st.number_input(
            "Estimated Effort (hours) *",
            min_value=0.1,
            max_value=500.0,
            value=float(editing_task.estimated_effort_hours) if editing_task else 1.0,
            step=0.5,
        )
        priority_options = ["Low", "Medium", "High"]
        priority_default_idx = (
            priority_options.index(editing_task.priority)
            if editing_task and editing_task.priority in priority_options
            else 1
        )
        priority = st.selectbox(
            "Priority *",
            options=priority_options,
            index=priority_default_idx,
        )
        description = st.text_area(
            "Description (optional)",
            value=editing_task.description if editing_task else "",
        )

        # Button row
        if editing_task_id:
            submit_col, cancel_col = st.columns([1, 1])
            submit_btn = submit_col.form_submit_button("💾 Save Changes")
            cancel_btn = cancel_col.form_submit_button("✖ Cancel")
        else:
            submit_btn = st.form_submit_button("➕ Add Task")
            cancel_btn = False

    # Handle Cancel (must be outside the form for session_state mutation)
    if cancel_btn:
        st.session_state.pop("editing_task_id", None)
        st.rerun()

    if submit_btn:
        task_obj = Task(
            id=editing_task_id if editing_task_id else uuid.uuid4().hex,
            name=name,
            course=course,
            deadline=deadline,
            estimated_effort_hours=effort,
            priority=priority,
            description=description,
        )
        try:
            if editing_task_id:
                task_manager.update_task(task_obj, path)
            else:
                task_manager.add_task(task_obj, path)
            st.success("Task saved.")
            st.session_state.pop("editing_task_id", None)
            st.rerun()
        except (ValueError, KeyError) as exc:
            st.error(str(exc))
