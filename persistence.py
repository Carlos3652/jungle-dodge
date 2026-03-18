"""
Jungle Dodge — persistence layer (task jd-03).

PersistenceManager handles settings, leaderboard, and daily-challenge JSON
files with graceful defaults, migration, and corrupt-file recovery.
"""

import copy
import json
import os
from datetime import date

from constants import LEADERBOARD_SIZE

# ── File paths (same directory as this module) ────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(_DIR, "settings.json")
LEADERBOARD_FILE = os.path.join(_DIR, "leaderboard.json")
DAILY_FILE = os.path.join(_DIR, "daily_challenge.json")

# ── Default schemas (spec Section 9.4) ────────────────────────────────────────
DEFAULT_SETTINGS = {
    "version": 1,
    "theme": "jungle",
    "difficulty": "normal",
    "volume_music": 0.7,
    "volume_sfx": 1.0,
    "volume_master": 1.0,
    "muted": False,
    "death_count": 0,
    "first_run": True,
    "show_tutorial": True,
    "fullscreen": True,
}

DEFAULT_LEADERBOARD = {
    "version": 1,
    "boards": {
        "normal": [],
        "easy": [],
        "hard": [],
        "daily": [],
    },
    "personal_bests": {
        "normal": 0,
        "easy": 0,
        "hard": 0,
        "daily": 0,
    },
}

DEFAULT_DAILY = {
    "version": 1,
    "current_date": "",
    "seed": 0,
    "completed": False,
    "best_score": 0,
    "attempts": 0,
}


# ── PersistenceManager ────────────────────────────────────────────────────────
class PersistenceManager:
    """Handles all JSON persistence: settings, leaderboard, daily challenge."""

    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = _DIR
        self.settings_file = os.path.join(base_dir, "settings.json")
        self.leaderboard_file = os.path.join(base_dir, "leaderboard.json")
        self.daily_file = os.path.join(base_dir, "daily_challenge.json")

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _load_with_defaults(path, defaults):
        """Load a JSON file; on missing/corrupt file return a copy of *defaults*.

        Performs a shallow merge so that any keys present in the file override
        the defaults while missing keys are filled in.
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return copy.deepcopy(defaults)
            merged = copy.deepcopy(defaults)
            merged.update(data)
            return merged
        except Exception:
            return copy.deepcopy(defaults)

    @staticmethod
    def _migrate(data, defaults):
        """Fill any keys present in *defaults* but missing from *data*.

        This supports forward-compatible schema evolution: new keys introduced
        in later versions are silently added with their default values.
        """
        for key, value in defaults.items():
            if key not in data:
                data[key] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(data.get(key), dict):
                # One-level recursive merge for nested dicts (e.g. boards, personal_bests)
                for sub_key, sub_val in value.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = copy.deepcopy(sub_val)
        return data

    @staticmethod
    def _save(path, data):
        """Write *data* as JSON to *path*, silently ignoring errors."""
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # ── Settings ──────────────────────────────────────────────────────────────

    def load_settings(self):
        """Return settings dict, filling missing keys from DEFAULT_SETTINGS."""
        data = self._load_with_defaults(self.settings_file, DEFAULT_SETTINGS)
        data = self._migrate(data, DEFAULT_SETTINGS)
        return data

    def save_settings(self, settings):
        """Persist *settings* dict to disk."""
        self._save(self.settings_file, settings)

    # ── Leaderboard ───────────────────────────────────────────────────────────

    def load_leaderboard(self):
        """Load leaderboard, migrating legacy flat-array format if needed."""
        try:
            with open(self.leaderboard_file, "r") as f:
                raw = json.load(f)
        except Exception:
            return copy.deepcopy(DEFAULT_LEADERBOARD)

        # Legacy format: flat array of {name, score, level}
        if isinstance(raw, list):
            migrated = copy.deepcopy(DEFAULT_LEADERBOARD)
            board = sorted(raw, key=lambda e: e.get("score", 0), reverse=True)[
                :LEADERBOARD_SIZE
            ]
            migrated["boards"]["normal"] = board
            if board:
                migrated["personal_bests"]["normal"] = board[0]["score"]
            self._save(self.leaderboard_file, migrated)
            return migrated

        if not isinstance(raw, dict):
            return copy.deepcopy(DEFAULT_LEADERBOARD)

        data = self._migrate(raw, DEFAULT_LEADERBOARD)
        return data

    def submit_score(self, name, score, level, difficulty="normal",
                     max_streak=0, badges=None, theme="jungle"):
        """Add a score entry; return 1-based rank (or None if not top-N)."""
        lb = self.load_leaderboard()
        board = lb["boards"].get(difficulty, [])

        entry = {
            "name": (name.upper() or "-----"),
            "score": score,
            "level": level,
            "max_streak": max_streak,
            "badges": badges or [],
            "theme": theme,
            "date": date.today().isoformat(),
        }

        board.append(entry)
        board.sort(key=lambda e: e.get("score", 0), reverse=True)

        # Determine rank via index-based lookup *before* slicing.
        # Among tied scores, our entry (appended last) lands last due to
        # stable sort.  Searching backwards finds it without relying on
        # object identity, which can return None after the slice rebuilds
        # the list.
        rank = None
        for i in range(len(board) - 1, -1, -1):
            if board[i]["score"] == score:
                rank = i + 1 if i < LEADERBOARD_SIZE else None
                break

        board = board[:LEADERBOARD_SIZE]
        lb["boards"][difficulty] = board

        # Update personal best
        pb = lb["personal_bests"]
        if score > pb.get(difficulty, 0):
            pb[difficulty] = score

        self._save(self.leaderboard_file, lb)
        return rank

    def is_top_score(self, score, difficulty="normal"):
        """Return True if *score* would qualify for the board."""
        if score <= 0:
            return False
        lb = self.load_leaderboard()
        board = lb["boards"].get(difficulty, [])
        if len(board) < LEADERBOARD_SIZE:
            return True
        return score > board[-1].get("score", 0)

    def get_board(self, difficulty="normal"):
        """Convenience: return sorted board list for *difficulty*."""
        lb = self.load_leaderboard()
        return lb["boards"].get(difficulty, [])

    def get_personal_best(self, difficulty="normal"):
        """Return the personal best score for *difficulty*."""
        lb = self.load_leaderboard()
        return lb["personal_bests"].get(difficulty, 0)

    # ── Daily Challenge ───────────────────────────────────────────────────────

    def load_daily_challenge(self):
        """Load daily challenge; regenerate seed when the date changes."""
        data = self._load_with_defaults(self.daily_file, DEFAULT_DAILY)
        data = self._migrate(data, DEFAULT_DAILY)
        today = date.today().isoformat()
        if data["current_date"] != today:
            data["current_date"] = today
            data["seed"] = int(today.replace("-", ""))
            data["completed"] = False
            data["best_score"] = 0
            data["attempts"] = 0
            self._save(self.daily_file, data)
        return data

    def save_daily_challenge(self, data):
        """Persist daily challenge state."""
        self._save(self.daily_file, data)
