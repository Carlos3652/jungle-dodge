"""Tests for jd-11: Difficulty selector (Easy/Normal/Hard)."""

import copy
import json
import os
import sys
import tempfile
from types import SimpleNamespace

import pygame
import pytest

# ── Ensure project root is on sys.path ────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from constants import DIFFICULTIES, DIFFICULTY_ORDER, MAX_LIVES, SPEED_SCALE
from persistence import PersistenceManager, DEFAULT_SETTINGS


# ─────────────────────────────────────────────────────────────────────────────
# 1. DIFFICULTIES config sanity
# ─────────────────────────────────────────────────────────────────────────────
class TestDifficultyConfig:
    def test_difficulty_keys_match_order(self):
        """DIFFICULTY_ORDER must contain exactly the keys in DIFFICULTIES."""
        assert set(DIFFICULTY_ORDER) == set(DIFFICULTIES.keys())

    def test_difficulty_order_tuple(self):
        assert DIFFICULTY_ORDER == ("easy", "normal", "hard")

    def test_easy_has_more_lives(self):
        assert DIFFICULTIES["easy"]["lives"] > DIFFICULTIES["normal"]["lives"]

    def test_hard_has_fewer_lives(self):
        assert DIFFICULTIES["hard"]["lives"] < DIFFICULTIES["normal"]["lives"]

    def test_normal_speed_is_one(self):
        assert DIFFICULTIES["normal"]["speed_mult"] == 1.0

    def test_easy_speed_slower(self):
        assert DIFFICULTIES["easy"]["speed_mult"] < 1.0

    def test_hard_speed_faster(self):
        assert DIFFICULTIES["hard"]["speed_mult"] > 1.0

    def test_each_difficulty_has_label(self):
        for key, cfg in DIFFICULTIES.items():
            assert "label" in cfg
            assert cfg["label"] == key.upper()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Persistence — difficulty setting round-trip
# ─────────────────────────────────────────────────────────────────────────────
class TestDifficultyPersistence:
    def test_default_difficulty_is_normal(self):
        with tempfile.TemporaryDirectory() as td:
            pm = PersistenceManager(td)
            settings = pm.load_settings()
            assert settings["difficulty"] == "normal"

    def test_persist_difficulty(self):
        with tempfile.TemporaryDirectory() as td:
            pm = PersistenceManager(td)
            settings = pm.load_settings()
            settings["difficulty"] = "hard"
            pm.save_settings(settings)

            # Reload
            pm2 = PersistenceManager(td)
            settings2 = pm2.load_settings()
            assert settings2["difficulty"] == "hard"

    def test_leaderboard_per_difficulty(self):
        with tempfile.TemporaryDirectory() as td:
            pm = PersistenceManager(td)
            pm.submit_score("AAA", 100, 5, difficulty="easy")
            pm.submit_score("BBB", 200, 3, difficulty="hard")
            pm.submit_score("CCC", 150, 4, difficulty="normal")

            easy_board = pm.get_board("easy")
            hard_board = pm.get_board("hard")
            normal_board = pm.get_board("normal")

            assert len(easy_board) == 1
            assert easy_board[0]["name"] == "AAA"
            assert len(hard_board) == 1
            assert hard_board[0]["name"] == "BBB"
            assert len(normal_board) == 1
            assert normal_board[0]["name"] == "CCC"

    def test_personal_best_per_difficulty(self):
        with tempfile.TemporaryDirectory() as td:
            pm = PersistenceManager(td)
            pm.submit_score("AAA", 100, 5, difficulty="easy")
            pm.submit_score("BBB", 200, 3, difficulty="hard")

            assert pm.get_personal_best("easy") == 100
            assert pm.get_personal_best("hard") == 200
            assert pm.get_personal_best("normal") == 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. GameContext difficulty + _new_game
# ─────────────────────────────────────────────────────────────────────────────
class TestNewGameDifficulty:
    """Test that _new_game applies difficulty settings to player and context."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        """Create a minimal GameContext for testing."""
        # Minimal pygame stub — only needs screen, display, clock, persistence
        import pygame
        pygame.init()

        from states import GameContext, _new_game
        from persistence import PersistenceManager
        from particles import ParticleSystem

        self._new_game = _new_game
        screen = pygame.Surface((100, 100))
        self.ctx = GameContext(
            screen=screen,
            display=screen,
            clock=pygame.time.Clock(),
            persistence=PersistenceManager(str(tmp_path)),
            particles=ParticleSystem(),
        )

    def test_easy_gives_4_lives(self):
        self.ctx.difficulty = "easy"
        self._new_game(self.ctx)
        assert self.ctx.player.lives == 4
        assert self.ctx.speed_mult == 0.85

    def test_normal_gives_3_lives(self):
        self.ctx.difficulty = "normal"
        self._new_game(self.ctx)
        assert self.ctx.player.lives == 3
        assert self.ctx.speed_mult == 1.0

    def test_hard_gives_2_lives(self):
        self.ctx.difficulty = "hard"
        self._new_game(self.ctx)
        assert self.ctx.player.lives == 2
        assert self.ctx.speed_mult == 1.15

    def test_unknown_difficulty_defaults_to_normal(self):
        self.ctx.difficulty = "impossible"
        self._new_game(self.ctx)
        assert self.ctx.player.lives == 3
        assert self.ctx.speed_mult == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Speed scaling applied to obstacles
# ─────────────────────────────────────────────────────────────────────────────
class TestSpeedScaling:
    """Test that _spawn applies speed_mult to obstacle vy."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        import pygame
        pygame.init()

        from states import GameContext, _new_game, _spawn
        from persistence import PersistenceManager
        from particles import ParticleSystem

        self._new_game = _new_game
        self._spawn = _spawn
        screen = pygame.Surface((100, 100))
        self.ctx = GameContext(
            screen=screen,
            display=screen,
            clock=pygame.time.Clock(),
            persistence=PersistenceManager(str(tmp_path)),
            particles=ParticleSystem(),
        )

    def test_hard_obstacles_faster(self):
        """Obstacles on hard should have higher vy than normal."""
        import random
        random.seed(42)

        # Normal difficulty
        self.ctx.difficulty = "normal"
        self._new_game(self.ctx)
        self.ctx.obstacles = []
        self._spawn(self.ctx)
        normal_vy = self.ctx.obstacles[0].vy

        # Hard difficulty (same seed for same obstacle type)
        random.seed(42)
        self.ctx.difficulty = "hard"
        self._new_game(self.ctx)
        self.ctx.obstacles = []
        self._spawn(self.ctx)
        hard_vy = self.ctx.obstacles[0].vy

        assert hard_vy > normal_vy

    def test_easy_obstacles_slower(self):
        """Obstacles on easy should have lower vy than normal."""
        import random
        random.seed(42)

        # Normal
        self.ctx.difficulty = "normal"
        self._new_game(self.ctx)
        self.ctx.obstacles = []
        self._spawn(self.ctx)
        normal_vy = self.ctx.obstacles[0].vy

        # Easy
        random.seed(42)
        self.ctx.difficulty = "easy"
        self._new_game(self.ctx)
        self.ctx.obstacles = []
        self._spawn(self.ctx)
        easy_vy = self.ctx.obstacles[0].vy

        assert easy_vy < normal_vy


# ─────────────────────────────────────────────────────────────────────────────
# 5. StartScreenState difficulty cycling
# ─────────────────────────────────────────────────────────────────────────────
class TestStartScreenDifficulty:
    """Test that UP/DOWN and 1/2/3 keys cycle difficulty on start screen."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        import pygame
        pygame.init()

        from states import GameContext, GameStateManager, StartScreenState
        from persistence import PersistenceManager
        from particles import ParticleSystem

        screen = pygame.Surface((100, 100))
        self.ctx = GameContext(
            screen=screen,
            display=screen,
            clock=pygame.time.Clock(),
            persistence=PersistenceManager(str(tmp_path)),
            particles=ParticleSystem(),
        )
        self.manager = GameStateManager(self.ctx)
        self.state = StartScreenState()
        self.state.enter(self.ctx)

    def _key_event(self, key):
        return SimpleNamespace(type=pygame.KEYDOWN, key=key, unicode="", mod=0, scancode=0)

    def test_default_is_normal(self):
        assert self.state.diff_idx == 1
        assert self.ctx.difficulty == "normal"

    def test_down_cycles_to_hard(self):
        self.state.handle_event(self.ctx, self._key_event(pygame.K_DOWN))
        assert self.state.diff_idx == 2
        assert self.ctx.difficulty == "hard"

    def test_up_cycles_to_easy(self):
        self.state.handle_event(self.ctx, self._key_event(pygame.K_UP))
        assert self.state.diff_idx == 0
        assert self.ctx.difficulty == "easy"

    def test_up_wraps_around(self):
        # From easy (0), UP should wrap to hard (2)
        self.state.diff_idx = 0
        self.state.handle_event(self.ctx, self._key_event(pygame.K_UP))
        assert self.state.diff_idx == 2
        assert self.ctx.difficulty == "hard"

    def test_number_keys(self):
        self.state.handle_event(self.ctx, self._key_event(pygame.K_1))
        assert self.ctx.difficulty == "easy"

        self.state.handle_event(self.ctx, self._key_event(pygame.K_3))
        assert self.ctx.difficulty == "hard"

        self.state.handle_event(self.ctx, self._key_event(pygame.K_2))
        assert self.ctx.difficulty == "normal"

    def test_difficulty_persists_to_settings(self):
        self.state.handle_event(self.ctx, self._key_event(pygame.K_3))
        settings = self.ctx.persistence.load_settings()
        assert settings["difficulty"] == "hard"

    def test_loads_correct_leaderboard(self):
        # Submit a score to easy board
        self.ctx.persistence.submit_score("TST", 999, 5, difficulty="easy")
        self.state.handle_event(self.ctx, self._key_event(pygame.K_1))
        assert len(self.ctx.leaderboard) == 1
        assert self.ctx.leaderboard[0]["name"] == "TST"
