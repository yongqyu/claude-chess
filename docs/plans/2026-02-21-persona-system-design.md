# Persona System Design

**Date:** 2026-02-21
**Status:** Approved

---

## Overview

A persona is a playable chess identity — a bot opponent with a distinct style, voice, and character. Personas can be hand-crafted for historical players (Fischer, Tal) or extracted automatically from any collection of game records, including a user's own history.

The key distinction from `profile` (which is a stats tracker): a persona is **who you play against**, a profile is **how you've been playing**.

---

## Term

**`persona`** — captures identity + behavior, works for both historical and extracted cases, clearly distinct from `profile`.

---

## Two-Layer Architecture

Every persona has two layers:

### Machine Layer — drives the engine
```json
{
  "opening_moves": { "white": ["e4"], "black": ["c5", "e5"] },
  "depth": 3,
  "blunder_rate": 0.02,
  "aggression": 0.85,
  "acpl": 28.0,
  "games_analyzed": 0
}
```

### Character Layer — drives Claude's voice (LLM-generated at extraction time)
```json
{
  "description": "Ruthlessly precise. Never satisfied with equality.",
  "personality": "Cold, calculating, sees chess as a war to be won.",
  "move_voice": "Dominates open files, centralizes everything, suffocates.",
  "coaching_voice": "You gave away the e-file. That's how you lose."
}
```

The character layer is written **once** at extraction/creation time by Claude, then stored in the persona file. During gameplay Claude reads these fields and stays in character — no extra generation per move.

---

## Full Persona Schema

```json
{
  "id": "fischer",
  "name": "Bobby Fischer",
  "source": "historical",

  "opening_moves": {
    "white": ["e4"],
    "black": ["c5", "e5"]
  },
  "depth": 3,
  "blunder_rate": 0.02,
  "aggression": 0.85,
  "acpl": 28.0,
  "games_analyzed": 0,
  "created_at": "ISO-8601 datetime",

  "description": "Ruthlessly precise. Never satisfied with equality.",
  "personality": "Cold, calculating, sees chess as a war to be won.",
  "move_voice": "Dominates open files, centralizes everything, suffocates.",
  "coaching_voice": "You gave away the e-file. That's how you lose."
}
```

`source` values: `"historical"` (hand-crafted) | `"extracted"` (from game records) | `"pgn"` (imported from PGN file).

---

## File Layout

```
plugins/chess-coach/
  personas/                  ← bundled, committed to repo
    fischer.json
    tal.json
    petrosian.json
    carlsen.json
  scripts/
    persona.py               ← new: list/show/extract commands
    pgn_adapter.py           ← new: PGN → internal game records
  skills/
    chess-coach/SKILL.md     ← updated: persona selection at session start
    extract-persona/
      SKILL.md               ← new skill

~/.chess_coach/
  personas/                  ← user-extracted, runtime only
    yonggyu.json
  games/                     ← existing archived game records
```

---

## Extraction Pipeline

**Option B** (chosen): PGN converts to internal game files first, then one unified extractor handles all sources.

```
User game records: ~/.chess_coach/games/*.json  ──┐
                                                    ├──▶ persona.py extract ──▶ raw stats
Historical PGN:    pgn_adapter.py → games/*.json  ──┘
                                      ↓
                              Claude enriches
                              (character layer)
                                      ↓
                              ~/.chess_coach/personas/<id>.json
```

### Extraction Algorithm

From a filtered set of move records (by `actor` name):

| Field | Method |
|---|---|
| `opening_moves.white` | Most common moves 1–5 when playing white |
| `opening_moves.black` | Most common responses 1–5 when playing black |
| `aggression` | captures / total moves, normalized 0–1 |
| `blunder_rate` | from existing `estimate_elo()` |
| `acpl` | from existing `estimate_elo()` |
| `depth` | derived: acpl < 40 → 3, acpl < 80 → 2, else → 1 |
| `games_analyzed` | game count used |

---

## New Script: `persona.py`

| Command | Description |
|---|---|
| `list` | Print all available personas (bundled + user-extracted) |
| `show --id <id>` | Print full persona JSON |
| `extract --actor <name> --id <id> --output <path>` | Compute machine layer from game records, output raw stats for Claude to enrich |
| `import_pgn --pgn <file> --player <name> --output <path>` | Convert PGN via pgn_adapter, then same extraction |

`extract` outputs **raw stats only** (no character layer). The skill is responsible for calling Claude to generate and merge the character layer before writing the final file.

---

## New Script: `pgn_adapter.py`

Parses a PGN file using `python-chess`'s `chess.pgn` module. For each game:
1. Filters by player name (White or Black)
2. Converts moves to internal `move_records` format
3. Re-evaluates each position with `common.evaluate()` to populate `score_before_cp` / `score_after_cp`
4. Writes one game JSON per game to a temp directory

Output files are in the same format as `~/.chess_coach/games/*.json`, so `persona.py extract` can process them identically.

---

## Engine Changes

### `engine.py` — `ai_move`

Gains `--persona <id>` flag:
- Resolves persona file (bundled dir first, then `~/.chess_coach/personas/`)
- Uses persona's `depth`, `blunder_rate`, `aggression` instead of level-based settings
- First 10 moves: if the current move number matches the persona's `opening_moves` sequence, play that move directly (skip minimax)

### `common.py` — `get_best_move`

Gains `aggression: float = 0.0` parameter:
- Before scoring, captures and checks receive a bonus of `aggression * 50` centipawns added to their evaluation
- This biases move ordering toward tactical play without changing the evaluation function itself

---

## New Skill: `extract-persona`

**Flow:**

1. Ask: "Extract from your own game history, or import a PGN file?"
2. **Game history path:**
   - `persona.py extract --actor <nickname>` → raw stats JSON
   - Claude generates character layer from stats
   - Merge and save to `~/.chess_coach/personas/<id>.json`
3. **PGN path:**
   - Ask for PGN file path and player name
   - `pgn_adapter.py` → temp game files
   - `persona.py extract` on temp files → raw stats JSON
   - Claude generates character layer
   - Merge and save to `~/.chess_coach/personas/<id>.json`
4. Confirm: "Persona saved. You can now play against **\<name\>**."

---

## Updated Skill: `chess-coach`

### Session Start (new step, after profile load)

```bash
python3 "$SCRIPT_DIR/persona.py" list
```

Ask: "Play against the standard AI, or choose a persona?"
- If persona chosen: load its JSON, read character layer fields
- Pass `--persona <id>` to every `ai_move` call for this session
- Claude adopts the persona's voice for the entire game

### During Gameplay (persona active)

- **After AI move:** narrate in `move_voice` style — brief, in character
- **After user move:** coach in `coaching_voice` style — react as that persona would

### Example contrast

| Persona | After Rxe5 | After user blunder |
|---|---|---|
| Fischer | "Rook takes e5. Your queenside is stranded." | "You left the file open. That's the game." |
| Tal | "I took the pawn. Let's see if you can survive what follows." | "Interesting. I didn't expect you to help me." |
| Petrosian | "Exchange. No risk. I'll improve from here." | "You weakened d5. I'll take it in ten moves." |

---

## Bundled Personas (hand-crafted)

| ID | Name | Style |
|---|---|---|
| `fischer` | Bobby Fischer | Aggressive, e4, open games, precision |
| `tal` | Mikhail Tal | Sacrificial, tactical chaos, king attacks |
| `petrosian` | Tigran Petrosian | Defensive, prophylactic, exchange-oriented |
| `carlsen` | Magnus Carlsen | Universal, accurate, endgame-dominant |

---

## Out of Scope (this iteration)

- Biasing the PST/eval function per persona (deep engine changes)
- Persona vs persona simulation (two bots)
- Web UI or visual persona browser
- Sharing personas between users
