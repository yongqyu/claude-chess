#!/usr/bin/env python3
"""
persona.py — Persona management for chess-coach.

Commands:
  list         [--bundled-dir DIR] [--user-dir DIR]
  show         --id ID [--bundled-dir DIR] [--user-dir DIR]
  extract      --actor NAME --id ID [--games-dir DIR]
  import_pgn   --pgn FILE --player NAME --id ID [--output PATH]

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
    for directory in [bundled_dir, user_dir]:
        for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
            try:
                with open(path) as f:
                    p = json.load(f)
                seen[p["id"]] = {
                    "id":     p["id"],
                    "name":   p["name"],
                    "source": p["source"],
                }
            except Exception:
                pass
    return list(seen.values())


def cmd_list(args) -> dict:
    personas = list_personas(args.bundled_dir, args.user_dir)
    return {"ok": True, "personas": personas}


def cmd_show(args) -> dict:
    persona = load_persona(args.id, args.bundled_dir, args.user_dir)
    if not persona:
        return {"ok": False, "error": f"Persona '{args.id}' not found."}
    return {"ok": True, "persona": persona}


def extract_machine_layer(actor: str, games_dir: str) -> dict | None:
    """Read game JSONs, filter by actor, compute machine layer."""
    from collections import Counter

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

        # Track per-game move index per color for opening_moves computation
        white_move_idx = 0
        black_move_idx = 0
        for r in records:
            color = r.get("player")
            if color == "white":
                r = dict(r, _white_move_idx=white_move_idx)
                white_move_idx += 1
            elif color == "black":
                r = dict(r, _black_move_idx=black_move_idx)
                black_move_idx += 1
            all_records.append(r)
        game_count += 1

    if not all_records:
        return None

    def top_moves(color, n=5):
        c = Counter()
        idx_key = f"_{color}_move_idx"
        for r in all_records:
            if r.get("actor") == actor and r.get("player") == color:
                if r.get(idx_key, 999) < 5:
                    c[r["move_san"]] += 1
        return [m for m, _ in c.most_common(n)]

    white_moves = top_moves("white")
    black_moves = top_moves("black")

    actor_records = [r for r in all_records if r.get("actor") == actor]
    total    = len(actor_records)
    captures = sum(1 for r in actor_records if "x" in r.get("move_san", ""))
    aggression = round(captures / total, 3) if total else 0.0

    white_count    = sum(1 for r in actor_records if r.get("player") == "white")
    dominant_color = "white" if white_count >= total / 2 else "black"
    elo_data       = estimate_elo(actor_records, player=dominant_color)

    acpl         = elo_data.get("acpl") or 80.0
    blunder_rate = elo_data.get("blunder_rate") or 0.05

    if acpl < 40:
        depth = 3
    elif acpl < 80:
        depth = 2
    else:
        depth = 1

    return {
        "opening_moves":  {"white": white_moves, "black": black_moves},
        "aggression":     aggression,
        "blunder_rate":   round(blunder_rate, 4),
        "acpl":           round(acpl, 1),
        "depth":          depth,
        "games_analyzed": game_count,
    }


def cmd_extract(args) -> dict:
    machine = extract_machine_layer(args.actor, args.games_dir)
    if not machine:
        return {"ok": False, "error": f"No games found for actor '{args.actor}' in {args.games_dir}"}

    persona = {
        "id":             args.id,
        "name":           args.actor,
        "source":         "extracted",
        "description":    "",
        "personality":    "",
        "move_voice":     "",
        "coaching_voice": "",
        "created_at":     datetime.now().isoformat(),
        **machine,
    }

    return {"ok": True, "persona": persona}


def cmd_import_pgn(args) -> dict:
    import tempfile
    import subprocess

    tmp_dir = tempfile.mkdtemp(prefix="pgn_games_")
    adapter = os.path.join(os.path.dirname(__file__), "pgn_adapter.py")

    r = subprocess.run(
        [sys.executable, adapter,
         "--pgn", args.pgn, "--player", args.player, "--output", tmp_dir],
        capture_output=True, text=True
    )
    try:
        adapter_result = json.loads(r.stdout)
    except Exception:
        return {"ok": False, "error": f"PGN adapter failed: {r.stderr}"}

    if not adapter_result.get("ok"):
        return {"ok": False, "error": "PGN conversion failed", "details": adapter_result}

    machine = extract_machine_layer(args.player, tmp_dir)
    if not machine:
        return {"ok": False, "error": "No moves found for player in PGN"}

    persona = {
        "id":             args.id,
        "name":           args.player,
        "source":         "pgn",
        "description":    "",
        "personality":    "",
        "move_voice":     "",
        "coaching_voice": "",
        "created_at":     datetime.now().isoformat(),
        **machine,
    }

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(persona, f, indent=2, ensure_ascii=False)

    return {"ok": True, "persona": persona}


def main():
    p = argparse.ArgumentParser(description="Persona manager")
    sub = p.add_subparsers(dest="command")

    ls = sub.add_parser("list")
    ls.add_argument("--bundled-dir", default=BUNDLED_DIR_DEFAULT)
    ls.add_argument("--user-dir",    default=USER_DIR_DEFAULT)

    sh = sub.add_parser("show")
    sh.add_argument("--id", required=True)
    sh.add_argument("--bundled-dir", default=BUNDLED_DIR_DEFAULT)
    sh.add_argument("--user-dir",    default=USER_DIR_DEFAULT)

    ex = sub.add_parser("extract")
    ex.add_argument("--actor",     required=True)
    ex.add_argument("--id",        required=True)
    ex.add_argument("--games-dir", default=GAMES_DIR_DEFAULT)
    ex.add_argument("--bundled-dir", default=BUNDLED_DIR_DEFAULT)
    ex.add_argument("--user-dir",    default=USER_DIR_DEFAULT)

    ip = sub.add_parser("import_pgn")
    ip.add_argument("--pgn",    required=True)
    ip.add_argument("--player", required=True)
    ip.add_argument("--id",     required=True)
    ip.add_argument("--output", default=None)
    ip.add_argument("--bundled-dir", default=BUNDLED_DIR_DEFAULT)
    ip.add_argument("--user-dir",    default=USER_DIR_DEFAULT)

    args = p.parse_args()
    args.bundled_dir = os.path.expanduser(args.bundled_dir)
    args.user_dir    = os.path.expanduser(args.user_dir)
    if hasattr(args, "games_dir"):
        args.games_dir = os.path.expanduser(args.games_dir)
    if hasattr(args, "output") and args.output:
        args.output = os.path.expanduser(args.output)

    dispatch = {
        "list":       cmd_list,
        "show":       cmd_show,
        "extract":    cmd_extract,
        "import_pgn": cmd_import_pgn,
    }
    result = dispatch[args.command](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
