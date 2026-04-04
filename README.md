# hermes-memory-decay

Human-like memory with natural decay for [Hermes Agent](https://github.com/openclaw/hermes-agent).

Memories strengthen on recall and fade over time — like real memory. Wraps [memory-decay-core](https://github.com/memory-decay/memory-decay-core) as a sidecar server.

## Quick Start

```bash
git clone https://github.com/memory-decay/memory-decay-core.git ~/memory-decay-core
cd ~/memory-decay-core && pip install -e ".[local]"

git clone https://github.com/memory-decay/hermes-memory-decay.git ~/hermes-memory-decay
pip install -e ~/hermes-memory-decay
```

Then configure:

```bash
hermes memory setup → select hermes-memory-decay → enter: /home/you/memory-decay-core
```

Or use the installer:

```bash
bash ~/hermes-memory-decay/scripts/install.sh
```

Verify:

```bash
hermes plugins list
```

## Embedding Providers

| Provider | API Key? | Notes |
|----------|----------|-------|
| `local` (default) | No | Uses `sentence-transformers`. Runs on CPU or GPU. |
| `gemini` | `GEMINI_API_KEY` | Google's embedding API. |
| `openai` | `OPENAI_API_KEY` | OpenAI-compatible API. |

For local embeddings, install with:

```bash
cd ~/memory-decay-core && pip install -e ".[local]"
```

## Configuration

Config lives at `~/.hermes/plugins/hermes-memory-decay/config.yaml`:

```yaml
memory_decay_path: "/home/you/memory-decay-core"
port: "8100"
db_path: "/home/you/.hermes/memory-decay/memories.db"
embedding_provider: "local"
tick_interval_seconds: 3600
auto_start_server: true
```

## Tools

| Tool | Description |
|------|-------------|
| `memory_search` | Search memories by semantic similarity |
| `memory_store` | Store a new memory |
| `memory_store_batch` | Store multiple memories at once |
| `memory_forget` | Delete a specific memory by ID |
| `memory_status` | Server health and memory statistics |

## Architecture

```
hermes-memory-decay/
├── scripts/install.sh
├── src/hermes_memory_decay/
│   ├── __init__.py            # Thin package stub
│   ├── memory_provider.py     # MemoryProvider ABC implementation
│   ├── http_client.py         # Zero-dep HTTP client
│   ├── server_manager.py      # Server subprocess lifecycle
│   ├── config.py              # Config loading
│   └── schemas.py             # Tool JSON schemas
├── skills/                    # Agent skills
├── tests/                     # pytest suite
└── pyproject.toml
```

The plugin registers as a **MemoryProvider** via `plugins/memory/hermes-memory-decay/` in your Hermes Agent installation. The MemoryManager routes tool calls and lifecycle hooks automatically.

## Update

```bash
bash ~/hermes-memory-decay/scripts/install.sh --update
```

Preserves your `config.yaml` and memory database.

## Development

```bash
pytest tests/ -v
```

## License

MIT
