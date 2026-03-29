"""Configuration loading for the hermes-memory-decay plugin.

Loads from config.yaml in the plugin directory, falling back to
sensible defaults. Expands ~ in paths.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_PATH_KEYS = {"python_path", "memory_decay_path", "db_path", "experiment_dir"}

DEFAULTS: dict = {
    "python_path": "python3",
    "memory_decay_path": str(Path.home() / "workspace" / "memory-decay-core"),
    "port": 8100,
    "db_path": str(Path.home() / ".hermes" / "memory-decay" / "memories.db"),
    "embedding_provider": "gemini",
    "embedding_model": None,
    "embedding_api_key_env": "GEMINI_API_KEY",
    "embedding_dim": None,
    "experiment_dir": None,
    "tick_interval_seconds": 3600,
    "auto_start_server": True,
    "server_startup_timeout_ms": 15000,
    "max_restarts": 3,
}


def load_config(plugin_dir: Path) -> dict:
    """Load plugin config from config.yaml, falling back to defaults."""
    config = dict(DEFAULTS)

    config_path = plugin_dir / "config.yaml"
    if config_path.exists():
        try:
            import yaml

            user_config = yaml.safe_load(config_path.read_text()) or {}
            config.update(user_config)
            logger.debug("Loaded config from %s", config_path)
        except ImportError:
            logger.warning(
                "PyYAML not installed -- cannot load %s, using defaults", config_path
            )
        except Exception as e:
            logger.warning("Failed to load config from %s: %s", config_path, e)
    else:
        logger.debug(
            "No config.yaml found at %s, using defaults. "
            "Copy config.yaml.example to config.yaml to customize.",
            plugin_dir / "config.yaml",
        )

    # Expand ~ in path values
    for key in _PATH_KEYS:
        val = config.get(key)
        if isinstance(val, str):
            config[key] = os.path.expanduser(val)

    return config
