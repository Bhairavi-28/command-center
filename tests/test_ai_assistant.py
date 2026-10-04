"""
tests/test_ai_assistant.py

Tests for ai/assistant.py — graceful fallback behavior.
Never makes real API calls. Works even when openai is not installed or broken.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

import ai.assistant as assistant_module
from ai.assistant import ai_available, explain_risks, extract_tasks


def test_ai_unavailable_without_key(monkeypatch):
    """Without OPENAI_API_KEY set, ai_available() must return False."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Patch _OPENAI_AVAILABLE to True so the only gate checked is the missing key.
    with patch.object(assistant_module, "_OPENAI_AVAILABLE", True), \
         patch.object(assistant_module, "_try_import_openai", return_value=None):
        assert ai_available() is False


def test_extract_tasks_returns_empty_on_failure(monkeypatch):
    """
    With OPENAI_API_KEY set but the API call raising an exception,
    extract_tasks must return [] without raising.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("network error")

    with patch.object(assistant_module, "_OPENAI_AVAILABLE", True), \
         patch.object(assistant_module, "_try_import_openai", return_value=None), \
         patch("ai.assistant._get_client", return_value=mock_client):
        result = extract_tasks("Math exam on Friday, 5 hours of study needed")

    assert result == []


def test_explain_risks_returns_empty_on_failure(monkeypatch):
    """
    With OPENAI_API_KEY set but the API call raising an exception,
    explain_risks must return "" without raising.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("network error")

    with patch.object(assistant_module, "_OPENAI_AVAILABLE", True), \
         patch.object(assistant_module, "_try_import_openai", return_value=None), \
         patch("ai.assistant._get_client", return_value=mock_client):
        result = explain_risks(tasks=[], metrics=None)

    assert result == ""
