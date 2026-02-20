# claude-chess Plugin Design

**Goal:** Package the existing chess coach Python scripts as a publishable Claude Code plugin hosted on GitHub.

**Architecture:** A standalone GitHub repo acts as both a plugin marketplace and container. The single `chess-coach` plugin lives under `plugins/chess-coach/`. Scripts are placed at the plugin level (shared across future skills). The SKILL.md references scripts using the skill's base directory provided in context at runtime — no install hooks, no hardcoded paths.

**Tech Stack:** Python 3 + `chess` library (existing), Claude Code plugin system (`.claude-plugin/plugin.json`, `skills/`, `hooks/` conventions).

---

## Repository Structure

```
github.com/{user}/claude-chess
├── README.md                          ← Marketplace-level: install instructions for users
└── plugins/
    └── chess-coach/                   ← The plugin
        ├── .claude-plugin/
        │   └── plugin.json            ← name, description, author metadata
        ├── scripts/                   ← Shared Python scripts (plugin-level)
        │   ├── engine.py
        │   ├── coach.py
        │   ├── common.py
        │   ├── profile.py
        │   ├── render.py
        │   └── review.py
        ├── skills/
        │   └── chess-coach/
        │       └── SKILL.md           ← Updated to use {SKILL_BASE_DIR}/../scripts/
        └── README.md                  ← Plugin-level: feature docs
```

---

## Key Design Decisions

### Scripts at plugin level (not skill level)
Scripts live in `plugins/chess-coach/scripts/` so future skills (e.g. `chess-puzzles`) can reference the same Python files without duplication.

### No install hooks
Scripts are not copied to `~/.chess_coach/scripts/` on install. Instead, the SKILL.md instructs Claude to construct the script path from the skill base directory provided in skill context at runtime:

```bash
SCRIPT_DIR="${SKILL_BASE_DIR}/../scripts"
python3 "$SCRIPT_DIR/engine.py" new_game --state ~/.chess_coach/current_game.json
```

### Game state still lives in `~/.chess_coach/`
All game data (current_game.json, profile.json, games/, reviews/) remains at `~/.chess_coach/` — unchanged from the existing design.

---

## User Install Flow

```bash
# Step 1: Register the marketplace
/plugin marketplace add {github-username}/claude-chess

# Step 2: Install the plugin
/plugin install chess-coach@claude-chess

# Step 3: Install Python dependency (once)
pip install chess --break-system-packages -q
```

---

## What Changes vs. Current Code

| Item | Change |
|------|--------|
| `SKILL.md` | Update all `python3 scripts/` → `python3 "$SCRIPT_DIR/scripts/` using SKILL_BASE_DIR variable; add SCRIPT_DIR setup at top of each command block |
| `plugins/chess-coach/.claude-plugin/plugin.json` | New file — plugin metadata |
| `plugins/chess-coach/README.md` | New file — plugin docs |
| `README.md` (repo root) | New file — marketplace / install instructions |
| Python files (`*.py`) | No changes — moved to `plugins/chess-coach/scripts/` |

---

## Future Extensions

Additional skills under `plugins/chess-coach/skills/` can reuse all scripts:
- `chess-puzzles/` — tactics training
- `chess-review/` — review games from PGN
- `chess-openings/` — opening explorer
