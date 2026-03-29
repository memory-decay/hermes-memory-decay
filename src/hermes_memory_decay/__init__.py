"""hermes-memory-decay plugin -- human-like memory with natural decay.

Entry point: register(ctx) is called by the Hermes plugin loader.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).parent

# Module-level state -- initialized in register()
_server_manager = None
_config: dict = {}


def _load_current_config() -> dict:
    """Load the latest config from disk for tool availability checks."""
    from .config import load_config

    return load_config(_PLUGIN_DIR)


def _check_prerequisites(require_embedding_key: bool = True) -> bool:
    """Verify plugin prerequisites without starting the server."""
    config_path = _PLUGIN_DIR / "config.yaml"
    if not config_path.exists():
        return False

    config = _load_current_config()
    if not config.get("memory_decay_path"):
        return False
    if not Path(config["memory_decay_path"]).is_dir():
        return False

    provider = config.get("embedding_provider", "gemini")
    if require_embedding_key and provider != "local":
        api_key_env = config.get("embedding_api_key_env", "GEMINI_API_KEY")
        if not os.environ.get(api_key_env):
            return False

    return True


def _check_tool_prerequisites() -> bool:
    """Tools that need embeddings require a configured provider key."""
    return _check_prerequisites(require_embedding_key=True)


def _check_status_prerequisites() -> bool:
    """Status only needs the core path configured so health can be reported."""
    return _check_prerequisites(require_embedding_key=False)


def register(ctx) -> None:
    """Entry point called by Hermes plugin loader."""
    global _server_manager, _config

    from .config import load_config
    from .schemas import (
        MEMORY_SEARCH_SCHEMA,
        MEMORY_STORE_SCHEMA,
        MEMORY_STORE_BATCH_SCHEMA,
        MEMORY_FORGET_SCHEMA,
        MEMORY_STATUS_SCHEMA,
    )
    from .tools import (
        handle_memory_search,
        handle_memory_store,
        handle_memory_store_batch,
        handle_memory_forget,
        handle_memory_status,
    )
    from .server_manager import ServerManager

    _config = load_config(_PLUGIN_DIR)
    _server_manager = ServerManager(_config)

    toolset = "memory_decay"

    ctx.register_tool(
        name="memory_search",
        toolset=toolset,
        schema=MEMORY_SEARCH_SCHEMA,
        handler=handle_memory_search,
        description="Search memories by semantic similarity",
        emoji="🔍",
        check_fn=_check_tool_prerequisites,
    )
    ctx.register_tool(
        name="memory_store",
        toolset=toolset,
        schema=MEMORY_STORE_SCHEMA,
        handler=handle_memory_store,
        description="Store a new memory",
        emoji="💾",
        check_fn=_check_tool_prerequisites,
    )
    ctx.register_tool(
        name="memory_store_batch",
        toolset=toolset,
        schema=MEMORY_STORE_BATCH_SCHEMA,
        handler=handle_memory_store_batch,
        description="Store multiple memories in one call",
        emoji="📦",
        check_fn=_check_tool_prerequisites,
    )
    ctx.register_tool(
        name="memory_forget",
        toolset=toolset,
        schema=MEMORY_FORGET_SCHEMA,
        handler=handle_memory_forget,
        description="Delete a specific memory by ID",
        emoji="🗑️",
        check_fn=_check_tool_prerequisites,
    )
    ctx.register_tool(
        name="memory_status",
        toolset=toolset,
        schema=MEMORY_STATUS_SCHEMA,
        handler=handle_memory_status,
        description="Check memory system health and stats",
        emoji="📊",
        check_fn=_check_status_prerequisites,
    )

    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("pre_llm_call", _pre_llm_call)

    logger.info("hermes-memory-decay plugin registered (port=%d)", _config["port"])


def _on_session_start(**kwargs) -> None:
    """Start the memory-decay server and apply time-based decay."""
    if _server_manager is None:
        return
    try:
        if _config.get("auto_start_server", True):
            _server_manager.ensure_running()
            client = _server_manager.get_client()
            result = client.auto_tick()
            if result.get("ticks_applied", 0) > 0:
                logger.info(
                    "Applied %d decay ticks (%.0fs elapsed)",
                    result["ticks_applied"],
                    result["elapsed_seconds"],
                )
    except Exception as e:
        logger.error("Failed to start memory-decay server: %s", e)


def _on_session_end(**kwargs) -> None:
    """Auto-tick on session end."""
    if _server_manager is None:
        return
    try:
        client = _server_manager.get_client()
        client.auto_tick()
    except Exception as e:
        logger.debug("auto_tick on session end failed: %s", e)


def _pre_llm_call(**kwargs) -> dict | None:
    """Inject memory-decay system prompt context."""
    from .prompt import get_system_prompt_fragment

    if _server_manager and _server_manager.is_running():
        return {"context": get_system_prompt_fragment()}
    return None
