"""
common.py — Shared chess evaluation utilities.

Imported by engine.py, coach.py, and review.py.
Do not run directly.
"""

import math
import chess

# ---------------------------------------------------------------------------
# Piece-square tables (White's perspective; use chess.square_mirror for Black)
# ---------------------------------------------------------------------------
PST: dict[int, list[int]] = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    chess.ROOK: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    chess.KING: [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ],
}

PIECE_VALUES: dict[int, int] = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}


def evaluate(board: chess.Board) -> int:
    """
    Static evaluation in centipawns.
    Positive = White advantage, negative = Black advantage.
    """
    if board.is_checkmate():
        return -99999 if board.turn == chess.WHITE else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece:
            idx = sq if piece.color == chess.WHITE else chess.square_mirror(sq)
            val = PIECE_VALUES[piece.piece_type] + PST[piece.piece_type][idx]
            score += val if piece.color == chess.WHITE else -val
    return score


def score_to_winrate(score: int, turn: chess.Color) -> float:
    """
    Convert centipawn score to win probability (0–1) for White.
    Uses a logistic sigmoid; matches Lichess/Stockfish approximation.
    """
    adjusted = score if turn == chess.WHITE else -score
    return round(1 / (1 + math.exp(-adjusted / 400)), 3)


def minimax(board: chess.Board, depth: int, alpha: int, beta: int, maximizing: bool) -> int:
    """Alpha-beta pruning minimax search."""
    if depth == 0 or board.is_game_over():
        return evaluate(board)
    if maximizing:
        best = -999999
        for move in board.legal_moves:
            board.push(move)
            best = max(best, minimax(board, depth - 1, alpha, beta, False))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 999999
        for move in board.legal_moves:
            board.push(move)
            best = min(best, minimax(board, depth - 1, alpha, beta, True))
            board.pop()
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


def get_best_move(
    board: chess.Board,
    depth: int,
    blunder_pct: float = 0.0,
    aggression: float = 0.0,
) -> tuple[chess.Move | None, int]:
    """
    Return (best_move, score_after_best_move).
    blunder_pct: probability of playing a random move (beginner simulation).
    aggression: 0.0–1.0; adds a bonus (up to 50 cp) for captures and checks.
    """
    import random
    moves = list(board.legal_moves)
    if not moves:
        return None, 0

    random.shuffle(moves)

    if blunder_pct > 0 and random.random() < blunder_pct:
        return random.choice(moves), 0

    is_white = board.turn == chess.WHITE
    best_move = moves[0]
    best_val = -999999 if is_white else 999999

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


def classify_move(delta_cp: int) -> tuple[str, str]:
    """
    Classify move quality based on centipawn loss from the moving side's perspective.
    Returns (quality_label, emoji).
    """
    if delta_cp >= 50:    return "brilliant",  "✨"
    if delta_cp >= 0:     return "good",        "✅"
    if delta_cp >= -50:   return "inaccuracy",  "⚠️ "
    if delta_cp >= -150:  return "mistake",     "❌"
    return "blunder", "💀"


def board_from_state(state: dict) -> chess.Board:
    """Reconstruct a Board from a saved state dict."""
    board = chess.Board()
    for uci in state.get("moves_uci", []):
        board.push(chess.Move.from_uci(uci))
    return board


# ---------------------------------------------------------------------------
# Opening name database (ECO-inspired, covering the most common lines)
# ---------------------------------------------------------------------------
OPENINGS: list[tuple[str, str]] = [
    # (move prefix in SAN space-separated, opening name)
    ("e4 e5 Nf3 Nc6 Bb5",        "Ruy López (Spanish Opening)"),
    ("e4 e5 Nf3 Nc6 Bc4",        "Italian Game"),
    ("e4 e5 Nf3 Nc6 d4",         "Scotch Game"),
    ("e4 e5 Nf3 f5",             "Latvian Gambit"),
    ("e4 e5 f4",                 "King's Gambit"),
    ("e4 c5",                    "Sicilian Defense"),
    ("e4 e6",                    "French Defense"),
    ("e4 c6",                    "Caro-Kann Defense"),
    ("e4 d5",                    "Scandinavian Defense"),
    ("e4 Nf6",                   "Alekhine's Defense"),
    ("d4 d5 c4",                 "Queen's Gambit"),
    ("d4 d5 c4 e6 Nc3 Nf6 Bg5", "Queen's Gambit Declined"),
    ("d4 d5 c4 c6",              "Slav Defense"),
    ("d4 Nf6 c4 g6",             "King's Indian Defense"),
    ("d4 Nf6 c4 e6 g3",         "Catalan Opening"),
    ("d4 Nf6 c4 c5",             "Benoni Defense"),
    ("d4 f5",                    "Dutch Defense"),
    ("c4",                       "English Opening"),
    ("Nf3 d5 c4",                "Réti Opening"),
    ("e4 e5",                    "Open Game (King's Pawn)"),
    ("d4 d5",                    "Closed Game (Queen's Pawn)"),
]


def detect_opening(moves_san: list[str]) -> str | None:
    """
    Match the current move list against known opening patterns.
    Returns the opening name or None if not recognized.
    Tries longest match first.
    """
    move_str = " ".join(moves_san)
    # Sort by length descending to find the most specific match
    for prefix, name in sorted(OPENINGS, key=lambda x: -len(x[0])):
        if move_str.startswith(prefix):
            return name
    return None


# ---------------------------------------------------------------------------
# ELO estimation
# ---------------------------------------------------------------------------
# Based on the correlation between average centipawn loss (ACPL) and ELO
# established in academic work (e.g., Guid & Bratko 2006, Lichess ACPL studies).
# Formula: ELO ≈ 1800 - (ACPL * 6) with blunder-rate penalty.
# Clamped to [400, 2200] for amateur range.

ELO_ACPL_SLOPE = 6        # ELO points lost per 1 cp of average loss
ELO_BASE = 1800           # ELO at ACPL = 0
ELO_BLUNDER_PENALTY = 40  # ELO penalty per 1% blunder rate
ELO_MIN, ELO_MAX = 400, 2200


def estimate_elo(records: list[dict], player: str = "white") -> dict:
    """
    Estimate ELO from game records for a given player ("white" or "black").

    Method:
      1. Compute Average Centipawn Loss (ACPL) for the player's moves.
      2. Compute blunder rate (blunders / total moves).
      3. ELO ≈ BASE - ACPL * SLOPE - blunder_rate_pct * PENALTY
      4. Clamp to [ELO_MIN, ELO_MAX].

    Returns a dict with elo, acpl, blunder_count, blunder_rate, move_count.
    """
    player_records = [r for r in records if r["player"] == player]
    if not player_records:
        return {"elo": None, "acpl": None, "blunder_count": 0,
                "blunder_rate": 0.0, "move_count": 0, "note": "no moves"}

    cp_losses = []
    blunder_count = 0

    for r in player_records:
        before = r["score_before_cp"]
        after  = r["score_after_cp"]
        # CP loss from the moving side's perspective (positive = loss)
        if r["player"] == "white":
            loss = max(0, before - after)   # white wants score to rise
        else:
            loss = max(0, after - before)   # black wants score to fall
        cp_losses.append(loss)
        if loss >= 150:
            blunder_count += 1

    move_count   = len(player_records)
    acpl         = sum(cp_losses) / move_count
    blunder_rate = blunder_count / move_count          # 0–1
    blunder_rate_pct = blunder_rate * 100              # 0–100

    raw_elo = ELO_BASE - (acpl * ELO_ACPL_SLOPE) - (blunder_rate_pct * ELO_BLUNDER_PENALTY)
    elo = int(max(ELO_MIN, min(ELO_MAX, raw_elo)))

    return {
        "elo":           elo,
        "acpl":          round(acpl, 1),
        "blunder_count": blunder_count,
        "blunder_rate":  round(blunder_rate, 3),
        "move_count":    move_count,
        "note":          f"ACPL={acpl:.1f}, blunder_rate={blunder_rate_pct:.1f}%",
    }


def elo_to_level(elo: int | None) -> str:
    """Map an ELO estimate to engine difficulty level."""
    if elo is None or elo < 900:
        return "beginner"
    if elo < 1300:
        return "intermediate"
    return "advanced"
