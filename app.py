"""
app.py

Streamlit entry point for Command Center.
Handles sidebar settings and tab wiring only — no business logic here.
"""

import os

import streamlit as st

from ai.assistant import ai_available
from core.task_manager import Settings, load_data, save_settings
from ui.ai_panel import render_ai_panel
from ui.dashboard import render_dashboard
from ui.plan_view import render_plan_view
from ui.tasks import render_tasks

st.set_page_config(page_title="Command Center", layout="wide")

# Settings sidebar — always visible across all tabs (FR-7.1)
path = os.environ.get("TASKS_FILE", "tasks.json")
try:
    _, settings = load_data(path)
except ValueError as exc:
    st.sidebar.error(f"Data file error: {exc}")
    settings = Settings()

new_hours = st.sidebar.number_input(
    "Available hours/day",
    min_value=0.5,
    max_value=24.0,
    value=settings.available_hours_per_day,
    step=0.5,
)
if new_hours != settings.available_hours_per_day:
    save_settings(Settings(available_hours_per_day=new_hours), path)
    st.rerun()

st.sidebar.caption(
    "Command Center — AI-assisted academic workload optimizer"
)

# Tab wiring
tab_labels = ["📊 Dashboard", "📝 Tasks", "📅 Execution Plan"]
if ai_available():
    tab_labels.append("🤖 AI Assistant")

tab_objects = st.tabs(tab_labels)

with tab_objects[0]:
    render_dashboard(path)
with tab_objects[1]:
    render_tasks(path)
with tab_objects[2]:
    render_plan_view(path)
if ai_available():
    with tab_objects[3]:
        render_ai_panel(path)
