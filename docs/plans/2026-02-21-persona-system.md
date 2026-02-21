# Persona System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a persona system that lets users play against distinct bot identities — hand-crafted historical players or extracted from any game record collection — with LLM-generated character voices that make each opponent feel alive.

**Architecture:** Two-layer personas (machine params for the engine + character text for Claude's voice) stored as JSON. Extraction pipeline uses a unified algorithm regardless of source — PGN files are first converted to internal game records by `pgn_adapter.py`, then `persona.py extract` runs identically for all sources. The `chess-coach` skill is updated to load a persona at session start and narrate in its voice throughout the game.

**Tech Stack:** Python 3.10+, `python-chess` (`pip install chess`), `pytest`, JSON files.

---

## Context for Implementer

### Project layout
```
plugins/chess-coach/
  scripts/           ← all game logic (Python, run via Bash tool by Claude)
    common.py        ← shared eval, minimax, ELO formula, opening DB
    engine.py        ← move validation, ai_move, game state persistence
    coach.py         ← move evaluation, coaching text
    profile.py       ← ELO history, nickname, difficulty recommendation
    render.py        ← board rendering (--plain for chat, --clear for terminal)
  skills/
    chess-coach/SKILL.md  ← the main skill Claude follows during a game
  personas/          ← TO CREATE: bundled historical persona JSONs (in repo)

~/.chess_coach/      ← runtime storage
  current_game.json  ← active game state
  games/*.json       ← archived completed games (each has move_records[])
  profile.json       ← player ELO + nickname
  personas/*.json    ← TO CREATE: user-extracted personas (not in repo)
```

### How a game record looks (key fields used by extraction)
```json
{
  "player_name": "yonggyu",
  "players": { "white": "yonggyu", "black": "ai" },
  "move_records": [
    {
      "move_san": "e4", "move_uci": "e2e4",
      "player": "white", "actor": "yonggyu",
      "score_before_cp": 0, "score_after_cp": 30
    }
  ],
  "opening": "Sicilian Defense"
}
```

### How `common.get_best_move` works today
```python
def get_best_move(board, depth, blunder_pct=0.0):
    # shuffles moves, runs minimax, returns best
    # blunder_pct: probability of random move (beginner sim)
```
We will add an `aggression` param that bonuses captures/checks.

### How `engine.py ai_move` works today
Reads `level` from state → maps to depth + blunder_pct → calls `get_best_move`.
We will add `--persona <id>` to override those values with persona's params.

---

## Task 1: Test infrastructure + bundled persona JSONs

**Files:**
- Create: `plugins/chess-coach/personas/fischer.json`
- Create: `plugins/chess-coach/personas/tal.json`
- Create: `plugins/chess-coach/personas/petrosian.json`
- Create: `plugins/chess-coach/personas/carlsen.json`
- Create: `plugins/chess-coach/tests/conftest.py`

**Step 1: Create tests directory and conftest**

```bash
mkdir -p plugins/chess-coach/tests
```

Create `plugins/chess-coach/tests/conftest.py`:
```python
import json
import os
import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
PERSONAS_DIR = os.path.join(os.path.dirname(__file__), "..", "personas")

@pytest.fixture
def sample_game_records():
    """Minimal game records for extraction tests."""
    return [
        {
            "player_name": "tester",
            "players": {"white": "tester", "black": "ai"},
            "move_records": [
                {"move_san": "e4",  "move_uci": "e2e4", "player": "white", "actor": "tester",
                 "score_before_cp": 0,   "score_after_cp": 30},
                {"move_san": "e5",  "move_uci": "e7e5", "player": "black", "actor": "ai",
                 "score_before_cp": 30,  "score_after_cp": -10},
                {"move_san": "Nf3", "move_uci": "g1f3", "player": "white", "actor": "tester",
                 "score_before_cp": -10, "score_after_cp": 40},
                {"move_san": "Nc6", "move_uci": "b8c6", "player": "black", "actor": "ai",
                 "score_before_cp": 40,  "score_after_cp": 0},
                # a blunder: big cp loss
                {"move_san": "d4",  "move_uci": "d2d4", "player": "white", "actor": "tester",
                 "score_before_cp": 0,   "score_after_cp": -200},
                {"move_san": "exd4","move_uci": "e5d4", "player": "black", "actor": "ai",
                 "score_before_cp": -200,"score_after_cp": 50},
            ],
            "opening": "Italian Game",
            "result": "0-1"
        },
        {
            "player_name": "tester",
            "players": {"white": "ai", "black": "tester"},
            "move_records": [
                {"move_san": "e4",  "move_uci": "e2e4", "player": "white", "actor": "ai",
                 "score_before_cp": 0,  "score_after_cp": 30},
                # tester as black plays c5 (Sicilian)
                {"move_san": "c5",  "move_uci": "c7c5", "player": "black", "actor": "tester",
                 "score_before_cp": 30, "score_after_cp": 10},
                # a capture by tester
                {"move_san": "Nxe4","move_uci": "c6e4", "player": "black", "actor": "tester",
                 "score_before_cp": 10, "score_after_cp": -30},
            ],
            "opening": "Sicilian Defense",
            "result": "1-0"
        }
    ]
```

**Step 2: Create bundled persona JSONs**

Create `plugins/chess-coach/personas/fischer.json`:
```json
{
  "id": "fischer",
  "name": "Bobby Fischer",
  "source": "historical",
  "description": "Ruthlessly precise. Never satisfied with equality — always plays for the win.",
  "personality": "Cold, calculating, and utterly confident. Sees chess as a scientific problem to solve, not an art form.",
  "move_voice": "Methodical domination — open files, centralized pieces, no weaknesses left unpunished.",
  "coaching_voice": "You left the e-file open. That's the game right there.",
  "opening_moves": { "white": ["e4"], "black": ["c5", "e5"] },
  "depth": 3,
  "blunder_rate": 0.02,
  "aggression": 0.75,
  "acpl": 28.0,
  "games_analyzed": 0,
  "created_at": "2026-02-21T00:00:00"
}
```

Create `plugins/chess-coach/personas/tal.json`:
```json
{
  "id": "tal",
  "name": "Mikhail Tal",
  "source": "historical",
  "description": "The Magician from Riga. Sacrifices material to create chaos — if you can't find the refutation, you're already lost.",
  "personality": "Joyful, provocative, thrives in complications. Chess is art, and chaos is his medium.",
  "move_voice": "Throws pieces into the fire — knights sacrificed, pawns offered, king marching forward.",
  "coaching_voice": "I offered you the piece. You took it. Now prove me wrong.",
  "opening_moves": { "white": ["e4"], "black": ["c5", "e6"] },
  "depth": 3,
  "blunder_rate": 0.08,
  "aggression": 0.95,
  "acpl": 45.0,
  "games_analyzed": 0,
  "created_at": "2026-02-21T00:00:00"
}
```

Create `plugins/chess-coach/personas/petrosian.json`:
```json
{
  "id": "petrosian",
  "name": "Tigran Petrosian",
  "source": "historical",
  "description": "Iron Tigran. The master of prophylaxis — he stops your plan before you know you had one.",
  "personality": "Patient, impenetrable, sees five moves of your plan before you play the first one.",
  "move_voice": "Exchanges pieces that might become dangerous, tightens the position, waits.",
  "coaching_voice": "You were planning Nd5. I took on c6 eight moves ago because of that.",
  "opening_moves": { "white": ["d4", "c4"], "black": ["d5", "Nf6"] },
  "depth": 3,
  "blunder_rate": 0.01,
  "aggression": 0.2,
  "acpl": 22.0,
  "games_analyzed": 0,
  "created_at": "2026-02-21T00:00:00"
}
```

Create `plugins/chess-coach/personas/carlsen.json`:
```json
{
  "id": "carlsen",
  "name": "Magnus Carlsen",
  "source": "historical",
  "description": "Universal, relentless, endgame-dominant. Turns the smallest edge into a win through sheer technique.",
  "personality": "Serene and persistent. Never panics, never rushes. Grinds you down move by move.",
  "move_voice": "Finds the most accurate continuation in every position — no style, just the best move.",
  "coaching_voice": "That trade gave me a slightly better endgame. That's all I need.",
  "opening_moves": { "white": ["e4", "d4", "Nf3"], "black": ["e5", "c5", "e6"] },
  "depth": 3,
  "blunder_rate": 0.01,
  "aggression": 0.55,
  "acpl": 18.0,
  "games_analyzed": 0,
  "created_at": "2026-02-21T00:00:00"
}
```

**Step 3: Verify JSONs are valid**

```bash
python3 -c "
import json, glob
for f in glob.glob('plugins/chess-coach/personas/*.json'):
    d = json.load(open(f))
    required = ['id','name','source','description','personality','move_voice',
                'coaching_voice','opening_moves','depth','blunder_rate','aggression']
    missing = [k for k in required if k not in d]
    print(f'{f}: OK' if not missing else f'{f}: MISSING {missing}')
"
```
Expected: all `OK`.

**Step 4: Commit**

```bash
git add plugins/chess-coach/personas/ plugins/chess-coach/tests/conftest.py
git commit -m "feat: add bundled historical personas and test fixtures"
```

---

## Task 2: `persona.py` — list and show

**Files:**
- Create: `plugins/chess-coach/scripts/persona.py`
- Create: `plugins/chess-coach/tests/test_persona.py`

**Step 1: Write failing tests**

Create `plugins/chess-coach/tests/test_persona.py`:
```python
import json
import os
import subprocess
import sys
import tempfile
import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
PERSONAS = os.path.join(os.path.dirname(__file__), "..", "personas")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def test_list_returns_bundled_personas():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "list",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    assert result["ok"] is True
    ids = [p["id"] for p in result["personas"]]
    assert "fischer" in ids
    assert "tal" in ids


def test_list_includes_source_field():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "list",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    fischer = next(p for p in result["personas"] if p["id"] == "fischer")
    assert fischer["source"] == "historical"


def test_show_returns_full_persona():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "show",
                  "--id", "fischer",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    assert result["ok"] is True
    assert result["persona"]["id"] == "fischer"
    assert "description" in result["persona"]
    assert "aggression" in result["persona"]


def test_show_unknown_id_returns_error():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "show",
                  "--id", "nonexistent_xyz",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    assert result["ok"] is False


def test_show_user_persona_takes_precedence(tmp_path):
    """A user persona with the same id as a bundled one should win."""
    custom = {"id": "fischer", "name": "Custom Fischer", "source": "extracted",
              "description": "", "personality": "", "move_voice": "",
              "coaching_voice": "", "opening_moves": {"white": ["d4"], "black": []},
              "depth": 1, "blunder_rate": 0.5, "aggression": 0.1,
              "acpl": 100.0, "games_analyzed": 5, "created_at": "2026-01-01"}
    (tmp_path / "fischer.json").write_text(json.dumps(custom))
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "show",
                  "--id", "fischer",
                  "--bundled-dir", PERSONAS, "--user-dir", str(tmp_path)])
    assert result["persona"]["source"] == "extracted"
```

**Step 2: Run to verify they fail**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_persona.py -v 2>&1 | head -30
```
Expected: `ModuleNotFoundError` or `FileNotFoundError` — `persona.py` doesn't exist yet.

**Step 3: Implement `persona.py` list and show**

Create `plugins/chess-coach/scripts/persona.py`:
```python
#!/usr/bin/env python3
"""
persona.py — Persona management for chess-coach.

Commands:
  list         [--bundled-dir DIR] [--user-dir DIR]
  show         --id ID [--bundled-dir DIR] [--user-dir DIR]
  extract      --actor NAME --id ID --output PATH [--games-dir DIR]
  import_pgn   --pgn FILE --player NAME --id ID --output PATH

Output: JSON to stdout.
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from common import estimate_elo, elo_to_level

BUNDLED_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "personas")
USER_DIR_DEFAULT    = os.path.expanduser("~/.chess_coach/personas")
GAMES_DIR_DEFAULT   = os.path.expanduser("~/.chess_coach/games")


# ---------------------------------------------------------------------------
# Persona I/O
# ---------------------------------------------------------------------------
def load_persona(persona_id: str, bundled_dir: str, user_dir: str) -> dict | None:
    """Load persona by id. User dir takes precedence over bundled."""
    for directory in [user_dir, bundled_dir]:
        path = os.path.join(directory, f"{persona_id}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return None


def list_personas(bundled_dir: str, user_dir: str) -> list[dict]:
    """Return summary dicts for all available personas. User overrides bundled."""
    seen = {}
    # bundled first, user second (user wins on duplicate id)
    for directory in [bundled_dir, user_dir]:
        for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
            try:
                with open(path) as f:
                    p = json.load(f)
                seen[p["id"]] = {
                    "id":     p["id"],
                    "name":   p["name"],
                    "source": p["source"],
                    "games_analyzed": p.get("games_analyzed", 0),
                }
            except Exception:
                pass
    return list(seen.values())


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_list(args) -> dict:
    personas = list_personas(args.bundled_dir, args.user_dir)
    return {"ok": True, "personas": personas}


def cmd_show(args) -> dict:
    persona = load_persona(args.id, args.bundled_dir, args.user_dir)
    if not persona:
        return {"ok": False, "error": f"Persona '{args.id}' not found."}
    return {"ok": True, "persona": persona}


# ---------------------------------------------------------------------------
# Entry point (extract + import_pgn added in later tasks)
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Persona manager")
    p.add_argument("--bundled-dir", default=BUNDLED_DIR_DEFAULT)
    p.add_argument("--user-dir",    default=USER_DIR_DEFAULT)
    sub = p.add_subparsers(dest="command")

    sub.add_parser("list")

    sh = sub.add_parser("show")
    sh.add_argument("--id", required=True)

    args = p.parse_args()
    args.bundled_dir = os.path.expanduser(args.bundled_dir)
    args.user_dir    = os.path.expanduser(args.user_dir)

    dispatch = {"list": cmd_list, "show": cmd_show}
    result = dispatch[args.command](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_persona.py::test_list_returns_bundled_personas \
                  tests/test_persona.py::test_list_includes_source_field \
                  tests/test_persona.py::test_show_returns_full_persona \
                  tests/test_persona.py::test_show_unknown_id_returns_error \
                  tests/test_persona.py::test_show_user_persona_takes_precedence \
                  -v
```
Expected: all 5 PASS.

**Step 5: Commit**

```bash
git add plugins/chess-coach/scripts/persona.py plugins/chess-coach/tests/test_persona.py
git commit -m "feat: persona.py list and show commands"
```

---

## Task 3: `persona.py` — extract command (machine layer)

**Files:**
- Modify: `plugins/chess-coach/scripts/persona.py`
- Modify: `plugins/chess-coach/tests/test_persona.py`

**Step 1: Add failing tests**

Append to `plugins/chess-coach/tests/test_persona.py`:
```python
# ── extraction tests ──────────────────────────────────────────────────────

def write_game_files(tmp_path, records_list):
    """Helper: write each game record to a temp JSON file."""
    for i, rec in enumerate(records_list):
        (tmp_path / f"game_{i:03d}.json").write_text(json.dumps(rec))


def test_extract_opening_moves_white(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    out = tmp_path / "tester.json"
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
                  "--actor", "tester", "--id", "tester",
                  "--games-dir", str(tmp_path), "--output", str(out)])
    assert result["ok"] is True
    assert "e4" in result["opening_moves"]["white"]


def test_extract_opening_moves_black(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    out = tmp_path / "tester.json"
    run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
         "--actor", "tester", "--id", "tester",
         "--games-dir", str(tmp_path), "--output", str(out)])
    persona = json.loads(out.read_text())
    assert "c5" in persona["opening_moves"]["black"]


def test_extract_aggression_is_float(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    out = tmp_path / "tester.json"
    run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
         "--actor", "tester", "--id", "tester",
         "--games-dir", str(tmp_path), "--output", str(out)])
    persona = json.loads(out.read_text())
    assert 0.0 <= persona["aggression"] <= 1.0


def test_extract_games_analyzed_count(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    out = tmp_path / "tester.json"
    run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
         "--actor", "tester", "--id", "tester",
         "--games-dir", str(tmp_path), "--output", str(out)])
    persona = json.loads(out.read_text())
    assert persona["games_analyzed"] == 2


def test_extract_depth_derived_from_acpl(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    out = tmp_path / "tester.json"
    run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
         "--actor", "tester", "--id", "tester",
         "--games-dir", str(tmp_path), "--output", str(out)])
    persona = json.loads(out.read_text())
    assert persona["depth"] in [1, 2, 3]


def test_extract_character_layer_empty(tmp_path, sample_game_records):
    """extract outputs only machine layer — character fields are blank."""
    write_game_files(tmp_path, sample_game_records)
    out = tmp_path / "tester.json"
    run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
         "--actor", "tester", "--id", "tester",
         "--games-dir", str(tmp_path), "--output", str(out)])
    persona = json.loads(out.read_text())
    assert persona["description"] == ""
    assert persona["personality"] == ""
    assert persona["move_voice"] == ""
    assert persona["coaching_voice"] == ""
```

**Step 2: Run to verify they fail**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_persona.py -k "extract" -v 2>&1 | head -20
```
Expected: FAIL — `extract` command not implemented yet.

**Step 3: Implement extract in `persona.py`**

Add after `cmd_show` in `persona.py`:
```python
def extract_machine_layer(actor: str, games_dir: str) -> dict | None:
    """
    Read all game JSONs in games_dir, filter by actor, compute machine layer.
    Returns dict of machine-layer fields, or None if no games found.
    """
    import chess as _chess

    all_records = []
    game_count  = 0

    for path in sorted(glob.glob(os.path.join(games_dir, "*.json"))):
        try:
            with open(path) as f:
                state = json.load(f)
        except Exception:
            continue

        records = state.get("move_records", [])
        actor_records = [r for r in records if r.get("actor") == actor]
        if not actor_records:
            continue

        all_records.extend(actor_records)
        game_count += 1

    if not all_records:
        return None

    # Opening preferences (most common first moves as each color)
    def top_moves(color, n=5):
        from collections import Counter
        c = Counter()
        for r in all_records:
            if r.get("player") == color:
                c[r["move_san"]] += 1
        return [m for m, _ in c.most_common(n)]

    white_moves = top_moves("white")
    black_moves = top_moves("black")

    # Aggression: fraction of moves that are captures (SAN contains 'x')
    total = len(all_records)
    captures = sum(1 for r in all_records if "x" in r.get("move_san", ""))
    aggression = round(captures / total, 3) if total else 0.0

    # ACPL + blunder rate from existing estimate_elo (needs color — pick dominant)
    white_count = sum(1 for r in all_records if r.get("player") == "white")
    dominant_color = "white" if white_count >= total / 2 else "black"
    elo_data = estimate_elo(all_records, player=dominant_color)

    acpl         = elo_data.get("acpl") or 80.0
    blunder_rate = elo_data.get("blunder_rate") or 0.05

    # Depth derived from ACPL
    if acpl < 40:
        depth = 3
    elif acpl < 80:
        depth = 2
    else:
        depth = 1

    return {
        "opening_moves": {"white": white_moves, "black": black_moves},
        "aggression":    aggression,
        "blunder_rate":  round(blunder_rate, 4),
        "acpl":          round(acpl, 1),
        "depth":         depth,
        "games_analyzed": game_count,
    }


def cmd_extract(args) -> dict:
    machine = extract_machine_layer(args.actor, args.games_dir)
    if not machine:
        return {"ok": False, "error": f"No games found for actor '{args.actor}' in {args.games_dir}"}

    persona = {
        "id":      args.id,
        "name":    args.actor,
        "source":  "extracted",
        # character layer — blank; skill calls LLM to fill these
        "description":   "",
        "personality":   "",
        "move_voice":    "",
        "coaching_voice": "",
        "created_at": datetime.now().isoformat(),
        **machine,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(persona, f, indent=2, ensure_ascii=False)

    return {"ok": True, **machine, "opening_moves": machine["opening_moves"]}
```

Add `extract` subparser and dispatch in `main()`:
```python
    # in main(), before args = p.parse_args():
    ex = sub.add_parser("extract")
    ex.add_argument("--actor",     required=True)
    ex.add_argument("--id",        required=True)
    ex.add_argument("--output",    required=True)
    ex.add_argument("--games-dir", default=GAMES_DIR_DEFAULT)

    # in dispatch dict:
    dispatch["extract"] = cmd_extract

    # in args expansion:
    if hasattr(args, 'games_dir'):
        args.games_dir = os.path.expanduser(args.games_dir)
    if hasattr(args, 'output'):
        args.output = os.path.expanduser(args.output)
```

**Step 4: Run tests**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_persona.py -k "extract" -v
```
Expected: all 6 PASS.

**Step 5: Commit**

```bash
git add plugins/chess-coach/scripts/persona.py plugins/chess-coach/tests/test_persona.py
git commit -m "feat: persona.py extract command (machine layer)"
```

---

## Task 4: `pgn_adapter.py` — PGN to internal game records

**Files:**
- Create: `plugins/chess-coach/scripts/pgn_adapter.py`
- Create: `plugins/chess-coach/tests/test_pgn_adapter.py`

**Step 1: Write failing tests**

Create `plugins/chess-coach/tests/test_pgn_adapter.py`:
```python
import json
import os
import subprocess
import sys
import tempfile
import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")

SAMPLE_PGN = """
[Event "Test Game"]
[White "Fischer"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0
"""

def run_adapter(pgn_text, player="Fischer", output_dir=None):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
        f.write(pgn_text)
        pgn_path = f.name
    out_dir = output_dir or tempfile.mkdtemp()
    r = subprocess.run(
        [sys.executable, f"{SCRIPTS}/pgn_adapter.py",
         "--pgn", pgn_path, "--player", player, "--output-dir", out_dir],
        capture_output=True, text=True
    )
    result = json.loads(r.stdout)
    return result, out_dir


def test_adapter_produces_game_file():
    result, out_dir = run_adapter(SAMPLE_PGN)
    assert result["ok"] is True
    assert result["games_written"] == 1


def test_adapter_sets_correct_actor():
    result, out_dir = run_adapter(SAMPLE_PGN, player="Fischer")
    game_files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    game = json.loads(open(os.path.join(out_dir, game_files[0])).read())
    white_moves = [r for r in game["move_records"] if r["player"] == "white"]
    assert all(r["actor"] == "Fischer" for r in white_moves)


def test_adapter_sets_ai_for_opponent():
    result, out_dir = run_adapter(SAMPLE_PGN, player="Fischer")
    game_files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    game = json.loads(open(os.path.join(out_dir, game_files[0])).read())
    black_moves = [r for r in game["move_records"] if r["player"] == "black"]
    assert all(r["actor"] == "ai" for r in black_moves)


def test_adapter_includes_cp_scores():
    result, out_dir = run_adapter(SAMPLE_PGN)
    game_files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    game = json.loads(open(os.path.join(out_dir, game_files[0])).read())
    for r in game["move_records"]:
        assert "score_before_cp" in r
        assert "score_after_cp" in r


def test_adapter_multi_game_pgn():
    two_games = SAMPLE_PGN + "\n" + SAMPLE_PGN.replace("1-0", "0-1")
    result, _ = run_adapter(two_games)
    assert result["games_written"] == 2
```

**Step 2: Run to verify they fail**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_pgn_adapter.py -v 2>&1 | head -20
```
Expected: FAIL — `pgn_adapter.py` doesn't exist.

**Step 3: Implement `pgn_adapter.py`**

Create `plugins/chess-coach/scripts/pgn_adapter.py`:
```python
#!/usr/bin/env python3
"""
pgn_adapter.py — Convert PGN files to internal game record format.

Each game in the PGN becomes one JSON file in the output directory,
using the same schema as ~/.chess_coach/games/*.json.
Positions are re-evaluated with common.evaluate() to populate cp scores.

Usage:
  python3 pgn_adapter.py --pgn FILE --player NAME --output-dir DIR
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from common import evaluate, score_to_winrate, detect_opening

import chess
import chess.pgn


def convert_game(game: chess.pgn.Game, player_name: str) -> dict:
    """Convert a python-chess Game to internal game record format."""
    headers = game.headers
    white   = headers.get("White", "")
    black   = headers.get("Black", "")
    result  = headers.get("Result", "*")

    # Determine which color the target player is
    if player_name.lower() in white.lower():
        player_color = "white"
    elif player_name.lower() in black.lower():
        player_color = "black"
    else:
        # Default to white if name not found
        player_color = "white"

    players = {
        "white": player_name if player_color == "white" else "ai",
        "black": player_name if player_color == "black" else "ai",
    }

    board        = game.board()
    move_records = []
    moves_uci    = []
    moves_san    = []

    for node in game.mainline():
        move         = node.move
        color        = "white" if board.turn == chess.WHITE else "black"
        actor        = players[color]
        score_before = evaluate(board)
        san          = board.san(move)
        board.push(move)
        score_after  = evaluate(board)

        move_records.append({
            "move_san":        san,
            "move_uci":        move.uci(),
            "player":          color,
            "actor":           actor,
            "score_before_cp": score_before,
            "score_after_cp":  score_after,
            "winrate_white":   score_to_winrate(score_after, chess.WHITE),
            "coaching":        None,
        })
        moves_uci.append(move.uci())
        moves_san.append(san)

    opening = detect_opening(moves_san)

    return {
        "player_name":  player_name,
        "players":      players,
        "color":        player_color,
        "level":        "unknown",
        "mode":         "pgn",
        "moves_uci":    moves_uci,
        "moves_san":    moves_san,
        "move_records": move_records,
        "move_count":   len(move_records),
        "result":       result,
        "opening":      opening,
        "pgn_white":    white,
        "pgn_black":    black,
    }


def main():
    p = argparse.ArgumentParser(description="PGN to internal game records")
    p.add_argument("--pgn",        required=True)
    p.add_argument("--player",     required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    args.pgn        = os.path.expanduser(args.pgn)
    args.output_dir = os.path.expanduser(args.output_dir)
    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.pgn) as f:
        content = f.read()

    pgn_io      = io.StringIO(content)
    games_written = 0

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        record = convert_game(game, args.player)
        ts     = datetime.now().strftime(f"%Y%m%d_%H%M%S_{games_written:04d}")
        out    = os.path.join(args.output_dir, f"game_{ts}.json")
        with open(out, "w") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        games_written += 1

    print(json.dumps({"ok": True, "games_written": games_written,
                      "output_dir": args.output_dir}, indent=2))


if __name__ == "__main__":
    main()
```

**Step 4: Run tests**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_pgn_adapter.py -v
```
Expected: all 5 PASS.

**Step 5: Commit**

```bash
git add plugins/chess-coach/scripts/pgn_adapter.py plugins/chess-coach/tests/test_pgn_adapter.py
git commit -m "feat: pgn_adapter.py converts PGN to internal game records"
```

---

## Task 5: `persona.py` — import_pgn command

**Files:**
- Modify: `plugins/chess-coach/scripts/persona.py`
- Modify: `plugins/chess-coach/tests/test_persona.py`

**Step 1: Add failing test**

Append to `test_persona.py`:
```python
# ── import_pgn tests ──────────────────────────────────────────────────────

SAMPLE_PGN = """
[Event "Test"]
[White "Fischer"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""


def test_import_pgn_creates_persona(tmp_path):
    pgn_file = tmp_path / "test.pgn"
    pgn_file.write_text(SAMPLE_PGN)
    out = tmp_path / "fischer_extracted.json"
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "import_pgn",
                  "--pgn", str(pgn_file), "--player", "Fischer",
                  "--id", "fischer_test", "--output", str(out)])
    assert result["ok"] is True
    assert out.exists()
    persona = json.loads(out.read_text())
    assert persona["id"] == "fischer_test"
    assert persona["source"] == "pgn"
    assert "e4" in persona["opening_moves"]["white"]
```

**Step 2: Run to verify it fails**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_persona.py::test_import_pgn_creates_persona -v
```
Expected: FAIL.

**Step 3: Implement `import_pgn` in `persona.py`**

Add to `persona.py` after `cmd_extract`:
```python
def cmd_import_pgn(args) -> dict:
    import tempfile
    import subprocess

    tmp_dir = tempfile.mkdtemp(prefix="pgn_games_")
    adapter = os.path.join(os.path.dirname(__file__), "pgn_adapter.py")

    r = subprocess.run(
        [sys.executable, adapter,
         "--pgn", args.pgn, "--player", args.player, "--output-dir", tmp_dir],
        capture_output=True, text=True
    )
    adapter_result = json.loads(r.stdout)
    if not adapter_result.get("ok"):
        return {"ok": False, "error": "PGN conversion failed", "details": adapter_result}

    # Now extract from the temp game files
    machine = extract_machine_layer(args.player, tmp_dir)
    if not machine:
        return {"ok": False, "error": "No moves found for player in PGN"}

    persona = {
        "id":      args.id,
        "name":    args.player,
        "source":  "pgn",
        "description":   "",
        "personality":   "",
        "move_voice":    "",
        "coaching_voice": "",
        "created_at": datetime.now().isoformat(),
        **machine,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(persona, f, indent=2, ensure_ascii=False)

    return {"ok": True, "games_processed": adapter_result["games_written"], **machine}
```

Add subparser and dispatch in `main()`:
```python
    ip = sub.add_parser("import_pgn")
    ip.add_argument("--pgn",    required=True)
    ip.add_argument("--player", required=True)
    ip.add_argument("--id",     required=True)
    ip.add_argument("--output", required=True)

    dispatch["import_pgn"] = cmd_import_pgn
```

**Step 4: Run tests**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_persona.py -v
```
Expected: all tests PASS.

**Step 5: Commit**

```bash
git add plugins/chess-coach/scripts/persona.py plugins/chess-coach/tests/test_persona.py
git commit -m "feat: persona.py import_pgn command"
```

---

## Task 6: `common.py` — aggression bias in `get_best_move`

**Files:**
- Modify: `plugins/chess-coach/scripts/common.py`
- Create: `plugins/chess-coach/tests/test_common_aggression.py`

**Step 1: Write failing test**

Create `plugins/chess-coach/tests/test_common_aggression.py`:
```python
import sys
import os
import chess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from common import get_best_move


def test_aggression_prefers_capture():
    """
    Set up a position where white can capture a pawn or make a quiet move.
    With high aggression, the capture should be preferred.
    """
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
    # White can capture d5 with exd5, or make various quiet moves
    capture_move = chess.Move.from_uci("e4d5")
    assert capture_move in board.legal_moves

    move_high, _ = get_best_move(board, depth=1, blunder_pct=0.0, aggression=1.0)
    move_low,  _ = get_best_move(board, depth=1, blunder_pct=0.0, aggression=0.0)

    # With max aggression, should prefer the capture
    assert move_high == capture_move


def test_aggression_zero_does_not_crash():
    board = chess.Board()
    move, score = get_best_move(board, depth=1, blunder_pct=0.0, aggression=0.0)
    assert move is not None
    assert isinstance(score, int)


def test_aggression_parameter_is_optional():
    """get_best_move still works without aggression param (default=0)."""
    board = chess.Board()
    move, score = get_best_move(board, depth=1, blunder_pct=0.0)
    assert move is not None
```

**Step 2: Run to verify they fail**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_common_aggression.py -v 2>&1 | head -20
```
Expected: FAIL — `get_best_move` has no `aggression` param yet.

**Step 3: Update `get_best_move` in `common.py`**

Replace the existing `get_best_move` function:
```python
def get_best_move(
    board: chess.Board,
    depth: int,
    blunder_pct: float = 0.0,
    aggression: float = 0.0,
) -> tuple[chess.Move | None, int]:
    """
    Return (best_move, score_after_best_move).
    blunder_pct: probability of playing a random move (beginner simulation).
    aggression: 0–1 bonus applied to captures and checks (biases move selection).
    """
    import random
    moves = list(board.legal_moves)
    if not moves:
        return None, 0

    random.shuffle(moves)

    if blunder_pct > 0 and random.random() < blunder_pct:
        return random.choice(moves), 0

    is_white  = board.turn == chess.WHITE
    best_move = moves[0]
    best_val  = -999999 if is_white else 999999

    aggression_bonus = int(aggression * 50)

    for move in moves:
        board.push(move)
        val = minimax(board, depth - 1, -999999, 999999, not is_white)
        board.pop()

        # Apply aggression bonus for captures and checks
        if aggression_bonus > 0:
            is_capture = board.is_capture(move)
            board.push(move)
            gives_check = board.is_check()
            board.pop()
            if is_capture or gives_check:
                val = val + aggression_bonus if is_white else val - aggression_bonus

        if (is_white and val > best_val) or (not is_white and val < best_val):
            best_val, best_move = val, move

    return best_move, best_val
```

**Step 4: Run tests**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_common_aggression.py -v
```
Expected: all 3 PASS.

**Step 5: Commit**

```bash
git add plugins/chess-coach/scripts/common.py plugins/chess-coach/tests/test_common_aggression.py
git commit -m "feat: add aggression param to get_best_move"
```

---

## Task 7: `engine.py` — `ai_move --persona` flag

**Files:**
- Modify: `plugins/chess-coach/scripts/engine.py`
- Create: `plugins/chess-coach/tests/test_engine_persona.py`

**Step 1: Write failing tests**

Create `plugins/chess-coach/tests/test_engine_persona.py`:
```python
import json
import os
import subprocess
import sys
import tempfile
import pytest

SCRIPTS  = os.path.join(os.path.dirname(__file__), "..", "scripts")
PERSONAS = os.path.join(os.path.dirname(__file__), "..", "personas")


def new_game(color="white", level="intermediate"):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    subprocess.run([sys.executable, f"{SCRIPTS}/engine.py", "new_game",
                    "--color", color, "--level", level,
                    "--state", state_path], capture_output=True)
    return state_path


def ai_move(state_path, persona_id=None, persona_dir=None):
    cmd = [sys.executable, f"{SCRIPTS}/engine.py", "ai_move",
           "--state", state_path]
    if persona_id:
        cmd += ["--persona", persona_id, "--bundled-persona-dir", persona_dir or PERSONAS]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def test_ai_move_with_persona_succeeds():
    state = new_game(color="black")   # AI plays white
    result = ai_move(state, persona_id="tal", persona_dir=PERSONAS)
    assert result["ok"] is True
    assert result["move_san"] != ""


def test_ai_move_without_persona_still_works():
    state = new_game(color="black")
    result = ai_move(state)
    assert result["ok"] is True


def test_ai_move_unknown_persona_falls_back():
    """Unknown persona ID should fall back to default behavior, not crash."""
    state = new_game(color="black")
    result = ai_move(state, persona_id="nonexistent_xyz", persona_dir=PERSONAS)
    assert result["ok"] is True


def test_ai_move_uses_persona_opening(tmp_path):
    """With a persona that always plays e4, first white move should be e4."""
    # Create a persona that mandates e4 as first white move
    persona = {
        "id": "test_e4_persona", "name": "E4 Bot", "source": "extracted",
        "description": "", "personality": "", "move_voice": "", "coaching_voice": "",
        "opening_moves": {"white": ["e4"], "black": []},
        "depth": 1, "blunder_rate": 0.0, "aggression": 0.0,
        "acpl": 50.0, "games_analyzed": 1, "created_at": "2026-01-01"
    }
    (tmp_path / "test_e4_persona.json").write_text(json.dumps(persona))

    state = new_game(color="black")  # AI plays white, move 1
    result = ai_move(state, persona_id="test_e4_persona", persona_dir=str(tmp_path))
    assert result["move_san"] == "e4"
```

**Step 2: Run to verify they fail**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_engine_persona.py -v 2>&1 | head -20
```
Expected: FAIL — `ai_move` has no `--persona` flag yet.

**Step 3: Update `engine.py`**

Add persona loading helper before `cmd_ai_move`:
```python
BUNDLED_PERSONA_DIR_DEFAULT = os.path.join(
    os.path.dirname(__file__), "..", "personas"
)

def load_persona_for_engine(persona_id: str, bundled_dir: str) -> dict | None:
    """Load persona from bundled dir then user dir. Returns None if not found."""
    user_dir = os.path.expanduser("~/.chess_coach/personas")
    for directory in [user_dir, bundled_dir]:
        path = os.path.join(directory, f"{persona_id}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return None
```

Update `cmd_ai_move` to use persona when provided:
```python
def cmd_ai_move(args) -> dict:
    state = load_state(args.state)
    board = board_from_state(state)

    if board.is_game_over():
        return {"ok": False, "error": "Game is already over."}

    score_before = evaluate(board)
    turn_before  = board.turn
    player       = "white" if turn_before == chess.WHITE else "black"
    actor        = state.get("players", {}).get(player, "ai")

    # Resolve depth, blunder_pct, aggression — persona overrides level
    persona      = None
    opening_move = None

    if getattr(args, "persona", None):
        bundled_dir = getattr(args, "bundled_persona_dir",
                              BUNDLED_PERSONA_DIR_DEFAULT)
        persona = load_persona_for_engine(args.persona, bundled_dir)

    if persona:
        depth      = persona.get("depth", 2)
        blunder_pc = persona.get("blunder_rate", 0.0)
        aggression = persona.get("aggression", 0.0)
        # Opening book: use persona's preferred move if within first 10 moves
        move_num   = state.get("move_count", 0)
        if move_num < 10:
            pref_moves = persona.get("opening_moves", {}).get(player, [])
            for san in pref_moves:
                try:
                    candidate = board.parse_san(san)
                    if candidate in board.legal_moves:
                        opening_move = candidate
                        break
                except Exception:
                    pass
    else:
        level      = state.get("level", "intermediate")
        depth      = DEPTH_MAP.get(level, 2)
        blunder_pc = BLUNDER_MAP.get(level, 0.0)
        aggression = 0.0

    if opening_move:
        move  = opening_move
        score_after = evaluate(chess.Board())
        board.push(move)
        score_after = evaluate(board)
    else:
        move, _ = get_best_move(board, depth, blunder_pc, aggression)
        if not move:
            return {"ok": False, "error": "No legal moves available."}
        san = board.san(move)
        board.push(move)
        score_after = evaluate(board)

    san = board.peek() and state["moves_san"]  # recalculate below

    # redo san cleanly
    board.pop()
    san = board.san(move)
    board.push(move)

    record = make_move_record(move, san, player, actor, score_before, score_after)
    state["moves_uci"].append(move.uci())
    state["moves_san"].append(san)
    state["move_records"].append(record)
    state["move_count"] += 1

    opening = detect_opening(state["moves_san"])
    if opening:
        state["opening"] = opening

    check_game_over(board, state)
    save_state(state, args.state)

    return {
        "ok":            True,
        "move_san":      san,
        "move_uci":      move.uci(),
        "fen":           board.fen(),
        "turn":          "white" if board.turn == chess.WHITE else "black",
        "score_cp":      score_after,
        "winrate_white": score_to_winrate(score_after, chess.WHITE),
        "is_check":      board.is_check(),
        "is_checkmate":  board.is_checkmate(),
        "is_stalemate":  board.is_stalemate(),
        "is_game_over":  board.is_game_over(),
        "result":        state["result"],
        "moves_san":     state["moves_san"],
        "opening":       state.get("opening"),
        "persona_used":  persona["id"] if persona else None,
    }
```

Add `--persona` and `--bundled-persona-dir` args in `main()`:
```python
    ai.add_argument("--persona",             default=None)
    ai.add_argument("--bundled-persona-dir", default=BUNDLED_PERSONA_DIR_DEFAULT)
```

**Step 4: Run tests**

```bash
cd plugins/chess-coach
python3 -m pytest tests/test_engine_persona.py -v
```
Expected: all 4 PASS.

**Step 5: Run all tests to check nothing broken**

```bash
cd plugins/chess-coach
python3 -m pytest tests/ -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add plugins/chess-coach/scripts/engine.py plugins/chess-coach/tests/test_engine_persona.py
git commit -m "feat: engine ai_move supports --persona flag with opening book"
```

---

## Task 8: `extract-persona` skill

**Files:**
- Create: `plugins/chess-coach/skills/extract-persona/SKILL.md`

**Step 1: Create skill directory and file**

```bash
mkdir -p plugins/chess-coach/skills/extract-persona
```

Create `plugins/chess-coach/skills/extract-persona/SKILL.md`:
````markdown
---
name: extract-persona
description: |
  Extract a chess persona from game records or a PGN file.
  Invoked when the user wants to create a bot persona from their own
  game history or from a historical player's PGN games.
---

# Extract Persona Skill

## Finding Scripts

```bash
SKILL_BASE="<Base directory from context>"
SCRIPT_DIR="$(python3 -c "import os,sys; print(os.path.normpath(os.path.join(sys.argv[1],'..','..','scripts')))" "$SKILL_BASE")"
PERSONA_DIR="$(python3 -c "import os,sys; print(os.path.normpath(os.path.join(sys.argv[1],'..','..','personas')))" "$SKILL_BASE")"
USER_PERSONA_DIR="$HOME/.chess_coach/personas"
```

## Flow

### Step 1 — Ask source

"Extract from your own game history, or import a PGN file?"

### Step 2a — Game history path

```bash
# Get nickname from profile
python3 "$SCRIPT_DIR/profile.py" recommend
```

Use `nickname` as the actor name. Then:

```bash
python3 "$SCRIPT_DIR/persona.py" extract \
  --actor "<nickname>" \
  --id "<nickname>" \
  --games-dir ~/.chess_coach/games \
  --output ~/.chess_coach/personas/<nickname>.json
```

Read the raw stats output (machine layer only — no description/voice yet).

### Step 2b — PGN path

Ask: "Path to the PGN file?" and "Player name in the PGN?"

```bash
python3 "$SCRIPT_DIR/persona.py" import_pgn \
  --pgn "<path>" \
  --player "<player_name>" \
  --id "<id>" \
  --output ~/.chess_coach/personas/<id>.json
```

### Step 3 — Claude enriches the character layer

Read the raw stats just written. Based on the numbers, write:

- **description**: 1–2 sentences capturing the overall identity
- **personality**: tone, attitude, how this player thinks about chess
- **move_voice**: how their moves feel — the pattern of their play
- **coaching_voice**: one example line they'd say after a user mistake

Consider:
- High aggression (>0.7) → tactical, attacking style
- Low blunder_rate (<0.03) → precise, unforgiving
- Narrow opening repertoire → specialist; wide → universal
- High ACPL (>80) → mistakes are part of the game, looser style
- If persona is a known historical player, draw on their actual known character

Then update the file with the character layer:

```python
import json, os

path = os.path.expanduser("~/.chess_coach/personas/<id>.json")
persona = json.load(open(path))
persona["description"]   = "<generated>"
persona["personality"]   = "<generated>"
persona["move_voice"]    = "<generated>"
persona["coaching_voice"] = "<generated>"
json.dump(persona, open(path, "w"), indent=2, ensure_ascii=False)
```

### Step 4 — Confirm

Tell the user:
```
Persona "<name>" created and saved.
  Games analyzed: N
  ACPL: X  |  Aggression: Y  |  Depth: Z

"<description>"

You can now play against this persona. Say "let's play" to start.
```
````

**Step 2: Verify file exists and is valid markdown**

```bash
cat plugins/chess-coach/skills/extract-persona/SKILL.md | head -5
```
Expected: shows the frontmatter `---` and name field.

**Step 3: Commit**

```bash
git add plugins/chess-coach/skills/extract-persona/
git commit -m "feat: extract-persona skill for building personas from games or PGN"
```

---

## Task 9: Update `chess-coach` skill — persona selection and voice

**Files:**
- Modify: `plugins/chess-coach/skills/chess-coach/SKILL.md`

**Step 1: Read current Session Start Flow section**

Open `plugins/chess-coach/skills/chess-coach/SKILL.md` and locate `## Session Start Flow`.

**Step 2: Add persona selection step after Step 1 (profile load)**

Insert between Step 1 and Step 2 (new game):

````markdown
### Step 1b — Persona selection (optional)

```bash
python3 "$SCRIPT_DIR/persona.py" list \
  --bundled-dir "$SCRIPT_DIR/../personas" \
  --user-dir ~/.chess_coach/personas
```

Ask: "Play against the standard AI, or choose a persona?"
- Show available personas by name with a one-line description
- If user chooses one: store `PERSONA_ID` for this session
- If standard AI: `PERSONA_ID` is empty

If a persona is chosen, load it:
```bash
python3 "$SCRIPT_DIR/persona.py" show --id "$PERSONA_ID" \
  --bundled-dir "$SCRIPT_DIR/../personas" \
  --user-dir ~/.chess_coach/personas
```

Read `description`, `personality`, `move_voice`, `coaching_voice` — hold these
in context for the entire session. Introduce the persona to the user:

"You'll be playing against **\<name\>**. \<description\>"
````

**Step 3: Update ai_move calls to pass --persona**

Find every occurrence of:
```bash
python3 "$SCRIPT_DIR/engine.py" ai_move
```

Replace with:
```bash
python3 "$SCRIPT_DIR/engine.py" ai_move \
  ${PERSONA_ID:+--persona "$PERSONA_ID" --bundled-persona-dir "$SCRIPT_DIR/../personas"}
```

**Step 4: Add voice narration instruction after AI move section**

After the existing "Claude relays coaching_lines from explain_ai" line, add:

```markdown
If a persona is active, narrate the AI move in the persona's `move_voice`
style — brief, in character, not just repeating the coaching text.
After user moves, react in `coaching_voice` style: one sentence, as that
persona would say it.

Do NOT break character during gameplay. The persona's personality should
color every response until the game ends.
```

**Step 5: Verify the skill reads cleanly end-to-end**

```bash
cat plugins/chess-coach/skills/chess-coach/SKILL.md | grep -n "persona" | head -20
```
Expected: multiple references — list, show, ai_move, voice narration.

**Step 6: Run full test suite one final time**

```bash
cd plugins/chess-coach
python3 -m pytest tests/ -v
```
Expected: all PASS.

**Step 7: Commit and push**

```bash
git add plugins/chess-coach/skills/chess-coach/SKILL.md
git commit -m "feat: chess-coach skill persona selection and in-character voice narration"
git push
```

---

## Summary

| Task | Deliverable |
|---|---|
| 1 | 4 bundled persona JSONs + test fixtures |
| 2 | `persona.py` list + show |
| 3 | `persona.py` extract (machine layer) |
| 4 | `pgn_adapter.py` PGN → internal records |
| 5 | `persona.py` import_pgn |
| 6 | `common.py` aggression bias |
| 7 | `engine.py` --persona flag + opening book |
| 8 | `extract-persona` skill |
| 9 | `chess-coach` skill updated with persona flow + voice |
