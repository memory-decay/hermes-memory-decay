"""Tool handlers for memory-decay tools.

Each handler follows the Hermes contract:
    def handler(args: dict, **kwargs) -> str

Returns a JSON string. ALL exceptions are caught and returned as
{"error": "..."} to never break the agent loop.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def _get_client():
    """Get the HTTP client from the server manager."""
    from . import _server_manager

    if _server_manager is None:
        raise RuntimeError("Memory-decay plugin not initialized")
    _server_manager.ensure_running()
    return _server_manager.get_client()


def handle_memory_search(args: dict, **kwargs) -> str:
    """Search memories by semantic similarity."""
    try:
        client = _get_client()
        query = args["query"]
        top_k = args.get("top_k", 5)
        result = client.search(query=query, top_k=min(top_k, 20))

        memories = result.get("results", [])
        if not memories:
            return json.dumps({"message": "No memories found.", "results": []})

        formatted = []
        for m in memories:
            storage_score = m.get("storage_score", 0)
            freshness = (
                "fresh" if storage_score > 0.7
                else "normal" if storage_score > 0.3
                else "stale"
            )
            formatted.append({
                "id": m["id"],
                "text": m["text"],
                "score": round(m["score"], 3),
                "freshness": freshness,
                "category": m.get("category", ""),
                "speaker": m.get("speaker", ""),
            })
        return json.dumps({"results": formatted, "count": len(formatted)})

    except Exception as e:
        logger.error("memory_search failed: %s", e)
        return json.dumps({"error": str(e)})


def handle_memory_store(args: dict, **kwargs) -> str:
    """Store a new memory."""
    try:
        client = _get_client()
        result = client.store(
            text=args["text"],
            importance=args.get("importance", 0.7),
            category=args.get("category", ""),
            mtype=args.get("mtype", "fact"),
            associations=args.get("associations"),
            speaker=args.get("speaker"),
        )
        return json.dumps({
            "stored": True,
            "id": result["id"],
            "text": result["text"],
            "tick": result["tick"],
        })
    except Exception as e:
        logger.error("memory_store failed: %s", e)
        return json.dumps({"error": str(e)})


def handle_memory_store_batch(args: dict, **kwargs) -> str:
    """Store multiple memories at once."""
    try:
        client = _get_client()
        items = args["items"]
        result = client.store_batch(items)
        return json.dumps({
            "stored": True,
            "count": result["count"],
            "ids": result["ids"],
        })
    except Exception as e:
        logger.error("memory_store_batch failed: %s", e)
        return json.dumps({"error": str(e)})


def handle_memory_forget(args: dict, **kwargs) -> str:
    """Delete a specific memory by ID."""
    try:
        client = _get_client()
        result = client.forget(memory_id=args["memory_id"])
        return json.dumps({"deleted": result["deleted"]})
    except Exception as e:
        logger.error("memory_forget failed: %s", e)
        return json.dumps({"error": str(e)})


def handle_memory_status(args: dict, **kwargs) -> str:
    """Check memory system health and stats."""
    try:
        client = _get_client()
        health = client.health()
        stats = client.stats()
        return json.dumps({
            "status": health.get("status", "unknown"),
            "current_tick": health.get("current_tick", 0),
            "num_memories": stats.get("num_memories", 0),
            "last_tick_time": stats.get("last_tick_time"),
        })
    except Exception as e:
        logger.error("memory_status failed: %s", e)
        return json.dumps({"error": str(e), "status": "unreachable"})
