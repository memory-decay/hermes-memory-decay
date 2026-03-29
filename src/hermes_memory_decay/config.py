"""Configuration loading for the hermes-memory-decay plugin.

Loads from config.yaml in the plugin directory, falling back to
sensible defaults. Expands ~ in paths.

PyYAML is imported lazily. If not available, a simple YAML-like
parser handles the flat key-value config format used here.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_PATH_KEYS = {"python_path", "memory_decay_path", "db_path", "experiment_dir"}

DEFAULTS: dict = {
    "python_path": "python3",
    "memory_decay_path": "",  # MUST be set in config.yaml
    "port": 8100,
    "db_path": "",  # Auto-generated from HERMES_HOME if not set
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


def _parse_simple_yaml(text: str) -> dict:
    """Parse a simple flat or lightly nested YAML without PyYAML.

    Handles:
      key: value
      key: "string value"
      key: null / true / false
      # comments
    Falls back to returning empty dict for anything it can't parse.
    """
    result: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+)$', line)
        if not m:
            continue
        key = m.group(1)
        raw = m.group(2).strip()
        # Strip inline comments (but not inside quoted strings)
        if not (raw.startswith('"') and raw.endswith('"')):
            raw = re.sub(r'\s+#.*$', '', raw)
        # Parse value
        if raw.lower() in ("null", "none", "~"):
            result[key] = None
        elif raw.lower() == "true":
            result[key] = True
        elif raw.lower() == "false":
            result[key] = False
        elif raw.isdigit():
            result[key] = int(raw)
        elif re.match(r'^\d+\.\d+$', raw):
            result[key] = float(raw)
        elif raw.startswith('"') and raw.endswith('"'):
            result[key] = raw[1:-1]
        elif raw.startswith("'") and raw.endswith("'"):
            result[key] = raw[1:-1]
        else:
            result[key] = raw
    return result


def load_config(plugin_dir: Path) -> dict:
    """Load plugin config from config.yaml, falling back to defaults."""
    config = dict(DEFAULTS)

    # Determine HERMES_HOME (same logic as Hermes plugins.py L190)
    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))

    config_path = plugin_dir / "config.yaml"
    if config_path.exists():
        try:
            user_config = _parse_simple_yaml(config_path.read_text())
            if not user_config:
                # Empty or unparseable — try PyYAML for richer formats
                try:
                    import yaml
                    user_config = yaml.safe_load(config_path.read_text()) or {}
                except ImportError:
                    logger.warning(
                        "Config appears complex but PyYAML is not installed. "
                        "Install pyyaml for full YAML support: pip install pyyaml"
                    )
            config.update(user_config)
            logger.debug("Loaded config from %s", config_path)
        except Exception as e:
            logger.warning("Failed to load config from %s: %s", config_path, e)
    else:
        logger.warning(
            "No config.yaml found in %s. "
            "Copy config.yaml.example to config.yaml and edit it.",
            plugin_dir,
        )

    # Auto-generate db_path if not set
    if not config.get("db_path"):
        config["db_path"] = os.path.join(hermes_home, "memory-decay", "memories.db")

    # Expand ~ in path values
    for key in _PATH_KEYS:
        val = config.get(key)
        if isinstance(val, str):
            config[key] = os.path.expanduser(val)

    # Validate required fields
    if not config.get("memory_decay_path"):
        logger.warning(
            "memory_decay_path is not set. "
            "The server will not start. Edit %s and set memory_decay_path.",
            config_path,
        )

    return config
