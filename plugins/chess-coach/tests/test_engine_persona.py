import json
import os
import subprocess
import sys
import tempfile
import pytest

SCRIPTS  = os.path.join(os.path.dirname(__file__), "..", "scripts")
PERSONAS = os.path.join(os.path.dirname(__file__), "..", "personas")


def new_game(tmp_path, color="white", level="intermediate"):
    state_path = str(tmp_path / "game.json")
    subprocess.run([sys.executable, f"{SCRIPTS}/engine.py", "new_game",
                    "--color", color, "--level", level,
                    "--state", state_path], capture_output=True)
    return state_path


def ai_move(state_path, persona_id=None, persona_dir=None):
    cmd = [sys.executable, f"{SCRIPTS}/engine.py", "ai_move",
           "--state", state_path]
    if persona_id:
        cmd += ["--persona", persona_id,
                "--bundled-persona-dir", persona_dir or PERSONAS]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def test_ai_move_with_persona_succeeds(tmp_path):
    state = new_game(tmp_path, color="black")   # AI plays white
    result = ai_move(state, persona_id="tal", persona_dir=PERSONAS)
    assert result["ok"] is True
    assert result["move_san"] != ""
    assert result["persona_used"] == "tal"


def test_ai_move_without_persona_still_works(tmp_path):
    state = new_game(tmp_path, color="black")
    result = ai_move(state)
    assert result["ok"] is True


def test_ai_move_unknown_persona_falls_back(tmp_path):
    """Unknown persona ID should fall back to default behavior, not crash."""
    state = new_game(tmp_path, color="black")
    result = ai_move(state, persona_id="nonexistent_xyz", persona_dir=PERSONAS)
    assert result["ok"] is True


def test_ai_move_uses_persona_opening(tmp_path):
    """With a persona that always plays e4, first white move should be e4."""
    persona = {
        "id": "test_e4_persona", "name": "E4 Bot", "source": "extracted",
        "description": "", "personality": "", "move_voice": "", "coaching_voice": "",
        "opening_moves": {"white": ["e4"], "black": []},
        "depth": 1, "blunder_rate": 0.0, "aggression": 0.0,
        "acpl": 50.0, "games_analyzed": 1, "created_at": "2026-01-01"
    }
    persona_dir = tmp_path / "personas"
    persona_dir.mkdir()
    (persona_dir / "test_e4_persona.json").write_text(json.dumps(persona))

    state = new_game(tmp_path, color="black")  # AI plays white, move 1
    result = ai_move(state, persona_id="test_e4_persona",
                     persona_dir=str(persona_dir))
    assert result["move_san"] == "e4"
