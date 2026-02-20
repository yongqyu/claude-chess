# claude-chess Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the existing chess coach scripts into a publishable Claude Code plugin at `github.com/{user}/claude-chess`.

**Architecture:** The repo acts as both a plugin marketplace and a container. One plugin (`chess-coach`) lives under `plugins/chess-coach/`. Python scripts are placed at the plugin level (`plugins/chess-coach/scripts/`) so future skills can share them. The SKILL.md instructs Claude to locate scripts dynamically from the skill base directory provided in runtime context.

**Tech Stack:** Python 3, `chess` library, Claude Code plugin system (`.claude-plugin/plugin.json`, `skills/`, directory conventions), GitHub.

---

### Task 1: Create the directory structure

**Files:**
- Create: `plugins/chess-coach/.claude-plugin/` (directory)
- Create: `plugins/chess-coach/scripts/` (directory)
- Create: `plugins/chess-coach/skills/chess-coach/` (directory)

**Step 1: Create all required directories**

```bash
mkdir -p plugins/chess-coach/.claude-plugin
mkdir -p plugins/chess-coach/scripts
mkdir -p plugins/chess-coach/skills/chess-coach
```

**Step 2: Verify directories exist**

```bash
find plugins/ -type d
```

Expected output:
```
plugins/
plugins/chess-coach
plugins/chess-coach/.claude-plugin
plugins/chess-coach/scripts
plugins/chess-coach/skills
plugins/chess-coach/skills/chess-coach
```

**Step 3: Commit**

```bash
git init
git add plugins/
git commit -m "chore: scaffold plugin directory structure"
```

---

### Task 2: Move Python scripts into plugin

**Files:**
- Move: `engine.py` → `plugins/chess-coach/scripts/engine.py`
- Move: `coach.py` → `plugins/chess-coach/scripts/coach.py`
- Move: `common.py` → `plugins/chess-coach/scripts/common.py`
- Move: `profile.py` → `plugins/chess-coach/scripts/profile.py`
- Move: `render.py` → `plugins/chess-coach/scripts/render.py`
- Move: `review.py` → `plugins/chess-coach/scripts/review.py`

**Step 1: Move all Python files**

```bash
mv engine.py  plugins/chess-coach/scripts/
mv coach.py   plugins/chess-coach/scripts/
mv common.py  plugins/chess-coach/scripts/
mv profile.py plugins/chess-coach/scripts/
mv render.py  plugins/chess-coach/scripts/
mv review.py  plugins/chess-coach/scripts/
```

**Step 2: Verify scripts are in place and root is clean**

```bash
ls plugins/chess-coach/scripts/
ls *.py 2>/dev/null && echo "ERROR: py files still at root" || echo "OK: root is clean"
```

Expected:
```
coach.py  common.py  engine.py  profile.py  render.py  review.py
OK: root is clean
```

**Step 3: Smoke-test that scripts still work from new location**

```bash
pip install chess --break-system-packages -q
python3 plugins/chess-coach/scripts/engine.py new_game --state /tmp/test_game.json
```

Expected: JSON output with `"ok": true` and a FEN string.

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: move python scripts to plugins/chess-coach/scripts/"
```

---

### Task 3: Create `plugin.json`

**Files:**
- Create: `plugins/chess-coach/.claude-plugin/plugin.json`

**Step 1: Create the metadata file**

Create `plugins/chess-coach/.claude-plugin/plugin.json` with this exact content (replace `{github-username}` and `{email}` with your own):

```json
{
  "name": "chess-coach",
  "description": "Interactive chess with ANSI terminal board, adaptive AI opponent, real-time coaching, ELO tracking, and automatic difficulty calibration. Invoke when the user wants to play chess, get coaching, or review a past game.",
  "author": {
    "name": "{github-username}",
    "email": "{email}"
  }
}
```

**Step 2: Validate JSON**

```bash
python3 -m json.tool plugins/chess-coach/.claude-plugin/plugin.json
```

Expected: pretty-printed JSON with no errors.

**Step 3: Commit**

```bash
git add plugins/chess-coach/.claude-plugin/plugin.json
git commit -m "feat: add plugin.json metadata"
```

---

### Task 4: Update SKILL.md and move it into the plugin

**Files:**
- Modify: `SKILL.md` (at root) → move to `plugins/chess-coach/skills/chess-coach/SKILL.md` with script path updates

**Background:** When Claude Code loads a skill, it provides:
```
Base directory for this skill: /path/to/skills/chess-coach
```
Scripts live one level up from `skills/chess-coach`, at `plugins/chess-coach/scripts/`. The SKILL.md must instruct Claude to derive `SCRIPT_DIR` from this context.

**Step 1: Read the current SKILL.md to understand all script references**

Open `SKILL.md` and note every line starting with `python3 scripts/`.

**Step 2: Create the updated SKILL.md at its new location**

Create `plugins/chess-coach/skills/chess-coach/SKILL.md` with the content below.

Key change: add this block at the top of **every bash code block** that calls a script:
```bash
SCRIPT_DIR="$(python3 -c "import os,sys; print(os.path.normpath(os.path.join('SKILL_BASE_DIR_PLACEHOLDER', '..', 'scripts')))")"
# Note: Replace SKILL_BASE_DIR_PLACEHOLDER with the actual path from "Base directory for this skill" in your context
```

Actually, the cleaner approach is to add a **"Scripts" section** at the top of the SKILL.md that tells Claude how to resolve the path, and update all `python3 scripts/X.py` calls to `python3 "$SCRIPT_DIR/X.py"`. See the full file content in Step 3.

**Step 3: Write the full updated SKILL.md**

Create `plugins/chess-coach/skills/chess-coach/SKILL.md`:

```markdown
---
name: chess-coach
description: |
  Interactive chess with ANSI terminal board, adaptive AI opponent, real-time coaching,
  ELO tracking, and automatic difficulty calibration from past games.
  Invoke when the user wants to play chess, get coaching, or review a past game.
---

# Chess Coach Skill

All game logic lives in Python scripts. Claude acts as orchestrator:
calls scripts in the correct order, reads their JSON output, and delivers
coaching naturally in conversation.

---

## Finding the Scripts

When this skill loads, your context includes:
```
Base directory for this skill: /path/to/.../skills/chess-coach
```

The scripts are one level up in `scripts/`. At the start of every session, set:

```bash
SKILL_BASE="<paste the Base directory from your context here>"
SCRIPT_DIR="$(python3 -c "import os; print(os.path.normpath(os.path.join('$SKILL_BASE', '..', 'scripts')))")"
```

Use `$SCRIPT_DIR/engine.py`, `$SCRIPT_DIR/coach.py`, etc. for all script calls below.

---

## Directory Layout

```
scripts/
  common.py    Shared evaluation, PST tables, ELO formula, opening DB
  engine.py    Game logic, move validation, AI moves, state persistence
  coach.py     Move evaluation, coaching text, state annotation
  render.py    ANSI terminal board output
  profile.py   Player profile, ELO history, difficulty recommendation
  review.py    End-of-game Markdown review generator
```

**Storage root:** `~/.chess_coach/`

```
~/.chess_coach/
  current_game.json     Active game state
  profile.json          Player ELO history and current level
  games/                Archived completed game states
  reviews/              Generated Markdown review files
```

**Install dependency (once):**
```bash
pip install chess --break-system-packages -q
```

---

## Session Start Flow

### Step 1 — Load player profile and recommend difficulty

```bash
python3 "$SCRIPT_DIR/profile.py" recommend
```

Read `recommended_level` and `note` from the output.
- If `games_played == 0`: inform the user this is their first game, default to `intermediate`.
- Otherwise: say "Based on your last N games (ELO ~X), I'll set difficulty to Y."
- Always let the user override.

### Step 2 — Start a new game

```bash
python3 "$SCRIPT_DIR/engine.py" new_game \
  --color white \           # or black — ask the user
  --level intermediate \    # resolved from profile or user override
  --mode play               # play | coach
```

**If user plays Black:** the AI moves first immediately after new_game:
```bash
python3 "$SCRIPT_DIR/engine.py" ai_move
python3 "$SCRIPT_DIR/coach.py" explain_ai
python3 "$SCRIPT_DIR/render.py" --clear
```

### Step 3 — Render the board

```bash
python3 "$SCRIPT_DIR/render.py" --clear
```

Use `--clear` on every render during gameplay to keep the board fixed at the
top of the terminal.

---

## Play Mode — Per-Turn Flow

### User's move

```bash
# 1. Evaluate BEFORE committing (for coaching feedback)
python3 "$SCRIPT_DIR/coach.py" evaluate_user --move <uci>

# 2. Commit the move
python3 "$SCRIPT_DIR/engine.py" move --move <uci>

# 3. Save coaching annotation to the record
MOVE_IDX=$(python3 -c "
import json, os; s=json.load(open(os.path.expanduser('~/.chess_coach/current_game.json')));
print(len(s['move_records'])-1)
")
python3 "$SCRIPT_DIR/coach.py" annotate --move_idx $MOVE_IDX --text "<coaching_text>"

# 4. Re-render
python3 "$SCRIPT_DIR/render.py" --clear
```

Claude then relays `coaching_lines` from step 1 conversationally.

### AI's move

```bash
# 1. Calculate and commit AI move
python3 "$SCRIPT_DIR/engine.py" ai_move

# 2. Generate and persist AI explanation
python3 "$SCRIPT_DIR/coach.py" explain_ai

# 3. Re-render
python3 "$SCRIPT_DIR/render.py" --clear
```

Claude relays `coaching_lines` from explain_ai.

---

## Coach Mode — Per-Turn Flow

Instead of the AI moving, Claude presents the position and asks the user
what they would play:

```
"What would you play in this position?"
→ User answers
→ evaluate_user (do NOT commit yet)
→ Deliver coaching feedback
→ "Would you like to play that, or try a different move?"
→ On confirmation: engine.py move → render
→ Repeat
```

---

## Move Input

Accept any of these and normalize to UCI before passing to scripts:
- SAN:            `e4`, `Nf3`, `O-O`, `Rxe5`
- UCI:            `e2e4`, `g1f3`
- Natural language: `"kingside castle"`, `"pawn to e4"`, `"knight f3"`

---

## Game Over

When any engine/ai_move response returns `"is_game_over": true`:

```bash
# 1. Generate review
python3 "$SCRIPT_DIR/review.py" --output ~/.chess_coach/reviews/review_$(date +%Y%m%d_%H%M%S).md

# 2. Update player profile with ELO from this game
python3 "$SCRIPT_DIR/profile.py" update --state ~/.chess_coach/current_game.json

# 3. Announce result and ELO update
```

Tell the user their estimated ELO for this game, how it compares to their
historical average, and where the review file was saved.

---

## Context Recovery

All game data is persisted in `~/.chess_coach/current_game.json`.
If Claude loses context mid-game, recover instantly:

```bash
python3 "$SCRIPT_DIR/engine.py" status
python3 "$SCRIPT_DIR/render.py" --clear
```

Tell the user: "I've reloaded the game from disk — here's the current position."

---

## Error Handling

| Situation | Response |
|-----------|----------|
| Illegal move (`ok: false`) | Explain why and ask for a different move |
| `chess` library not installed | Run `pip install chess --break-system-packages` |
| State file missing | Run `new_game` to start fresh |
| Game already over | Offer rematch or review |

---

## Opening Session Message

```
♟  Welcome to Chess Coach!

Which mode would you like?
  1. 🎮 Play   — Play against the AI (difficulty auto-set from your history)
  2. 📚 Coach  — Get feedback on every move

[Loading your player profile...]
```
```

**Step 4: Verify the new SKILL.md exists and has correct content**

```bash
head -10 plugins/chess-coach/skills/chess-coach/SKILL.md
grep 'SCRIPT_DIR' plugins/chess-coach/skills/chess-coach/SKILL.md | wc -l
```

Expected: frontmatter at top, at least 8 occurrences of `SCRIPT_DIR`.

**Step 5: Remove the old SKILL.md from root**

```bash
rm SKILL.md
ls SKILL.md 2>/dev/null && echo "ERROR: still exists" || echo "OK: removed"
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: move and update SKILL.md to use SCRIPT_DIR from skill context"
```

---

### Task 5: Create plugin-level README

**Files:**
- Create: `plugins/chess-coach/README.md`

**Step 1: Create the README**

Create `plugins/chess-coach/README.md`:

```markdown
# chess-coach

Interactive chess in your terminal with real-time coaching, ELO tracking,
and an adaptive AI opponent.

## Features

- ANSI chess board rendered directly in the terminal
- Three difficulty levels: beginner, intermediate, advanced
- ELO-based adaptive difficulty (auto-calibrates after each game)
- Real-time coaching: move quality, best alternative, opening names
- Play mode and Coach mode
- Post-game review saved as Markdown

## Prerequisites

```bash
pip install chess --break-system-packages -q
```

## Usage

Once installed, start a new Claude Code session and say:

> "Let's play chess" or "I want chess coaching"

Claude will load your profile, recommend a difficulty level, and start a game.

## Game Data

All game state is stored in `~/.chess_coach/`:

```
~/.chess_coach/
  current_game.json   Active game
  profile.json        ELO history and current level
  games/              Archived completed games
  reviews/            Post-game Markdown reviews
```
```

**Step 2: Verify**

```bash
wc -l plugins/chess-coach/README.md
```

Expected: > 30 lines.

**Step 3: Commit**

```bash
git add plugins/chess-coach/README.md
git commit -m "docs: add plugin README"
```

---

### Task 6: Create repo-level README (marketplace README)

**Files:**
- Create: `README.md` (repo root)

**Step 1: Create root README**

Create `README.md` at the repo root:

```markdown
# claude-chess

A Claude Code plugin that turns Claude into an interactive chess coach with
ANSI terminal board, adaptive AI, ELO tracking, and real-time coaching.

## Installation

**Step 1:** Register this repo as a plugin marketplace in Claude Code:

```
/plugin marketplace add {github-username}/claude-chess
```

**Step 2:** Install the chess-coach plugin:

```
/plugin install chess-coach@claude-chess
```

**Step 3:** Install the Python dependency (once):

```bash
pip install chess --break-system-packages -q
```

**Step 4:** Start a new Claude Code session and say:

> "Let's play chess"

## What's Included

| Plugin | Description |
|--------|-------------|
| `chess-coach` | Full chess game with coaching, ELO tracking, and adaptive difficulty |

## License

MIT
```

**Step 2: Verify**

```bash
wc -l README.md
```

Expected: > 35 lines.

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add marketplace README with install instructions"
```

---

### Task 7: Add `.gitignore`

**Files:**
- Create: `.gitignore`

**Step 1: Create .gitignore**

Create `.gitignore`:

```
__pycache__/
*.pyc
*.pyo
.DS_Store
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

### Task 8: Create GitHub repo and push

**Prerequisites:** GitHub CLI (`gh`) must be installed and authenticated.
Check with `gh auth status`.

**Step 1: Verify git log looks clean**

```bash
git log --oneline
```

Expected: 6-7 commits covering each task above.

**Step 2: Create GitHub repo**

```bash
gh repo create claude-chess --public --description "Chess coaching Claude Code plugin with ANSI board, adaptive AI, and ELO tracking"
```

Expected: repo URL printed, e.g. `https://github.com/{username}/claude-chess`

**Step 3: Push**

```bash
git remote add origin https://github.com/{username}/claude-chess.git
git push -u origin main
```

**Step 4: Verify**

```bash
gh repo view claude-chess --web
```

Expected: GitHub page opens in browser showing the README.

**Step 5: Test install in Claude Code**

In a new Claude Code session:
```
/plugin marketplace add {github-username}/claude-chess
/plugin install chess-coach@claude-chess
```

Expected: plugin installs without errors, and starting a new session triggers the chess-coach skill when you say "Let's play chess".
