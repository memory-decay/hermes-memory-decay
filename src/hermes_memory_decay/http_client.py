"""HTTP client for the memory-decay server.

Uses only urllib (no external dependencies) for zero-dep installation.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Any


class MemoryDecayHTTPClient:
    """Synchronous HTTP client for memory-decay API."""

    def __init__(self, port: int = 8100):
        self._base_url = f"http://127.0.0.1:{port}"

    def _request(self, method: str, path: str, body: Any = None, timeout: int = 30) -> dict:
        """Make an HTTP request and return parsed JSON."""
        url = f"{self._base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"{method} {path} failed ({e.code}): {body_text}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Connection to memory-decay server failed: {e}"
            ) from e

    def health(self) -> dict:
        """Check server health. Uses short timeout for startup polling."""
        return self._request("GET", "/health", timeout=3)

    def stats(self) -> dict:
        """Get memory statistics."""
        return self._request("GET", "/stats")

    def store(
        self,
        text: str,
        importance: float = 0.7,
        category: str = "",
        mtype: str = "fact",
        associations: list[str] | None = None,
        speaker: str | None = None,
    ) -> dict:
        """Store a single memory."""
        payload: dict[str, Any] = {
            "text": text,
            "importance": importance,
            "category": category,
            "mtype": mtype,
        }
        if associations:
            payload["associations"] = associations
        if speaker:
            payload["speaker"] = speaker
        return self._request("POST", "/store", payload)

    def store_batch(self, items: list[dict]) -> dict:
        """Store multiple memories in one call."""
        return self._request("POST", "/store-batch", items)

    def search(self, query: str, top_k: int = 5) -> dict:
        """Search memories by semantic similarity."""
        return self._request("POST", "/search", {"query": query, "top_k": top_k})

    def forget(self, memory_id: str) -> dict:
        """Delete a memory by ID. Validates format to prevent URL injection."""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', memory_id):
            raise ValueError(f"Invalid memory_id format: {memory_id}")
        return self._request("DELETE", f"/forget/{urllib.parse.quote(memory_id, safe='')}")

    def auto_tick(self) -> dict:
        """Apply decay ticks based on elapsed real time."""
        return self._request("POST", "/auto-tick")
