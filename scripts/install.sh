#!/usr/bin/env bash
# hermes-memory-decay — all-in-one installer and updater
#
# Usage:
#   bash install.sh              Fresh install (clone core + deps + register)
#   bash install.sh --update     Update repos + plugin files, preserve config
#   bash install.sh --check      Check if updates are available (no changes)
#   bash install.sh --core /path Use existing memory-decay-core at /path
#
# No interactive prompts — fully automatable.
#
# Environment:
#   HERMES_HOME     Override default ~/.hermes
#   MEMORY_DECAY_EMBEDDING_PROVIDER  "local" (default), "gemini", or "openai"

set -euo pipefail

# ── Args ──────────────────────────────────────────────────────────────────
MODE="install"
CORE_OVERRIDE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --update)  MODE="update"; shift ;;
        --check)   MODE="check"; shift ;;
        --core)    shift; CORE_OVERRIDE="${1:-}"; shift ;;
        -h|--help)
            sed -n '2,/^$/{ s/^# //; s/^#//; p }' "$0"
            exit 0 ;;
        *) shift ;;
    esac
done

# ── Paths ─────────────────────────────────────────────────────────────────
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$HERMES_HOME/plugins/hermes-memory-decay"
MEMORY_PLUGIN_DIR="$HERMES_HOME/hermes-agent/plugins/memory/hermes-memory-decay"
SKILLS_DIR="$HERMES_HOME/skills/memory-decay"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/hermes-memory-decay"
CORE_NAME="memory-decay-core"
CORE_REPO="https://github.com/memory-decay/memory-decay-core.git"

# ── Logging ───────────────────────────────────────────────────────────────
log()  { printf "[INFO]  %s\n" "$*"; }
warn() { printf "[WARN]  %s\n" "$*" >&2; }
err()  { printf "[ERROR] %s\n" "$*" >&2; }

# ── Version helpers ───────────────────────────────────────────────────────
get_local_version() {
    if [[ -f "$REPO_DIR/pyproject.toml" ]]; then
        grep '^version' "$REPO_DIR/pyproject.toml" | head -1 | sed 's/.*= *"//' | tr -d '"' || echo "unknown"
    else
        echo "not installed"
    fi
}

get_remote_version() {
    local version
    version=$(git ls-remote --tags --sort=-v:refname \
        "https://github.com/memory-decay/hermes-memory-decay.git" \
        'v*' 2>/dev/null | head -1 | sed 's|.*/v||' | tr -d '^{}')
    echo "${version:-unknown}"
}

get_pending_commits() {
    local repo_dir="$1"
    if [[ ! -d "$repo_dir/.git" ]]; then
        echo "0"
        return
    fi
    local count
    count=$(cd "$repo_dir" && git fetch --quiet 2>/dev/null && \
        git log HEAD..origin/main --oneline 2>/dev/null | wc -l | tr -d ' ') || echo "0"
    echo "${count:-0}"
}

# ── Detect memory-decay-core ─────────────────────────────────────────────
find_core() {
    if [[ -n "$CORE_OVERRIDE" ]]; then
        if [[ -d "$CORE_OVERRIDE/src/memory_decay" ]]; then
            echo "$CORE_OVERRIDE"
            return 0
        else
            err "Specified core path does not contain src/memory_decay/: $CORE_OVERRIDE"
            exit 1
        fi
    fi

    if [[ -f "$PLUGIN_DIR/config.yaml" ]]; then
        local existing
        existing=$(grep '^memory_decay_path:' "$PLUGIN_DIR/config.yaml" 2>/dev/null | \
            head -1 | sed 's/^memory_decay_path:[[:space:]]*//' | tr -d '"' || true)
        if [[ -n "$existing" ]]; then
            existing="${existing/#\~/$HOME}"
            if [[ -d "$existing/src/memory_decay" ]]; then
                echo "$existing"
                return 0
            fi
        fi
    fi

    local search_paths=(
        "$HOME/workspace/$CORE_NAME"
        "$HOME/projects/$CORE_NAME"
        "$HOME/dev/$CORE_NAME"
        "$HOME/src/$CORE_NAME"
        "$HOME/$CORE_NAME"
        "$DATA_DIR/$CORE_NAME"
    )
    for p in "${search_paths[@]}"; do
        if [[ -d "$p/src/memory_decay" ]]; then
            echo "$p"
            return 0
        fi
    done

    return 1
}

clone_core() {
    log "Cloning memory-decay-core ..." >&2
    mkdir -p "$DATA_DIR"
    git clone --depth 1 "$CORE_REPO" "$DATA_DIR/$CORE_NAME" >&2 || {
        err "Failed to clone memory-decay-core"
        exit 1
    }
    echo "$DATA_DIR/$CORE_NAME"
}

update_core() {
    local core_path="$1"
    if [[ -d "$core_path/.git" ]]; then
        log "Updating memory-decay-core ..."
        (cd "$core_path" && git pull --ff-only 2>&1) || warn "git pull failed for core (continuing)"
    else
        warn "memory-decay-core is not a git repo ($core_path) — skipping update"
    fi
}

# ── Install core Python deps ─────────────────────────────────────────────
install_core_deps() {
    local core_path="$1"
    local embedding_provider="${2:-local}"
    local py="python3"

    if [[ -f "$core_path/.venv/bin/python" ]]; then
        py="$core_path/.venv/bin/python"
    elif [[ -f "$core_path/venv/bin/python" ]]; then
        py="$core_path/venv/bin/python"
    fi

    if [[ "$embedding_provider" == "local" ]]; then
        log "Installing memory-decay-core with local embedding deps ..." >&2
        (cd "$core_path" && "$py" -m pip install -e ".[local]" --quiet 2>&1) || warn "pip install failed for core (continuing)"
    else
        log "Installing memory-decay-core ..." >&2
        (cd "$core_path" && "$py" -m pip install -e "." --quiet 2>&1) || warn "pip install failed for core (continuing)"
    fi

    echo "$py"
}

# ── Detect existing memories.db ──────────────────────────────────────────
find_db() {
    local core_path="$1"

    if [[ -f "$PLUGIN_DIR/config.yaml" ]]; then
        local existing
        existing=$(grep '^db_path:' "$PLUGIN_DIR/config.yaml" 2>/dev/null | \
            head -1 | sed 's/^db_path:[[:space:]]*//' | tr -d '"' || true)
        if [[ -n "$existing" ]]; then
            existing="${existing/#\~/$HOME}"
            if [[ -f "$existing" ]]; then
                echo "$existing"
                return 0
            fi
        fi
    fi

    local db_candidates=(
        "$core_path/data/memories.db"
        "$core_path/memories.db"
    )
    for f in "${db_candidates[@]}"; do
        if [[ -f "$f" ]]; then
            echo "$f"
            return 0
        fi
    done

    echo "$HERMES_HOME/memory-decay/memories.db"
}

# ── Generate config.yaml ─────────────────────────────────────────────────
generate_config() {
    local core_path="$1"
    local embedding_provider="${2:-local}"
    local db_path
    db_path=$(find_db "$core_path")

    cat > "$PLUGIN_DIR/config.yaml" << EOF
# hermes-memory-decay — auto-generated by install.sh
# Edit freely. Reinstalling (--update) will NOT overwrite this file.

memory_decay_path: "$core_path"
port: "8100"
db_path: "$db_path"
embedding_provider: "$embedding_provider"
tick_interval_seconds: 3600
auto_start_server: true
server_startup_timeout_ms: 15000
max_restarts: 3
EOF
}

# ── Register plugin with Hermes Agent ────────────────────────────────────
register_memory_provider() {
    # Create plugins/memory/hermes-memory-decay/ for MemoryProvider discovery
    mkdir -p "$MEMORY_PLUGIN_DIR"

    cat > "$MEMORY_PLUGIN_DIR/__init__.py" << 'PYEOF'
from hermes_memory_decay.memory_provider import MemoryDecayMemoryProvider

def register(ctx) -> None:
    ctx.register_memory_provider(MemoryDecayMemoryProvider())
PYEOF

    cat > "$MEMORY_PLUGIN_DIR/plugin.yaml" << YAMLEOF
name: hermes-memory-decay
version: "$(get_local_version)"
description: "Human-like memory with natural decay."
pip_dependencies: []
hooks:
  - on_session_end
YAMLEOF

    log "Memory provider registered at $MEMORY_PLUGIN_DIR"
}

# ── Deploy plugin files (pip install) ────────────────────────────────────
install_plugin_package() {
    log "Installing hermes-memory-decay package ..." >&2
    pip install -e "$REPO_DIR" --quiet 2>&1 || warn "pip install failed for plugin (continuing)"
}

deploy_skills() {
    if [[ -d "$REPO_DIR/skills" ]]; then
        mkdir -p "$SKILLS_DIR"
        cp -rn "$REPO_DIR/skills/"* "$SKILLS_DIR/" 2>/dev/null || true
        log "Skills -> $SKILLS_DIR"
    fi
}

check_api_key() {
    local provider="local"
    if [[ -f "$PLUGIN_DIR/config.yaml" ]]; then
        provider=$(grep '^embedding_provider:' "$PLUGIN_DIR/config.yaml" 2>/dev/null | \
            head -1 | sed 's/^embedding_provider:[[:space:]]*//' | tr -d '"' || echo "local")
    fi
    if [[ "$provider" == "local" ]]; then
        log "Embedding provider: local (no API key needed)"
        return
    fi

    local api_key_env="GEMINI_API_KEY"
    if [[ -f "$PLUGIN_DIR/config.yaml" ]]; then
        api_key_env=$(grep '^embedding_api_key_env:' "$PLUGIN_DIR/config.yaml" 2>/dev/null | \
            head -1 | sed 's/^embedding_api_key_env:[[:space:]]*//' | tr -d '"' || echo "GEMINI_API_KEY")
    fi
    if [[ -z "${!api_key_env:-}" ]]; then
        warn "Set $api_key_env before first use (or set embedding_provider: local):"
        warn "  export $api_key_env=your-key-here"
    else
        log "$api_key_env is set"
    fi
}

print_summary() {
    echo ""
    log "Done."
    echo ""
    echo "  Config:  $PLUGIN_DIR/config.yaml"
    echo "  Provider: $MEMORY_PLUGIN_DIR"
    echo "  Skills:  $SKILLS_DIR"
    echo "  Core:    ${core_path:-<not found>}"
    echo ""
    echo "  Verify:  hermes plugins list"
    echo "  Setup:   hermes memory setup  → select hermes-memory-decay"
    echo ""
}

# ── Check mode ────────────────────────────────────────────────────────────
do_check() {
    log "Checking for updates ..."

    local local_ver
    local_ver=$(get_local_version)
    log "  Installed version: $local_ver"

    local remote_ver
    remote_ver=$(get_remote_version)
    if [[ "$remote_ver" != "unknown" ]]; then
        log "  Latest release:    $remote_ver"
    fi

    local core_path=""
    local plugin_pending
    local core_pending="N/A"
    plugin_pending=$(get_pending_commits "$REPO_DIR")
    if core_path=$(find_core 2>/dev/null); then
        core_pending=$(get_pending_commits "$core_path")
    fi

    echo ""
    if [[ "$plugin_pending" -gt 0 ]] || [[ "$core_pending" != "N/A" && "$core_pending" -gt 0 ]]; then
        log "Updates available:"
        [[ "$plugin_pending" -gt 0 ]] && echo "  hermes-memory-decay: $plugin_pending new commits"
        [[ "$core_pending" -gt 0 ]]   && echo "  memory-decay-core:   $core_pending new commits"
        echo ""
        echo "  To update, run:"
        echo "    bash $REPO_DIR/scripts/install.sh --update"
    else
        log "Everything is up to date."
    fi
    echo ""
}

# ── Main ─────────────────────────────────────────────────────────────────
main() {
    if ! command -v python3 &>/dev/null; then
        err "python3 not found. Install Python 3.10+ first."
        exit 1
    fi
    if ! command -v git &>/dev/null; then
        err "git not found. Install git first."
        exit 1
    fi

    if [[ "$MODE" == "check" ]]; then
        do_check
        return 0
    fi

    local embedding_provider="${MEMORY_DECAY_EMBEDDING_PROVIDER:-local}"

    log "hermes-memory-decay $MODE"
    log "  Hermes:  $HERMES_HOME"
    log "  Repo:    $REPO_DIR"

    # ── Step 1: memory-decay-core ──
    core_path=""
    py_path="python3"

    if [[ "$MODE" == "update" ]]; then
        if [[ -d "$REPO_DIR/.git" ]]; then
            log "Updating hermes-memory-decay ..."
            (cd "$REPO_DIR" && git pull --ff-only 2>&1) || warn "git pull failed for plugin repo (continuing)"
        fi
        if core_path=$(find_core 2>/dev/null); then
            update_core "$core_path"
            py_path=$(install_core_deps "$core_path" "$embedding_provider")
        else
            warn "memory-decay-core not found — skipping core update"
        fi
    else
        if core_path=$(find_core 2>/dev/null); then
            :
        else
            core_path=$(clone_core)
        fi
        py_path=$(install_core_deps "$core_path" "$embedding_provider")
    fi

    # ── Step 2: Plugin package (pip install) ──
    install_plugin_package

    # ── Step 3: Register memory provider ──
    register_memory_provider

    # ── Step 4: Config ──
    if [[ -f "$PLUGIN_DIR/config.yaml" ]]; then
        log "Existing config.yaml preserved"
    elif [[ -n "$core_path" ]]; then
        generate_config "$core_path" "$embedding_provider"
        log "Generated config.yaml"
    fi

    # ── Step 5: Skills ──
    deploy_skills

    # ── Step 6: Summary ──
    check_api_key
    print_summary
}

main "$@"
