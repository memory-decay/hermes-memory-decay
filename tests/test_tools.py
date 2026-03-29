"""Tests for tool handlers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def test_handle_memory_search_empty():
    from hermes_memory_decay.tools import handle_memory_search

    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}

    with patch("hermes_memory_decay.tools._get_client", return_value=mock_client):
        result = json.loads(handle_memory_search({"query": "test"}))
        assert result["results"] == []
        assert result["message"] == "No memories found."


def test_handle_memory_search_with_results():
    from hermes_memory_decay.tools import handle_memory_search

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "id": "mem_1",
                "text": "some memory",
                "score": 0.85,
                "storage_score": 0.9,
                "category": "fact",
                "speaker": "user",
            },
            {
                "id": "mem_2",
                "text": "old memory",
                "score": 0.4,
                "storage_score": 0.2,
                "category": "",
                "speaker": "",
            },
        ]
    }

    with patch("hermes_memory_decay.tools._get_client", return_value=mock_client):
        result = json.loads(handle_memory_search({"query": "test"}))
        assert result["count"] == 2
        assert result["results"][0]["freshness"] == "fresh"
        assert result["results"][1]["freshness"] == "stale"


def test_handle_memory_store_success():
    from hermes_memory_decay.tools import handle_memory_store

    mock_client = MagicMock()
    mock_client.store.return_value = {"id": "mem_abc", "text": "hello", "tick": 5}

    with patch("hermes_memory_decay.tools._get_client", return_value=mock_client):
        result = json.loads(handle_memory_store({"text": "hello"}))
        assert result["stored"] is True
        assert result["id"] == "mem_abc"


def test_handle_memory_store_error():
    from hermes_memory_decay.tools import handle_memory_store

    with patch(
        "hermes_memory_decay.tools._get_client",
        side_effect=RuntimeError("server down"),
    ):
        result = json.loads(handle_memory_store({"text": "hello"}))
        assert "error" in result


def test_handle_memory_store_batch_success():
    from hermes_memory_decay.tools import handle_memory_store_batch

    mock_client = MagicMock()
    mock_client.store_batch.return_value = {"ids": ["mem_1", "mem_2"], "count": 2}

    with patch("hermes_memory_decay.tools._get_client", return_value=mock_client):
        result = json.loads(handle_memory_store_batch({
            "items": [{"text": "one"}, {"text": "two"}]
        }))
        assert result["stored"] is True
        assert result["count"] == 2


def test_handle_memory_forget_success():
    from hermes_memory_decay.tools import handle_memory_forget

    mock_client = MagicMock()
    mock_client.forget.return_value = {"deleted": "mem_abc"}

    with patch("hermes_memory_decay.tools._get_client", return_value=mock_client):
        result = json.loads(handle_memory_forget({"memory_id": "mem_abc"}))
        assert result["deleted"] == "mem_abc"


def test_handle_memory_status_success():
    from hermes_memory_decay.tools import handle_memory_status

    mock_client = MagicMock()
    mock_client.health.return_value = {"status": "ok", "current_tick": 10}
    mock_client.stats.return_value = {"num_memories": 42, "last_tick_time": 1000.0}

    with patch("hermes_memory_decay.tools._get_client", return_value=mock_client):
        result = json.loads(handle_memory_status({}))
        assert result["status"] == "ok"
        assert result["num_memories"] == 42
        assert result["current_tick"] == 10


def test_handle_memory_status_error():
    from hermes_memory_decay.tools import handle_memory_status

    with patch(
        "hermes_memory_decay.tools._get_client",
        side_effect=RuntimeError("server unreachable"),
    ):
        result = json.loads(handle_memory_status({}))
        assert "error" in result
        assert result["status"] == "unreachable"
