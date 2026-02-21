#!/usr/bin/env python3
"""
pgn_adapter.py — Convert PGN files to internal game record format.

Usage:
  python3 pgn_adapter.py --pgn FILE --player NAME --output DIR
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


def convert_game(game: chess.pgn.Game, player_name: str) -> dict | None:
    headers = game.headers
    white   = headers.get("White", "")
    black   = headers.get("Black", "")
    result  = headers.get("Result", "*")

    if player_name.lower() in white.lower():
        player_color = "white"
    elif player_name.lower() in black.lower():
        player_color = "black"
    else:
        return None

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
    p.add_argument("--pgn",    required=True)
    p.add_argument("--player", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    args.pgn    = os.path.expanduser(args.pgn)
    args.output = os.path.expanduser(args.output)
    os.makedirs(args.output, exist_ok=True)

    with open(args.pgn) as f:
        content = f.read()

    pgn_io        = io.StringIO(content)
    games_written = 0

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        record = convert_game(game, args.player)
        if record is None:
            continue
        ts     = datetime.now().strftime(f"%Y%m%d_%H%M%S_{games_written:04d}")
        out    = os.path.join(args.output, f"game_{ts}.json")
        with open(out, "w") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        games_written += 1

    print(json.dumps({"ok": True, "games_written": games_written,
                      "output_dir": args.output}, indent=2))


if __name__ == "__main__":
    main()
