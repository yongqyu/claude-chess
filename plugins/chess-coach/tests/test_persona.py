import json
import os
import subprocess
import sys
import tempfile
import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
PERSONAS = os.path.join(os.path.dirname(__file__), "..", "personas")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def test_list_returns_bundled_personas():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "list",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    assert result["ok"] is True
    ids = [p["id"] for p in result["personas"]]
    assert "fischer" in ids
    assert "tal" in ids


def test_list_includes_source_field():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "list",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    fischer = next(p for p in result["personas"] if p["id"] == "fischer")
    assert fischer["source"] == "historical"


def test_list_only_has_id_name_source():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "list",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    for p in result["personas"]:
        assert set(p.keys()) == {"id", "name", "source"}


def test_show_returns_full_persona():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "show",
                  "--id", "fischer",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    assert result["ok"] is True
    assert result["persona"]["id"] == "fischer"
    assert "description" in result["persona"]
    assert "aggression" in result["persona"]


def test_show_unknown_id_returns_error():
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "show",
                  "--id", "nonexistent_xyz",
                  "--bundled-dir", PERSONAS, "--user-dir", "/tmp/nonexistent"])
    assert result["ok"] is False


def test_show_user_persona_takes_precedence(tmp_path):
    custom = {"id": "fischer", "name": "Custom Fischer", "source": "extracted",
              "description": "", "personality": "", "move_voice": "",
              "coaching_voice": "", "opening_moves": {"white": ["d4"], "black": []},
              "depth": 1, "blunder_rate": 0.5, "aggression": 0.1,
              "acpl": 100.0, "games_analyzed": 5, "created_at": "2026-01-01"}
    (tmp_path / "fischer.json").write_text(json.dumps(custom))
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "show",
                  "--id", "fischer",
                  "--bundled-dir", PERSONAS, "--user-dir", str(tmp_path)])
    assert result["persona"]["source"] == "extracted"


# ── extraction tests ──────────────────────────────────────────────────────

def write_game_files(tmp_path, records_list):
    for i, rec in enumerate(records_list):
        (tmp_path / f"game_{i:03d}.json").write_text(json.dumps(rec))


def test_extract_opening_moves_white(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
                  "--actor", "tester", "--id", "tester",
                  "--games-dir", str(tmp_path)])
    assert result["ok"] is True
    assert "persona" in result
    assert "e4" in result["persona"]["opening_moves"]["white"]


def test_extract_opening_moves_black(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
                  "--actor", "tester", "--id", "tester",
                  "--games-dir", str(tmp_path)])
    assert "c5" in result["persona"]["opening_moves"]["black"]


def test_extract_aggression_is_float(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
                  "--actor", "tester", "--id", "tester",
                  "--games-dir", str(tmp_path)])
    assert 0.0 <= result["persona"]["aggression"] <= 1.0


def test_extract_games_analyzed_count(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
                  "--actor", "tester", "--id", "tester",
                  "--games-dir", str(tmp_path)])
    assert result["persona"]["games_analyzed"] == 2


def test_extract_depth_derived_from_acpl(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
                  "--actor", "tester", "--id", "tester",
                  "--games-dir", str(tmp_path)])
    assert result["persona"]["depth"] in [1, 2, 3]


def test_extract_character_layer_empty(tmp_path, sample_game_records):
    write_game_files(tmp_path, sample_game_records)
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "extract",
                  "--actor", "tester", "--id", "tester",
                  "--games-dir", str(tmp_path)])
    persona = result["persona"]
    assert persona["description"] == ""
    assert persona["personality"] == ""
    assert persona["move_voice"] == ""
    assert persona["coaching_voice"] == ""


# ── import_pgn tests ──────────────────────────────────────────────────────

SAMPLE_PGN = """[Event "Test"]
[White "Fischer"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""


def test_import_pgn_creates_persona(tmp_path):
    pgn_file = tmp_path / "test.pgn"
    pgn_file.write_text(SAMPLE_PGN)
    out = tmp_path / "fischer_extracted.json"
    result = run([sys.executable, f"{SCRIPTS}/persona.py", "import_pgn",
                  "--pgn", str(pgn_file), "--player", "Fischer",
                  "--id", "fischer_test", "--output", str(out)])
    assert result["ok"] is True
    assert out.exists()
    persona = json.loads(out.read_text())
    assert persona["id"] == "fischer_test"
    assert persona["source"] == "pgn"
    assert "e4" in persona["opening_moves"]["white"]
