# hermes-memory-decay -- Quick Start

The memory-decay plugin is now installed. Your agent has human-like memory that naturally decays over time.

## Setup

1. **Configure the plugin:**
   ```bash
   cp ~/.hermes/plugins/hermes-memory-decay/config.yaml.example \
      ~/.hermes/plugins/hermes-memory-decay/config.yaml
   # Edit config.yaml with your paths and embedding provider
   ```

2. **Install memory-decay-core** (if not already):
   ```bash
   cd ~/workspace/memory-decay-core
   pip install -e ".[server]"
   ```

3. **Set your API key** for the embedding provider:
   ```bash
   export GEMINI_API_KEY="your-key-here"  # or OPENAI_API_KEY
   ```

## Usage

The memory server starts automatically when you begin a Hermes session. The agent can:

- **Search** past memories with `memory_search`
- **Store** new memories with `memory_store`
- **Batch store** with `memory_store_batch`
- **Forget** specific memories with `memory_forget`
- **Check status** with `memory_status`

Memories naturally fade over time but are reinforced when recalled -- just like human memory.
