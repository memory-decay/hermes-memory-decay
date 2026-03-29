---
name: memory-decay-remember
description: Store important information into persistent memory with proper type classification and association linking.
version: 1.1.0
license: MIT
metadata:
  hermes:
    tags: [Memory, Decay, Remember, Store, Persistence]
    related_skills: [memory-decay-recall, memory-decay-forget, memory-decay-status, memory-decay-install]
---

# Remember -- Store Memories

Store important information using `memory_store` or `memory_store_batch`.

## Pre-flight: Search Before Storing

Before storing, do a quick `memory_search` to:
1. **Avoid duplicates** -- if it already exists, skip or update via forget+store
2. **Find association targets** -- link new memories to related existing ones

## Classification

| mtype | When | importance | example |
|-------|------|------------|---------|
| preference | User likes/dislikes, style, workflow | 0.8-1.0 | "Korean for conversation" |
| decision | Choice made with rationale | 0.8-0.9 | "SQLite over Postgres -- single-node" |
| fact | Technical knowledge, env detail, API quirk | 0.7-0.9 | "Auth returns 4xx on token expiry" |
| episode | Session event, task completed | 0.3-0.6 | "Migrated auth middleware to v2" |

**category** is independent from mtype. Use free-text tags: `backend`, `deploy`, `auth`, `config`, `debugging`, etc.

## Association Pattern

When a new memory relates to an existing one, link them:

```
1. memory_search("related topic")  → finds mem_abc123
2. memory_store(text="new detail", associations=["mem_abc123"])
```

Associations enable the testing effect: recalling one memory boosts the other.

## End-of-Session Batch

At the end of a productive session, batch-store key takeaways:

```
memory_store_batch({
  "items": [
    {"text": "Decided to use Redis for session cache", "mtype": "decision", "category": "architecture", "importance": 0.85},
    {"text": "Fixed race condition in order service", "mtype": "episode", "category": "debugging", "importance": 0.4},
    {"text": "User prefers short commit messages", "mtype": "preference", "importance": 0.9}
  ]
})
```

## What NOT to Store

- Ephemeral instructions (re-discoverable next session)
- Temporary task progress (use session_search)
- Raw data dumps or full conversation transcripts
- Trivial/obvious information
