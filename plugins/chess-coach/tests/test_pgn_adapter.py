import json
import os
import subprocess
import sys
import tempfile
import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")

SAMPLE_PGN = """[Event "Test Game"]
[White "Fischer"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0
"""

def run_adapter(pgn_text, player="Fischer", output_dir=None):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
        f.write(pgn_text)
        pgn_path = f.name
    out_dir = output_dir or tempfile.mkdtemp()
    r = subprocess.run(
        [sys.executable, f"{SCRIPTS}/pgn_adapter.py",
         "--pgn", pgn_path, "--player", player, "--output", out_dir],
        capture_output=True, text=True
    )
    result = json.loads(r.stdout)
    return result, out_dir


def test_adapter_produces_game_file():
    result, out_dir = run_adapter(SAMPLE_PGN)
    assert result["ok"] is True
    assert result["games_written"] == 1


def test_adapter_sets_correct_actor():
    result, out_dir = run_adapter(SAMPLE_PGN, player="Fischer")
    game_files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    game = json.loads(open(os.path.join(out_dir, game_files[0])).read())
    white_moves = [r for r in game["move_records"] if r["player"] == "white"]
    assert all(r["actor"] == "Fischer" for r in white_moves)


def test_adapter_sets_ai_for_opponent():
    result, out_dir = run_adapter(SAMPLE_PGN, player="Fischer")
    game_files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    game = json.loads(open(os.path.join(out_dir, game_files[0])).read())
    black_moves = [r for r in game["move_records"] if r["player"] == "black"]
    assert all(r["actor"] == "ai" for r in black_moves)


def test_adapter_includes_cp_scores():
    result, out_dir = run_adapter(SAMPLE_PGN)
    game_files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    game = json.loads(open(os.path.join(out_dir, game_files[0])).read())
    for r in game["move_records"]:
        assert "score_before_cp" in r
        assert "score_after_cp" in r


def test_adapter_multi_game_pgn():
    two_games = SAMPLE_PGN + "\n" + SAMPLE_PGN.replace("1-0", "0-1")
    result, _ = run_adapter(two_games)
    assert result["games_written"] == 2


def test_adapter_skips_non_matching_player():
    result, out_dir = run_adapter(SAMPLE_PGN, player="Kasparov")
    assert result["ok"] is True
    assert result["games_written"] == 0
    game_files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    assert len(game_files) == 0
