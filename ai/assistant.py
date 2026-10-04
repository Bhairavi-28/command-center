"""
ai/assistant.py

OpenAI wrapper with graceful fallback.
The application remains fully functional when openai is not installed
or when OPENAI_API_KEY is not set.
"""

import json
import logging
import os
import uuid
from datetime import date, timedelta

from core.task_manager import Task
from core.workload import WorkloadMetrics

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import guard — lazy, so pytest collection never triggers a hanging import.
# The first call to ai_available() or _get_client() loads the module once.
# ---------------------------------------------------------------------------
_openai = None  # type: ignore[assignment]
_OPENAI_AVAILABLE: bool | None = None  # None = not yet attempted


def _try_import_openai() -> None:
    """Attempt to import openai exactly once. Sets module-level globals."""
    global _openai, _OPENAI_AVAILABLE  # noqa: PLW0603
    if _OPENAI_AVAILABLE is not None:
        return  # already attempted
    try:
        import openai as _oi  # type: ignore[import]
        _openai = _oi
        _OPENAI_AVAILABLE = True
    except Exception:  # noqa: BLE001 — broad: survive broken/incompatible installs
        _openai = None
        _OPENAI_AVAILABLE = False


def ai_available() -> bool:
    """Returns True only when openai is importable AND OPENAI_API_KEY is set."""
    _try_import_openai()
    return bool(_OPENAI_AVAILABLE) and bool(os.environ.get("OPENAI_API_KEY"))


def _get_client():
    """Returns a v1.x OpenAI client. Never call when ai_available() is False."""
    return _openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))  # type: ignore[union-attr]


def _dict_to_task(d: dict) -> Task:
    """
    Converts a raw AI response dict into a Task object.

    Expected AI JSON keys:
        name                  (str, required — raises ValueError if absent)
        course                (str, default "Unknown")
        deadline              ("YYYY-MM-DD" string, default today+7)
        estimated_effort_hours (float, default 1.0)
        priority              ("Low" | "Medium" | "High", default "Medium")

    Invalid deadline string falls back to today+7 days.
    """
    if "name" not in d or not d["name"]:
        raise ValueError("AI task dict missing required 'name' field")

    default_deadline = date.today() + timedelta(days=7)

    raw_deadline = d.get("deadline")
    if raw_deadline:
        try:
            deadline = date.fromisoformat(str(raw_deadline))
        except (ValueError, TypeError):
            logger.warning("Could not parse deadline %r; using today+7.", raw_deadline)
            deadline = default_deadline
    else:
        deadline = default_deadline

    priority = d.get("priority", "Medium")
    if priority not in {"Low", "Medium", "High"}:
        priority = "Medium"

    return Task(
        id=uuid.uuid4().hex,
        name=str(d["name"]),
        course=str(d.get("course", "Unknown")),
        deadline=deadline,
        estimated_effort_hours=float(d.get("estimated_effort_hours", 1.0)),
        priority=priority,
        description="",
    )


def extract_tasks(text: str) -> list[Task]:
    """
    Sends text to GPT-4o-mini and asks it to extract a JSON array of tasks.
    Returns a list of Task objects, or [] on any failure.
    Never raises to caller.
    """
    if not ai_available():
        return []

    prompt = (
        "You are a helpful academic assistant. "
        "Extract academic tasks from the following text and return ONLY a JSON array. "
        "Each element must have these keys: "
        "\"name\" (string), \"course\" (string), \"deadline\" (YYYY-MM-DD string), "
        "\"estimated_effort_hours\" (number), \"priority\" (\"Low\", \"Medium\", or \"High\"). "
        "If information is missing, make a reasonable guess. "
        "Return ONLY the JSON array, no explanation.\n\n"
        f"Text:\n{text}"
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        raw_list = json.loads(content)
        if not isinstance(raw_list, list):
            logger.warning("AI response was not a JSON array; got %s", type(raw_list))
            return []

        tasks: list[Task] = []
        for item in raw_list:
            try:
                tasks.append(_dict_to_task(item))
            except (ValueError, KeyError, TypeError) as exc:
                logger.warning("Skipping invalid AI task dict %r: %s", item, exc)

        return tasks

    except json.JSONDecodeError as exc:
        logger.warning("JSON decode error parsing AI response: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001
        if _openai and isinstance(exc, _openai.APIConnectionError):
            logger.warning("OpenAI connection error: %s", exc)
        elif _openai and isinstance(exc, _openai.AuthenticationError):
            logger.error("OpenAI authentication error: %s", exc)
        elif _openai and isinstance(exc, _openai.RateLimitError):
            logger.warning("OpenAI rate limit: %s", exc)
        else:
            logger.exception("Unexpected error calling extract_tasks: %s", exc)
        return []


def explain_risks(tasks: list[Task], metrics: WorkloadMetrics | None) -> str:
    """
    Sends a summary of tasks and metrics to GPT-4o-mini and returns a plain-English
    narration of the workload risks. Returns "" on any failure. Never raises to caller.
    """
    if not ai_available():
        return ""

    try:
        # Build a text summary to send
        lines = ["Academic Workload Summary:", ""]
        if metrics is not None:
            lines.append(f"Total tasks: {metrics.total_tasks}")
            lines.append(f"Total required hours: {metrics.total_required_hours:.1f}h")
            lines.append(f"Available hours: {metrics.available_hours:.1f}h")
            lines.append(f"Surplus/deficit: {metrics.surplus_deficit:.1f}h")
            lines.append(f"Overloaded: {'Yes' if metrics.is_overloaded else 'No'}")
            collision_count = sum(1 for c in metrics.collisions if c.is_collision)
            lines.append(f"Tasks with deadline collisions: {collision_count}")
            lines.append("")

        if tasks:
            lines.append("Tasks (by priority/score):")
            for task in tasks:
                lines.append(
                    f"  - {task.name} ({task.course}): due {task.deadline}, "
                    f"{task.estimated_effort_hours}h, priority={task.priority}"
                )

        summary_text = "\n".join(lines)

        prompt = (
            "You are an academic workload advisor. "
            "Based on the following student workload data, provide a brief, practical "
            "plain-English explanation of the key risks and recommendations. "
            "Be concise (3-5 sentences).\n\n"
            f"{summary_text}"
        )

        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return (response.choices[0].message.content or "").strip()

    except Exception as exc:  # noqa: BLE001
        if _openai and isinstance(exc, _openai.APIConnectionError):
            logger.warning("OpenAI connection error in explain_risks: %s", exc)
        elif _openai and isinstance(exc, _openai.AuthenticationError):
            logger.error("OpenAI authentication error in explain_risks: %s", exc)
        elif _openai and isinstance(exc, _openai.RateLimitError):
            logger.warning("OpenAI rate limit in explain_risks: %s", exc)
        else:
            logger.exception("Unexpected error in explain_risks: %s", exc)
        return ""
