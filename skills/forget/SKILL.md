---
name: memory-decay-forget
description: Safely delete or correct stored memories. Always confirms before deletion.
version: 1.1.0
license: MIT
metadata:
  hermes:
    tags: [Memory, Decay, Forget, Delete, Correction]
    related_skills: [memory-decay-remember, memory-decay-recall, memory-decay-status, memory-decay-install]
---

# Forget -- Delete Memories

Find and permanently delete stored memories.

## Workflow

1. **Search** to find the target: `memory_search(query)`
2. **Show** matching memories with IDs and content
3. **Confirm** with the user before deleting anything
4. **Delete** with `memory_forget(memory_id)`
5. **Correct** if needed: delete old + store new version

## Rules

- Never delete without explicit user confirmation
- Always search first -- never guess memory IDs
- Deletion is permanent and irreversible
- "Forget everything about X" → search broadly, show all, confirm batch delete
