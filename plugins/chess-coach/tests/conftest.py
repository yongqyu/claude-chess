import json
import os
import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
PERSONAS_DIR = os.path.join(os.path.dirname(__file__), "..", "personas")

@pytest.fixture
def sample_game_records():
    """Minimal game records for extraction tests."""
    return [
        {
            "player_name": "tester",
            "players": {"white": "tester", "black": "ai"},
            "move_records": [
                {"move_san": "e4",  "move_uci": "e2e4", "player": "white", "actor": "tester",
                 "score_before_cp": 0,   "score_after_cp": 30},
                {"move_san": "e5",  "move_uci": "e7e5", "player": "black", "actor": "ai",
                 "score_before_cp": 30,  "score_after_cp": -10},
                {"move_san": "Nf3", "move_uci": "g1f3", "player": "white", "actor": "tester",
                 "score_before_cp": -10, "score_after_cp": 40},
                {"move_san": "Nc6", "move_uci": "b8c6", "player": "black", "actor": "ai",
                 "score_before_cp": 40,  "score_after_cp": 0},
                {"move_san": "d4",  "move_uci": "d2d4", "player": "white", "actor": "tester",
                 "score_before_cp": 0,   "score_after_cp": -200},
                {"move_san": "exd4","move_uci": "e5d4", "player": "black", "actor": "ai",
                 "score_before_cp": -200,"score_after_cp": 50},
            ],
            "opening": "Italian Game",
            "result": "0-1"
        },
        {
            "player_name": "tester",
            "players": {"white": "ai", "black": "tester"},
            "move_records": [
                {"move_san": "e4",  "move_uci": "e2e4", "player": "white", "actor": "ai",
                 "score_before_cp": 0,  "score_after_cp": 30},
                {"move_san": "c5",  "move_uci": "c7c5", "player": "black", "actor": "tester",
                 "score_before_cp": 30, "score_after_cp": 10},
                {"move_san": "Nxe4","move_uci": "c6e4", "player": "black", "actor": "tester",
                 "score_before_cp": 10, "score_after_cp": -30},
            ],
            "opening": "Sicilian Defense",
            "result": "1-0"
        }
    ]
