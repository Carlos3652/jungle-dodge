"""
Tests for persistence.py (task jd-03).

Six tests per spec:
  1. test_submit_score_returns_correct_rank
  2. test_submit_score_caps_at_10
  3. test_load_missing_file_returns_defaults
  4. test_migrate_adds_missing_keys
  5. test_daily_challenge_regenerates_on_new_date
  6. test_personal_best_survives_leaderboard_reset
"""

import json
import os
import tempfile
from datetime import date
from unittest import mock

import pytest

# Allow importing from project root
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from persistence import (
    DEFAULT_LEADERBOARD,
    DEFAULT_SETTINGS,
    LEADERBOARD_SIZE,
    PersistenceManager,
)


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a PersistenceManager backed by a temporary directory."""
    return PersistenceManager(base_dir=str(tmp_path))


@pytest.fixture
def tmp_path_str(tmp_path):
    return str(tmp_path)


# ── 1. submit_score returns correct rank ──────────────────────────────────────
def test_submit_score_returns_correct_rank(tmp_dir):
    """Submitting a score should return the 1-based rank on the board."""
    # First score → rank 1
    rank = tmp_dir.submit_score("AAA", 5000, 10)
    assert rank == 1

    # Higher score → rank 1, previous drops to 2
    rank = tmp_dir.submit_score("BBB", 9000, 15)
    assert rank == 1

    # Lower score → rank 3
    rank = tmp_dir.submit_score("CCC", 3000, 5)
    assert rank == 3


# ── 2. submit_score caps at 10 entries ────────────────────────────────────────
def test_submit_score_caps_at_10(tmp_dir):
    """Board should never exceed LEADERBOARD_SIZE entries."""
    for i in range(15):
        tmp_dir.submit_score(f"P{i:02d}", (i + 1) * 100, 1)

    board = tmp_dir.get_board("normal")
    assert len(board) == LEADERBOARD_SIZE

    # Lowest remaining score should be the 6th submitted (600) since
    # scores 100-500 get pushed off
    scores = [e["score"] for e in board]
    assert scores == sorted(scores, reverse=True)
    assert min(scores) == 600


# ── 3. load_missing_file_returns_defaults ─────────────────────────────────────
def test_load_missing_file_returns_defaults(tmp_dir):
    """Loading from a non-existent file should return default schemas."""
    settings = tmp_dir.load_settings()
    assert settings["version"] == DEFAULT_SETTINGS["version"]
    assert settings["theme"] == "jungle"
    assert settings["first_run"] is True

    lb = tmp_dir.load_leaderboard()
    assert lb["version"] == 1
    assert lb["boards"]["normal"] == []
    assert lb["personal_bests"]["normal"] == 0


# ── 4. migrate adds missing keys ─────────────────────────────────────────────
def test_migrate_adds_missing_keys(tmp_dir, tmp_path):
    """_migrate should fill keys added in newer schema versions."""
    # Write a leaderboard file missing 'daily' board and 'daily' personal_best
    incomplete = {
        "version": 1,
        "boards": {"normal": [], "easy": [], "hard": []},
        "personal_bests": {"normal": 0, "easy": 0, "hard": 0},
    }
    lb_path = os.path.join(str(tmp_path), "leaderboard.json")
    with open(lb_path, "w") as f:
        json.dump(incomplete, f)

    lb = tmp_dir.load_leaderboard()
    # daily board and personal_best should have been added
    assert "daily" in lb["boards"]
    assert lb["boards"]["daily"] == []
    assert "daily" in lb["personal_bests"]
    assert lb["personal_bests"]["daily"] == 0


# ── 5. daily_challenge regenerates on new date ────────────────────────────────
def test_daily_challenge_regenerates_on_new_date(tmp_dir, tmp_path):
    """When the date changes, daily challenge should reset with a new seed."""
    # Write a stale daily challenge
    stale = {
        "version": 1,
        "current_date": "2025-01-01",
        "seed": 20250101,
        "completed": True,
        "best_score": 9999,
        "attempts": 5,
    }
    daily_path = os.path.join(str(tmp_path), "daily_challenge.json")
    with open(daily_path, "w") as f:
        json.dump(stale, f)

    data = tmp_dir.load_daily_challenge()
    today = date.today().isoformat()
    assert data["current_date"] == today
    assert data["seed"] == int(today.replace("-", ""))
    assert data["completed"] is False
    assert data["best_score"] == 0
    assert data["attempts"] == 0


# ── 6. personal_best survives leaderboard reset ──────────────────────────────
def test_personal_best_survives_leaderboard_reset(tmp_dir, tmp_path):
    """Personal bests should persist even if the board entries are cleared."""
    # Submit a high score
    tmp_dir.submit_score("ACE", 12000, 20)
    assert tmp_dir.get_personal_best("normal") == 12000

    # Manually wipe the board entries but keep personal_bests
    lb_path = os.path.join(str(tmp_path), "leaderboard.json")
    with open(lb_path, "r") as f:
        lb = json.load(f)
    lb["boards"]["normal"] = []
    with open(lb_path, "w") as f:
        json.dump(lb, f)

    # Personal best should still be there
    assert tmp_dir.get_personal_best("normal") == 12000
