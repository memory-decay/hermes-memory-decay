# hermes-memory-decay

Human-like memory with natural decay for [Hermes Agent](https://github.com/openclaw/hermes-agent). Wraps [memory-decay-core](https://github.com/memory-decay/memory-decay-core) as a sidecar server.

Memories strengthen on recall and fade over time, just like human memory. The agent uses them proactively — recalling context before you ask, saving what matters, linking related memories together.

## How it works

```
Hermes Agent
  ├── plugin: hermes-memory-decay (this repo)
  │     ├── registers 5 tools (search, store, batch, forget, status)
  │     ├── injects system prompt via pre_llm_call hook
  │     └── auto-ticks decay on session start/end
  └── sidecar: memory-decay-core FastAPI server
        ├── SQLite storage with semantic + BM25 hybrid search
        ├── graph-based associations (testing effect)
        ├── configurable embedding providers (Gemini, OpenAI, local)
        └── time-based decay with recall reinforcement
```

## Prerequisites

- **Python 3.10+**
- **[memory-decay-core](https://github.com/memory-decay/memory-decay-core)** installed:
  ```bash
  git clone https://github.com/memory-decay/memory-decay-core.git
  cd memory-decay-core
  pip install -e ".[server]"
  ```
- **Embedding provider** (one of):
  - `gemini`: Set `GEMINI_API_KEY` env var
  - `openai`: Set `OPENAI_API_KEY` env var
  - `local`: Requires `torch` + `sentence-transformers`

## Installation

### Install script (recommended)

```bash
git clone https://github.com/memory-decay/hermes-memory-decay.git
cd hermes-memory-decay
bash scripts/install.sh
```

The script:
- Copies plugin files to `~/.hermes/plugins/hermes-memory-decay/`
- Creates a starter `config.yaml` (edit before first use)
- Installs skills to `~/.hermes/skills/memory-decay/`
- Respects `HERMES_HOME` if set

### Manual install

```bash
mkdir -p ~/.hermes/plugins/hermes-memory-decay
cp src/hermes_memory_decay/*.py ~/.hermes/plugins/hermes-memory-decay/
cp src/hermes_memory_decay/plugin.yaml ~/.hermes/plugins/hermes-memory-decay/
# Create config.yaml from example and edit it
cp src/hermes_memory_decay/config.yaml.example ~/.hermes/plugins/hermes-memory-decay/config.yaml
```

## Configuration

Edit `~/.hermes/plugins/hermes-memory-decay/config.yaml`:

```yaml
# Required — absolute path to your memory-decay-core clone
memory_decay_path: /home/you/memory-decay-core

# Python interpreter (use venv path if applicable)
python_path: python3

# Server
port: 8100
auto_start_server: true
server_startup_timeout_ms: 15000

# Embedding
embedding_provider: gemini
embedding_api_key_env: GEMINI_API_KEY

# Storage (auto-generated from HERMES_HOME if omitted)
# db_path: ~/.hermes/memory-decay/memories.db

# Decay
tick_interval_seconds: 3600  # 1 hour per tick
```

See `config.yaml.example` for all options with documentation.

## Available tools

| Tool | Description |
|------|-------------|
| `memory_search` | Search memories by semantic similarity |
| `memory_store` | Store a new memory with type, importance, associations |
| `memory_store_batch` | Store multiple memories in one call |
| `memory_forget` | Delete a specific memory by ID |
| `memory_status` | Check server health and memory statistics |

## Features

- **Zero external dependencies** — uses only stdlib (`urllib`, no `requests`)
- **PyYAML optional** — built-in simple YAML parser falls back gracefully
- **Fault-tolerant** — errors return JSON, never crash the agent loop
- **Cross-platform** — works on Linux, macOS, WSL
- **Port collision detection** — fails fast with clear message if port is taken
- **Orphan cleanup** — PID file + atexit handler prevents zombie servers
- **Secure** — API keys passed via env var, never command-line arguments
- **No-clobber install** — user-customized skills are preserved on reinstall

## Skills

The plugin includes Hermes skills that teach the agent how to use memory tools effectively:

| Skill | Purpose |
|-------|---------|
| `remember` | When and how to store memories, classification guide |
| `recall` | Proactive search triggers, query strategy, result interpretation |
| `forget` | Safe deletion workflow with user confirmation |
| `memory-status` | Health check and diagnostics |
| `install` | Installation and setup reference |

Skills are installed to `~/.hermes/skills/memory-decay/` by the install script.

## Development

```bash
# Run tests
python3 -m pytest tests/ -v

# Run specific test
python3 -m pytest tests/test_http_client.py -v

# Install script test (clean slate)
rm -rf ~/.hermes/plugins/hermes-memory-decay ~/.hermes/skills/memory-decay
bash scripts/install.sh
```

## Architecture

```
hermes-memory-decay/
├── src/hermes_memory_decay/
│   ├── __init__.py          # Plugin entry: register(ctx), hooks
│   ├── config.py            # Config loading (YAML parser, defaults, validation)
│   ├── http_client.py       # urllib HTTP client (zero-dep)
│   ├── server_manager.py    # Subprocess lifecycle, PID file, port check
│   ├── schemas.py           # Tool JSON schemas
│   ├── tools.py             # Tool handlers (fail-soft)
│   ├── prompt.py            # System prompt fragment for agent
│   └── plugin.yaml          # Hermes plugin manifest
├── scripts/install.sh       # Install to ~/.hermes/
├── skills/                  # Hermes skills (remember, recall, forget, ...)
├── tests/                   # pytest suite (26 tests)
└── pyproject.toml
```

## License

MIT
