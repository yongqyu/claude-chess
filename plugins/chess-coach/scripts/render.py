#!/usr/bin/env python3
"""
render.py — ANSI terminal chess board renderer.

Usage:
  python3 render.py --state FILE [--clear]

With --clear: uses ANSI escape codes to overwrite the terminal from the top,
              creating a "fixed position" effect.
Without --clear: plain print (useful for piping or logging).

Layout:
  ♟  Chess Coach
  ┌─── 8×8 board ───┐
  │  Unicode pieces  │
  │  Last move: yellow highlight │
  └──────────────────┘
  Win-rate bar  [████░░░]  W 62% / B 38%
  Move history  1. e4 e5  2. Nf3 ...
  ──────────────────────────────────────
  [Coaching text for last move]
  ──────────────────────────────────────
  ⬜ White to move  │  Level: Intermediate  │  Mode: Play  │  Playing: White
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import board_from_state

import chess

# ---------------------------------------------------------------------------
# ANSI constants
# ---------------------------------------------------------------------------
RESET    = "\033[0m"
BOLD     = "\033[1m"
FG_BLACK = "\033[30m"
FG_WHITE = "\033[97m"
FG_GRAY  = "\033[90m"
FG_CYAN  = "\033[96m"
FG_YEL   = "\033[33m"
FG_GREEN = "\033[92m"
FG_RED   = "\033[91m"
FG_MAG   = "\033[95m"

BG_LIGHT  = "\033[48;2;240;217;181m"  # chess.com light tan
BG_DARK   = "\033[48;2;181;136;99m"   # chess.com dark brown
BG_HL_L   = "\033[48;2;205;210;106m"  # last-move highlight light
BG_HL_D   = "\033[48;2;170;162;58m"   # last-move highlight dark

CLEAR_AND_HOME = "\033[2J\033[H"

PIECE_UNICODE = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}


# ---------------------------------------------------------------------------
# Sub-renderers
# ---------------------------------------------------------------------------
def render_board(board: chess.Board, last_uci: str | None = None) -> str:
    """Return the 8×8 ANSI board as a multi-line string."""
    highlight: set[str] = set()
    if last_uci and len(last_uci) >= 4:
        highlight.add(last_uci[:2])
        highlight.add(last_uci[2:4])

    rows = [f"  ┌{'─' * 24}┐"]
    for rank in range(7, -1, -1):
        row = f"{BOLD}{FG_GRAY}{rank + 1}{RESET} │"
        for file in range(8):
            sq      = chess.square(file, rank)
            sq_name = chess.square_name(sq)
            light   = (rank + file) % 2 == 1
            in_hl   = sq_name in highlight

            if in_hl:
                bg = BG_HL_L if light else BG_HL_D
            else:
                bg = BG_LIGHT if light else BG_DARK

            piece = board.piece_at(sq)
            if piece:
                symbol = PIECE_UNICODE[piece.symbol()]
                fg     = FG_WHITE if piece.color == chess.WHITE else FG_BLACK
                row   += f"{bg}{fg}{BOLD} {symbol} {RESET}"
            else:
                row   += f"{bg}   {RESET}"
        row += f"{BOLD}{FG_GRAY}│{RESET}"
        rows.append(row)

    rows.append(f"  └{'─' * 24}┘")
    rows.append(f"    {'  '.join('abcdefgh')}")
    return "\n".join(rows)


def render_winbar(winrate_white: float, width: int = 28) -> str:
    """Return a text win-probability bar."""
    w_blocks = round(winrate_white * width)
    b_blocks = width - w_blocks
    bar = (
        f"{BOLD}{FG_WHITE}{'█' * w_blocks}{RESET}"
        f"{BOLD}{FG_GRAY}{'░' * b_blocks}{RESET}"
    )
    w_pct = int(winrate_white * 100)
    b_pct = 100 - w_pct
    return (
        f"  [{bar}]  "
        f"{BOLD}{FG_WHITE}W {w_pct}%{RESET}  /  "
        f"{BOLD}{FG_GRAY}B {b_pct}%{RESET}"
    )


def render_moves(moves_san: list[str], max_pairs: int = 8) -> str:
    """Return formatted move history (PGN-style pairs)."""
    if not moves_san:
        return f"  {FG_GRAY}(no moves yet){RESET}"

    pairs = []
    for i in range(0, len(moves_san), 2):
        n       = i // 2 + 1
        white_m = moves_san[i]
        black_m = moves_san[i + 1] if i + 1 < len(moves_san) else "..."
        pairs.append(
            f"{FG_GRAY}{n}.{RESET}{FG_WHITE}{white_m}{RESET} {FG_GRAY}{black_m}{RESET}"
        )

    shown = pairs[-max_pairs:]
    if len(pairs) > max_pairs:
        shown = [f"{FG_GRAY}...{RESET}"] + shown
    return "  " + "   ".join(shown)


def render_coaching(coaching: str) -> str:
    """Return coaching text lines with yellow color."""
    lines = coaching.strip().split("\n")
    return "\n".join(f"  {FG_YEL}{line}{RESET}" for line in lines)


def render_status(board: chess.Board, state: dict) -> str:
    """Return the bottom status bar."""
    turn     = "⬜ White to move" if board.turn == chess.WHITE else "⬛ Black to move"
    level    = state.get("level", "?").capitalize()
    mode     = state.get("mode",  "?").capitalize()
    color    = state.get("color", "?").capitalize()
    opening  = state.get("opening", "")
    check    = f"  {FG_RED}{BOLD}CHECK!{RESET}" if board.is_check() else ""
    opening_str = f"  {FG_GRAY}│  {opening}{RESET}" if opening else ""
    return (
        f"  {BOLD}{FG_CYAN}{turn}{RESET}{check}"
        f"  {FG_GRAY}│  Level: {level}  │  Mode: {mode}  │  Playing: {color}{RESET}"
        f"{opening_str}"
    )


# ---------------------------------------------------------------------------
# Full render
# ---------------------------------------------------------------------------
def full_render(state: dict, do_clear: bool) -> str:
    board      = board_from_state(state)
    moves_uci  = state.get("moves_uci", [])
    last_uci   = moves_uci[-1] if moves_uci else None
    records    = state.get("move_records", [])
    wr_white   = records[-1]["winrate_white"] if records else 0.5
    coaching   = records[-1].get("coaching") if records else None

    parts = []
    if do_clear:
        parts.append(CLEAR_AND_HOME)

    parts.append(f"\n  {BOLD}{FG_MAG}♟  Chess Coach{RESET}\n")
    parts.append(render_board(board, last_uci))
    parts.append("")
    parts.append(render_winbar(wr_white))
    parts.append("")
    parts.append(render_moves(state.get("moves_san", [])))

    if coaching:
        sep = f"  {FG_GRAY}{'─' * 52}{RESET}"
        parts.append(sep)
        parts.append(render_coaching(coaching))
        parts.append(sep)

    parts.append(render_status(board, state))
    parts.append("")

    if board.is_game_over():
        result = state.get("result", "?")
        parts.append(f"  {BOLD}{FG_GREEN}🏁 Game over  —  Result: {result}{RESET}\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="ANSI chess board renderer")
    p.add_argument("--state", default="~/.chess_coach/current_game.json")
    p.add_argument("--clear", action="store_true",
                   help="Clear the terminal before rendering (fixed-position effect)")
    args = p.parse_args()
    args.state = os.path.expanduser(args.state)

    with open(args.state) as f:
        state = json.load(f)

    output = full_render(state, args.clear)
    sys.stdout.write(output)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
