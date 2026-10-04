"""
tests/test_ai_assistant.py

Tests for ai/assistant.py — graceful fallback behavior.
Relies on openai being importable (installed from requirements-dev.txt).
Never makes real API calls.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

import ai.assistant as assistant_module
from ai.assistant import ai_available, explain_risks, extract_tasks


def test_ai_unavailable_without_key(monkeypatch):
    """Without OPENAI_API_KEY set, ai_available() must return False."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ai_available() is False


def test_extract_tasks_returns_empty_on_failure(monkeypatch):
    """
    With OPENAI_API_KEY set but the API call raising an exception,
    extract_tasks must return [] without raising.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("ai.assistant._openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("network error")

        result = extract_tasks("Math exam on Friday, 5 hours of study needed")
    assert result == []


def test_explain_risks_returns_empty_on_failure(monkeypatch):
    """
    With OPENAI_API_KEY set but the API call raising an exception,
    explain_risks must return "" without raising.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("ai.assistant._openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("network error")

        result = explain_risks(tasks=[], metrics=None)
    assert result == ""
