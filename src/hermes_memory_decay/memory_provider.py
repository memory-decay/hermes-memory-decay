"""Memory provider for hermes-memory-decay.

Communicates with an external memory-decay FastAPI server via
ServerManager + MemoryDecayHTTPClient. This class is duck-typed;
the agent-side plugin wrapper inherits from MemoryProvider.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryDecayMemoryProvider:
    """Hermes-memory-decay provider using external HTTP server.

    This class implements the MemoryProvider interface via duck-typing.
    The agent-side plugin (__init__.py) wraps it with an adapter that
    inherits from agent.memory_provider.MemoryProvider.
    """

    def __init__(self):
        self._server_manager = None
        self._config: dict = {}
        self._sync_thread: Optional[threading.Thread] = None

    @property
    def name(self) -> str:
        return "hermes-memory-decay"

    def is_available(self) -> bool:
        """Check prerequisites: dependencies installed and config exists.

        Called before initialize(), so cannot rely on self._config.
        """
        import os
        from pathlib import Path

        try:
            import fastapi  # noqa: F401
        except ImportError:
            return False

        hermes_home = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
        config_path = Path(hermes_home) / "plugins" / "hermes-memory-decay" / "config.yaml"
        return config_path.exists()

    def initialize(self, session_id: str, **kwargs) -> None:
        from pathlib import Path
        import os

        from hermes_memory_decay.config import DEFAULTS, _parse_simple_yaml
        from hermes_memory_decay.server_manager import ServerManager

        self._session_id = session_id
        hermes_home = kwargs.get("hermes_home", "")

        # Prefer Hermes config location; fall back to package directory.
        config_path = Path(hermes_home) / "plugins" / "hermes-memory-decay" / "config.yaml"
        if config_path.exists():
            config = dict(DEFAULTS)
            try:
                text = config_path.read_text()
                user_config = _parse_simple_yaml(text)
                if not user_config:
                    try:
                        import yaml
                        user_config = yaml.safe_load(text) or {}
                    except ImportError:
                        pass
                config.update(user_config)
            except Exception as e:
                logger.warning("Failed to load config from %s: %s", config_path, e)
        else:
            from hermes_memory_decay.config import load_config
            plugin_dir = Path(__file__).parent.parent.parent / "hermes_memory_decay"
            config = load_config(plugin_dir)

        if hermes_home and not config.get("db_path"):
            config["db_path"] = os.path.join(hermes_home, "memory-decay", "memories.db")

        self._config = config
        self._server_manager = ServerManager(config)
        self._server_manager.ensure_running()

        try:
            result = self._server_manager.get_client().auto_tick()
            if result.get("ticks_applied", 0) > 0:
                logger.info(
                    "Applied %d decay ticks (%.0fs elapsed)",
                    result["ticks_applied"],
                    result["elapsed_seconds"],
                )
        except Exception as e:
            logger.debug("auto_tick on init failed: %s", e)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
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
        if not self._server_manager:
            return json.dumps({"error": "Memory server not initialized."})

        client = self._server_manager.get_client()
        try:
            handlers = {
                "memory_search": lambda: client.search(
                    args.get("query", ""), top_k=int(args.get("top_k", 5))
                ),
                "memory_store": lambda: client.store(
                    text=args["text"],
                    importance=float(args.get("importance", 0.7)),
                    category=args.get("category", ""),
                    mtype=args.get("mtype", "fact"),
                    associations=args.get("associations"),
                    speaker=args.get("speaker"),
                ),
                "memory_store_batch": lambda: client.store_batch(args["items"]),
                "memory_forget": lambda: client.forget(args["memory_id"]),
                "memory_status": lambda: {"health": client.health(), "stats": client.stats()},
            }
            handler = handlers[tool_name]
            return json.dumps({"result": handler()})
        except KeyError:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            logger.error("Memory tool %s failed: %s", tool_name, e)
            return json.dumps({"error": f"memory tool '{tool_name}' failed: {e}"})

    def shutdown(self) -> None:
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)
        if self._server_manager:
            self._server_manager.stop()

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        if not self._server_manager:
            return

        def _sync():
            try:
                client = self._server_manager.get_client()
                client.store(text=user_content[:4000], importance=0.5, mtype="episode", speaker="user")
                client.store(text=assistant_content[:4000], importance=0.5, mtype="episode", speaker="assistant")
            except Exception as e:
                logger.debug("sync_turn failed: %s", e)

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)
        self._sync_thread = threading.Thread(target=_sync, daemon=True, name="memory-decay-sync")
        self._sync_thread.start()

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        if not self._server_manager:
            return
        try:
            self._server_manager.get_client().auto_tick()
        except Exception as e:
            logger.debug("on_session_end auto_tick failed: %s", e)

    def system_prompt_block(self) -> str:
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

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if not self._server_manager or not self._server_manager.is_running():
            return ""
        if not query:
            return ""
        try:
            client = self._server_manager.get_client()
            memories = client.search(query, top_k=3).get("results", [])
            if not memories:
                return ""
            lines = [f"- [{m.get('relevance', 0):.2f}] {m.get('text', '')}" for m in memories]
            return "## Relevant Memories\n" + "\n".join(lines)
        except Exception as e:
            logger.debug("prefetch search failed: %s", e)
        return ""

    def on_memory_write(self, action: str, target: str, content: str) -> None:
        if action != "add" or target not in ("memory", "user") or not content:
            return
        if not self._server_manager:
            return

        def _mirror():
            try:
                self._server_manager.get_client().store(
                    text=content, importance=0.8, mtype="fact", speaker="builtin",
                )
            except Exception as e:
                logger.debug("on_memory_write mirror failed: %s", e)

        t = threading.Thread(target=_mirror, daemon=True, name="memory-decay-mirror")
        t.start()

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "memory_decay_path",
                "description": "Absolute path to the memory-decay-core repository",
                "required": True,
            },
            {
                "key": "port",
                "description": "Port for the memory-decay server",
                "default": "8100",
            },
            {
                "key": "embedding_provider",
                "description": "Embedding provider: gemini, openai, local",
                "default": "local",
                "choices": ["local", "gemini", "openai"],
            },
            {
                "key": "tick_interval_seconds",
                "description": "Decay tick interval in seconds",
                "default": "3600",
            },
        ]

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        from pathlib import Path

        from hermes_memory_decay.config import _parse_simple_yaml

        config_path = Path(hermes_home) / "plugins" / "hermes-memory-decay" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        existing = {}
        if config_path.exists():
            try:
                existing = _parse_simple_yaml(config_path.read_text())
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
