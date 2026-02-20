#!/usr/bin/env bash
# install.sh — Manually install the chess-coach Claude Code plugin.
# Run this if `/plugin marketplace add` doesn't work in your session.
#
# Usage: bash install.sh

set -euo pipefail

REPO="yongqyu/claude-chess"
PLUGIN_NAME="chess-coach"
MARKETPLACE_NAME="claude-chess"
CLAUDE_PLUGINS="$HOME/.claude/plugins"
VERSION="1.0.0"

echo "Installing $PLUGIN_NAME..."

# ── 1. Register marketplace ──────────────────────────────────────────────────
python3 - <<PYEOF
import json, os
path = os.path.expanduser("~/.claude/plugins/known_marketplaces.json")
with open(path) as f:
    data = json.load(f)
if "$MARKETPLACE_NAME" not in data:
    data["$MARKETPLACE_NAME"] = {
        "source": {"source": "github", "repo": "$REPO"},
        "installLocation": os.path.expanduser("~/.claude/plugins/marketplaces/$MARKETPLACE_NAME"),
        "lastUpdated": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print("  ✓ Registered marketplace")
else:
    print("  · Marketplace already registered")
PYEOF

# ── 2. Clone / update marketplace repo ───────────────────────────────────────
MARKETPLACE_DIR="$CLAUDE_PLUGINS/marketplaces/$MARKETPLACE_NAME"
if [ ! -d "$MARKETPLACE_DIR/.git" ]; then
    git clone --quiet "https://github.com/$REPO.git" "$MARKETPLACE_DIR"
    echo "  ✓ Cloned marketplace"
else
    git -C "$MARKETPLACE_DIR" pull --quiet
    echo "  ✓ Updated marketplace"
fi

# ── 3. Copy plugin files into cache ──────────────────────────────────────────
INSTALL_PATH="$CLAUDE_PLUGINS/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION"
mkdir -p "$INSTALL_PATH"
cp -r "$MARKETPLACE_DIR/plugins/$PLUGIN_NAME/." "$INSTALL_PATH/"
echo "  ✓ Copied plugin to cache"

# ── 4. Register in installed_plugins.json ────────────────────────────────────
python3 - <<PYEOF
import json, os
from datetime import datetime, timezone
path = os.path.expanduser("~/.claude/plugins/installed_plugins.json")
with open(path) as f:
    data = json.load(f)
key = "$PLUGIN_NAME@$MARKETPLACE_NAME"
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
if key not in data["plugins"]:
    data["plugins"][key] = [{
        "scope": "user",
        "installPath": os.path.expanduser("~/.claude/plugins/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION"),
        "version": "$VERSION",
        "installedAt": now,
        "lastUpdated": now,
    }]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print("  ✓ Registered in installed_plugins.json")
else:
    print("  · Plugin already in installed_plugins.json")
PYEOF

echo ""
echo "✅ chess-coach installed. Start a new Claude Code session and say: 'Let's play chess'"
echo ""
echo "   Dependency (if needed): pip install chess --break-system-packages -q"
