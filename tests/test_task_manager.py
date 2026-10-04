"""
tests/test_task_manager.py

Tests for core/task_manager.py CRUD and persistence operations.
All tests use pytest's tmp_path fixture for file isolation.
"""

import uuid
from datetime import date

import pytest

from core.task_manager import (
    Settings,
    Task,
    add_task,
    delete_task,
    load_data,
    save_settings,
    update_task,
)


def _make_task(**kwargs) -> Task:
    defaults = dict(
        id=uuid.uuid4().hex,
        name="Test Assignment",
        course="CS101",
        deadline=date(2025, 12, 31),
        estimated_effort_hours=3.0,
        priority="Medium",
        description="",
    )
    defaults.update(kwargs)
    return Task(**defaults)


def test_add_task_persists(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = _make_task(name="Homework 1")
    add_task(task, path)
    tasks, _ = load_data(path)
    assert len(tasks) == 1
    assert tasks[0].name == "Homework 1"
    assert tasks[0].id == task.id


def test_delete_task(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = _make_task()
    add_task(task, path)
    delete_task(task.id, path)
    tasks, _ = load_data(path)
    assert tasks == []


def test_update_task(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = _make_task(name="Original Name")
    add_task(task, path)
    updated = Task(
        id=task.id,
        name="Updated Name",
        course=task.course,
        deadline=task.deadline,
        estimated_effort_hours=task.estimated_effort_hours,
        priority=task.priority,
        description=task.description,
    )
    update_task(updated, path)
    tasks, _ = load_data(path)
    assert len(tasks) == 1
    assert tasks[0].name == "Updated Name"


def test_save_settings(tmp_path):
    path = str(tmp_path / "tasks.json")
    save_settings(Settings(available_hours_per_day=8.0), path)
    _, settings = load_data(path)
    assert settings.available_hours_per_day == 8.0


def test_add_task_invalid_name(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = _make_task(name="")
    with pytest.raises(ValueError, match="Task name is required"):
        add_task(task, path)


def test_add_task_invalid_effort(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = _make_task(estimated_effort_hours=0.0)
    with pytest.raises(ValueError, match="Effort must be > 0"):
        add_task(task, path)


def test_update_task_invalid_name(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = _make_task(name="Valid Name")
    add_task(task, path)
    invalid = Task(
        id=task.id,
        name="",
        course=task.course,
        deadline=task.deadline,
        estimated_effort_hours=task.estimated_effort_hours,
        priority=task.priority,
        description=task.description,
    )
    with pytest.raises(ValueError, match="Task name is required"):
        update_task(invalid, path)


def test_update_task_invalid_effort(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = _make_task(name="Valid Name")
    add_task(task, path)
    invalid = Task(
        id=task.id,
        name=task.name,
        course=task.course,
        deadline=task.deadline,
        estimated_effort_hours=0.0,
        priority=task.priority,
        description=task.description,
    )
    with pytest.raises(ValueError, match="Effort must be > 0"):
        update_task(invalid, path)


def test_missing_file_returns_empty(tmp_path):
    path = str(tmp_path / "nonexistent.json")
    tasks, settings = load_data(path)
    assert tasks == []
    assert settings.available_hours_per_day == Settings().available_hours_per_day


def test_malformed_json_raises(tmp_path):
    path = str(tmp_path / "bad.json")
    with open(path, "w") as f:
        f.write("not valid json {{{")
    with pytest.raises(ValueError, match="malformed"):
        load_data(path)
