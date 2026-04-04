# hermes-memory-decay MemoryProvider ABC Implementation Plan

> **Worker note:** Execute this plan task-by-task. Each step uses checkbox (`- [ ]`) syntax for progress tracking.

**Goal:** Re-architect hermes-memory-decay as an official `MemoryProvider` ABC implementation (B pattern: external HTTP server + HTTP client), compatible with `hermes memory setup` wizard and `MemoryManager` lifecycle.

**Architecture:** hermes-memory-decay is installed as a pip package exposing the `hermes_agent.plugins` entry point. The plugin implements `MemoryProvider` ABC and registers via `ctx.register_memory_provider()`. It communicates with the `memory-decay-core` FastAPI server (spawned by `ServerManager`) via `MemoryDecayHTTPClient`. The `MemoryProvider` is the interface layer; `ServerManager` + HTTP client are re-used as-is.

**Tech Stack:** Python 3.10+, Hermes Agent (installed at `~/.hermes/hermes-agent/`), abstract base class `agent.memory_provider.MemoryProvider`, orchestrator `agent.memory_manager.MemoryManager`, existing `ServerManager` + `MemoryDecayHTTPClient`.

**Work Scope:**
- **In scope:** MemoryProvider class, plugin.yaml, register(), tool schemas, lifecycle hooks, config schema, system prompt block, prefetch, sync_turn, on_memory_write, tests
- **Out of scope:** memory-decay-core FastAPI server modifications, ServerManager/HTTPClient changes

**Verification Strategy:**
- **Level:** test-suite (pytest)
- **Command:** `pytest tests/ -v`
- **What it validates:** All existing tests pass + new MemoryProvider tests pass

---

## File Structure

```
# Hermes Agent plugin discovery path:
~/.hermes/hermes-agent/plugins/memory/hermes-memory-decay/
  __init__.py    # MemoryDecayMemoryProvider + register()
  plugin.yaml    # Metadata + hooks

# These live in the hermes-memory-decay repo:
src/hermes_memory_decay/
  __init__.py          # OLD register(ctx) — REMOVE
  memory_provider.py   # NEW: MemoryDecayMemoryProvider class
  http_client.py       # UNCHANGED (re-used)
  server_manager.py    # UNCHANGED (re-used)
  config.py            # UNCHANGED (used by ServerManager)

tests/
  test_memory_provider.py  # NEW: MemoryProvider lifecycle + tool routing tests
  test_http_client.py      # UNCHANGED
  test_server_manager.py   # UNCHANGED
  test_tools.py            # UNCHANGED (server-side tool handlers)
  conftest.py              # UNCHANGED
```

**Key architectural note:** The `plugins/memory/hermes-memory-decay/__init__.py` imports and re-uses `hermes_memory_decay.ServerManager` and `hermes_memory_decay.MemoryDecayHTTPClient` from the pip-installed package. It does NOT copy the code — it references it.

---

## Task Decomposition

### Task 1: Create MemoryProvider class skeleton

**Dependencies:** None (can run in parallel)
**Files:**
- Create: `src/hermes_memory_decay/memory_provider.py`

- [ ] **Step 1: Create the file with all required ABC methods**

```python
"""MemoryProvider implementation for hermes-memory-decay.

Implements the official MemoryProvider ABC (B pattern: external HTTP server).
Server lifecycle managed by ServerManager; HTTP communication via MemoryDecayHTTPClient.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)


class MemoryDecayMemoryProvider(MemoryProvider):
    """Hermes-memory-decay provider using external FastAPI server."""

    def __init__(self):
        self._server_manager = None   # ServerManager instance
        self._config: dict = {}
        self._session_id: str = ""
        self._sync_thread: Optional[threading.Thread] = None

    @property
    def name(self) -> str:
        return "hermes-memory-decay"

    def is_available(self) -> bool:
        """Return True if memory_decay_path is configured. No network calls."""
        # Config is injected from initialize(); use cached config
        if not self._config:
            return False
        memory_decay_path = self._config.get("memory_decay_path", "")
        if not memory_decay_path:
            return False
        import os
        from pathlib import Path
        if not Path(memory_decay_path).is_dir():
            return False
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """Start the memory-decay server and warm up.

        kwargs always includes: hermes_home, platform, agent_context
        """
        from hermes_memory_decay.server_manager import ServerManager
        from hermes_memory_decay.config import load_config

        self._session_id = session_id
        hermes_home = kwargs.get("hermes_home", "")

        # Load config from plugin directory
        import os
        from pathlib import Path
        plugin_dir = Path(__file__).parent.parent.parent / "hermes_memory_decay"
        self._config = load_config(plugin_dir)

        # Auto-generate db_path from hermes_home if not set
        if not self._config.get("db_path"):
            self._config["db_path"] = os.path.join(hermes_home, "memory-decay", "memories.db")

        # Create and start server
        self._server_manager = ServerManager(self._config)
        self._server_manager.ensure_running()

        # Apply time-based decay on startup
        try:
            client = self._server_manager.get_client()
            result = client.auto_tick()
            if result.get("ticks_applied", 0) > 0:
                logger.info(
                    "Applied %d decay ticks (%.0fs elapsed)",
                    result["ticks_applied"],
                    result["elapsed_seconds"],
                )
        except Exception as e:
            logger.debug("auto_tick on init failed: %s", e)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI-format tool schemas for the 5 memory tools."""
        from hermes_memory_decay.schemas import (
            MEMORY_SEARCH_SCHEMA,
            MEMORY_STORE_SCHEMA,
            MEMORY_STORE_BATCH_SCHEMA,
            MEMORY_FORGET_SCHEMA,
            MEMORY_STATUS_SCHEMA,
        )
        return [
            MEMORY_SEARCH_SCHEMA,
            MEMORY_STORE_SCHEMA,
            MEMORY_STORE_BATCH_SCHEMA,
            MEMORY_FORGET_SCHEMA,
            MEMORY_STATUS_SCHEMA,
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Route a tool call to the appropriate handler."""
        if not self._server_manager:
            return json.dumps({"error": "Memory server not initialized."})

        client = self._server_manager.get_client()

        try:
            if tool_name == "memory_search":
                query = args.get("query", "")
                top_k = int(args.get("top_k", 5))
                result = client.search(query, top_k=top_k)
                return json.dumps({"result": result})

            elif tool_name == "memory_store":
                result = client.store(
                    text=args["text"],
                    importance=float(args.get("importance", 0.7)),
                    category=args.get("category", ""),
                    mtype=args.get("mtype", "fact"),
                    associations=args.get("associations"),
                    speaker=args.get("speaker"),
                )
                return json.dumps({"result": result})

            elif tool_name == "memory_store_batch":
                result = client.store_batch(args["items"])
                return json.dumps({"result": result})

            elif tool_name == "memory_forget":
                result = client.forget(args["memory_id"])
                return json.dumps({"result": result})

            elif tool_name == "memory_status":
                health = client.health()
                stats = client.stats()
                return json.dumps({"health": health, "stats": stats})

            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except Exception as e:
            logger.error("Memory tool %s failed: %s", tool_name, e)
            return json.dumps({"error": f"memory tool '{tool_name}' failed: {e}"})

    def shutdown(self) -> None:
        """Stop the server and join any pending sync thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)
        if self._server_manager:
            self._server_manager.stop()
```

---

### Task 2: Add optional hooks (sync_turn, on_session_end, system_prompt_block, prefetch, on_memory_write)

**Dependencies:** Task 1 completes
**Files:**
- Modify: `src/hermes_memory_decay/memory_provider.py` (append new methods)

- [ ] **Step 1: Add sync_turn (non-blocking, daemon thread)**

Append to `MemoryDecayMemoryProvider` class:

```python
def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
    """Persist a completed turn to the memory-decay server (non-blocking)."""
    if not self._server_manager:
        return

    def _sync():
        try:
            client = self._server_manager.get_client()
            # Store user turn
            client.store(
                text=user_content[:4000],
                importance=0.5,
                mtype="episode",
                speaker="user",
            )
            # Store assistant turn
            client.store(
                text=assistant_content[:4000],
                importance=0.5,
                mtype="episode",
                speaker="assistant",
            )
        except Exception as e:
            logger.debug("sync_turn failed: %s", e)

    if self._sync_thread and self._sync_thread.is_alive():
        self._sync_thread.join(timeout=5.0)
    self._sync_thread = threading.Thread(target=_sync, daemon=True, name="memory-decay-sync")
    self._sync_thread.start()
```

- [ ] **Step 2: Add on_session_end (flush decay)**

Append to `MemoryDecayMemoryProvider` class:

```python
def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
    """Apply auto-tick on session end."""
    if not self._server_manager:
        return
    try:
        client = self._server_manager.get_client()
        client.auto_tick()
    except Exception as e:
        logger.debug("on_session_end auto_tick failed: %s", e)
```

- [ ] **Step 3: Add system_prompt_block**

Append to `MemoryDecayMemoryProvider` class:

```python
def system_prompt_block(self) -> str:
    """Return system prompt text for memory context."""
    if not self._server_manager or not self._server_manager.is_running():
        return ""
    return (
        "# Hermès Memory (hermes-memory-decay)\n"
        "Active. Use memory_store to save important facts, preferences, or decisions. "
        "Use memory_search to recall past context. "
        "Use memory_forget to delete specific memories. "
        "Use memory_status to check system health. "
        "Memories naturally decay over time but are reinforced when recalled."
    )
```

- [ ] **Step 4: Add prefetch (context injection before each turn)**

Append to `MemoryDecayMemoryProvider` class:

```python
def prefetch(self, query: str, *, session_id: str = "") -> str:
    """Return relevant memory context for the upcoming turn."""
    if not self._server_manager or not self._server_manager.is_running():
        return ""
    if not query:
        return ""
    try:
        client = self._server_manager.get_client()
        result = client.search(query, top_k=3)
        memories = result.get("results", [])
        if not memories:
            return ""
        lines = []
        for m in memories:
            text = m.get("text", "")
            score = m.get("relevance", 0)
            lines.append(f"- [{score:.2f}] {text}")
        if lines:
            return "## Relevant Memories\n" + "\n".join(lines)
    except Exception as e:
        logger.debug("prefetch search failed: %s", e)
    return ""
```

- [ ] **Step 5: Add on_memory_write (mirror built-in memory writes)**

Append to `MemoryDecayMemoryProvider` class:

```python
def on_memory_write(self, action: str, target: str, content: str) -> None:
    """Mirror built-in memory writes to the decay backend."""
    if action != "add" or target not in ("memory", "user") or not content:
        return
    if not self._server_manager:
        return

    def _mirror():
        try:
            client = self._server_manager.get_client()
            client.store(
                text=content,
                importance=0.8,
                mtype="fact",
                speaker="builtin",
            )
        except Exception as e:
            logger.debug("on_memory_write mirror failed: %s", e)

    t = threading.Thread(target=_mirror, daemon=True, name="memory-decay-mirror")
    t.start()
```

---

### Task 3: Add get_config_schema and save_config (for `hermes memory setup`)

**Dependencies:** Task 1 completes
**Files:**
- Modify: `src/hermes_memory_decay/memory_provider.py` (append methods)

- [ ] **Step 1: Add get_config_schema**

Append to `MemoryDecayMemoryProvider` class:

```python
def get_config_schema(self) -> List[Dict[str, Any]]:
    """Return config fields for hermes memory setup wizard."""
    return [
        {
            "key": "memory_decay_path",
            "description": "Absolute path to the memory-decay-core repository",
            "required": True,
            "default": "",
        },
        {
            "key": "port",
            "description": "Port for the memory-decay server (default 8100)",
            "default": "8100",
        },
        {
            "key": "embedding_provider",
            "description": "Embedding provider: gemini, openai, local",
            "default": "gemini",
            "choices": ["gemini", "openai", "local"],
        },
        {
            "key": "embedding_api_key_env",
            "description": "Environment variable name for the embedding API key",
            "secret": True,
            "env_var": "GEMINI_API_KEY",
            "url": "https://console.gemini.google.com/apikey",
        },
        {
            "key": "tick_interval_seconds",
            "description": "Decay tick interval in seconds (default 3600)",
            "default": "3600",
        },
    ]
```

- [ ] **Step 2: Add save_config**

Append to `MemoryDecayMemoryProvider` class:

```python
def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
    """Write non-secret config to config.yaml memory section."""
    import os
    import re
    from pathlib import Path

    config_path = Path(hermes_home) / "plugins" / "hermes-memory-decay" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if config_path.exists():
        try:
            text = config_path.read_text()
            # Parse existing config using the plugin's parser
            from hermes_memory_decay.config import _parse_simple_yaml
            existing = _parse_simple_yaml(text)
        except Exception:
            pass

    existing.update(values)

    lines = []
    for key, val in existing.items():
        if val is None or val == "":
            lines.append(f"{key}:")
        elif isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, int):
            lines.append(f"{key}: {val}")
        else:
            lines.append(f'{key}: "{val}"')

    config_path.write_text("\n".join(lines) + "\n")
    logger.info("Config saved to %s", config_path)
```

---

### Task 4: Create plugin entry point register()

**Dependencies:** Tasks 1-3 complete
**Files:**
- Create: `~/.hermes/hermes-agent/plugins/memory/hermes-memory-decay/__init__.py`

**NOTE:** This file lives in the Hermes Agent install directory, NOT in the hermes-memory-decay repo. It imports MemoryDecayMemoryProvider from the pip-installed package.

- [ ] **Step 1: Create the plugin entry point**

Create at `/home/roach/.hermes/hermes-agent/plugins/memory/hermes-memory-decay/__init__.py`:

```python
"""hermes-memory-decay memory provider plugin for Hermes Agent.

Discovery path: plugins/memory/hermes-memory-decay/
Loaded by: hermes_cli.memory_setup.discover_memory_providers()
Entry point: register(ctx) -> ctx.register_memory_provider(MemoryDecayMemoryProvider())
"""

from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

def register(ctx) -> None:
    """Register hermes-memory-decay as a memory provider."""
    ctx.register_memory_provider(MemoryDecayMemoryProvider())
```

- [ ] **Step 2: Create plugin.yaml**

Create at `/home/roach/.hermes/hermes-agent/plugins/memory/hermes-memory-decay/plugin.yaml`:

```yaml
name: hermes-memory-decay
version: "0.1.0"
description: "Human-like memory with natural decay — memories fade over time but reinforce on recall."
pip_dependencies: []
hooks:
  - on_session_end
```

**NOTE:** `pip_dependencies` is empty because hermes-memory-decay is installed separately. The plugin itself has no pip deps.

---

### Task 5: Write MemoryProvider unit tests

**Dependencies:** Tasks 1-4 complete
**Files:**
- Create: `tests/test_memory_provider.py`

- [ ] **Step 1: Write the test file**

```python
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

    def test_is_available_returns_false_when_not_configured(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        provider._config = {}
        assert provider.is_available() is False

    def test_is_available_returns_false_when_path_missing(self):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider
        provider = MemoryDecayMemoryProvider()
        provider._config = {"memory_decay_path": "/nonexistent/path"}
        assert provider.is_available() is False

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

    @patch("hermes_memory_decay.memory_provider.ServerManager")
    def test_initialize_starts_server(self, mock_sm_class):
        from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

        mock_sm = MagicMock()
        mock_sm_class.return_value = mock_sm

        provider = MemoryDecayMemoryProvider()
        with patch("hermes_memory_decay.memory_provider.load_config") as mock_cfg:
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
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_memory_provider.py -v`
Expected: ALL PASS

---

### Task 6: Final Verification

**Dependencies:** All preceding tasks
**Files:** None (read-only verification)

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS — existing tests + new MemoryProvider tests

- [ ] **Step 2: Verify hermes memory setup integration**

Run: `hermes memory setup` (interactive — verify hermes-memory-decay appears as a provider option)
Expected: Provider listed and configurable

- [ ] **Step 3: Verify MemoryManager routing**

Manually test that MemoryManager correctly routes tool calls:
```python
from agent.memory_manager import MemoryManager
from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

mgr = MemoryManager()
provider = MemoryDecayMemoryProvider()
mgr.add_provider(provider)
schemas = mgr.get_all_tool_schemas()
assert len(schemas) == 5
```

- [ ] **Step 4: Verify success criteria**

- [ ] `hermes memory setup` shows hermes-memory-decay as a provider
- [ ] Provider selected → config schema prompts appear
- [ ] Config written to `~/.hermes/plugins/hermes-memory-decay/config.yaml`
- [ ] 5 tool schemas present in MemoryManager
- [ ] `sync_turn` fires without blocking the main thread
- [ ] `on_session_end` triggers auto_tick
- [ ] `shutdown()` stops the server cleanly
- [ ] All pytest tests pass

---

## Open Questions / Assumptions

1. **Plugin discovery path assumption:** The `plugins/memory/hermes-memory-decay/` directory must be created at `~/.hermes/hermes-agent/plugins/memory/hermes-memory-decay/` (inside the Hermes Agent install). The pip package (`hermes-memory-decay`) installs the core code; the plugin wrapper directory registers it with MemoryManager.

2. **Config path assumption:** `save_config()` writes to `~/.hermes/plugins/hermes-memory-decay/config.yaml`. Verify this matches what `ServerManager` expects for `memory_decay_path`.

3. **ServerManager re-use:** The existing `ServerManager` uses `atexit` to stop the server on Python exit. Since `MemoryProvider.shutdown()` is called by `MemoryManager.shutdown_all()` on session end, there may be a double-stop. The `atexit` handler will be a no-op if `_stopped` flag is already True (already handled in current `ServerManager.stop()`).
