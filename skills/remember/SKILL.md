   - `category`: Best-fit category -- do NOT default everything to "fact"
   - `mtype`: Memory type matching the category (fact, episode, preference, decision)

4. **Confirm** what was saved, including the category and importance used.

## Batch Mode

When multiple memories should be saved at once (e.g., end of a productive session), use `memory_store_batch` with an `items` array. More efficient than repeated individual stores.

Example:
```json
{
  "items": [
    {"text": "User prefers dark mode", "importance": 0.9, "category": "preference", "mtype": "preference"},
    {"text": "Decided to use Redis for caching", "importance": 0.85, "category": "decision", "mtype": "decision"},
    {"text": "Auth middleware migration completed", "importance": 0.4, "category": "episode", "mtype": "episode"}
  ]
}
```

## Importance Calibration Guide

| Situation | Importance | Reasoning |
|-----------|------------|-----------|
| User says "remember this" | 0.9-1.0 | Explicit request, high intent |
| User corrects a mistake | 0.85-0.95 | Prevents future errors |
| Technical decision with rationale | 0.8-0.9 | Guides future choices |
| Discovered API behavior / bug | 0.7-0.85 | Reference for debugging |
| User preference (likes/dislikes) | 0.8-1.0 | High retention, used often |
| Session summary / what was done | 0.3-0.5 | Transient, fades naturally |
| Completed task / feature | 0.4-0.6 | Useful context but not critical |

## What NOT to Store

- Ephemeral instructions that won't matter next session
- Information easily re-discovered (e.g., "run `ls` to see files")
- Temporary task progress (use session_search instead)
- Raw data dumps or full conversation transcripts
- Trivial/obvious information

## Rules

- Do NOT write memory files to any file path. Always use `memory_store` / `memory_store_batch`.
- If the user provides specific text, store it verbatim.
- If the user references the conversation, summarize the relevant context before storing.
- Don't wait for a command -- store proactively when the conditions above are met.
- Prefer `preference` for user corrections over `fact`.
