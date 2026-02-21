---
name: extract-persona
description: |
  Extract a chess persona from game records or a PGN file.
  Invoked when the user wants to create a bot persona from their own
  game history or from a historical player's PGN games.
---

# Extract Persona Skill

## Finding Scripts

The scripts and personas live at fixed paths relative to the repo root:

```
SCRIPT_DIR         = plugins/chess-coach/scripts
BUNDLED_PERSONA_DIR = plugins/chess-coach/personas
USER_PERSONA_DIR    = ~/.chess_coach/personas
```

Every command uses these paths directly — no shell variable expansion needed.

## Flow

### Step 1 — Ask source

"Extract from your own game history, or import a PGN file?"

### Step 2a — Game history path

```bash
python3 "plugins/chess-coach/scripts/profile.py" recommend
```

Use `nickname` as the actor name. Ask for a persona ID (default: nickname).

```bash
python3 "plugins/chess-coach/scripts/persona.py" extract --actor "<nickname>" --id "<id>" --games-dir ~/.chess_coach/games
```

Read `persona` from the JSON output (machine layer only — no character voice yet).

If `result["ok"]` is false (e.g., no games found for this actor), inform the
user: "No game records found for '<nickname>'. Play some games first, then
try again." and stop.

### Step 2b — PGN path

Ask: "Path to the PGN file?" and "Player name in the PGN?" and "Persona ID?"

```bash
python3 "plugins/chess-coach/scripts/persona.py" import_pgn --pgn "<path>" --player "<player_name>" --id "<id>"
```

Read `persona` from the JSON output.

If `result["ok"]` is false, inform the user with the error message from
`result["error"]` and stop.

### Step 3 — Claude enriches the character layer

Based on the machine layer stats, write:

- **description**: 1–2 sentences capturing the overall identity
- **personality**: tone, attitude, how this player thinks about chess
- **move_voice**: how their moves feel — the pattern of their play
- **coaching_voice**: one example line they'd say after a user mistake

Guidelines:
- High aggression (>0.7) → tactical, attacking, sacrificial
- Low blunder_rate (<0.03) → precise, unforgiving
- Narrow opening repertoire → specialist; wide → universal
- High ACPL (>80) → looser, mistakes are part of the game
- Low ACPL (<30) → near-perfect, relentless accuracy

Then write the full persona to disk:

Write the complete persona JSON to `~/.chess_coach/personas/<id>.json` using the Write tool.
Combine the machine layer fields from the `persona.py` output (Step 2) with
the character fields you just generated.

### Step 4 — Confirm

Tell the user:
```
Persona "<name>" created and saved.
  Games analyzed: N
  ACPL: X  |  Aggression: Y  |  Depth: Z

"<description>"

You can now play against this persona. Say "let's play" to start a game.
```
