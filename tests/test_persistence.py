"""
Tests for persistence.py (task jd-03).

Eight tests:
  1. test_submit_score_returns_correct_rank
  2. test_submit_score_caps_at_10
  3. test_load_missing_file_returns_defaults
  4. test_migrate_adds_missing_keys
  5. test_daily_challenge_regenerates_on_new_date
  6. test_personal_best_survives_leaderboard_reset
  7. test_legacy_flat_array_migration
  8. test_corrupt_file_returns_defaults
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

from constants import LEADERBOARD_SIZE
from persistence import (
    DEFAULT_LEADERBOARD,
    DEFAULT_SETTINGS,
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


# ── 7. legacy flat-array leaderboard migration ───────────────────────────────
def test_legacy_flat_array_migration(tmp_dir, tmp_path):
    """A legacy flat-array leaderboard.json should be migrated to the new schema."""
    legacy = [
        {"name": "AAA", "score": 8000, "level": 12},
        {"name": "BBB", "score": 5000, "level": 8},
        {"name": "CCC", "score": 9500, "level": 15},
    ]
    lb_path = os.path.join(str(tmp_path), "leaderboard.json")
    with open(lb_path, "w") as f:
        json.dump(legacy, f)

    lb = tmp_dir.load_leaderboard()

    # Entries should appear under boards.normal, sorted descending
    board = lb["boards"]["normal"]
    assert len(board) == 3
    assert board[0]["score"] == 9500
    assert board[1]["score"] == 8000
    assert board[2]["score"] == 5000

    # Personal best for normal should equal the highest score
    assert lb["personal_bests"]["normal"] == 9500

    # Other boards/personal_bests should remain at defaults
    assert lb["boards"]["easy"] == []
    assert lb["personal_bests"]["easy"] == 0

    # The file should have been rewritten in the new schema
    with open(lb_path, "r") as f:
        saved = json.load(f)
    assert isinstance(saved, dict)
    assert "boards" in saved
    assert "personal_bests" in saved
    assert saved["version"] == 1


# ── 8. corrupt file returns defaults ─────────────────────────────────────────
def test_corrupt_file_returns_defaults(tmp_dir, tmp_path):
    """Corrupt JSON files should be handled gracefully, returning defaults."""
    # Write invalid JSON to settings file
    settings_path = os.path.join(str(tmp_path), "settings.json")
    with open(settings_path, "w") as f:
        f.write("{not valid json!!! @@#$")

    settings = tmp_dir.load_settings()
    assert settings["version"] == DEFAULT_SETTINGS["version"]
    assert settings["theme"] == "jungle"

    # Write invalid JSON to leaderboard file
    lb_path = os.path.join(str(tmp_path), "leaderboard.json")
    with open(lb_path, "w") as f:
        f.write("<<<corrupt>>>")

    lb = tmp_dir.load_leaderboard()
    assert lb["version"] == 1
    assert lb["boards"]["normal"] == []
    assert lb["personal_bests"]["normal"] == 0

    # Write invalid JSON to daily challenge file
    daily_path = os.path.join(str(tmp_path), "daily_challenge.json")
    with open(daily_path, "w") as f:
        f.write("")

    data = tmp_dir.load_daily_challenge()
    assert data["version"] == 1
    assert data["completed"] is False


# ── 9. is_top_score ──────────────────────────────────────────────────────────
def test_is_top_score_empty_board(tmp_dir):
    """Any positive score qualifies when the board is empty."""
    assert tmp_dir.is_top_score(1) is True


def test_is_top_score_zero_rejected(tmp_dir):
    """Zero and negative scores never qualify."""
    assert tmp_dir.is_top_score(0) is False
    assert tmp_dir.is_top_score(-100) is False


def test_is_top_score_full_board(tmp_dir):
    """Score must beat the lowest entry when board is full."""
    for i in range(LEADERBOARD_SIZE):
        tmp_dir.submit_score(f"P{i:02d}", (i + 1) * 1000, 1)
    # Lowest on board is 1000
    assert tmp_dir.is_top_score(500) is False
    assert tmp_dir.is_top_score(1001) is True


# ── 10. settings round-trip ───────────────────────────────────────────────────
def test_settings_save_and_reload(tmp_dir):
    """Settings saved to disk should be reloaded identically."""
    settings = tmp_dir.load_settings()
    settings["theme"] = "space"
    settings["volume_music"] = 0.3
    tmp_dir.save_settings(settings)

    reloaded = tmp_dir.load_settings()
    assert reloaded["theme"] == "space"
    assert reloaded["volume_music"] == 0.3


# ── 11. daily challenge round-trip ────────────────────────────────────────────
def test_daily_challenge_save_and_reload(tmp_dir):
    """Daily challenge state should persist across loads."""
    data = tmp_dir.load_daily_challenge()
    data["attempts"] = 3
    data["best_score"] = 7500
    tmp_dir.save_daily_challenge(data)

    reloaded = tmp_dir.load_daily_challenge()
    assert reloaded["attempts"] == 3
    assert reloaded["best_score"] == 7500


# ── 12. submit score with non-default difficulty ──────────────────────────────
def test_submit_score_different_difficulties(tmp_dir):
    """Scores submitted to different difficulties stay separate."""
    tmp_dir.submit_score("AAA", 5000, 10, difficulty="easy")
    tmp_dir.submit_score("BBB", 8000, 15, difficulty="hard")

    assert len(tmp_dir.get_board("easy")) == 1
    assert len(tmp_dir.get_board("hard")) == 1
    assert len(tmp_dir.get_board("normal")) == 0
    assert tmp_dir.get_personal_best("easy") == 5000
    assert tmp_dir.get_personal_best("hard") == 8000


# ── 13. empty name defaults to dashes ─────────────────────────────────────────
def test_empty_name_defaults_to_dashes(tmp_dir):
    """An empty name string should be replaced with '-----'."""
    tmp_dir.submit_score("", 1000, 5)
    board = tmp_dir.get_board("normal")
    assert board[0]["name"] == "-----"
