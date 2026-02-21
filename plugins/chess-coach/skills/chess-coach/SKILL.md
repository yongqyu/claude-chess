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

The Python scripts live at `plugins/chess-coach/scripts/` relative to the repo root.
Claude Code always opens at the repo root, so use this fixed path throughout:

```
SCRIPT_DIR = plugins/chess-coach/scripts
```

Every command in this skill uses that prefix directly, e.g.:
```bash
python3 plugins/chess-coach/scripts/engine.py status
```

No shell variable expansion or `$()` substitution needed.

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
python3 "plugins/chess-coach/scripts/profile.py" recommend
```

Read `nickname`, `recommended_level`, and `note` from the output.
- If `nickname` is null: ask the user "What should I call you?" and persist it:
  ```bash
  python3 "plugins/chess-coach/scripts/profile.py" set_nickname --name "<name>"
  ```
  Use the returned `nickname` for all subsequent references and game records.
- If `nickname` is set: greet them by name — "Welcome back, <nickname>!"
- If `games_played == 0`: inform the user this is their first game, default to `intermediate`.
- Otherwise: say "Based on your last N games (ELO ~X), I'll set difficulty to Y."
- Always let the user override.

### Step 1b — Persona selection (optional)

```bash
python3 "plugins/chess-coach/scripts/persona.py" list --bundled-dir "plugins/chess-coach/personas" --user-dir ~/.chess_coach/personas
```

Show available personas as a numbered list (name and source only — descriptions
are loaded when a persona is selected). Let the user pick by number or name.
Ask: "Play against the standard AI, or choose a persona?"

- If user chooses a persona: note the persona ID for this session. Load its full data:
  ```bash
  python3 "plugins/chess-coach/scripts/persona.py" show --id "<persona_id>" --bundled-dir "plugins/chess-coach/personas" --user-dir ~/.chess_coach/personas
  ```
  Read `description`, `personality`, `move_voice`, `coaching_voice` — hold in context.
  Introduce: "You'll be playing against **\<name\>**. \<description\>"
- If standard AI: proceed without a persona.

### Step 2 — Start a new game

```bash
python3 "plugins/chess-coach/scripts/engine.py" new_game --color white --level intermediate --mode play --player "<nickname>"
```

Replace `white` with `black` if the user picks Black, `intermediate` with the resolved difficulty, and `<nickname>` with the player's name.

**If user plays Black:** the AI moves first immediately after new_game. Run in sequence:

With persona active:
```bash
python3 "plugins/chess-coach/scripts/engine.py" ai_move --persona "<persona_id>" --bundled-persona-dir "plugins/chess-coach/personas"
```
Without persona:
```bash
python3 "plugins/chess-coach/scripts/engine.py" ai_move
```
Then:
```bash
python3 "plugins/chess-coach/scripts/coach.py" explain_ai
python3 "plugins/chess-coach/scripts/render.py" --plain
```

### Step 3 — Render the board

```bash
python3 "plugins/chess-coach/scripts/render.py" --plain
```

**The printed output is the board.** After every move, run this command and paste the
output verbatim as a fenced code block in your reply.
Use `--plain` (not `--clear`) — plain mode produces clean text readable in the Claude Code
chat window.

---

## Play Mode — Per-Turn Flow

### User's move

Evaluate before committing:
```bash
python3 "plugins/chess-coach/scripts/coach.py" evaluate_user --move <uci>
```
Note `coaching_lines` from the output — relay them conversationally after the move.

Commit the move:
```bash
python3 "plugins/chess-coach/scripts/engine.py" move --move <uci>
```

Get the move index for the annotation step (prints a single integer):
```bash
python3 -c "import json,os; s=json.load(open(os.path.expanduser('~/.chess_coach/current_game.json'))); print(len(s['move_records'])-1)"
```
Use the printed number as `<idx>` in the annotate call:
```bash
python3 "plugins/chess-coach/scripts/coach.py" annotate --move_idx <idx> --text "<coaching_text>"
```

Render the board:
```bash
python3 "plugins/chess-coach/scripts/render.py" --plain
```
Include the output as a code block in your reply.

### AI's move

With persona active:
```bash
python3 "plugins/chess-coach/scripts/engine.py" ai_move --persona "<persona_id>" --bundled-persona-dir "plugins/chess-coach/personas"
```
Without persona:
```bash
python3 "plugins/chess-coach/scripts/engine.py" ai_move
```

Then:
```bash
python3 "plugins/chess-coach/scripts/coach.py" explain_ai
python3 "plugins/chess-coach/scripts/render.py" --plain
```

Relay `coaching_lines` from explain_ai, and include the board output as a code block in
your reply.
If a persona is active, narrate the AI move **in the persona's `move_voice` style** — brief,
in character. After user moves, react in `coaching_voice` style: one sentence as that persona
would say it. Do not break character during gameplay.

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

Generate a review file — use the current date and time as the timestamp (format: YYYYMMDD_HHMMSS):
```bash
python3 "plugins/chess-coach/scripts/review.py" --output ~/.chess_coach/reviews/review_<YYYYMMDD_HHMMSS>.md
```

Update the player profile:
```bash
python3 "plugins/chess-coach/scripts/profile.py" update --state ~/.chess_coach/current_game.json
```

Tell the user their estimated ELO for this game, how it compares to their
historical average, and where the review file was saved.

---

## Context Recovery

All game data is persisted in `~/.chess_coach/current_game.json`.
If Claude loses context mid-game, recover instantly:

```bash
python3 "plugins/chess-coach/scripts/engine.py" status
python3 "plugins/chess-coach/scripts/render.py" --plain
```

Tell the user: "I've reloaded the game from disk — here's the current position."
Include the board output as a code block in your reply.

**If a persona was active:** The current game state does not store the active persona ID.
Ask the user: "Were you playing against a persona? If so, which one?" and reload
it via `persona.py show` if they respond with a name.

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
