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
coaching naturally in conversation. Keep thinking brief — only reason at
length when the situation needs guidance or coaching commentary.

## Finding the Scripts

When this skill loads, your context will include a line like:
  Base directory for this skill: /path/to/.../skills/chess-coach

The Python scripts are two levels up from that, in the `scripts/` folder.
At the start of every session, determine SCRIPT_DIR:

```bash
SKILL_BASE="<the Base directory path from your context>"
SCRIPT_DIR="$(python3 -c "import os,sys; print(os.path.normpath(os.path.join(sys.argv[1],'..','..','scripts')))" "$SKILL_BASE")"
```

Use `$SCRIPT_DIR/engine.py`, `$SCRIPT_DIR/coach.py`, etc. throughout this skill.

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

**Always print a plain-text board in the conversation after every move** (both
after the user's move and after the AI's response). The user must always see
the board in the chat. Output this in your reply:

```python
import chess, json, os
state = json.load(open(os.path.expanduser('~/.chess_coach/current_game.json')))
board = chess.Board()
for uci in state.get('moves_uci', []): board.push(chess.Move.from_uci(uci))
pieces = {'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙','k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟'}
print('\n    a   b   c   d   e   f   g   h')
print('  ┌───┬───┬───┬───┬───┬───┬───┬───┐')
for rank in range(7,-1,-1):
    row = f'{rank+1} │'
    for file in range(8):
        p = board.piece_at(chess.square(file,rank))
        row += f' {pieces[p.symbol()] if p else " "} │'
    print(row)
    if rank > 0: print('  ├───┼───┼───┼───┼───┼───┼───┼───┤')
print('  └───┴───┴───┴───┴───┴───┴───┴───┘')
print('    a   b   c   d   e   f   g   h')
```

Include the output as a code block in your reply so the user sees the board
in the conversation without needing to look at the terminal.

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

# 4. Re-render (terminal + plain-text in reply)
python3 "$SCRIPT_DIR/render.py" --clear
```

Claude then relays `coaching_lines` from step 1 conversationally,
and includes the plain-text board in the reply (see Step 3 above).

### AI's move

```bash
# 1. Calculate and commit AI move
python3 "$SCRIPT_DIR/engine.py" ai_move

# 2. Generate and persist AI explanation
python3 "$SCRIPT_DIR/coach.py" explain_ai

# 3. Re-render (terminal + plain-text in reply)
python3 "$SCRIPT_DIR/render.py" --clear
```

Claude relays `coaching_lines` from explain_ai,
and includes the plain-text board in the reply (see Step 3 above).

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
