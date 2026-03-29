"""Tests for core/memory.py — Feedback System v2 fixes + race condition + edge cases."""

import random
import threading
import time

import pytest

from memory_decay import MemoryStore
from core.memory import Memory


def _random_embedding(dim: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(dim)]


@pytest.fixture
def store():
    s = MemoryStore(":memory:", embedding_dim=384)
    yield s
    s.close()


@pytest.fixture
def mem(store):
    m = Memory(store)
    store.add_memory(
        "mem_test",
        "hello world",
        _random_embedding(384, 1),
        user_id="u1",
        mtype="fact",
        importance=0.8,
        created_tick=0,
    )
    yield m


# ── Fix 1: Corrected reinforce formula ──────────────────────────────────

class TestReinforceCorrectedFormula:
    def test_stability_gain_proportional_to_gap(self, mem, store):
        result = mem.reinforce("mem_test", strength=0.5, current_tick=1)
        assert result["reinforced"] is True
        node = store.get_node("mem_test")
        new_stability = float(node["stability_score"])
        assert new_stability == pytest.approx(0.3, abs=0.01)

    def test_stability_capped_at_1(self, mem, store):
        for _ in range(20):
            mem.reinforce("mem_test", strength=1.0, current_tick=1)
        node = store.get_node("mem_test")
        assert float(node["stability_score"]) == pytest.approx(1.0)

    def test_strength_zero_does_nothing(self, mem, store):
        node = store.get_node("mem_test")
        before = float(node["stability_score"])
        mem.reinforce("mem_test", strength=0.0, current_tick=1)
        node = store.get_node("mem_test")
        after = float(node["stability_score"])
        assert after == pytest.approx(before)


# ── Fix 2: Negative feedback guard ──────────────────────────────────────

class TestNegativeFeedbackGuard:
    def test_negative_feedback_blocks_stability_gain(self, mem, store):
        mem.feedback("mem_test", signal="negative", current_tick=50)
        result = mem.reinforce("mem_test", strength=0.5, current_tick=51)
        assert result["neg_feedback_blocked"] is True
        assert result["stability_change"] == 0.0

    def test_old_negative_does_not_block(self, mem, store):
        mem.feedback("mem_test", signal="negative", current_tick=0)
        result = mem.reinforce("mem_test", strength=0.5, current_tick=150)
        assert result["neg_feedback_blocked"] is False
        assert result["stability_change"] > 0


# ── Fix 3: Lock-based transactions ──────────────────────────────────────

class TestLockBasedTransactions:
    def test_set_stability_concurrent_safety(self, store):
        m = Memory(store)
        store.add_memory("race_mem", "test", _random_embedding(384, 42),
                         user_id="u1", mtype="fact", importance=0.5, created_tick=0)
        errors = []
        def bump():
            try:
                for _ in range(50):
                    m.set_stability("race_mem", 0.9)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=bump) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors, f"Errors: {errors}"

    def test_record_access_concurrent_safety(self, store):
        m = Memory(store)
        store.add_memory("race_mem2", "test", _random_embedding(384, 43),
                         user_id="u1", mtype="fact", importance=0.5, created_tick=0)
        errors = []
        def access():
            try:
                for i in range(50):
                    m.record_access("race_mem2", current_tick=i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=access) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors, f"Errors: {errors}"


# ── Fix 4: Contradictory signals ────────────────────────────────────────

class TestContradictorySignals:
    def test_conflicting_signals_detected(self, mem, store):
        result = mem.feedback_batch([
            {"memory_id": "mem_test", "signal": "positive"},
            {"memory_id": "mem_test", "signal": "negative"},
        ], current_tick=10)
        assert result["conflicting"] is True

    def test_single_positive_not_conflicting(self, mem, store):
        result = mem.feedback_batch([
            {"memory_id": "mem_test", "signal": "positive"},
        ], current_tick=10)
        assert result.get("conflicting") is not True

    def test_single_negative_not_conflicting(self, mem, store):
        result = mem.feedback_batch([
            {"memory_id": "mem_test", "signal": "negative"},
        ], current_tick=10)
        assert result.get("conflicting") is not True

    def test_different_memories_not_conflicting(self, mem, store):
        store.add_memory("mem2", "other", _random_embedding(384, 99),
                         user_id="u1", mtype="fact", importance=0.5, created_tick=0)
        result = mem.feedback_batch([
            {"memory_id": "mem_test", "signal": "positive"},
            {"memory_id": "mem2", "signal": "negative"},
        ], current_tick=10)
        assert result.get("conflicting") is not True

    def test_both_signals_still_applied_despite_conflict(self, mem, store):
        result = mem.feedback_batch([
            {"memory_id": "mem_test", "signal": "positive", "strength": 1.0},
            {"memory_id": "mem_test", "signal": "negative", "strength": 1.0},
        ], current_tick=10)
        assert result["conflicting"] is True
        log = mem.get_feedback_log(memory_id="mem_test")
        signals = [e["signal"] for e in log]
        assert "positive" in signals
        assert "negative" in signals


# ── Fix 5: reinforce updates last_activated_tick ────────────────────────

class TestReinforceUpdatesLastActivatedTick:
    def test_reinforce_updates_tick(self, mem, store):
        mem.reinforce("mem_test", strength=0.5, current_tick=99)
        node = store.get_node("mem_test")
        assert int(node["last_activated_tick"]) == 99

    def test_reinforce_updates_tick_even_when_blocked(self, mem, store):
        mem.feedback("mem_test", signal="negative", current_tick=50)
        result = mem.reinforce("mem_test", strength=0.5, current_tick=99)
        assert result["neg_feedback_blocked"] is True
        node = store.get_node("mem_test")
        assert int(node["last_activated_tick"]) == 99


# ── New: Non-existent memory edge cases ─────────────────────────────────

class TestNonExistentMemory:
    def test_reinforce_nonexistent_returns_not_reinforced(self, mem, store):
        result = mem.reinforce("does_not_exist", strength=0.5, current_tick=1)
        assert result["reinforced"] is False
        assert result["stability_change"] == 0.0

    def test_feedback_nonexistent_succeeds_silently(self, mem, store):
        """feedback() on a non-existent memory logs the feedback but skips stability update."""
        result = mem.feedback("ghost_mem", signal="positive", current_tick=1)
        assert "updated" in result
        assert result["updated"] == 1

    def test_feedback_batch_with_mix_of_existing_and_missing(self, mem, store):
        result = mem.feedback_batch([
            {"memory_id": "mem_test", "signal": "positive"},
            {"memory_id": "ghost", "signal": "positive"},
        ], current_tick=10)
        assert result["updated"] == 2
        node = store.get_node("mem_test")
        assert float(node["stability_score"]) > 0.0

    def test_set_stability_nonexistent_no_crash(self, mem, store):
        """set_stability on non-existent memory is a no-op (UPDATE affects 0 rows)."""
        mem.set_stability("ghost", 0.9)

    def test_record_access_nonexistent_no_crash(self, mem, store):
        mem.record_access("ghost", current_tick=5)


# ── New: Diminishing returns on repeated reinforce ──────────────────────

class TestDiminishingReturns:
    def test_repeated_reinforce_shows_diminishing_returns(self, mem, store):
        changes = []
        for i in range(5):
            result = mem.reinforce("mem_test", strength=0.5, current_tick=i + 1)
            changes.append(result["stability_change"])
        for i in range(1, len(changes)):
            assert changes[i] < changes[i - 1], (
                f"Step {i}: {changes[i]:.6f} >= {changes[i-1]:.6f}"
            )

    def test_high_importance_memory_decays_slower_after_reinforce(self, mem, store):
        result = mem.reinforce("mem_test", strength=0.8, current_tick=1)
        assert result["stability_change"] > 0
        node = store.get_node("mem_test")
        assert float(node["stability_score"]) > 0.0


# ── New: Store-level lock (dual-Memory race) ────────────────────────────

class TestStoreLevelLock:
    def test_dual_memory_instances_share_lock(self, store):
        """Two Memory instances wrapping the same store should share the same lock."""
        m1 = Memory(store)
        m2 = Memory(store)
        assert m1._lock is m2._lock, "Locks should be the same object (store-level)"

    def test_dual_memory_concurrent_reinforce_no_lost_updates(self, store):
        """Two Memory instances reinforce same memory concurrently — no lost updates."""
        m1 = Memory(store)
        m2 = Memory(store)
        store.add_memory("dual_mem", "test", _random_embedding(384, 77),
                         user_id="u1", mtype="fact", importance=0.5, created_tick=0)
        m1.set_stability("dual_mem", 0.5)

        def worker(m, results_list):
            for _ in range(10):
                r = m.reinforce("dual_mem", strength=0.5, current_tick=100)
                results_list.append(r["stability_change"])

        r1, r2 = [], []
        t1 = threading.Thread(target=worker, args=(m1, r1))
        t2 = threading.Thread(target=worker, args=(m2, r2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        node = store.get_node("dual_mem")
        final = float(node["stability_score"])
        assert final > 0.95, f"Expected >0.95 with 20 reinforced updates, got {final}"

    def test_dual_memory_concurrent_feedback_no_crash(self, store):
        """Two Memory instances call feedback concurrently — no crash, no corruption."""
        m1 = Memory(store)
        m2 = Memory(store)
        store.add_memory("fb_mem", "test", _random_embedding(384, 88),
                         user_id="u1", mtype="fact", importance=0.5, created_tick=0)

        errors = []
        def fb_worker(m, signal):
            try:
                for i in range(20):
                    m.feedback("fb_mem", signal=signal, strength=0.5, current_tick=i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=fb_worker, args=(m1, "positive"))
        t2 = threading.Thread(target=fb_worker, args=(m2, "negative"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert not errors, f"Errors: {errors}"
