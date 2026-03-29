cp "$REPO_DIR/src/hermes_memory_decay/plugin.yaml" "$PLUGIN_DIR/"

# Copy config example if config doesn't already exist
if [ ! -f "$PLUGIN_DIR/config.yaml" ]; then
    if [ -f "$REPO_DIR/src/hermes_memory_decay/config.yaml.example" ]; then
        cp "$REPO_DIR/src/hermes_memory_decay/config.yaml.example" "$PLUGIN_DIR/config.yaml.example"
        echo "  Config example copied. Edit config.yaml to customize."
    fi
else
    echo "  Existing config.yaml preserved."
fi

# Copy skills to Hermes skills directory
SKILLS_DIR="$HOME/.hermes/skills/memory-decay"
if [ -d "$REPO_DIR/skills" ]; then
    mkdir -p "$SKILLS_DIR"
    cp -r "$REPO_DIR/skills/"* "$SKILLS_DIR/"
    echo "  Skills installed to: $SKILLS_DIR"
fi

echo ""
echo "Installed to: $PLUGIN_DIR"
echo ""
echo "Next steps:"
echo "  1. Copy config.yaml.example to config.yaml and edit it:"
echo "     cp $PLUGIN_DIR/config.yaml.example $PLUGIN_DIR/config.yaml"
echo "  2. Ensure memory-decay-core is installed:"
echo "     cd ~/workspace/memory-decay-core && pip install -e '.[server]'"
echo "  3. Set your embedding API key (e.g. GEMINI_API_KEY)"
echo "  4. Verify: hermes plugins list"
echo ""
echo "Done!"
