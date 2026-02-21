import sys
import os
import chess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from common import get_best_move


def test_aggression_prefers_capture():
    """
    Position where white can capture d5 with exd5, or make quiet moves.
    With high aggression, the capture should be preferred.
    """
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
    capture_move = chess.Move.from_uci("e4d5")
    assert capture_move in board.legal_moves

    move_high, _ = get_best_move(board, depth=1, blunder_pct=0.0, aggression=1.0)
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
