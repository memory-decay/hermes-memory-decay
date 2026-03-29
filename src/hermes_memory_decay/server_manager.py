"""Manages the memory-decay FastAPI server as a subprocess.

Mirrors the OpenClaw TypeScript MemoryDecayService pattern:
spawn python -m memory_decay.server, health-check loop, auto-restart,
graceful shutdown.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
import time
from typing import Optional

from .http_client import MemoryDecayHTTPClient

logger = logging.getLogger(__name__)


class ServerManager:
    """Spawn and manage the memory-decay server process."""

    def __init__(self, config: dict):
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._client = MemoryDecayHTTPClient(port=config["port"])
        self._restart_count = 0
        self._max_restarts = config.get("max_restarts", 3)
        self._lock = threading.Lock()
        self._stopped = False

    def get_client(self) -> MemoryDecayHTTPClient:
        return self._client

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def ensure_running(self) -> None:
        """Start the server if not already running."""
        with self._lock:
            if self.is_running():
                try:
                    self._client.health()
                    return
                except Exception:
                    pass
            self._start()

    def _start(self) -> None:
        """Spawn the server subprocess and wait for health."""
        self._stopped = False

        python_path = self._config["python_path"]
        memory_decay_path = self._config["memory_decay_path"]
        port = self._config["port"]
        db_path = self._config["db_path"]

        if not memory_decay_path:
            raise RuntimeError(
                "memory_decay_path is not configured. "
                "Edit ~/.hermes/plugins/hermes-memory-decay/config.yaml "
                "and set memory_decay_path to the absolute path of your "
                "memory-decay-core repository."
            )

        if not os.path.isdir(memory_decay_path):
            raise RuntimeError(
                f"memory_decay_path does not exist: {memory_decay_path}. "
                "Clone memory-decay-core and set the correct path in config.yaml."
            )

        # Ensure DB directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        args = [
            python_path, "-m", "memory_decay.server",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--db-path", db_path,
        ]

        if self._config.get("embedding_provider"):
            args.extend(["--embedding-provider", self._config["embedding_provider"]])
        if self._config.get("embedding_model"):
            args.extend(["--embedding-model", self._config["embedding_model"]])

        api_key_env = self._config.get("embedding_api_key_env")
        if api_key_env:
            api_key = os.environ.get(api_key_env)
            if api_key:
                args.extend(["--embedding-api-key", api_key])

        if self._config.get("embedding_dim"):
            args.extend(["--embedding-dim", str(self._config["embedding_dim"])])
        if self._config.get("experiment_dir"):
            args.extend(["--experiment-dir", self._config["experiment_dir"]])
        if self._config.get("tick_interval_seconds"):
            args.extend(["--tick-interval", str(self._config["tick_interval_seconds"])])

        env = {**os.environ, "PYTHONPATH": os.path.join(memory_decay_path, "src")}

        logger.info("Starting memory-decay server on port %d", port)
        logger.debug("Server command: %s", " ".join(args))

        self._process = subprocess.Popen(
            args,
            cwd=memory_decay_path,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        # Drain stderr in background
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self._wait_for_health()

    def _read_stderr(self) -> None:
        if self._process and self._process.stderr:
            for line in iter(self._process.stderr.readline, b""):
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.debug("[memory-decay] %s", text)

    def _wait_for_health(self) -> None:
        timeout_ms = self._config.get("server_startup_timeout_ms", 15000)
        deadline = time.monotonic() + (timeout_ms / 1000)

        while time.monotonic() < deadline:
            if self._stopped:
                return
            try:
                self._client.health()
                self._restart_count = 0
                logger.info("memory-decay server healthy on port %d", self._config["port"])
                return
            except Exception:
                time.sleep(0.5)

        raise RuntimeError(
            f"memory-decay server failed to start within {timeout_ms}ms"
        )

    def stop(self) -> None:
        self._stopped = True
        with self._lock:
            if self._process is not None:
                try:
                    self._process.send_signal(signal.SIGTERM)
                    self._process.wait(timeout=5)
                except Exception:
                    self._process.kill()
                finally:
                    self._process = None
                logger.info("memory-decay server stopped")
