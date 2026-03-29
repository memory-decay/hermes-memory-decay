---
name: hermes-memory-decay-dev
description: Develop and test the hermes-memory-decay plugin. Covers project structure, testing, install verification, and Hermes integration checks.
version: 1.0.0
author: Roach
license: MIT
metadata:
  hermes:
    tags: [memory-decay, hermes, plugin, testing, development]
    related_skills: [systematic-debugging, test-driven-development, claude-code]
---

# hermes-memory-decay Development

Hermes Agent plugin that wraps memory-decay-core as persistent memory with
natural decay. This skill covers development workflow and testing.

## Project Layout

```
~/workspace/hermes-memory-decay/
  src/hermes_memory_decay/
    __init__.py          # register(ctx) entry point, hooks, check_fn
    plugin.yaml          # manifest (name, version, requires_env, provides_tools/hooks)
    config.py            # config.yaml loader with PyYAML fallback parser
    server_manager.py    # subprocess lifecycle (spawn, health-check, orphan cleanup)
    http_client.py       # urllib-only HTTP client (zero external deps)
    schemas.py           # OpenAI-format tool schemas
    tools.py             # tool handlers (search, store, batch, forget, status)
    prompt.py            # system prompt fragment for pre_llm_call hook
  skills/                # Hermes agent skills (SKILL.md files)
  scripts/install.sh     # all-in-one installer/updater
  tests/
    conftest.py          # adds src/ to sys.path
    test_tools.py        # tool handler tests (mocked server)
    test_server_manager.py  # subprocess management tests
    test_http_client.py  # HTTP client tests
```

## Key Paths

| What | Path |
|------|------|
| Plugin source | `~/workspace/hermes-memory-decay/src/hermes_memory_decay/` |
| Installed plugin | `~/.hermes/plugins/hermes-memory-decay/` |
| Installed skills | `~/.hermes/skills/memory-decay/` |
| Config | `~/.hermes/plugins/hermes-memory-decay/config.yaml` |
| Core repo | `~/workspace/memory-decay-core/` |
| Core DB (existing) | `~/workspace/memory-decay-core/data/memories.db` |
| GitHub | `github.com/memory-decay/hermes-memory-decay` |

## Architecture

```
Hermes Agent
  └─ plugin loader → __init__.py:register(ctx)
       ├─ registers 5 tools (memory_search/store/batch/forget/status)
       ├─ registers 3 hooks (on_session_start, on_session_end, pre_llm_call)
       └─ ServerManager (subprocess)
            └─ memory-decay-core server (FastAPI, port 8100)
                 └─ SQLite DB (memories.db)
```

- Plugin is pure Python stdlib (urllib only, no pip deps)
- memory-decay-core is a separate Python package (pip install -e)
- Communication: HTTP JSON over localhost
- API key passed via env var (not CLI args — avoids ps leakage)

## Quick Commands

### Run tests

```bash
cd ~/workspace/hermes-memory-decay
python3 -m pytest tests/ -v
```

### Install/update plugin to Hermes

```bash
bash ~/workspace/hermes-memory-decay/scripts/install.sh --update
```

### Check for updates (dry-run)

```bash
bash ~/workspace/hermes-memory-decay/scripts/install.sh --check
```

### Verify plugin loads in Hermes

```bash
hermes plugins list
hermes chat -q "Run memory_status tool"
```

### Check memory system health

```bash
# From within Hermes session, or via HTTP directly:
curl -s http://127.0.0.1:8100/health
curl -s http://127.0.0.1:8100/stats
```

## Testing Procedures

### 1. Unit Tests (always run)

```bash
cd ~/workspace/hermes-memory-decay
python3 -m pytest tests/ -v
# Expect: 26 passed
```

### 2. Clean Install Test (FAKE_HOME)

Simulates first-time install without touching real Hermes:

```bash
FAKE_HOME=$(mktemp -d)
HERMES_HOME="$FAKE_HOME/.hermes" HOME="$FAKE_HOME" \
  bash ~/workspace/hermes-memory-decay/scripts/install.sh \
  --core ~/workspace/memory-decay-core

# Verify:
grep db_path "$FAKE_HOME/.hermes/plugins/hermes-memory-decay/config.yaml"
# Should show: db_path: /home/roach/workspace/memory-decay-core/data/memories.db
# (auto-detected existing DB, NOT the default empty path)

rm -rf "$FAKE_HOME"
```

### 3. Syntax Check (install.sh)

```bash
bash -n ~/workspace/hermes-memory-decay/scripts/install.sh && echo "OK"
```

### 4. Full Integration Test

```bash
# Reinstall
bash ~/workspace/hermes-memory-decay/scripts/install.sh --update

# Verify in Hermes
hermes plugins list
hermes chat -q "Run memory_status tool"
# Should show status: ok, num_memories: 14+
```

## Plugin Conventions (Hermes)

When modifying `__init__.py`, follow these rules:

- **`ctx.register_tool()`** must include `check_fn`, `requires_env`, `emoji` (real emoji char)
- **`check_fn`** must be fast (<100ms), no server connections — just validate prereqs
- **`handler(args, **kwargs) -> str`** returns JSON, catches all exceptions internally
- **Hook `pre_llm_call`** returns `{"context": "..."}` to inject system prompt fragment
- **Hook `on_session_start`** calls `ensure_running()` + `auto_tick()`
- **No external deps** in plugin code — urllib only

## Common Pitfalls

### write_file truncates .sh files

`write_file` sometimes produces 0-byte files for shell scripts.
**Workaround:** Use `terminal(cat > file.sh << 'EOF' ... EOF)` or `execute_code` with heredoc.

### install.sh stdout/stderr separation

Functions called in `$()` must send logs to `>&2`.
Stdout is reserved for data capture (e.g., `python_path` from `install_core_deps`).

### check_api_key syntax

The grep command in `check_api_key` was previously broken (truncated).
Verify with `bash -n scripts/install.sh` after any edit.

### Port 8100 conflicts

If a previous session left the server running, `install.sh --update` + `hermes chat`
will fail with "Port 8100 already in use". Kill orphan:

```bash
# Find and kill
lsof -ti:8100 | xargs kill -9 2>/dev/null
# Or clean PID file
rm -f ~/.hermes/memory-decay/server.pid
```

### memory-decay-core must be pip installed

```bash
cd ~/workspace/memory-decay-core
.venv/bin/python -m pip install -e '.[server]'
```

If PEP 668 error on system Python, use the venv (auto-detected by installer).

## Installer Modes

| Mode | Command | What it does |
|------|---------|-------------|
| Fresh install | `bash install.sh` | Clone core, pip install, generate config, deploy |
| Update | `bash install.sh --update` | git pull both repos, overwrite plugin files, preserve config+DB |
| Check | `bash install.sh --check` | Compare versions, count pending commits (no changes) |
| Custom core | `bash install.sh --core /path` | Use existing memory-decay-core at /path |

## Commit + Push Checklist

```bash
# 1. Tests pass
python3 -m pytest tests/ -v

# 2. Syntax check
bash -n scripts/install.sh

# 3. Clean install test (FAKE_HOME)
FAKE_HOME=$(mktemp -d) && HERMES_HOME="$FAKE_HOME/.hermes" HOME="$FAKE_HOME" bash scripts/install.sh --core ~/workspace/memory-decay-core && rm -rf $FAKE_HOME

# 4. Commit and push
git add -A && git commit -m "description" && git push
```
