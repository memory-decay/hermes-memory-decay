# hermes-memory-decay

Human-like memory with natural decay for [Hermes Agent](https://github.com/openclaw/hermes-agent).

Memories strengthen on recall and fade over time — like real memory. The plugin wraps [memory-decay-core](https://github.com/memory-decay/memory-decay-core) as a sidecar server, giving the agent tools to store, search, and delete persistent memories across sessions.

## Quick Start

Paste this into Claude Code, Hermes Agent, or any terminal:

```
git clone https://github.com/memory-decay/hermes-memory-decay.git ~/hermes-memory-decay
bash ~/hermes-memory-decay/scripts/install.sh
```

That's it. The script:
1. Finds or clones memory-decay-core
2. Installs Python dependencies
3. Copies plugin files to `~/.hermes/plugins/`
4. Generates `config.yaml` with detected paths
5. Installs skills to `~/.hermes/skills/`
6. Optional: warns if embedding API key missing

Verify installation:

```
hermes plugins list
```

### Embedding API key (optional)

For semantic search embeddings, set an API key. Supports multiple providers:

| Provider | Env var | Setup |
|----------|---------|-------|
| `gemini` (default) | `GEMINI_API_KEY` | `export GEMINI_API_KEY=your-key` |
| `openai` | `OPENAI_API_KEY` | `export OPENAI_API_KEY=your-key` + set `embedding_provider: openai` in config |
| `local` | — | No key needed. Set `embedding_provider: local` in config |

Or skip it entirely — the plugin works without embeddings (keyword-only search).

## Update

Re-run the same script. It preserves your `config.yaml` and memory database:

```
bash ~/hermes-memory-decay/scripts/install.sh --update
```

Or if you cloned elsewhere:

```
bash scripts/install.sh --update
```

What gets updated:
| Path | Behavior |
|------|----------|
| `~/.hermes/plugins/hermes-memory-decay/*.py` | Overwritten (code updates) |
| `~/.hermes/plugins/hermes-memory-decay/config.yaml` | Preserved |
| `~/.hermes/skills/memory-decay/` | New/updated files added, existing untouched |
| `~/.hermes/memory-decay/memories.db` | Never touched |
| `memory-decay-core` | `git pull --ff-only` |
| `hermes-memory-decay` | `git pull --ff-only` |

## Configuration

Config lives at `~/.hermes/plugins/hermes-memory-decay/config.yaml` (auto-generated on install, preserved on update):

```yaml
memory_decay_path: /home/you/.local/share/hermes-memory-decay/memory-decay-core
python_path: python3
port: 8100
db_path: ~/.hermes/memory-decay/memories.db
embedding_provider: gemini          # gemini | openai | local
embedding_api_key_env: GEMINI_API_KEY
tick_interval_seconds: 3600        # 1 hour per decay tick
auto_start_server: true
```



## Tools

| Tool | Description |
|------|-------------|
| `memory_search` | Search memories by semantic similarity |
| `memory_store` | Store a new memory (type, importance, associations) |
| `memory_store_batch` | Store multiple memories in one call |
| `memory_forget` | Delete a specific memory by ID |
| `memory_status` | Server health and memory statistics |

## Install Script Options

```bash
bash install.sh                  # Fresh install
bash install.sh --update         # Update repos + plugin files
bash install.sh --core /path     # Use existing memory-decay-core at /path
bash install.sh -h               # Help
```

Respects `HERMES_HOME` if set (defaults to `~/.hermes`).

## Architecture

```
hermes-memory-decay/
├── scripts/install.sh           # All-in-one installer + updater
├── src/hermes_memory_decay/
│   ├── __init__.py              # Plugin entry: register(ctx), hooks
│   ├── config.py                # Config loading (YAML, no PyYAML required)
│   ├── http_client.py           # urllib client (zero-dep)
│   ├── server_manager.py        # Sidecar lifecycle, PID file, port check
│   ├── schemas.py               # Tool JSON schemas
│   ├── tools.py                 # Tool handlers (fail-soft)
│   ├── prompt.py                # System prompt injection
│   └── plugin.yaml              # Hermes plugin manifest
├── skills/                      # Agent skills (remember, recall, forget, ...)
├── tests/                       # pytest suite
└── pyproject.toml
```

## Features

- **Zero external deps** — stdlib only (`urllib`, built-in YAML parser)
- **Auto-install** — clones memory-decay-core, installs deps, generates config
- **Idempotent update** — re-run anytime, config and data preserved
- **Fault-tolerant** — errors return JSON, never crash the agent loop
- **Cross-platform** — Linux, macOS, WSL
- **Port collision detection** — fails fast with clear message
- **Orphan cleanup** — PID file + atexit prevents zombie servers
- **Secure** — API keys via env var, never CLI args
- **No-clobber skills** — user customizations preserved on reinstall

## Development

```bash
python3 -m pytest tests/ -v
```

## License

MIT
