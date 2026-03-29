- **Fault-tolerant**: Memory is a nice-to-have; errors never break the agent loop

## Prerequisites

- **Python 3.10+**
- **memory-decay-core** installed:
  ```bash
  cd ~/workspace/memory-decay-core
  pip install -e ".[server]"
  ```
- **Embedding provider** configured (one of):
  - `gemini`: Set `GEMINI_API_KEY` env var
  - `openai`: Set `OPENAI_API_KEY` env var
  - `local`: Requires `torch` + `sentence-transformers`

## Installation

### Option 1: Install script

```bash
git clone https://github.com/memory-decay/hermes-memory-decay.git
cd hermes-memory-decay
bash scripts/install.sh
```

### Option 2: Manual copy

```bash
mkdir -p ~/.hermes/plugins/hermes-memory-decay
cp src/hermes_memory_decay/*.py ~/.hermes/plugins/hermes-memory-decay/
cp src/hermes_memory_decay/plugin.yaml ~/.hermes/plugins/hermes-memory-decay/
cp src/hermes_memory_decay/config.yaml.example ~/.hermes/plugins/hermes-memory-decay/config.yaml
# Edit config.yaml with your paths
```

### Option 3: pip (for entry-point discovery)

```bash
pip install -e .
```

## Configuration

Copy `config.yaml.example` to `config.yaml` in the plugin directory and customize:

```yaml
python_path: python3
memory_decay_path: ~/workspace/memory-decay-core
port: 8100
db_path: ~/.hermes/memory-decay/memories.db
embedding_provider: gemini
embedding_api_key_env: GEMINI_API_KEY
tick_interval_seconds: 3600
auto_start_server: true
```

See `config.yaml.example` for all available options.

## Available tools

| Tool | Description |
|------|-------------|
| `memory_search` | Search memories by semantic similarity |
| `memory_store` | Store a new memory with importance and type |
| `memory_store_batch` | Store multiple memories efficiently |
| `memory_forget` | Delete a specific memory by ID |
| `memory_status` | Check memory system health and statistics |

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test file
pytest tests/test_http_client.py -v
```

## License

MIT
