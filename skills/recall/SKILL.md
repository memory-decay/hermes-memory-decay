---
name: memory-decay-recall
description: Proactively search and retrieve past memories before responding when context would improve the answer.
version: 1.1.0
license: MIT
metadata:
  hermes:
    tags: [Memory, Decay, Recall, Search, Context]
    related_skills: [memory-decay-remember, memory-decay-forget, memory-decay-status, memory-decay-install]
---

# Recall -- Search Memories

Retrieve stored memories using `memory_search`. Be proactive, not reactive.

## When to Search (before the user asks)

- **Task kickoff**: Starting work on something you've seen before → search for past context
- **Decision point**: About to recommend an approach → search for prior decisions on similar topics
- **User preference check**: Response style might benefit from knowing user preferences → search
- **Debugging**: Error or unexpected behavior → search for past encounters with the same issue
- **Cross-session continuity**: User references "last time", "we decided", "like before" → search immediately

## Query Strategy

| Goal | Good query | Bad query |
|------|-----------|-----------|
| Past decision | "which database did we choose and why" | "database" |
| User preference | "user's preferred coding style or conventions" | "style" |
| Debug context | "race condition we fixed in order service" | "error" |
| Session history | "what we implemented for the auth migration" | "migration" |

## Presenting Results

- Show content, category, and memory ID (`mem_xxx`)
- Map storage_score to freshness:
  - **fresh** (> 0.7) -- act on it confidently
  - **normal** (0.3-0.7) -- reliable, verify if consequential
  - **stale** (< 0.3) -- warn user, may be outdated
- When results overlap, synthesize rather than listing all of them

## Rules

- Never fabricate memories if nothing is found. Say "no relevant memories found."
- Recall reinforces memories (testing effect) -- this is a feature, not a bug.
- Default top_k=5. Increase to 10 for broad sweeps ("everything about X").
