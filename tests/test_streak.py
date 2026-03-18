"""Tests for streak combo multiplier system (task jd-08).

Tests cover:
  - Streak increment on dodge
  - Multiplier tier calculation (1x / 1.5x / 2x / 3x)
  - Streak reset on hit
  - 'STREAK LOST' particle emission when streak >= 5
  - Points awarded with correct multiplier
  - HUD streak tier info helper
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call

# ── Stub pygame before importing game code ───────────────────────────────────
# Reuse the existing mock if already registered (full-suite runs), else create.
if "pygame" not in sys.modules:
    _pg = types.ModuleType("pygame")
    _pg.init = MagicMock()
    _pg.Surface = MagicMock
    _pg.Rect = MagicMock()
    _pg.FULLSCREEN = 0
    _pg.SCALED = 0
    _pg.SRCALPHA = 0x00010000
    _pg.KEYDOWN = 2
    _pg.QUIT = 12
    _pg.font = types.ModuleType("pygame.font")
    _pg.font.init = MagicMock()
    _pg.font.get_init = MagicMock(return_value=True)
    _pg.font.SysFont = MagicMock(return_value=MagicMock())
    _pg.font.Font = MagicMock(return_value=MagicMock())
    _pg.display = types.ModuleType("pygame.display")
    _pg.display.set_mode = MagicMock(return_value=MagicMock())
    _pg.display.set_caption = MagicMock()
    _pg.display.flip = MagicMock()
    _pg.mouse = types.ModuleType("pygame.mouse")
    _pg.mouse.set_visible = MagicMock()
    _pg.time = types.ModuleType("pygame.time")
    _pg.time.Clock = MagicMock
    _pg.time.get_ticks = MagicMock(return_value=0)
    _pg.draw = types.ModuleType("pygame.draw")
    _pg.draw.rect = MagicMock()
    _pg.draw.line = MagicMock()
    _pg.draw.lines = MagicMock()
    _pg.draw.circle = MagicMock()
    _pg.draw.ellipse = MagicMock()
    _pg.draw.polygon = MagicMock()
    _pg.draw.arc = MagicMock()
    _pg.image = types.ModuleType("pygame.image")
    _pg.image.load = MagicMock(return_value=MagicMock())
    _pg.transform = types.ModuleType("pygame.transform")
    _pg.transform.scale = MagicMock(return_value=MagicMock())
    _pg.transform.rotate = MagicMock(return_value=MagicMock(
        get_size=MagicMock(return_value=(100, 100))))
    _pg.mixer = types.ModuleType("pygame.mixer")
    _pg.mixer.init = MagicMock()
    _pg.mixer.Sound = MagicMock
    _pg.key = types.ModuleType("pygame.key")
    _pg.key.get_pressed = MagicMock(return_value={})
    _pg.event = types.ModuleType("pygame.event")
    _pg.event.get = MagicMock(return_value=[])
    _pg.K_LEFT = 276
    _pg.K_RIGHT = 275
    _pg.K_a = 97
    _pg.K_d = 100
    _pg.K_SPACE = 32
    _pg.K_ESCAPE = 27
    _pg.K_F11 = 292
    _pg.K_TAB = 9
    _pg.K_RETURN = 13
    _pg.K_KP_ENTER = 271
    _pg.K_BACKSPACE = 8
    sys.modules["pygame"] = _pg
    sys.modules.setdefault("pygame.font", _pg.font)
    sys.modules.setdefault("pygame.display", _pg.display)
    sys.modules.setdefault("pygame.mixer", _pg.mixer)

_pg = sys.modules["pygame"]

from states import get_streak_multiplier, GameContext, PlayState, _new_game
from constants import DODGE_PTS, STREAK_TIERS, STREAK_LOST_THRESHOLD, CLR, GROUND_Y, S
from hud import _streak_tier_info


# ─────────────────────────────────────────────────────────────────────────────
#  Tests for get_streak_multiplier()
# ─────────────────────────────────────────────────────────────────────────────
class TestStreakMultiplierTiers(unittest.TestCase):
    """Verify each multiplier tier boundary."""

    def test_tier_0_to_4_is_1x(self):
        for s in range(0, 5):
            self.assertEqual(get_streak_multiplier(s), 1.0,
                             f"streak={s} should be 1.0x")

    def test_tier_5_to_9_is_1_5x(self):
        for s in range(5, 10):
            self.assertEqual(get_streak_multiplier(s), 1.5,
                             f"streak={s} should be 1.5x")

    def test_tier_10_to_19_is_2x(self):
        for s in range(10, 20):
            self.assertEqual(get_streak_multiplier(s), 2.0,
                             f"streak={s} should be 2.0x")

    def test_tier_20_plus_is_3x(self):
        for s in [20, 25, 50, 100]:
            self.assertEqual(get_streak_multiplier(s), 3.0,
                             f"streak={s} should be 3.0x")

    def test_exact_boundaries(self):
        """Verify the exact boundary values: 0, 4, 5, 9, 10, 19, 20."""
        self.assertEqual(get_streak_multiplier(0), 1.0)
        self.assertEqual(get_streak_multiplier(4), 1.0)
        self.assertEqual(get_streak_multiplier(5), 1.5)
        self.assertEqual(get_streak_multiplier(9), 1.5)
        self.assertEqual(get_streak_multiplier(10), 2.0)
        self.assertEqual(get_streak_multiplier(19), 2.0)
        self.assertEqual(get_streak_multiplier(20), 3.0)


# ─────────────────────────────────────────────────────────────────────────────
#  Tests for streak increment on dodge (unit-level, not going through Player.update)
# ─────────────────────────────────────────────────────────────────────────────
class TestStreakIncrement(unittest.TestCase):
    """Verify streak increments when obstacles are dodged.

    These tests exercise PlayState.update() with player.update mocked out
    to avoid pygame.key.get_pressed() mock conflicts in full-suite runs.
    """

    def _make_ctx(self):
        """Create a minimal GameContext for testing."""
        from persistence import PersistenceManager
        ctx = GameContext(
            screen=MagicMock(),
            display=MagicMock(),
            clock=MagicMock(),
            persistence=MagicMock(spec=PersistenceManager),
        )
        ctx.persistence.is_top_score = MagicMock(return_value=False)
        return ctx

    def _make_scored_obstacle(self):
        """Return a mock obstacle that's scored and not hit."""
        obs = MagicMock()
        obs.alive = True
        obs.scored = True
        obs._pts = False
        obs.did_hit = False
        obs.x = 100.0
        obs.exp_r = 50
        obs.check_hit = MagicMock(return_value=False)
        return obs

    def _run_update(self, ctx, state, dt=0.016):
        """Run PlayState.update() with player.update mocked to avoid
        pygame.key dependencies."""
        with patch.object(ctx.player, 'update'):
            state.update(ctx, dt)

    def test_streak_increments_on_dodge(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        self.assertEqual(ctx.streak, 0)

        obs = self._make_scored_obstacle()
        ctx.obstacles = [obs]
        state = PlayState()
        self._run_update(ctx, state)

        self.assertEqual(ctx.streak, 1)

    def test_streak_increments_multiple_dodges(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        state = PlayState()

        for i in range(7):
            obs = self._make_scored_obstacle()
            ctx.obstacles = [obs]
            self._run_update(ctx, state)

        self.assertEqual(ctx.streak, 7)

    def test_points_apply_multiplier_at_1x(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        state = PlayState()

        obs = self._make_scored_obstacle()
        ctx.obstacles = [obs]
        self._run_update(ctx, state)

        # At streak=1, multiplier is 1.0x, so pts = 10
        self.assertEqual(ctx.score, DODGE_PTS)

    def test_points_apply_multiplier_at_1_5x(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        state = PlayState()

        # Build up 4 dodges at 1x (40 pts)
        for _ in range(4):
            obs = self._make_scored_obstacle()
            ctx.obstacles = [obs]
            self._run_update(ctx, state)

        self.assertEqual(ctx.score, 40)  # 4 * 10

        # 5th dodge -> streak=5 -> 1.5x -> 15 pts
        obs = self._make_scored_obstacle()
        ctx.obstacles = [obs]
        self._run_update(ctx, state)

        self.assertEqual(ctx.score, 55)  # 40 + 15
        self.assertEqual(ctx.streak, 5)

    def test_points_apply_multiplier_at_3x(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        state = PlayState()

        # Build 19 dodges
        for _ in range(19):
            obs = self._make_scored_obstacle()
            ctx.obstacles = [obs]
            self._run_update(ctx, state)

        score_before = ctx.score

        # 20th dodge -> streak=20 -> 3x -> 30 pts
        obs = self._make_scored_obstacle()
        ctx.obstacles = [obs]
        self._run_update(ctx, state)

        self.assertEqual(ctx.streak, 20)
        self.assertEqual(ctx.score - score_before, 30)


# ─────────────────────────────────────────────────────────────────────────────
#  Tests for streak reset on hit
# ─────────────────────────────────────────────────────────────────────────────
class TestStreakReset(unittest.TestCase):
    """Verify streak resets to 0 when player is hit."""

    def _make_ctx(self):
        from persistence import PersistenceManager
        ctx = GameContext(
            screen=MagicMock(),
            display=MagicMock(),
            clock=MagicMock(),
            persistence=MagicMock(spec=PersistenceManager),
        )
        ctx.persistence.is_top_score = MagicMock(return_value=False)
        return ctx

    def _run_update(self, ctx, state, dt=0.016):
        with patch.object(ctx.player, 'update'):
            state.update(ctx, dt)

    def test_streak_resets_on_hit(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        ctx.streak = 3
        state = PlayState()

        obs = MagicMock()
        obs.alive = True
        obs.scored = False
        obs._pts = False
        obs.did_hit = False
        obs.check_hit = MagicMock(return_value=True)
        ctx.obstacles = [obs]

        self._run_update(ctx, state)

        self.assertEqual(ctx.streak, 0)

    def test_streak_lost_particle_emitted_when_streak_gte_5(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        ctx.streak = 7
        state = PlayState()

        ctx.particles.pop_text = MagicMock()

        obs = MagicMock()
        obs.alive = True
        obs.scored = False
        obs._pts = False
        obs.did_hit = False
        obs.check_hit = MagicMock(return_value=True)
        ctx.obstacles = [obs]

        self._run_update(ctx, state)

        # Should have 2 pop_text calls: "OUCH!" and "STREAK LOST"
        calls = ctx.particles.pop_text.call_args_list
        texts = [c[0][2] for c in calls]  # 3rd positional arg is text
        self.assertIn("OUCH!", texts)
        self.assertIn("STREAK LOST", texts)
        self.assertEqual(ctx.streak, 0)

    def test_no_streak_lost_particle_when_streak_below_5(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        ctx.streak = 3
        state = PlayState()

        ctx.particles.pop_text = MagicMock()

        obs = MagicMock()
        obs.alive = True
        obs.scored = False
        obs._pts = False
        obs.did_hit = False
        obs.check_hit = MagicMock(return_value=True)
        ctx.obstacles = [obs]

        self._run_update(ctx, state)

        calls = ctx.particles.pop_text.call_args_list
        texts = [c[0][2] for c in calls]
        self.assertNotIn("STREAK LOST", texts)
        self.assertEqual(ctx.streak, 0)

    def test_streak_lost_emitted_at_exactly_5(self):
        """Edge case: streak == STREAK_LOST_THRESHOLD (5) should emit."""
        ctx = self._make_ctx()
        _new_game(ctx)
        ctx.streak = 5
        state = PlayState()

        ctx.particles.pop_text = MagicMock()

        obs = MagicMock()
        obs.alive = True
        obs.scored = False
        obs._pts = False
        obs.did_hit = False
        obs.check_hit = MagicMock(return_value=True)
        ctx.obstacles = [obs]

        self._run_update(ctx, state)

        calls = ctx.particles.pop_text.call_args_list
        texts = [c[0][2] for c in calls]
        self.assertIn("STREAK LOST", texts)

    def test_new_game_resets_streak(self):
        ctx = self._make_ctx()
        _new_game(ctx)
        ctx.streak = 15
        _new_game(ctx)
        self.assertEqual(ctx.streak, 0)


# ─────────────────────────────────────────────────────────────────────────────
#  Tests for HUD streak tier info helper
# ─────────────────────────────────────────────────────────────────────────────
class TestStreakTierInfo(unittest.TestCase):
    """Verify _streak_tier_info returns correct tier/color for HUD badge."""

    def test_no_badge_below_5(self):
        mult, tier_name, color = _streak_tier_info(0)
        self.assertEqual(mult, 1.0)
        self.assertIsNone(tier_name)
        self.assertIsNone(color)

        mult, tier_name, color = _streak_tier_info(4)
        self.assertEqual(mult, 1.0)
        self.assertIsNone(tier_name)

    def test_bronze_badge_at_5(self):
        mult, tier_name, color = _streak_tier_info(5)
        self.assertEqual(mult, 1.5)
        self.assertEqual(tier_name, "bronze")
        self.assertIsNotNone(color)

    def test_silver_badge_at_10(self):
        mult, tier_name, color = _streak_tier_info(10)
        self.assertEqual(mult, 2.0)
        self.assertEqual(tier_name, "silver")

    def test_gold_badge_at_20(self):
        mult, tier_name, color = _streak_tier_info(20)
        self.assertEqual(mult, 3.0)
        self.assertEqual(tier_name, "gold")

    def test_gold_badge_at_50(self):
        mult, tier_name, color = _streak_tier_info(50)
        self.assertEqual(mult, 3.0)
        self.assertEqual(tier_name, "gold")


# ─────────────────────────────────────────────────────────────────────────────
#  Tests for score multiplier math
# ─────────────────────────────────────────────────────────────────────────────
class TestScoreMultiplierMath(unittest.TestCase):
    """Verify points = int(DODGE_PTS * multiplier) for each tier."""

    def test_1x_yields_10(self):
        self.assertEqual(int(DODGE_PTS * get_streak_multiplier(3)), 10)

    def test_1_5x_yields_15(self):
        self.assertEqual(int(DODGE_PTS * get_streak_multiplier(7)), 15)

    def test_2x_yields_20(self):
        self.assertEqual(int(DODGE_PTS * get_streak_multiplier(15)), 20)

    def test_3x_yields_30(self):
        self.assertEqual(int(DODGE_PTS * get_streak_multiplier(25)), 30)


if __name__ == "__main__":
    unittest.main()
