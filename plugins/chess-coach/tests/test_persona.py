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
