#!/usr/bin/env python3
"""
coach.py — Move evaluation and coaching annotation.

Commands:
  evaluate_user  --state FILE --move <uci>   Evaluate a user move before committing
  explain_ai     --state FILE                Explain the last AI move
  annotate       --state FILE --move_idx N --text "..."  Save coaching text to a record

All output: JSON to stdout.
Coaching text is stored back into state['move_records'][n]['coaching'].
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import (
    evaluate, score_to_winrate, get_best_move, minimax,
    classify_move, board_from_state, detect_opening,
    PIECE_VALUES,
)

import chess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_state(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_state(state: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def cp_fmt(score: int, turn: chess.Color) -> str:
    """Format score as +X.XX / -X.XX from the moving side's perspective."""
    adj = score if turn == chess.WHITE else -score
    return f"{adj / 100:+.2f}"


def hanging_pieces(board: chess.Board, our_color: chess.Color) -> list[str]:
    """Return names of our pieces that are attacked and undefended."""
    opp = not our_color
    result = []
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == our_color:
            if board.is_attacked_by(opp, sq) and not board.is_attacked_by(our_color, sq):
                result.append(f"{chess.piece_name(piece.piece_type)} on {chess.square_name(sq)}")
    return result


def opening_hint(moves_san: list[str], move_san: str, board_before: chess.Board, move: chess.Move) -> list[str]:
    """Generate opening-principle coaching hints for early game moves."""
    hints = []
    move_num = len(moves_san)  # 0-indexed before this move

    # Detect named opening
    tentative = moves_san + [move_san]
    opening = detect_opening(tentative)
    if opening:
        hints.append(f"Opening: {opening}")
        return hints  # opening name is sufficient context

    # Generic principles for first 10 half-moves
    if move_num >= 10:
        return hints

    piece = board_before.piece_at(move.from_square)
    if not piece:
        return hints

    file_to = chess.square_file(move.to_square)

    if piece.piece_type == chess.PAWN and file_to in [3, 4]:
        hints.append("Center pawn advance — strong opening principle.")
    elif piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
        hints.append("Piece development — good progress toward castling.")
    elif move_san in ["O-O", "O-O-O"]:
        hints.append("Castling secures king safety.")
    elif piece.piece_type == chess.QUEEN and move_num < 6:
        hints.append("Tip: early queen development can be risky — it may be harassed by opponent pieces.")

    return hints


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_evaluate_user(args) -> dict:
    """
    Evaluate a user move before it is committed to state.
    Provides: quality label, win-rate change, best alternative.
    """
    state      = load_state(args.state)
    board_pre  = board_from_state(state)
    turn_before = board_pre.turn

    move = chess.Move.from_uci(args.move)
    if move not in board_pre.legal_moves:
        return {"ok": False, "error": f"Illegal move: {args.move}"}

    move_san      = board_pre.san(move)
    score_before  = evaluate(board_pre)
    wr_before     = score_to_winrate(score_before, chess.WHITE)

    # Best move from this position
    best_move, _ = get_best_move(board_pre, depth=2)
    best_san      = board_pre.san(best_move) if best_move else None

    # Score after best move
    board_pre.push(best_move)
    best_score_after = evaluate(board_pre)
    board_pre.pop()

    # Score after user move
    board_after = board_from_state(state)
    board_after.push(move)
    score_after  = evaluate(board_after)
    wr_after     = score_to_winrate(score_after, chess.WHITE)

    # CP delta from the moving side's perspective
    if turn_before == chess.WHITE:
        delta_user = score_after - score_before
        delta_best = best_score_after - score_before
    else:
        delta_user = -(score_after - score_before)
        delta_best = -(best_score_after - score_before)

    quality, icon = classify_move(delta_user)
    missed_cp     = delta_best - delta_user   # how much better the best move was

    # ── Build coaching lines ──────────────────────────────────────────────
    lines = []
    wr_pct      = int(wr_after * 100)
    wr_prev_pct = int(wr_before * 100)
    trend       = "▲" if wr_after > wr_before else ("▼" if wr_after < wr_before else "—")

    lines.append(f"{icon} [{quality.upper()}]  {move_san}")
    lines.append(
        f"Win rate (White):  {wr_prev_pct}% → {wr_pct}% {trend}   "
        f"Eval: {cp_fmt(score_after, turn_before)}"
    )

    if best_move and best_move.uci() == args.move:
        lines.append("⭐ Best move — engine's top choice!")
    elif missed_cp > 20:
        lines.append(f"💡 Better: {best_san}  (gains ~{missed_cp / 100:.1f} more pawns)")

    # Opening hints
    board_hint = board_from_state(state)
    o_hints = opening_hint(state.get("moves_san", []), move_san, board_hint, move)
    lines.extend(o_hints)

    # Hanging piece warnings after user move
    hangers = hanging_pieces(board_after, turn_before)
    for h in hangers[:2]:
        lines.append(f"⚠️  Your {h} is undefended!")

    coaching_text = "\n".join(lines)

    return {
        "ok":              True,
        "move_san":        move_san,
        "quality":         quality,
        "quality_icon":    icon,
        "score_before_cp": score_before,
        "score_after_cp":  score_after,
        "winrate_before":  wr_before,
        "winrate_after":   wr_after,
        "best_move_san":   best_san,
        "missed_cp":       missed_cp,
        "coaching_text":   coaching_text,
        "coaching_lines":  lines,
    }


def cmd_explain_ai(args) -> dict:
    """
    Explain the last move in state (which was the AI's move).
    Saves coaching text back to the record.
    """
    state   = load_state(args.state)
    records = state.get("move_records", [])
    if not records:
        return {"ok": False, "error": "No moves recorded yet."}

    last    = records[-1]
    move_san   = last["move_san"]
    score_before = last["score_before_cp"]
    score_after  = last["score_after_cp"]
    player  = last["player"]

    delta = (score_after - score_before) if player == "white" else -(score_after - score_before)

    # Reconstruct board before the last move
    board_pre = chess.Board()
    for uci in state["moves_uci"][:-1]:
        board_pre.push(chess.Move.from_uci(uci))

    move  = chess.Move.from_uci(last["move_uci"])
    piece = board_pre.piece_at(move.from_square)

    # Check for capture
    captured = board_pre.piece_at(move.to_square)

    board_pre.push(move)
    gives_check = board_pre.is_check()

    lines = [f"AI played {move_san}."]

    if piece:
        pname  = chess.piece_name(piece.piece_type)
        fr, to = chess.square_name(move.from_square), chess.square_name(move.to_square)
        lines.append(f"  {pname.capitalize()} {fr} → {to}.")

    if gives_check:
        lines.append("  Delivers check — forces a defensive response.")
    if move.promotion:
        lines.append("  Pawn promotion to queen — decisive material gain.")
    if captured:
        cname = chess.piece_name(captured.piece_type)
        lines.append(f"  Captures the {cname} — material gain.")

    if delta > 50:
        lines.append(f"  Improves the position by ~{delta / 100:.1f} pawns.")
    elif delta > 10:
        lines.append("  Slightly improves the position.")
    elif delta < -10:
        lines.append("  Maintains balance while staying active.")
    else:
        lines.append("  Positional move — consolidating the position.")

    wr_pct = int(last["winrate_white"] * 100)
    lines.append(f"Win rate (White): {wr_pct}%")

    coaching_text = "\n".join(lines)

    # Persist coaching
    state["move_records"][-1]["coaching"] = coaching_text
    save_state(state, args.state)

    return {
        "ok":            True,
        "coaching_text": coaching_text,
        "coaching_lines": lines,
    }


def cmd_annotate(args) -> dict:
    """Attach arbitrary coaching text to a specific move record by index."""
    state   = load_state(args.state)
    records = state.get("move_records", [])
    idx     = args.move_idx

    if idx < 0 or idx >= len(records):
        return {"ok": False, "error": f"Invalid move_idx {idx} (have {len(records)} records)"}

    records[idx]["coaching"] = args.text
    save_state(state, args.state)

    return {"ok": True, "annotated_move": records[idx]["move_san"], "move_idx": idx}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    p   = argparse.ArgumentParser(description="Chess coaching CLI")
    sub = p.add_subparsers(dest="command")

    eu = sub.add_parser("evaluate_user")
    eu.add_argument("--state", default="~/.chess_coach/current_game.json")
    eu.add_argument("--move",  required=True, help="UCI move string, e.g. e2e4")

    ea = sub.add_parser("explain_ai")
    ea.add_argument("--state", default="~/.chess_coach/current_game.json")

    an = sub.add_parser("annotate")
    an.add_argument("--state",     default="~/.chess_coach/current_game.json")
    an.add_argument("--move_idx",  type=int, required=True)
    an.add_argument("--text",      required=True)

    args = p.parse_args()
    args.state = os.path.expanduser(args.state)

    dispatch = {
        "evaluate_user": cmd_evaluate_user,
        "explain_ai":    cmd_explain_ai,
        "annotate":      cmd_annotate,
    }
    result = dispatch[args.command](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
