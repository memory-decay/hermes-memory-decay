"""Tests for MemoryDecayMemoryProvider."""

import json
import pytest
from unittest.mock import MagicMock, patch


class TestMemoryDecayMemoryProvider:
    """Test suite for MemoryDecayMemoryProvider."""

    def test_name_property(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        assert provider.name == "hermes-memory-decay"

    def test_is_available_returns_false_when_config_missing(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        with patch.dict("os.environ", {"HERMES_HOME": "/nonexistent_hermes_home"}):
            assert provider.is_available() is False

    def test_is_available_returns_true_when_config_exists(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        with patch.dict("os.environ", {"HERMES_HOME": "/tmp"}, clear=False):
            with patch("pathlib.Path.exists", return_value=True):
                assert provider.is_available() is True

    def test_get_tool_schemas_returns_5_tools(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        schemas = provider.get_tool_schemas()
        assert len(schemas) == 5
        tool_names = {s["name"] for s in schemas}
        assert tool_names == {
            "memory_search",
            "memory_store",
            "memory_store_batch",
            "memory_forget",
            "memory_status",
        }

    def test_handle_tool_call_unknown_tool(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        result = json.loads(provider.handle_tool_call("unknown_tool", {}))
        assert "error" in result

    def test_handle_tool_call_without_server_returns_error(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        result = json.loads(provider.handle_tool_call("memory_search", {"query": "test"}))
        assert "error" in result

    @patch("hermes_memory_decay.server_manager.ServerManager")
    def test_initialize_starts_server(self, mock_sm_class):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

        mock_sm = MagicMock()
        mock_sm_class.return_value = mock_sm

        provider = MemoryDecayMemoryProvider()
        with patch("hermes_memory_decay.config.load_config") as mock_cfg:
            mock_cfg.return_value = {
                "memory_decay_path": "/fake/path",
                "port": 8100,
                "db_path": "/tmp/test.db",
            }
            with patch("pathlib.Path.is_dir", return_value=True):
                provider.initialize("test-session", hermes_home="/tmp")

        mock_sm.ensure_running.assert_called_once()

    def test_sync_turn_is_nonblocking(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        from unittest.mock import MagicMock

        provider = MemoryDecayMemoryProvider()
        mock_client = MagicMock()
        mock_client.store.return_value = {}
        mock_client.store_batch.return_value = {}

        provider._server_manager = MagicMock()
        provider._server_manager.get_client.return_value = mock_client

        # First call starts a thread
        provider.sync_turn("user message", "assistant message")
        assert provider._sync_thread is not None
        assert provider._sync_thread.daemon is True

    def test_get_config_schema_returns_expected_fields(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        schema = provider.get_config_schema()
        keys = {field["key"] for field in schema}
        assert "memory_decay_path" in keys
        assert "port" in keys
        assert "embedding_provider" in keys

    def test_system_prompt_block_when_running(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

        provider = MemoryDecayMemoryProvider()
        provider._server_manager = MagicMock()
        provider._server_manager.is_running.return_value = True

        block = provider.system_prompt_block()
        assert "hermes-memory-decay" in block
        assert "memory_store" in block

    def test_system_prompt_block_when_stopped(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

        provider = MemoryDecayMemoryProvider()
        provider._server_manager = None

        block = provider.system_prompt_block()
        assert block == ""

    def test_prefetch_returns_empty_when_no_query(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

        provider = MemoryDecayMemoryProvider()
        provider._server_manager = MagicMock()
        provider._server_manager.is_running.return_value = True

        result = provider.prefetch("")
        assert result == ""

    def test_on_memory_write_ignores_remove_action(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

        provider = MemoryDecayMemoryProvider()
        provider._server_manager = MagicMock()
        # Should not raise, just ignore
        provider.on_memory_write("remove", "memory", "some content")
