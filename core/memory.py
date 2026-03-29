"""Feedback-aware Memory wrapper."""

from __future__ import annotations
import threading
import time
from typing import Any
from memory_decay import MemoryStore

DECAY_TICKS_WINDOW = 100

# Store-level lock registry: ensures one lock per underlying store (by DB connection id).
# This prevents race conditions when multiple Memory instances wrap the same store.
_store_locks: dict[int, threading.RLock] = {}
_store_locks_guard = threading.Lock()


def _get_store_lock(store: MemoryStore) -> threading.RLock:
    """Get or create a per-store RLock, keyed by the store's DB connection id()."""
    db_id = id(store._db)
    with _store_locks_guard:
        if db_id not in _store_locks:
            _store_locks[db_id] = threading.RLock()
        return _store_locks[db_id]


class Memory:
    def __init__(self, store):
        self._store = store
        self._lock = _get_store_lock(store)
        self._init_feedback_schema()

    def _init_feedback_schema(self):
        self._store._db.execute(
            "CREATE TABLE IF NOT EXISTS feedback_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "memory_id TEXT NOT NULL, "
            "signal TEXT NOT NULL, "
            "strength REAL NOT NULL DEFAULT 1.0, "
            "tick INTEGER NOT NULL, "
            "source TEXT NOT NULL DEFAULT '', "
            "created_at REAL NOT NULL)"
        )
        self._store._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_feedback_memory_tick "
            "ON feedback_log (memory_id, tick)"
        )
        self._store.commit()

    def feedback(self, memory_id, signal="positive", strength=1.0, current_tick=None, source=""):
        return self.feedback_batch(
            [{"memory_id": memory_id, "signal": signal, "strength": strength,
              "tick": current_tick, "source": source}],
            current_tick=current_tick
        )

    def feedback_batch(self, batch, current_tick=None):
        if not batch:
            return {"updated": 0, "conflicting": False, "details": []}
        if current_tick is None:
            current_tick = int(self._store.get_metadata("current_tick", "0"))
        for item in batch:
            item.setdefault("signal", "positive")
            item.setdefault("strength", 1.0)
            item.setdefault("tick", current_tick)
            item.setdefault("source", "")
        return self._apply_feedback(batch)

    def _apply_feedback(self, batch):
        if not batch:
            return {"updated": 0, "conflicting": False, "details": []}
        with self._lock:
            memory_signals = {}
            for item in batch:
                mid = item["memory_id"]
                sig = item["signal"]
                memory_signals.setdefault(mid, set()).add(sig)
            conflicting = any(
                {"positive", "negative"} <= sigs
                for sigs in memory_signals.values()
            )
            now = time.time()
            details = []
            for item in batch:
                mid = item["memory_id"]
                sig = item["signal"]
                strength = float(item.get("strength", 1.0))
                tick = int(item.get("tick", 0))
                source = str(item.get("source", ""))
                self._store._db.execute(
                    "INSERT INTO feedback_log (memory_id, signal, strength, tick, source, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (mid, sig, strength, tick, source, now)
                )
                # Read current stability directly from DB (avoids stale cache from get_node)
                row = self._store._db.execute(
                    "SELECT stability_score FROM memories WHERE id = ?", (mid,)
                ).fetchone()
                if row is None:
                    continue
                stability = float(row[0])
                if sig == "positive":
                    gap = max(1.0 - stability, 0.0)
                    new_stability = min(1.0, stability + gap * strength * 0.6)
                    self._store._db.execute(
                        "UPDATE memories SET stability_score = ? WHERE id = ?",
                        (new_stability, mid)
                    )
                    details.append(f"{mid}: {stability:.3f} -> {new_stability:.3f}")
                elif sig == "negative":
                    new_stability = max(0.0, stability - strength * 0.3)
                    self._store._db.execute(
                        "UPDATE memories SET stability_score = ? WHERE id = ?",
                        (new_stability, mid)
                    )
                    details.append(f"{mid}: {stability:.3f} -> {new_stability:.3f} (neg)")
            self._store.commit()
            return {"updated": len(batch), "conflicting": conflicting, "details": details}

    def reinforce(self, memory_id, strength=0.5, current_tick=None):
        with self._lock:
            if current_tick is None:
                current_tick = int(self._store.get_metadata("current_tick", "0"))
            window_start = current_tick - DECAY_TICKS_WINDOW
            neg_rows = self._store._db.execute(
                "SELECT COUNT(*) FROM feedback_log WHERE memory_id = ? AND signal = ? AND tick >= ?",
                (memory_id, "negative", window_start)
            ).fetchone()[0]
            neg_feedback_blocked = bool(neg_rows > 0)
            row = self._store._db.execute(
                "SELECT stability_score FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if row is None:
                return {
                    "reinforced": False, "decay_rate_reduced": False,
                    "last_activated_tick": 0, "neg_feedback_blocked": neg_feedback_blocked,
                    "stability_change": 0.0
                }
            stability = float(row[0])
            old_stability = stability
            self._store._db.execute(
                "UPDATE memories SET last_activated_tick = ? WHERE id = ?",
                (current_tick, memory_id)
            )
            if neg_feedback_blocked:
                new_stability = stability
            else:
                gap = max(1.0 - stability, 0.0)
                new_stability = min(1.0, stability + gap * strength * 0.6)
            self._store._db.execute(
                "UPDATE memories SET stability_score = ? WHERE id = ?",
                (new_stability, memory_id)
            )
            self._store.commit()
            return {
                "reinforced": True,
                "decay_rate_reduced": not neg_feedback_blocked,
                "last_activated_tick": current_tick,
                "neg_feedback_blocked": neg_feedback_blocked,
                "stability_change": new_stability - old_stability
            }

    def set_stability(self, memory_id, stability):
        """Set stability score directly. Value is clamped to [0.0, 1.0]."""
        with self._lock:
            capped = min(max(float(stability), 0.0), 1.0)
            self._store._db.execute(
                "UPDATE memories SET stability_score = ? WHERE id = ?",
                (capped, memory_id)
            )
            self._store.commit()

    def record_access(self, memory_id, current_tick=None):
        with self._lock:
            if current_tick is None:
                current_tick = int(self._store.get_metadata("current_tick", "0"))
            self._store._db.execute(
                "UPDATE memories SET last_activated_tick = ? WHERE id = ?",
                (current_tick, memory_id)
            )
            self._store.commit()

    def get_feedback_log(self, memory_id=None, limit=100):
        with self._lock:
            if memory_id:
                rows = self._store._db.execute(
                    "SELECT id, memory_id, signal, strength, tick, source, created_at "
                    "FROM feedback_log WHERE memory_id = ? ORDER BY created_at DESC LIMIT ?",
                    (memory_id, limit)
                ).fetchall()
            else:
                rows = self._store._db.execute(
                    "SELECT id, memory_id, signal, strength, tick, source, created_at "
                    "FROM feedback_log ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [
                {"id": r[0], "memory_id": r[1], "signal": r[2],
                 "strength": r[3], "tick": r[4], "source": r[5], "created_at": r[6]}
                for r in rows
            ]

    def clear_feedback_log(self, memory_id=None):
        with self._lock:
            if memory_id:
                count = self._store._db.execute(
                    "DELETE FROM feedback_log WHERE memory_id = ?",
                    (memory_id,)
                ).rowcount
            else:
                count = self._store._db.execute("DELETE FROM feedback_log").rowcount
            self._store.commit()
            return count
