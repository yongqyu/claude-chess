import sys
import os
import chess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from common import get_best_move


def test_aggression_selects_capture_over_quiet():
    """
    In a position with available captures, high aggression should always
    pick a capture move.

    Position after 1.e4 e5 2.d4 exd4 — white can recapture (capture) or
    play a quiet developing move. With aggression=1.0 the engine must
    choose a capture.
    """
    board = chess.Board("rnbqkbnr/pppp1ppp/8/8/3pP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3")

    # Verify there are both captures and non-captures available
    all_captures = [m for m in board.legal_moves if board.is_capture(m)]
    assert len(all_captures) > 0, "Position must have captures available"

    move, _ = get_best_move(board, depth=1, blunder_pct=0.0, aggression=1.0)
    assert board.is_capture(move), f"Expected a capture with high aggression, got {board.san(move)}"


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
