"""
ui/dashboard.py

Renders the Dashboard tab.
Imports from core/ only — no scheduling or metric calculation logic here.
"""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from core import task_manager, workload


def render_dashboard(path: str) -> None:
    st.header("📊 Dashboard")

    # Load data and compute metrics
    try:
        tasks, settings = task_manager.load_data(path)
    except ValueError as exc:
        st.error(f"Failed to load tasks: {exc}")
        return

    metrics = workload.compute_metrics(tasks, date.today(), settings.available_hours_per_day)

    # --- Four metric tiles ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tasks", metrics.total_tasks)
    col2.metric("Required Hours", f"{metrics.total_required_hours:.1f}h")
    col3.metric("Available Hours", f"{metrics.available_hours:.1f}h")

    sd = metrics.surplus_deficit
    col4.metric(
        "Surplus / Deficit",
        f"{sd:+.1f}h",
        delta=f"{sd:+.1f}h",
        delta_color="normal",  # green when positive, red when negative
    )

    # --- Overload warning ---
    if metrics.is_overloaded:
        st.error(
            f"⚠ Workload overload: you need {abs(sd):.1f} more hours than available."
        )

    # --- Per-task collision warnings (independent of overload) ---
    for c in metrics.collisions:
        if c.is_collision:
            st.warning(
                f"⚠ Collision: '{c.task.name}' needs {c.task.estimated_effort_hours}h "
                f"but only {c.hours_available_before_deadline}h available before deadline."
            )

    st.divider()

    # --- Upcoming deadlines list (FR-2.2) ---
    st.subheader("Upcoming Deadlines")
    if metrics.upcoming_deadlines:
        deadline_rows = [
            {
                "Task": t.name,
                "Course": t.course,
                "Deadline": str(t.deadline),
                "Effort (h)": t.estimated_effort_hours,
                "Priority": t.priority,
            }
            for t in metrics.upcoming_deadlines
        ]
        st.table(pd.DataFrame(deadline_rows))
    else:
        st.info("No upcoming deadlines.")

    if not tasks:
        st.info("Add some tasks to see charts.")
        return

    st.divider()

    # --- Hours per course bar chart (FR-2.4) ---
    st.subheader("Hours by Course")
    course_df = (
        pd.DataFrame(
            [{"Course": t.course, "Hours": t.estimated_effort_hours} for t in tasks]
        )
        .groupby("Course", as_index=False)["Hours"]
        .sum()
    )
    fig_bar = px.bar(
        course_df,
        x="Course",
        y="Hours",
        title="Total Estimated Hours per Course",
        color="Course",
        labels={"Hours": "Estimated Hours"},
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Gantt-style deadline timeline (FR-2.4) ---
    st.subheader("Task Deadline Timeline")
    today_str = str(date.today())
    gantt_rows = [
        {
            "Task": t.name,
            "Course": t.course,
            "Start": today_str,
            "Finish": str(t.deadline),
            "Priority": t.priority,
        }
        for t in tasks
    ]
    gantt_df = pd.DataFrame(gantt_rows)
    # Ensure Finish >= Start for plotly (past deadlines would break timeline)
    gantt_df["Finish"] = gantt_df[["Start", "Finish"]].max(axis=1)
    fig_gantt = px.timeline(
        gantt_df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Priority",
        title="Task Deadlines (Today → Deadline)",
        labels={"Task": "Task", "Start": "Start", "Finish": "Deadline"},
        color_discrete_map={"High": "#e74c3c", "Medium": "#f39c12", "Low": "#2ecc71"},
    )
    fig_gantt.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_gantt, use_container_width=True)
