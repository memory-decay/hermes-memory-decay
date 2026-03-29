"""Tests for MemoryDecayHTTPClient."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

from hermes_memory_decay.http_client import MemoryDecayHTTPClient


def _mock_response(data: dict) -> MagicMock:
    """Create a mock urllib response."""
    mock = MagicMock()
    mock.read.return_value = json.dumps(data).encode("utf-8")
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_health_success():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({"status": "ok", "current_tick": 42})

    with patch("urllib.request.urlopen", return_value=mock):
        result = client.health()
        assert result["status"] == "ok"
        assert result["current_tick"] == 42


def test_stats_success():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({"num_memories": 10, "current_tick": 5, "last_tick_time": 1000.0})

    with patch("urllib.request.urlopen", return_value=mock):
        result = client.stats()
        assert result["num_memories"] == 10


def test_store_sends_correct_payload():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({"id": "mem_abc", "text": "hello", "tick": 0})

    with patch("urllib.request.urlopen", return_value=mock) as mock_open:
        result = client.store(text="hello", importance=0.9, category="test")
        assert result["id"] == "mem_abc"
        # Verify request body
        call_args = mock_open.call_args
        req = call_args[0][0]
        body = json.loads(req.data)
        assert body["text"] == "hello"
        assert body["importance"] == 0.9
        assert body["category"] == "test"


def test_store_with_associations():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({"id": "mem_xyz", "text": "linked", "tick": 1})

    with patch("urllib.request.urlopen", return_value=mock) as mock_open:
        result = client.store(
            text="linked",
            associations=["mem_abc", "mem_def"],
            speaker="user",
        )
        assert result["id"] == "mem_xyz"
        req = mock_open.call_args[0][0]
        body = json.loads(req.data)
        assert body["associations"] == ["mem_abc", "mem_def"]
        assert body["speaker"] == "user"


def test_store_batch():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({"ids": ["mem_1", "mem_2"], "count": 2, "tick": 0})

    with patch("urllib.request.urlopen", return_value=mock):
        result = client.store_batch([
            {"text": "one", "importance": 0.5},
            {"text": "two", "importance": 0.8},
        ])
        assert result["count"] == 2


def test_search_returns_results():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({
        "results": [
            {
                "id": "mem_1", "text": "test", "score": 0.95,
                "storage_score": 0.8, "retrieval_score": 0.9,
                "category": "", "created_tick": 0,
            }
        ]
    })

    with patch("urllib.request.urlopen", return_value=mock):
        result = client.search(query="test", top_k=3)
        assert len(result["results"]) == 1
        assert result["results"][0]["score"] == 0.95


def test_forget_success():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({"deleted": "mem_abc"})

    with patch("urllib.request.urlopen", return_value=mock):
        result = client.forget("mem_abc")
        assert result["deleted"] == "mem_abc"


def test_auto_tick():
    client = MemoryDecayHTTPClient(port=9999)
    mock = _mock_response({"ticks_applied": 3, "current_tick": 15, "elapsed_seconds": 10800.0})

    with patch("urllib.request.urlopen", return_value=mock):
        result = client.auto_tick()
        assert result["ticks_applied"] == 3


def test_connection_error_raises():
    client = MemoryDecayHTTPClient(port=9999)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        try:
            client.health()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "Connection" in str(e)


def test_http_error_raises():
    client = MemoryDecayHTTPClient(port=9999)
    error = urllib.error.HTTPError(
        url="http://127.0.0.1:9999/health",
        code=500,
        msg="Internal Server Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    error.read = lambda: b"server error details"  # type: ignore[assignment]

    with patch("urllib.request.urlopen", side_effect=error):
        try:
            client.health()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "500" in str(e)
            assert "server error details" in str(e)
