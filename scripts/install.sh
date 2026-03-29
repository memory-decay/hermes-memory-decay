#!/usr/bin/env bash
# Install hermes-memory-decay plugin to Hermes plugins directory
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Respect HERMES_HOME like Hermes itself does (plugins.py L190)
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_DIR="$HERMES_HOME/plugins/hermes-memory-decay"
SKILLS_DIR="$HERMES_HOME/skills/memory-decay"

echo "Installing hermes-memory-decay plugin..."
echo "  Repo:   $REPO_DIR"
echo "  Hermes: $HERMES_HOME"
echo "  Plugin: $PLUGIN_DIR"

# Pre-flight checks
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+ first."
    exit 1
fi

# Create plugin directory
mkdir -p "$PLUGIN_DIR"

# Copy plugin source files
cp "$REPO_DIR/src/hermes_memory_decay/"*.py "$PLUGIN_DIR/"
cp "$REPO_DIR/src/hermes_memory_decay/plugin.yaml" "$PLUGIN_DIR/"

# Copy config example (never overwrite existing config.yaml)
if [ -f "$PLUGIN_DIR/config.yaml" ]; then
    echo "  Existing config.yaml preserved."
else
    if [ -f "$REPO_DIR/src/hermes_memory_decay/config.yaml.example" ]; then
        cp "$REPO_DIR/src/hermes_memory_decay/config.yaml.example" "$PLUGIN_DIR/config.yaml.example"
    fi
    # Generate a starter config.yaml with user-specific paths
    cat > "$PLUGIN_DIR/config.yaml" << GENEOF
# hermes-memory-decay configuration
# See config.yaml.example for all options

# IMPORTANT: Set these to absolute paths for your environment
# memory_decay_path: /path/to/memory-decay-core
# python_path: /path/to/venv/bin/python  (or leave as python3 if installed globally)

# Uncomment and edit after installing memory-decay-core:
# memory_decay_path: ~/workspace/memory-decay-core
# embedding_provider: gemini
# embedding_api_key_env: GEMINI_API_KEY
GENEOF
    echo "  Created config.yaml -- EDIT THIS before first use."
fi

# Copy skills (merge, don't clobber)
if [ -d "$REPO_DIR/skills" ]; then
    mkdir -p "$SKILLS_DIR"
    cp -r "$REPO_DIR/skills/"* "$SKILLS_DIR/"
    echo "  Skills installed to: $SKILLS_DIR"
fi

echo ""
echo "Installed successfully."
echo ""
echo "Before first use, edit the config:"
echo "  nano $PLUGIN_DIR/config.yaml"
echo ""
echo "Required settings:"
echo "  memory_decay_path  -- absolute path to memory-decay-core repo"
echo "  python_path         -- python from memory-decay-core venv"
echo "  embedding_api_key_env -- env var with your embedding API key"
echo ""
echo "Then verify:"
echo "  hermes plugins list"
echo ""
