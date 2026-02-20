#!/usr/bin/env python3
"""
review.py — Generate a Markdown game review from a saved state file.

Usage:
  python3 review.py --state FILE [--output FILE]

Output sections:
  1. Game Summary  (result, players, level, ELO estimate, date)
  2. Full PGN
  3. Win-Probability Chart  (ASCII text graph)
  4. Move-by-Move Analysis  (table with quality, eval, coaching)
  5. Key Mistakes & Blunders  (detailed breakdown)
  6. ELO Estimate & Methodology

Default output: ~/.chess_coach/reviews/<timestamp>.md
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from common import classify_move, estimate_elo, board_from_state

import chess
import chess.pgn


# ---------------------------------------------------------------------------
# PGN builder
# ---------------------------------------------------------------------------
def build_pgn(state: dict) -> str:
    game = chess.pgn.Game()
    game.headers["Event"]  = "Chess Coach Session"
    game.headers["Date"]   = datetime.now().strftime("%Y.%m.%d")
    user_color = state.get("color", "white")
    level      = state.get("level", "?")
    game.headers["White"]  = "User"          if user_color == "white" else f"AI ({level})"
    game.headers["Black"]  = f"AI ({level})" if user_color == "white" else "User"
    game.headers["Result"] = state.get("result") or "*"

    node = game
    for uci in state.get("moves_uci", []):
        node = node.add_variation(chess.Move.from_uci(uci))
    return str(game)


# ---------------------------------------------------------------------------
# ASCII win-probability chart
# ---------------------------------------------------------------------------
def build_winrate_chart(records: list[dict], width: int = 50) -> str:
    if not records:
        return "(no data)"

    winrates = [r["winrate_white"] for r in records]
    n        = len(winrates)
    height   = 12

    grid = [[" "] * width for _ in range(height)]

    for i, wr in enumerate(winrates):
        x = int(i / max(n - 1, 1) * (width - 1))
        y = int((1 - wr) * (height - 1))
        y = max(0, min(height - 1, y))
        grid[y][x] = "●"

    # 50% midline
    mid = height // 2
    for x in range(width):
        if grid[mid][x] == " ":
            grid[mid][x] = "·"

    lines = ["```"]
    lines.append("  Win probability — White  (100% top / 50% middle / 0% bottom)")
    lines.append(f"  {'─' * width}")

    for row_idx, row in enumerate(grid):
        pct   = int((1 - row_idx / (height - 1)) * 100)
        label = f"{pct:3d}% │" if pct in [100, 75, 50, 25, 0] else "     │"
        lines.append(label + "".join(row) + "│")

    lines.append(f"     └{'─' * width}┘")

    # X-axis move numbers
    step     = max(1, n // 10)
    x_labels = "      "
    for i in range(0, n, step):
        x     = int(i / max(n - 1, 1) * (width - 1))
        label = str(i + 1)
        pad   = x - len(x_labels) + 6
        if pad >= 0:
            x_labels += " " * pad + label
    lines.append(x_labels[:width + 7])
    lines.append(f"      {'Move number':^{width}}")
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Move analysis table
# ---------------------------------------------------------------------------
def build_move_table(records: list[dict]) -> str:
    if not records:
        return "(no moves)"

    rows = ["| # | Player | Move | Quality | W Win% | Coaching |",
            "|---|--------|------|---------|--------|---------|"]

    for i, r in enumerate(records):
        player   = "White ⬜" if r["player"] == "white" else "Black ⬛"
        move     = r["move_san"]
        before   = r["score_before_cp"]
        after    = r["score_after_cp"]
        delta    = (after - before) if r["player"] == "white" else -(after - before)
        quality, icon = classify_move(delta)
        wr_pct   = f"{int(r['winrate_white'] * 100)}%"
        coaching = r.get("coaching") or ""
        # First line only, truncated, pipe-escaped
        note     = coaching.split("\n")[0][:55].replace("|", "ǀ") if coaching else "—"
        rows.append(f"| {i+1} | {player} | **{move}** | {icon} {quality} | {wr_pct} | {note} |")

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Blunders & mistakes
# ---------------------------------------------------------------------------
def build_blunders(records: list[dict]) -> str:
    bad = []
    for i, r in enumerate(records):
        before = r["score_before_cp"]
        after  = r["score_after_cp"]
        delta  = (after - before) if r["player"] == "white" else -(after - before)
        if delta <= -50:
            quality, icon = classify_move(delta)
            bad.append((i + 1, r["player"], r["move_san"], quality, icon, delta,
                        r.get("coaching") or ""))

    if not bad:
        return "No significant mistakes or blunders detected. Well played! 🎉"

    lines = []
    for (num, player, move_san, quality, icon, delta, coaching) in bad:
        side = "White" if player == "white" else "Black"
        lines.append(f"### Move {num} — {side}: **{move_san}**  {icon} {quality.upper()}")
        lines.append(f"Eval change: {delta / 100:+.2f} pawns\n")
        if coaching:
            for line in coaching.split("\n"):
                lines.append(f"> {line}")
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ELO section
# ---------------------------------------------------------------------------
def build_elo_section(state: dict) -> str:
    records    = state.get("move_records", [])
    user_color = state.get("color", "white")

    elo_data = estimate_elo(records, player=user_color)

    lines = []
    if elo_data["elo"] is None:
        lines.append("Not enough moves to estimate ELO.")
        return "\n".join(lines)

    elo        = elo_data["elo"]
    acpl       = elo_data["acpl"]
    blunders   = elo_data["blunder_count"]
    b_rate     = round(elo_data["blunder_rate"] * 100, 1)
    move_count = elo_data["move_count"]

    # Rough skill band label
    if elo >= 1800:  band = "Advanced / Club player"
    elif elo >= 1400: band = "Intermediate"
    elif elo >= 1000: band = "Beginner / Casual"
    else:             band = "Novice"

    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| **Estimated ELO** | **{elo}** |")
    lines.append(f"| Skill band | {band} |")
    lines.append(f"| Moves analyzed | {move_count} |")
    lines.append(f"| Average centipawn loss (ACPL) | {acpl} cp |")
    lines.append(f"| Blunders (≥150 cp loss) | {blunders} ({b_rate}%) |")
    lines.append("")
    lines.append("**Methodology:**  ")
    lines.append("ELO is estimated using the formula:  ")
    lines.append("`ELO ≈ 1800 − (ACPL × 6) − (blunder_rate% × 40)`  ")
    lines.append("Based on Guid & Bratko (2006) and Lichess ACPL studies.  ")
    lines.append("Clamped to the range [400, 2200]. Accuracy improves with more games.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def generate_review(state: dict, output_path: str) -> dict:
    records    = state.get("move_records", [])
    result     = state.get("result") or "*"
    level      = state.get("level",  "?")
    mode       = state.get("mode",   "?")
    user_color = state.get("color",  "?")
    opening    = state.get("opening") or "Unknown / Custom"
    move_count = state.get("move_count", 0)
    date_str   = datetime.now().strftime("%Y-%m-%d %H:%M")

    result_desc = {
        "1-0":     "White wins",
        "0-1":     "Black wins",
        "1/2-1/2": "Draw",
        "*":       "Incomplete",
    }.get(result, result)

    final_wr = records[-1]["winrate_white"] if records else 0.5
    elo_data = estimate_elo(records, player=user_color)
    elo_str  = str(elo_data["elo"]) if elo_data["elo"] else "N/A"

    md = []
    md.append("# ♟ Chess Coach — Game Review")
    md.append("")
    md.append(f"| Field | Value |")
    md.append(f"|-------|-------|")
    md.append(f"| Date | {date_str} |")
    md.append(f"| Result | {result} ({result_desc}) |")
    md.append(f"| Your color | {user_color.capitalize()} |")
    md.append(f"| AI level | {level.capitalize()} |")
    md.append(f"| Mode | {mode.capitalize()} |")
    md.append(f"| Opening | {opening} |")
    md.append(f"| Total moves | {move_count} |")
    md.append(f"| Final win rate (White) | {int(final_wr * 100)}% |")
    md.append(f"| **Estimated ELO** | **{elo_str}** |")

    md.append("\n---\n")
    md.append("## 📜 PGN\n")
    md.append("```")
    md.append(build_pgn(state))
    md.append("```")

    md.append("\n---\n")
    md.append("## 📊 Win Probability Chart\n")
    md.append(build_winrate_chart(records))

    md.append("\n---\n")
    md.append("## 🔍 Move-by-Move Analysis\n")
    md.append(build_move_table(records))

    md.append("\n---\n")
    md.append("## ⚠️ Mistakes & Blunders\n")
    md.append(build_blunders(records))

    md.append("\n---\n")
    md.append("## 🎯 ELO Estimate\n")
    md.append(build_elo_section(state))

    md.append("\n---\n")
    md.append("*Generated by Chess Coach skill.*")

    content = "\n".join(md)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "ok":          True,
        "output_path": output_path,
        "move_count":  move_count,
        "elo_estimate": elo_data["elo"],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Generate a Markdown game review")
    p.add_argument("--state",  default="~/.chess_coach/current_game.json")
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_out = os.path.expanduser(f"~/.chess_coach/reviews/review_{ts}.md")
    p.add_argument("--output", default=default_out)

    args = p.parse_args()
    args.state  = os.path.expanduser(args.state)
    args.output = os.path.expanduser(args.output)

    with open(args.state) as f:
        state = json.load(f)

    result = generate_review(state, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
