#!/usr/bin/env python3
"""
engine.py — Chess game logic, move validation, AI, and state persistence.

Commands:
  new_game   --state FILE [--color white|black] [--level auto|beginner|intermediate|advanced] [--mode play|coach]
  move       --state FILE --move <san_or_uci>
  ai_move    --state FILE [--persona ID] [--bundled-persona-dir DIR]
  legal      --state FILE
  status     --state FILE

All output: JSON to stdout.
State is persisted to the given FILE after every command.
"""

import argparse
import json
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from common import (
    evaluate, score_to_winrate, get_best_move,
    board_from_state, detect_opening,
)

import chess

# ---------------------------------------------------------------------------
# Difficulty settings
# ---------------------------------------------------------------------------
DEPTH_MAP    = {"beginner": 1, "intermediate": 2, "advanced": 3}
BLUNDER_MAP  = {"beginner": 0.25, "intermediate": 0.0, "advanced": 0.0}

BUNDLED_PERSONA_DIR_DEFAULT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "personas")
)


def load_persona_for_engine(persona_id: str, bundled_dir: str) -> dict | None:
    """Load persona from user dir then bundled dir. Returns None if not found."""
    user_dir = os.path.expanduser("~/.chess_coach/personas")
    for directory in [user_dir, bundled_dir]:
        path = os.path.join(directory, f"{persona_id}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                import sys
                print(f"Warning: could not load persona from {path}: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Move parsing
# ---------------------------------------------------------------------------
def parse_move(user_input: str, board: chess.Board) -> tuple[chess.Move | None, str | None]:
    """
    Accept SAN, UCI, or natural-language aliases.
    Returns (move, None) on success, (None, error_message) on failure.
    """
    s = user_input.strip()

    # Try UCI
    try:
        m = chess.Move.from_uci(s.lower().replace(" ", ""))
        if m in board.legal_moves:
            return m, None
    except Exception:
        pass

    # Try SAN
    try:
        m = board.parse_san(s)
        if m in board.legal_moves:
            return m, None
    except Exception:
        pass

    # Natural language aliases
    nl_map = {
        "castle kingside":  "O-O",
        "short castle":     "O-O",
        "kingside castle":  "O-O",
        "castle queenside": "O-O-O",
        "long castle":      "O-O-O",
        "queenside castle": "O-O-O",
    }
    for phrase, san in nl_map.items():
        if phrase in s.lower():
            try:
                m = board.parse_san(san)
                return m, None
            except Exception:
                pass

    # Suggest similar legal moves
    examples = [board.san(m) for m in list(board.legal_moves)[:6]]
    return None, f"Cannot parse '{s}'. Legal examples: {', '.join(examples)}"


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------
def load_state(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_state(state: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def make_move_record(
    move: chess.Move,
    san: str,
    player: str,
    actor: str,
    score_before: int,
    score_after: int,
) -> dict:
    """Build a move record dict for storage in state['move_records']."""
    return {
        "move_san":        san,
        "move_uci":        move.uci(),
        "player":          player,  # "white" or "black"
        "actor":           actor,   # "human" or "ai"
        "score_before_cp": score_before,
        "score_after_cp":  score_after,
        "winrate_white":   score_to_winrate(score_after, chess.WHITE),
        "coaching":        None,    # filled later by coach.py
    }


def check_game_over(board: chess.Board, state: dict) -> None:
    """Update state['result'] if the game is over."""
    if board.is_game_over():
        outcome = board.outcome()
        if outcome:
            if outcome.winner == chess.WHITE:
                state["result"] = "1-0"
            elif outcome.winner == chess.BLACK:
                state["result"] = "0-1"
            else:
                state["result"] = "1/2-1/2"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_new_game(args) -> dict:
    board      = chess.Board()
    score      = evaluate(board)
    human_name = args.player or "human"
    players    = {
        args.color:                                        human_name,
        "black" if args.color == "white" else "white":    "ai",
    }
    state = {
        "color":        args.color,
        "player_name":  human_name,
        "players":      players,   # {"white": name_or_"ai", "black": name_or_"ai"}
        "level":        args.level,
        "mode":         args.mode,
        "moves_uci":    [],
        "moves_san":    [],
        "move_records": [],
        "move_count":   0,
        "result":       None,
        "opening":      None,
    }
    save_state(state, args.state)
    return {
        "ok":             True,
        "fen":            board.fen(),
        "score_cp":       score,
        "winrate_white":  score_to_winrate(score, chess.WHITE),
        "state_file":     args.state,
        "players":        players,
    }


def cmd_move(args) -> dict:
    state = load_state(args.state)
    board = board_from_state(state)

    score_before = evaluate(board)
    turn_before  = board.turn
    player       = "white" if turn_before == chess.WHITE else "black"
    actor        = state.get("players", {}).get(player, "human")

    move, err = parse_move(args.move, board)
    if err:
        return {"ok": False, "error": err}

    san = board.san(move)
    board.push(move)
    score_after = evaluate(board)

    record = make_move_record(move, san, player, actor, score_before, score_after)
    state["moves_uci"].append(move.uci())
    state["moves_san"].append(san)
    state["move_records"].append(record)
    state["move_count"] += 1

    # Update opening detection
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
    }


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

    persona_id = getattr(args, "persona", None)
    if persona_id:
        bundled_dir = getattr(args, "bundled_persona_dir",
                              BUNDLED_PERSONA_DIR_DEFAULT)
        persona = load_persona_for_engine(persona_id, bundled_dir)

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
        move = opening_move
    else:
        move, _ = get_best_move(board, depth, blunder_pc, aggression)
        if not move:
            return {"ok": False, "error": "No legal moves available."}

    san = board.san(move)
    board.push(move)
    score_after = evaluate(board)

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
        "persona_used":  persona.get("id") if persona else None,
    }


def cmd_status(args) -> dict:
    state = load_state(args.state)
    board = board_from_state(state)
    score = evaluate(board)
    return {
        "ok":            True,
        "fen":           board.fen(),
        "turn":          "white" if board.turn == chess.WHITE else "black",
        "score_cp":      score,
        "winrate_white": score_to_winrate(score, chess.WHITE),
        "moves_san":     state["moves_san"],
        "move_count":    state["move_count"],
        "is_game_over":  board.is_game_over(),
        "is_check":      board.is_check(),
        "result":        state.get("result"),
        "level":         state.get("level"),
        "mode":          state.get("mode"),
        "color":         state.get("color"),
        "opening":       state.get("opening"),
    }


def cmd_legal(args) -> dict:
    state = load_state(args.state)
    board = board_from_state(state)
    return {
        "ok": True,
        "legal_moves": [
            {"uci": m.uci(), "san": board.san(m)}
            for m in board.legal_moves
        ],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Chess engine CLI")
    sub = p.add_subparsers(dest="command")

    # new_game
    ng = sub.add_parser("new_game")
    ng.add_argument("--color",  default="white",
                    choices=["white", "black"])
    ng.add_argument("--level",  default="auto",
                    choices=["auto", "beginner", "intermediate", "advanced"])
    ng.add_argument("--mode",   default="play",
                    choices=["play", "coach"])
    ng.add_argument("--player", default="human",
                    help="Human player's nickname (stored in game record)")
    ng.add_argument("--state",  default="~/.chess_coach/current_game.json")

    # move
    mv = sub.add_parser("move")
    mv.add_argument("--move",  required=True)
    mv.add_argument("--state", default="~/.chess_coach/current_game.json")

    # ai_move
    ai = sub.add_parser("ai_move")
    ai.add_argument("--state", default="~/.chess_coach/current_game.json")
    ai.add_argument("--persona",             default=None,
                    help="Persona ID to use for AI move")
    ai.add_argument("--bundled-persona-dir", default=BUNDLED_PERSONA_DIR_DEFAULT,
                    help="Path to bundled personas directory")

    # status
    st = sub.add_parser("status")
    st.add_argument("--state", default="~/.chess_coach/current_game.json")

    # legal
    lg = sub.add_parser("legal")
    lg.add_argument("--state", default="~/.chess_coach/current_game.json")

    args = p.parse_args()
    if not args.command:
        p.print_help()
        sys.exit(1)
    # Expand ~ in state path
    args.state = os.path.expanduser(args.state)

    dispatch = {
        "new_game": cmd_new_game,
        "move":     cmd_move,
        "ai_move":  cmd_ai_move,
        "status":   cmd_status,
        "legal":    cmd_legal,
    }
    result = dispatch[args.command](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
