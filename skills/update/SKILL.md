---
name: memory-decay-update
description: Check for and apply updates to the hermes-memory-decay plugin and memory-decay-core.
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [Memory, Decay, Update, Upgrade, Version]
    related_skills: [memory-decay-install, memory-decay-status]
---

# Update memory-decay

Check for and apply updates. Preserves user config and memory database.

## When to check

- User asks "is there an update?" or "check for updates"
- User mentions a version number or changelog
- After installing for the first time (verify it's latest)
- Periodically — if the plugin hasn't been updated in a while

## Check (no changes)

Run this first to see if updates exist without changing anything:

```bash
bash ~/hermes-memory-decay/scripts/install.sh --check
```

Output tells you:
- Installed version vs latest release
- Number of pending commits for plugin and core
- Whether an update is needed

## Apply update

If updates are available (or user explicitly asks):

```bash
bash ~/hermes-memory-decay/scripts/install.sh --update
```

This does:
1. `git pull --ff-only` on hermes-memory-decay repo
2. `git pull --ff-only` on memory-decay-core repo
3. Reinstall core Python deps
4. Overwrite plugin .py files (code updates)
5. **Preserve** `config.yaml` (user settings)
6. **Preserve** `~/.hermes/memory-decay/memories.db` (memories)
7. Update skills (no-clobber — user edits preserved)

## What is NOT preserved

- Plugin source files (.py, plugin.yaml) — always overwritten with latest
- Skills — new/updated files are copied in, but existing files are not overwritten

## After update

1. Restart Hermes to load the new plugin code
2. Verify: `hermes plugins list`
3. Quick health check: `memory_status` tool

## Install path variants

If the repo is cloned somewhere else:

```bash
bash /path/to/hermes-memory-decay/scripts/install.sh --update
```

Or if using the agent-browser to run it, find the repo path first:

```bash
find ~ -name "install.sh" -path "*/hermes-memory-decay/*" 2>/dev/null
```
