"""
Tests for persistence.py (task jd-03).

Twenty tests covering submit_score ranking, board capacity, file
handling, migration, daily challenges, settings, ties, and edge cases.
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


# ── 14. submit_score returns rank on tied scores ────────────────────────────
def test_submit_score_returns_rank_on_ties(tmp_dir):
    """When multiple entries share the same score, submit_score must still
    return a valid rank instead of None (the old `is` identity bug).
    Stable sort means each new tied entry lands after existing ones."""
    for i in range(LEADERBOARD_SIZE):
        rank = tmp_dir.submit_score(f"P{i:02d}", 5000, 10)
        # Stable sort: new entry appended last among equal scores
        assert rank == i + 1, f"Expected rank {i + 1} for tied score, got {rank}"


def test_submit_score_tie_on_full_board(tmp_dir):
    """A score tying with the lowest entry on a full board should still get
    a rank (not None) if it qualifies."""
    # Fill with scores 1000..10000
    for i in range(LEADERBOARD_SIZE):
        tmp_dir.submit_score(f"P{i:02d}", (i + 1) * 1000, 1)

    # Submit a score that ties with the highest (10000) — stable sort puts
    # the new entry after the existing 10000, so rank is 2
    rank = tmp_dir.submit_score("TIE", 10000, 1)
    assert rank == 2

    # Submit a score that ties with a mid-range entry (5000)
    rank = tmp_dir.submit_score("MID", 5000, 1)
    assert rank is not None
    assert isinstance(rank, int)


def test_submit_score_tie_with_lowest_returns_none(tmp_dir):
    """A score tying with the lowest on a full board should return None
    because the new entry is appended last, sorts after the existing one
    (stable sort), and gets sliced off."""
    # Fill board: scores 1000, 2000, ..., 10000
    for i in range(LEADERBOARD_SIZE):
        tmp_dir.submit_score(f"P{i:02d}", (i + 1) * 1000, 1)

    # Lowest on board is 1000. Submit another 1000 — it should NOT survive
    # the slice (stable sort keeps the old 1000 at index 9, new at 10 → cut).
    rank = tmp_dir.submit_score("DUP", 1000, 1)
    assert rank is None, (
        "Tying the lowest score on a full board must not award a rank"
    )

    # Board should still have exactly LEADERBOARD_SIZE entries
    board = tmp_dir.get_board("normal")
    assert len(board) == LEADERBOARD_SIZE
    # The original P00 entry (score 1000) should still be last, not DUP
    assert board[-1]["name"] == "P00"


def test_submit_score_below_board_returns_none(tmp_dir):
    """A score that doesn't make it onto a full board should return None."""
    for i in range(LEADERBOARD_SIZE):
        tmp_dir.submit_score(f"P{i:02d}", (i + 1) * 1000, 1)

    # Lowest on board is 1000; submitting 500 should not qualify
    rank = tmp_dir.submit_score("LOW", 500, 1)
    assert rank is None


# ── 17. tie at cutoff gets a rank ────────────────────────────────────────────
def test_submit_score_tie_at_cutoff_gets_rank(tmp_dir):
    """A score tying at exactly position LEADERBOARD_SIZE (the last slot)
    should still receive a valid rank, not None."""
    # Fill board with LEADERBOARD_SIZE - 1 entries, all different scores
    for i in range(LEADERBOARD_SIZE - 1):
        tmp_dir.submit_score(f"P{i:02d}", (i + 2) * 1000, 1)

    # The lowest score on board is 2000.  Submit a tie at 2000 —
    # it should land at exactly position LEADERBOARD_SIZE (the cutoff).
    rank = tmp_dir.submit_score("CUT", 2000, 1)
    assert rank == LEADERBOARD_SIZE, (
        f"Tying the lowest on a not-full board should give rank "
        f"{LEADERBOARD_SIZE}, got {rank}"
    )


# ── 18. pushed-off score returns None ────────────────────────────────────────
def test_submit_score_pushed_off_full_board_returns_none(tmp_dir):
    """When every entry on a full board shares the same score, a new
    submission with that score is appended last by stable sort and pushed
    off the board — submit_score must return None."""
    # Fill with LEADERBOARD_SIZE identical scores
    for i in range(LEADERBOARD_SIZE):
        rank = tmp_dir.submit_score(f"P{i:02d}", 5000, 10)
        assert rank == i + 1

    # 11th identical score: stable sort places it at index LEADERBOARD_SIZE
    # (past the cutoff) → should return None
    rank = tmp_dir.submit_score("OFF", 5000, 10)
    assert rank is None, (
        "An identical score on a full board should be pushed off and return None"
    )

    # Board size unchanged, and the newcomer should NOT be present
    board = tmp_dir.get_board("normal")
    assert len(board) == LEADERBOARD_SIZE
    assert all(e["name"] != "OFF" for e in board)


def test_submit_score_duplicate_entry_identity(tmp_dir):
    """Two identical entries (same name/score/level/date) must each get the
    correct rank via identity lookup, not value-equality."""
    rank1 = tmp_dir.submit_score("AAA", 5000, 10)
    assert rank1 == 1

    # Second submission with the exact same fields on the same day produces
    # a value-equal dict.  The identity-based lookup must still return the
    # correct rank for the *new* entry (rank 2, after the first).
    rank2 = tmp_dir.submit_score("AAA", 5000, 10)
    assert rank2 == 2

    board = tmp_dir.get_board("normal")
    assert len(board) == 2
    assert board[0]["score"] == board[1]["score"] == 5000
