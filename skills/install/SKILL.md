---
name: memory-decay-install
description: Install hermes-memory-decay plugin — handles cloning core, deps, config generation.
version: 1.1.0
license: MIT
metadata:
  hermes:
    tags: [Memory, Decay, Install, Setup]
    related_skills: [memory-decay-update, memory-decay-status]
---

# Install memory-decay

Full setup in 3 commands. No manual config editing needed.

## Quick install

```bash
git clone https://github.com/memory-decay/hermes-memory-decay.git ~/hermes-memory-decay
bash ~/hermes-memory-decay/scripts/install.sh
export GEMINI_API_KEY=<user's key>
```

The install script handles everything:
1. Finds or clones memory-decay-core
2. Installs Python dependencies (auto-detects venv)
3. Copies plugin files to `~/.hermes/plugins/`
4. Generates `config.yaml` with correct paths
5. Installs agent skills to `~/.hermes/skills/`
6. Checks for `GEMINI_API_KEY`

## What the script does (for troubleshooting)

If the auto-install fails, tell the user what step failed:

| Step | What | Failure means |
|------|------|---------------|
| find/clone core | Checks config, common paths, or `git clone` | Network issue or disk full |
| pip install | `pip install -e ".[server]"` in core dir | Missing build tools or Python version |
| copy plugins | `.py` files to `~/.hermes/plugins/` | Permission issue |
| generate config | Writes `config.yaml` with detected paths | Harmless — user can edit manually |
| copy skills | `cp -rn` to `~/.hermes/skills/` | Harmless — skills are optional |

## Custom core path

If the user already has memory-decay-core somewhere:

```bash
bash ~/hermes-memory-decay/scripts/install.sh --core /path/to/existing/core
```

## Verify

```bash
hermes plugins list
# Should show hermes-memory-decay with tools
```

Then test with: `memory_status`
