"""Tests for near-miss scoring system (task jd-10).

Tests cover:
  - NEAR_MISS_PTS and NEAR_MISS_THRESHOLD are defined in constants
  - Near-miss bonus awarded when obstacle scores within threshold
  - No bonus awarded when obstacle is outside threshold
  - _near_miss_checked flag prevents double-counting
  - 'CLOSE!' particle emitted on near-miss
  - No near-miss when obstacle hit the player (did_hit=True)
  - near_misses counter incremented and reset by _new_game()
  - Threshold is scaled correctly (~144px at 4K)
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call

# ── Stub pygame before importing game code ───────────────────────────────────
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
    _pg.K_UP = 273
    _pg.K_DOWN = 274
    _pg.K_1 = 49
    _pg.K_2 = 50
    _pg.K_3 = 51
    _pg.quit = MagicMock()
    sys.modules["pygame"] = _pg
    sys.modules.setdefault("pygame.font", _pg.font)
    sys.modules.setdefault("pygame.display", _pg.display)
    sys.modules.setdefault("pygame.mixer", _pg.mixer)

_pg = sys.modules["pygame"]

from constants import NEAR_MISS_PTS, NEAR_MISS_THRESHOLD, S
from states import GameContext, PlayState, _new_game
from persistence import PersistenceManager


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_ctx():
    """Create a minimal GameContext for testing."""
    ctx = GameContext(
        screen=MagicMock(),
        display=MagicMock(),
        clock=MagicMock(),
        persistence=MagicMock(spec=PersistenceManager),
    )
    ctx.persistence.is_top_score = MagicMock(return_value=False)
    return ctx


def _make_scored_obs(player_x=500.0, obs_x=500.0, did_hit=False):
    """Return a mock obstacle that has scored (passed ground) and not hit player."""
    obs = MagicMock()
    obs.alive = True
    obs.scored = True
    obs._pts = False
    obs.did_hit = did_hit
    obs.x = obs_x
    obs.exp_r = 50
    obs.check_hit = MagicMock(return_value=False)
    obs._near_miss_checked = False
    return obs


def _run_update(ctx, state, dt=0.016):
    """Run PlayState.update() with player.update mocked to avoid key deps."""
    with patch.object(ctx.player, 'update'):
        state.update(ctx, dt)


# ─────────────────────────────────────────────────────────────────────────────
#  Constants tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNearMissConstants(unittest.TestCase):

    def test_near_miss_pts_is_5(self):
        self.assertEqual(NEAR_MISS_PTS, 5)

    def test_near_miss_threshold_scaled(self):
        """NEAR_MISS_THRESHOLD should equal int(40 * S)."""
        expected = int(40 * S)
        self.assertEqual(NEAR_MISS_THRESHOLD, expected)

    def test_near_miss_threshold_approx_144_at_4k(self):
        """At 4K (S=3.6), threshold should be ~144px."""
        # S = H/600 = 2160/600 = 3.6, int(40 * 3.6) = 144
        self.assertGreaterEqual(NEAR_MISS_THRESHOLD, 140)
        self.assertLessEqual(NEAR_MISS_THRESHOLD, 150)


# ─────────────────────────────────────────────────────────────────────────────
#  Detection: within threshold
# ─────────────────────────────────────────────────────────────────────────────

class TestNearMissDetected(unittest.TestCase):

    def test_bonus_awarded_when_within_threshold(self):
        """Score increases by NEAR_MISS_PTS when obstacle.x is within threshold."""
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        # Place obstacle exactly 1px inside threshold
        obs_x = player_x + (NEAR_MISS_THRESHOLD - 1)
        obs = _make_scored_obs(obs_x=obs_x)
        ctx.obstacles = [obs]

        score_before = ctx.score
        _run_update(ctx, state)

        # streak=1 → multiplier=1x → dodge=10, near-miss=5 → total=15
        self.assertEqual(ctx.score - score_before, 15)

    def test_near_misses_counter_incremented(self):
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x)  # same x = within threshold
        ctx.obstacles = [obs]

        _run_update(ctx, state)

        self.assertEqual(ctx.near_misses, 1)

    def test_close_particle_emitted(self):
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x)
        ctx.obstacles = [obs]

        ctx.particles.pop_text = MagicMock()
        _run_update(ctx, state)

        calls = ctx.particles.pop_text.call_args_list
        texts = [c[0][2] for c in calls]  # 3rd positional arg
        self.assertIn("CLOSE!", texts)

    def test_exact_threshold_boundary_is_miss(self):
        """abs(obs.x - player.x) == NEAR_MISS_THRESHOLD is NOT a near-miss (strict <)."""
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x + NEAR_MISS_THRESHOLD)
        ctx.obstacles = [obs]

        initial_near_misses = ctx.near_misses
        _run_update(ctx, state)

        self.assertEqual(ctx.near_misses, initial_near_misses,
                         "Exactly at threshold should NOT trigger near-miss")


# ─────────────────────────────────────────────────────────────────────────────
#  Detection: outside threshold
# ─────────────────────────────────────────────────────────────────────────────

class TestNearMissNotDetected(unittest.TestCase):

    def test_no_bonus_when_outside_threshold(self):
        """No NEAR_MISS_PTS awarded when obstacle.x is beyond threshold."""
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x + NEAR_MISS_THRESHOLD + 100)
        ctx.obstacles = [obs]

        score_before = ctx.score
        _run_update(ctx, state)

        # Only dodge pts (10 for streak=1), no near-miss pts
        self.assertEqual(ctx.score - score_before, 10)

    def test_near_misses_counter_unchanged_when_far(self):
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x + NEAR_MISS_THRESHOLD + 500)
        ctx.obstacles = [obs]

        _run_update(ctx, state)

        self.assertEqual(ctx.near_misses, 0)

    def test_no_close_particle_when_far(self):
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x + NEAR_MISS_THRESHOLD + 500)
        ctx.obstacles = [obs]

        ctx.particles.pop_text = MagicMock()
        _run_update(ctx, state)

        calls = ctx.particles.pop_text.call_args_list
        texts = [c[0][2] for c in calls]
        self.assertNotIn("CLOSE!", texts)


# ─────────────────────────────────────────────────────────────────────────────
#  No near-miss when player was hit
# ─────────────────────────────────────────────────────────────────────────────

class TestNearMissNotWhenHit(unittest.TestCase):

    def test_no_near_miss_when_did_hit_true(self):
        """Near-miss should not trigger if obs.did_hit is True."""
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        # obs is within threshold but hit the player
        obs = _make_scored_obs(obs_x=player_x, did_hit=True)
        obs.scored = True
        obs._pts = True  # already scored dodge pts (would not be double-counted)
        ctx.obstacles = [obs]

        initial_near_misses = ctx.near_misses
        initial_score = ctx.score
        _run_update(ctx, state)

        self.assertEqual(ctx.near_misses, initial_near_misses)
        # Score should not gain near-miss pts
        self.assertEqual(ctx.score, initial_score)


# ─────────────────────────────────────────────────────────────────────────────
#  Flag prevents double-counting
# ─────────────────────────────────────────────────────────────────────────────

class TestNearMissFlag(unittest.TestCase):

    def test_near_miss_checked_flag_prevents_double_count(self):
        """Running update twice on the same scored obstacle must only award bonus once."""
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x)
        obs._pts = True   # pretend dodge pts already awarded
        ctx.obstacles = [obs]

        _run_update(ctx, state)
        score_after_first = ctx.score
        near_misses_after_first = ctx.near_misses

        # Second update — same obstacle still in list (simulate it staying alive)
        _run_update(ctx, state)

        self.assertEqual(ctx.score, score_after_first,
                         "Score must not increase on second update")
        self.assertEqual(ctx.near_misses, near_misses_after_first,
                         "near_misses must not increment on second update")

    def test_obstacle_near_miss_checked_flag_set(self):
        """After processing, obs._near_miss_checked must be True."""
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs = _make_scored_obs(obs_x=player_x)
        ctx.obstacles = [obs]

        _run_update(ctx, state)

        self.assertTrue(obs._near_miss_checked)


# ─────────────────────────────────────────────────────────────────────────────
#  _new_game resets near_misses
# ─────────────────────────────────────────────────────────────────────────────

class TestNearMissReset(unittest.TestCase):

    def test_new_game_resets_near_misses(self):
        ctx = _make_ctx()
        _new_game(ctx)
        ctx.near_misses = 7
        _new_game(ctx)
        self.assertEqual(ctx.near_misses, 0)

    def test_near_misses_starts_at_zero(self):
        ctx = _make_ctx()
        _new_game(ctx)
        self.assertEqual(ctx.near_misses, 0)


# ─────────────────────────────────────────────────────────────────────────────
#  Multiple near-misses in one update
# ─────────────────────────────────────────────────────────────────────────────

class TestMultipleNearMisses(unittest.TestCase):

    def test_two_near_misses_increment_counter_twice(self):
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        obs1 = _make_scored_obs(obs_x=player_x + 10)
        obs2 = _make_scored_obs(obs_x=player_x - 10)
        obs1._pts = True  # skip dodge scoring to isolate near-miss
        obs2._pts = True
        ctx.obstacles = [obs1, obs2]

        _run_update(ctx, state)

        self.assertEqual(ctx.near_misses, 2)

    def test_mixed_near_and_far_obstacles(self):
        """Only near obstacles count; far obstacles don't."""
        ctx = _make_ctx()
        _new_game(ctx)
        state = PlayState()

        player_x = ctx.player.x
        near_obs = _make_scored_obs(obs_x=player_x + 10)
        far_obs = _make_scored_obs(obs_x=player_x + NEAR_MISS_THRESHOLD + 500)
        near_obs._pts = True
        far_obs._pts = True
        ctx.obstacles = [near_obs, far_obs]

        _run_update(ctx, state)

        self.assertEqual(ctx.near_misses, 1)


if __name__ == "__main__":
    unittest.main()
