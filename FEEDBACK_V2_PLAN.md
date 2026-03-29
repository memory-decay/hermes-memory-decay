strength. `reinforce(strength=0.5)` and `set_stability(0.5)` are inconsistent in practice.

**Fix:** Treat `strength` as the proportion of the gap to close, not a raw multiplier:
```
decay_rate_new = decay_rate * (1 - strength * 0.6)
stability_new  = min(1.0, stability + (1 - stability) * strength * 0.6)
```
With strength=0.5: decay_rate reduced by 30%, stability gains 30% of the remaining gap.

**File:** `core/memory.py` — `reinforce()` method

---

### Issue 2 — negative feedback is erased by next search reinforcing (HIGH)

**Problem:** When user gives negative feedback on a memory, `decay_rate` is pushed up. But the very
next `search()` call runs `reinforce()` on matched memories, which can push `decay_rate` back down
before the user ever sees the effect. Negative feedback becomes invisible.

**Fix:** `reinforce()` must check `self.feedback_log` for recent (≤ DECAY_TICKS_WINDOW=100 ticks)
negative entries for the same memory and **refuse to reduce decay_rate** if any exist.

**File:** `core/memory.py` — `reinforce()` method

---

### Issue 3 — lost update risk in read-compute-write sequences (MEDIUM)

**Problem:** The pattern `val = get_x(); val = compute(val); set_x(val)` is not atomic. Concurrent
access (e.g., background reinforcement + user feedback) can cause lost updates.

**Fix:** Wrap all feedback operations in `_apply_feedback()` using the existing `Lock`-based
transaction pattern. `reinforce()` already does this; `set_stability()` and `record_access()`
must be updated to match.

**File:** `core/memory.py` — `set_stability()`, `record_access()`, and `reinforce()` methods

---

### Issue 4 — contradictory signals in same batch silently merge (MEDIUM)

**Problem:** If the same batch contains both `positive` and `negative` signals for the same
memory, they are both appended to `feedback_log` and both applied to `decay_rate`. The net result
may be correct (both signals recorded) but the response does not warn the caller.

**Fix:** Detect contradictory signals in `_apply_feedback()`. If both exist for the same memory
in the same batch, apply both (they both get recorded in feedback_log) but set
`response["conflicting"] = True`. Callers can then surface a warning.

**File:** `core/memory.py` — `_apply_feedback()` method

---

### Issue 5 — `reinforce()` does not update `last_activated_tick` (HIGH)

**Problem:** `reinforce()` reduces decay_rate but does NOT update `last_activated_tick`. A memory
that is reinforced every tick (because it matches the user's search) gets its decay_rate
continuously reduced, but `last_activated_tick` stays frozen. This means:
- Memory appears "freshly accessed" even if not recently used
- `stability` appears high even when the memory is rarely actually accessed

**Fix:** `reinforce()` must call `record_access()` to update `last_activated_tick`, so that
subsequent `step()` calls correctly account for time-based decay. `record_access()` itself must
also use the lock-based transaction pattern (Issue 3).

**File:** `core/memory.py` — `reinforce()` and `record_access()` methods

---

## Implementation Order

1. Fix `record_access()` to use lock-based transaction (Issue 3 prerequisite)
2. Fix `set_stability()` to use lock-based transaction (Issue 3)
3. Fix `reinforce()` — add negative feedback check (Issue 2) + update `last_activated_tick` (Issue 5)
   + use corrected stability formula (Issue 1)
4. Fix `_apply_feedback()` — detect contradictory signals (Issue 4)
5. Write/update tests to cover all five issues

---

## File to Modify

- `hermes-memory-decay/core/memory.py`

## Test File

- `hermes-memory-decay/tests/test_memory.py` (existing — extend)

---

## Verification

```bash
cd /home/roach/workspace/hermes-memory-decay-feedback-v2
source venv/bin/activate
python -m pytest tests/ -q
```

All 5 issues must be verified by test cases.
