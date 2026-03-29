"""Tests for ServerManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hermes_memory_decay.server_manager import ServerManager


def _make_config(**overrides) -> dict:
    config = {
        "python_path": "python3",
        "memory_decay_path": "/tmp/memory-decay-core",
        "port": 9999,
        "db_path": "/tmp/test.db",
        "embedding_provider": "local",
        "embedding_model": None,
        "embedding_api_key_env": None,
        "embedding_dim": None,
        "experiment_dir": None,
        "tick_interval_seconds": 3600,
        "max_restarts": 2,
        "server_startup_timeout_ms": 2000,
    }
    config.update(overrides)
    return config


def test_is_running_false_initially():
    mgr = ServerManager(_make_config())
    assert not mgr.is_running()


def test_get_client_returns_client():
    mgr = ServerManager(_make_config())
    client = mgr.get_client()
    assert client is not None
    assert client._base_url == "http://127.0.0.1:9999"


def test_ensure_running_starts_server():
    mgr = ServerManager(_make_config())
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.stderr = MagicMock()
    mock_proc.stderr.readline = MagicMock(return_value=b"")

    with patch("subprocess.Popen", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True), \
         patch.object(mgr._client, "health", return_value={"status": "ok"}):
        mgr.ensure_running()
        assert mgr.is_running()


def test_ensure_running_fails_without_path():
    mgr = ServerManager(_make_config(memory_decay_path=""))
    try:
        mgr.ensure_running()
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "memory_decay_path is not configured" in str(e)


def test_ensure_running_fails_if_path_missing():
    mgr = ServerManager(_make_config(memory_decay_path="/nonexistent/path"))
    try:
        mgr.ensure_running()
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "does not exist" in str(e)


def test_ensure_running_skips_if_healthy():
    mgr = ServerManager(_make_config())
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mgr._process = mock_proc

    with patch.object(mgr._client, "health", return_value={"status": "ok"}):
        mgr.ensure_running()
        # Should not have called Popen since already healthy
        assert mgr._process is mock_proc


def test_stop_sends_sigterm():
    mgr = ServerManager(_make_config())
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mgr._process = mock_proc

    mgr.stop()
    mock_proc.send_signal.assert_called()
    assert mgr._process is None


def test_stop_when_not_running():
    mgr = ServerManager(_make_config())
    # Should not raise
    mgr.stop()
    assert mgr._process is None
