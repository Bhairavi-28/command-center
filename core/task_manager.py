"""
core/task_manager.py

Defines Task and Settings dataclasses plus all CRUD and JSON persistence operations.
This is the sole canonical home for both dataclasses. No core/models.py exists.
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Task:
    id: str
    name: str
    course: str
    deadline: date
    estimated_effort_hours: float
    priority: str
    description: str = ""


@dataclass
class Settings:
    available_hours_per_day: float = 6.0


_VALID_PRIORITIES = {"Low", "Medium", "High"}


def _task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "name": task.name,
        "course": task.course,
        "deadline": task.deadline.isoformat(),
        "estimated_effort_hours": task.estimated_effort_hours,
        "priority": task.priority,
        "description": task.description,
    }


def _dict_to_task(d: dict) -> Task:
    return Task(
        id=d.get("id", uuid.uuid4().hex),
        name=d.get("name", ""),
        course=d.get("course", ""),
        deadline=date.fromisoformat(d["deadline"]),
        estimated_effort_hours=float(d.get("estimated_effort_hours", 1.0)),
        priority=d.get("priority", "Medium"),
        description=d.get("description", ""),
    )


def load_data(path: str) -> tuple[list[Task], Settings]:
    """
    Reads the JSON file. Returns ([], Settings()) if the file does not exist.
    Raises ValueError with a descriptive message if the file contains malformed JSON.
    Missing optional fields are filled with defaults.
    """
    if not os.path.exists(path):
        return ([], Settings())

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"tasks.json is malformed: {exc}") from exc

    tasks_raw = raw.get("tasks", [])
    tasks = []
    for d in tasks_raw:
        tasks.append(_dict_to_task(d))

    settings_raw = raw.get("settings", {})
    settings = Settings(
        available_hours_per_day=float(
            settings_raw.get("available_hours_per_day", 6.0)
        )
    )

    return tasks, settings


def save_data(tasks: list[Task], settings: Settings, path: str) -> None:
    """
    Serializes and writes atomically: write to path+".tmp", then rename with os.replace.
    """
    data = {
        "tasks": [_task_to_dict(t) for t in tasks],
        "settings": {"available_hours_per_day": settings.available_hours_per_day},
    }
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def _validate_task(task: Task) -> None:
    if not task.name or not task.name.strip():
        raise ValueError("Task name is required")
    if not task.course or not task.course.strip():
        raise ValueError("Course is required")
    if task.estimated_effort_hours <= 0:
        raise ValueError("Effort must be > 0")
    if task.priority not in _VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {task.priority!r}. Must be one of {_VALID_PRIORITIES}")


def add_task(task: Task, path: str) -> None:
    """
    Validates the task, loads current data, appends the task, saves.
    Raises ValueError on validation failure.
    """
    _validate_task(task)
    tasks, settings = load_data(path)
    tasks.append(task)
    save_data(tasks, settings, path)


def update_task(task: Task, path: str) -> None:
    """
    Validates the task, loads current data, finds task by id, replaces in-place, saves.
    Raises ValueError on validation failure.
    Raises KeyError if the id is not found.
    """
    _validate_task(task)
    tasks, settings = load_data(path)
    for i, t in enumerate(tasks):
        if t.id == task.id:
            tasks[i] = task
            save_data(tasks, settings, path)
            return
    raise KeyError(f"Task with id {task.id!r} not found")


def delete_task(task_id: str, path: str) -> None:
    """
    Loads current data, removes task by id, saves.
    Raises KeyError if not found.
    """
    tasks, settings = load_data(path)
    new_tasks = [t for t in tasks if t.id != task_id]
    if len(new_tasks) == len(tasks):
        raise KeyError(f"Task with id {task_id!r} not found")
    save_data(new_tasks, settings, path)


def save_settings(settings: Settings, path: str) -> None:
    """
    Loads current data (tasks unchanged), replaces settings, saves.
    """
    tasks, _ = load_data(path)
    save_data(tasks, settings, path)
