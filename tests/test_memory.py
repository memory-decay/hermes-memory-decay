"""Tests for core/memory.py — Feedback System v2 fixes."""

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


class TestNegativeFeedbackGuard:
    def test_negative_feedback_blocks_stability_gain(self, mem, store):
        # After negative feedback, reinforce() should not increase stability
        mem.feedback("mem_test", signal="negative", current_tick=50)
        result = mem.reinforce("mem_test", strength=0.5, current_tick=51)
        # neg_feedback_blocked=True AND stability_change=0
        assert result["neg_feedback_blocked"] is True
        assert result["stability_change"] == 0.0

    def test_old_negative_does_not_block(self, mem, store):
        mem.feedback("mem_test", signal="negative", current_tick=0)
        result = mem.reinforce("mem_test", strength=0.5, current_tick=150)
        # Outside 100-tick window: negative should NOT block
        assert result["neg_feedback_blocked"] is False
        assert result["stability_change"] > 0


class TestLockBasedTransactions:
    def test_set_stability_concurrent_safety(self, store):
        m = Memory(store)
        store.add_memory("race_mem", "test", _random_embedding(384, 42),
                         user_id="u1", mtype="fact", importance=0.5, created_tick=0)
        errors = []
        def bump():
            try:
                for _ in range(50):
                    m.set_stability("race_mem", 0.9, current_tick=1)
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
