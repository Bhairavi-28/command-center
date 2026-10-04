"""
ui/ai_panel.py

AI Assistant tab renderer.
Imports ai/assistant.py and delegates all AI logic there.
No metric or scheduling logic in this module.
"""

from datetime import date

import streamlit as st

from ai.assistant import ai_available, explain_risks, extract_tasks
from core import task_manager, workload


def render_ai_panel(path: str) -> None:
    st.header("🤖 AI Assistant")

    # Guard: only render if AI is available
    if not ai_available():
        st.info("AI features are disabled — set OPENAI_API_KEY to enable.")
        return

    # Load current data for context
    try:
        tasks, settings = task_manager.load_data(path)
    except ValueError as exc:
        st.error(f"Failed to load tasks: {exc}")
        return

    today = date.today()
    metrics = workload.compute_metrics(tasks, today, settings.available_hours_per_day)

    # --- Section 1: Extract Tasks from Text ---
    with st.expander("📋 Extract Tasks from Text", expanded=True):
        st.write(
            "Paste a syllabus excerpt, email, or notes and the AI will extract "
            "academic tasks for you to review before adding."
        )
        raw_text = st.text_area(
            "Paste your text here",
            height=150,
            key="ai_extract_text",
            placeholder="e.g. 'Assignment 2 due Friday, 5 hours, hard. Final exam in 3 weeks.'",
        )

        if st.button("🔍 Extract Tasks", key="ai_extract_btn"):
            if raw_text.strip():
                with st.spinner("Extracting tasks…"):
                    suggestions = extract_tasks(raw_text)
                if suggestions:
                    st.session_state["ai_suggestions"] = suggestions
                    st.success(f"Found {len(suggestions)} task(s). Review below.")
                else:
                    st.warning("AI request failed or no tasks found; please try again.")
                    st.session_state.pop("ai_suggestions", None)
            else:
                st.info("Please enter some text first.")

        # Show preview and confirm button if we have suggestions
        suggestions = st.session_state.get("ai_suggestions", [])
        if suggestions:
            st.write("**Suggested Tasks (preview):**")
            preview_rows = [
                {
                    "Name": t.name,
                    "Course": t.course,
                    "Deadline": str(t.deadline),
                    "Effort (h)": t.estimated_effort_hours,
                    "Priority": t.priority,
                }
                for t in suggestions
            ]
            import pandas as pd  # local import to keep module-level imports clean
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)

            if st.button("✅ Add these tasks", key="ai_add_btn"):
                added = 0
                for task in suggestions:
                    try:
                        task_manager.add_task(task, path)
                        added += 1
                    except ValueError as exc:
                        st.error(f"Could not add '{task.name}': {exc}")
                st.session_state.pop("ai_suggestions", None)
                if added:
                    st.success(f"Added {added} task(s) successfully.")
                    st.rerun()

    # --- Section 2: Explain Workload Risks ---
    with st.expander("💡 Explain Workload Risks", expanded=False):
        st.write(
            "Get a plain-English explanation of your current workload risks and "
            "recommendations from the AI."
        )
        if st.button("🔍 Explain Risks", key="ai_explain_btn"):
            with st.spinner("Analyzing workload…"):
                explanation = explain_risks(tasks, metrics)
            if explanation:
                st.write(explanation)
            else:
                st.warning("AI request failed; please try again.")
