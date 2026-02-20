#!/usr/bin/env python3
"""
profile.py — Player profile management.

Commands:
  load       [--profile FILE]            Print current profile as JSON
  update     --state FILE [--profile FILE]   Compute ELO from finished game, update profile
  recommend  [--profile FILE]            Print recommended difficulty level

Profile file: ~/.chess_coach/profile.json
Games index:  ~/.chess_coach/games/  (saved state files)

Profile schema:
  {
    "games_played": int,
    "elo_history":  [int, ...],       # one entry per completed game
    "elo_current":  int | null,
    "level":        "beginner" | "intermediate" | "advanced",
    "last_updated": "ISO datetime"
  }
"""

import argparse
import json
import os
import sys
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from common import estimate_elo, elo_to_level

DEFAULT_PROFILE = os.path.expanduser("~/.chess_coach/profile.json")
GAMES_DIR       = os.path.expanduser("~/.chess_coach/games/")

# ELO smoothing: weighted average of last N games
ELO_WINDOW = 5


# ---------------------------------------------------------------------------
# Profile I/O
# ---------------------------------------------------------------------------
def load_profile(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {
        "games_played": 0,
        "elo_history":  [],
        "elo_current":  None,
        "level":        "intermediate",   # default until enough data
        "last_updated": None,
    }


def save_profile(profile: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    profile["last_updated"] = datetime.now().isoformat()
    with open(path, "w") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# ELO smoothing
# ---------------------------------------------------------------------------
def smoothed_elo(history: list[int], window: int = ELO_WINDOW) -> int | None:
    if not history:
        return None
    recent = history[-window:]
    # Linear weighting: more recent games count more
    weights = list(range(1, len(recent) + 1))
    weighted = sum(e * w for e, w in zip(recent, weights))
    return int(weighted / sum(weights))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_load(args) -> dict:
    profile = load_profile(args.profile)
    return {"ok": True, "profile": profile}


def cmd_update(args) -> dict:
    """
    Read the completed game state, compute ELO, update profile.
    Also archives the game file to ~/.chess_coach/games/.
    """
    if not os.path.exists(args.state):
        return {"ok": False, "error": f"State file not found: {args.state}"}

    with open(args.state) as f:
        state = json.load(f)

    records   = state.get("move_records", [])
    user_color = state.get("color", "white")

    elo_result = estimate_elo(records, player=user_color)
    if elo_result["elo"] is None:
        return {"ok": False, "error": "Not enough moves to estimate ELO.", "details": elo_result}

    profile = load_profile(args.profile)
    profile["games_played"] += 1
    profile["elo_history"].append(elo_result["elo"])

    smoothed = smoothed_elo(profile["elo_history"])
    profile["elo_current"] = smoothed
    profile["level"] = elo_to_level(smoothed)

    save_profile(profile, args.profile)

    # Archive the game
    os.makedirs(GAMES_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(GAMES_DIR, f"game_{ts}.json")
    with open(archive_path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    return {
        "ok":              True,
        "elo_this_game":   elo_result["elo"],
        "elo_smoothed":    smoothed,
        "acpl":            elo_result["acpl"],
        "blunder_count":   elo_result["blunder_count"],
        "blunder_rate":    elo_result["blunder_rate"],
        "games_played":    profile["games_played"],
        "recommended_level": profile["level"],
        "archived_to":     archive_path,
    }


def cmd_recommend(args) -> dict:
    """Return the recommended difficulty level based on profile history."""
    profile = load_profile(args.profile)
    elo     = profile.get("elo_current")
    level   = profile.get("level", "intermediate")
    games   = profile.get("games_played", 0)

    note = ""
    if games == 0:
        note = "No game history found. Starting at intermediate difficulty."
    elif games < 3:
        note = f"Only {games} game(s) recorded. ELO estimate may not be accurate yet."
    else:
        note = f"Based on {games} games. Smoothed ELO: {elo}."

    return {
        "ok":            True,
        "recommended_level": level,
        "elo_current":   elo,
        "games_played":  games,
        "note":          note,
    }


def cmd_history(args) -> dict:
    """List all archived game files with basic metadata."""
    if not os.path.exists(GAMES_DIR):
        return {"ok": True, "games": [], "note": "No games archived yet."}

    files = sorted(glob.glob(os.path.join(GAMES_DIR, "game_*.json")))
    games = []
    for path in files[-20:]:   # show last 20
        try:
            with open(path) as f:
                s = json.load(f)
            records    = s.get("move_records", [])
            user_color = s.get("color", "white")
            elo_data   = estimate_elo(records, player=user_color)
            games.append({
                "file":       os.path.basename(path),
                "result":     s.get("result", "*"),
                "color":      user_color,
                "level":      s.get("level"),
                "move_count": s.get("move_count", 0),
                "elo_estimate": elo_data.get("elo"),
                "acpl":         elo_data.get("acpl"),
            })
        except Exception as e:
            games.append({"file": os.path.basename(path), "error": str(e)})

    return {"ok": True, "games": games}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Player profile manager")
    p.add_argument("--profile", default=DEFAULT_PROFILE,
                   help="Path to profile JSON file")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("load")
    sub.add_parser("recommend")
    sub.add_parser("history")

    upd = sub.add_parser("update")
    upd.add_argument("--state", required=True,
                     help="Path to completed game state JSON")

    args = p.parse_args()
    args.profile = os.path.expanduser(args.profile)

    dispatch = {
        "load":      cmd_load,
        "update":    cmd_update,
        "recommend": cmd_recommend,
        "history":   cmd_history,
    }
    result = dispatch[args.command](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
