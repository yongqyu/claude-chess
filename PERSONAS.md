# Personas

A persona is a playable chess identity — a bot opponent with a distinct playing style, opening repertoire, and character voice. Every game, Claude asks whether you want to play against the standard AI or choose a persona.

---

## How personas work

Each persona has two layers:

**Machine layer** — drives the engine
- `opening_moves` — preferred first moves as White and Black (used for the first ~5 moves)
- `depth` — minimax search depth (1–3)
- `blunder_rate` — probability of a random move (simulates human-like imperfection)
- `aggression` — 0–1 bonus applied to captures and checks (biases toward tactical play)
- `acpl` — average centipawn loss (lower = more precise)

**Character layer** — drives Claude's voice
- `description` — one-line identity summary
- `personality` — how this player thinks about chess
- `move_voice` — style Claude uses when narrating the AI's moves
- `coaching_voice` — style Claude uses when reacting to your moves

The character layer is written once at creation time — either hand-crafted (for bundled personas) or LLM-generated (for extracted ones). During gameplay Claude reads these fields and stays in character.

---

## Bundled personas

### Bobby Fischer
> "Ruthlessly precise. Never satisfied with equality — always plays for the win."

- **Style:** Open games, e4, scientific precision
- **Opens with (White):** e4 — **Black:** Sicilian (c5) or Open (e5)
- `depth: 3` · `aggression: 0.75` · `blunder_rate: 0.02` · `acpl: 28`
- **Coaching voice:** *"You left the e-file open. That's the game right there."*

---

### Mikhail Tal
> "The Magician from Riga. Sacrifices material to create chaos — if you can't find the refutation, you're already lost."

- **Style:** Sacrificial attacks, king hunts, tactical complications
- **Opens with (White):** e4 — **Black:** Sicilian (c5) or French (e6)
- `depth: 3` · `aggression: 0.95` · `blunder_rate: 0.08` · `acpl: 45`
- **Coaching voice:** *"I offered you the piece. You took it. Now prove me wrong."*

---

### Tigran Petrosian
> "Iron Tigran. The master of prophylaxis — he stops your plan before you know you had one."

- **Style:** Defensive, exchange-heavy, prophylactic
- **Opens with (White):** d4 or c4 — **Black:** d5 or Nf6
- `depth: 3` · `aggression: 0.2` · `blunder_rate: 0.01` · `acpl: 22`
- **Coaching voice:** *"You were planning Nd5. I took on c6 eight moves ago because of that."*

---

### Magnus Carlsen
> "Universal, relentless, endgame-dominant. Turns the smallest edge into a win through sheer technique."

- **Style:** No fixed style — finds the best move in every position
- **Opens with (White):** e4, d4, or Nf3 — **Black:** e5, c5, or e6
- `depth: 3` · `aggression: 0.55` · `blunder_rate: 0.01` · `acpl: 18`
- **Coaching voice:** *"That trade gave me a slightly better endgame. That's all I need."*

---

## Extracting a persona

You can create a persona from any collection of game records — your own history or a PGN file of another player.

### From your own games

After playing a few games, say:

> *"Extract a persona from my games"*

Claude will run the extraction, compute your playing style (opening tendencies, aggression, accuracy), then write a character voice that matches the numbers. The result is saved to `~/.chess_coach/personas/<your_nickname>.json`.

### From a PGN file

Provide a PGN file of any player:

> *"Extract a persona from this PGN file"*

Claude will ask for the file path and the player's name as it appears in the PGN headers, then run the same pipeline. This works for any publicly available game collection — Kasparov, Karpov, your club rival, anyone.

---

## Persona file format

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
  "aggression": 0.75,
  "acpl": 28.0,
  "games_analyzed": 0,
  "created_at": "2026-02-21T00:00:00",

  "description": "Ruthlessly precise. Never satisfied with equality — always plays for the win.",
  "personality": "Cold, calculating, and utterly confident. Sees chess as a scientific problem to solve.",
  "move_voice": "Methodical domination — open files, centralized pieces, no weaknesses left unpunished.",
  "coaching_voice": "You left the e-file open. That's the game right there."
}
```

`source` is one of:
- `"historical"` — hand-crafted bundled persona
- `"extracted"` — extracted from game records
- `"pgn"` — imported from a PGN file

---

## File locations

| Location | Contents |
|----------|----------|
| `plugins/chess-coach/personas/` | Bundled personas (committed to repo) |
| `~/.chess_coach/personas/` | User-extracted personas (runtime only) |

If a user persona has the same ID as a bundled one, the user version takes precedence.

---

## CLI reference

```bash
# List all available personas
python3 plugins/chess-coach/scripts/persona.py list \
  --bundled-dir plugins/chess-coach/personas \
  --user-dir ~/.chess_coach/personas

# Show a specific persona
python3 plugins/chess-coach/scripts/persona.py show --id fischer \
  --bundled-dir plugins/chess-coach/personas \
  --user-dir ~/.chess_coach/personas

# Extract from game history
python3 plugins/chess-coach/scripts/persona.py extract \
  --actor "yonggyu" \
  --id "yonggyu" \
  --games-dir ~/.chess_coach/games

# Import from PGN
python3 plugins/chess-coach/scripts/persona.py import_pgn \
  --pgn /path/to/kasparov.pgn \
  --player "Kasparov" \
  --id kasparov \
  --output ~/.chess_coach/personas/kasparov.json
```
