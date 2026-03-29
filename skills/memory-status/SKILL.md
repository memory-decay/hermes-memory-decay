---
name: memory-decay-status
description: Check memory system health and statistics.
version: 1.1.0
license: MIT
metadata:
  hermes:
    tags: [Memory, Decay, Status, Health, Debugging]
    related_skills: [memory-decay-remember, memory-decay-recall, memory-decay-forget, memory-decay-install]
---

# Memory Status

Check system health with `memory_status`. Keep the report concise.

If unreachable:
- `curl http://127.0.0.1:8100/health`
- `hermes gateway restart`
- Check `~/.hermes/plugins/hermes-memory-decay/config.yaml`
