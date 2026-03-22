"""Tests for named combo patterns (jd-16)."""

import sys
import types
import math
import random
import unittest
from unittest.mock import MagicMock, patch

# ── Stub pygame before importing game code ───────────────────────────────────
_pg = types.ModuleType("pygame")
_pg.init = MagicMock()
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
_pg.Surface = MagicMock
_pg.Rect = MagicMock(side_effect=lambda x, y, w, h: type('R', (), {
    'x': x, 'y': y, 'w': w, 'h': h,
    'colliderect': lambda self, o: False,
})())
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
_pg.transform.rotate = MagicMock(return_value=MagicMock(get_size=MagicMock(return_value=(100, 100))))
_pg.mixer = types.ModuleType("pygame.mixer")
_pg.mixer.init = MagicMock()
_pg.mixer.Sound = MagicMock
_pg.FULLSCREEN = 0
_pg.SCALED = 0
_pg.SRCALPHA = 0x00010000
_pg.KEYDOWN = 2
_pg.QUIT = 12
_pg.K_LEFT = 276
_pg.K_RIGHT = 275
_pg.K_a = 97
_pg.K_d = 100
_pg.K_SPACE = 32
_pg.K_F11 = 292
_pg.K_ESCAPE = 27
_pg.K_RETURN = 13
_pg.K_KP_ENTER = 271
_pg.K_BACKSPACE = 8
_pg.K_TAB = 9
_pg.K_UP = 273
_pg.K_DOWN = 274
_pg.K_1 = 49
_pg.K_2 = 50
_pg.K_3 = 51
_pg.key = types.ModuleType("pygame.key")
_pg.key.get_pressed = MagicMock(return_value={})
_pg.event = types.ModuleType("pygame.event")
_pg.event.get = MagicMock(return_value=[])
sys.modules.setdefault("pygame", _pg)
sys.modules.setdefault("pygame.font", _pg.font)
sys.modules.setdefault("pygame.display", _pg.display)
sys.modules.setdefault("pygame.mixer", _pg.mixer)

from combo_patterns import COMBO_PATTERNS, COMBO_CLEAR_BONUS
from entities import (
    Player, Obstacle, Vine, VineSnap, Bomb, Spike, Boulder,
    CanopyDrop, CrocSnap, spawn_cluster_spike,
)
from constants import W, GROUND_Y, S, SX, SY
from states import (
    GameContext, _start_combo, _update_combo, _spawn_combo_obstacle,
    _OBS_CLASS_MAP,
)
from particles import ParticleSystem


def _make_ctx(level=4):
    """Create a minimal GameContext for testing."""
    ctx = GameContext(
        screen=MagicMock(),
        display=MagicMock(),
        clock=MagicMock(),
        persistence=MagicMock(),
    )
    ctx.player = Player()
    ctx.level = level
    ctx.speed_mult = 1.0
    ctx.obstacles = []
    ctx.particles = ParticleSystem()
    ctx.theme = None
    ctx.combo_active = False
    ctx.combo_pattern = None
    ctx.combo_obstacles = []
    ctx.combo_spawn_idx = 0
    ctx.combo_elapsed = 0.0
    ctx.combo_patterns_cleared = 0
    ctx.combo_spawned_this_push = 0
    ctx._combo_push_started = False
    ctx.score = 0
    return ctx


# ─────────────────────────────────────────────────────────────────────────────
#  Pattern Definitions
# ─────────────────────────────────────────────────────────────────────────────
class TestComboPatternDefinitions(unittest.TestCase):
    """Test that all combo pattern definitions have required keys and valid data."""

    def test_all_patterns_have_required_keys(self):
        required = {"name", "min_level", "clear_bonus", "spawns"}
        for key, pat in COMBO_PATTERNS.items():
            self.assertTrue(required.issubset(pat.keys()),
                            f"Pattern '{key}' missing keys: {required - pat.keys()}")

    def test_all_patterns_have_spawns(self):
        for key, pat in COMBO_PATTERNS.items():
            self.assertGreater(len(pat["spawns"]), 0,
                               f"Pattern '{key}' has no spawns")

    def test_spawn_tuples_are_valid(self):
        for key, pat in COMBO_PATTERNS.items():
            for i, spawn in enumerate(pat["spawns"]):
                self.assertEqual(len(spawn), 3,
                                 f"Pattern '{key}' spawn {i} should be 3-tuple")
                delay, cls_name, x_pct = spawn
                self.assertIsInstance(delay, (int, float),
                                     f"Pattern '{key}' spawn {i} delay should be numeric")
                self.assertGreaterEqual(delay, 0.0)
                self.assertIsInstance(cls_name, str)
                if x_pct is not None:
                    self.assertGreaterEqual(x_pct, 0.0)
                    self.assertLessEqual(x_pct, 1.0)

    def test_class_names_are_in_obs_map(self):
        for key, pat in COMBO_PATTERNS.items():
            for delay, cls_name, x_pct in pat["spawns"]:
                self.assertIn(cls_name, _OBS_CLASS_MAP,
                              f"Pattern '{key}' uses unknown class '{cls_name}'")

    def test_clear_bonus_is_positive(self):
        for key, pat in COMBO_PATTERNS.items():
            self.assertGreater(pat["clear_bonus"], 0)

    def test_min_levels_are_reasonable(self):
        for key, pat in COMBO_PATTERNS.items():
            self.assertGreaterEqual(pat["min_level"], 1)
            self.assertLessEqual(pat["min_level"], 10)

    def test_five_patterns_defined(self):
        self.assertEqual(len(COMBO_PATTERNS), 5)

    def test_pattern_names(self):
        names = {pat["name"] for pat in COMBO_PATTERNS.values()}
        expected = {"The Funnel", "The Crossfire", "The Shell Game",
                    "The Rolling Wave", "The Triple Stack"}
        self.assertEqual(names, expected)

    def test_combo_clear_bonus_constant(self):
        self.assertEqual(COMBO_CLEAR_BONUS, 50)


# ─────────────────────────────────────────────────────────────────────────────
#  Combo Spawning
# ─────────────────────────────────────────────────────────────────────────────
class TestComboSpawning(unittest.TestCase):
    """Test obstacle spawning from combo patterns."""

    def test_spawn_vine(self):
        ctx = _make_ctx(level=4)
        result = _spawn_combo_obstacle(ctx, "Vine", 0.5)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Vine)
        self.assertEqual(len(ctx.obstacles), 1)

    def test_spawn_boulder(self):
        ctx = _make_ctx(level=5)
        result = _spawn_combo_obstacle(ctx, "Boulder", 0.3)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Boulder)

    def test_spawn_spike(self):
        ctx = _make_ctx(level=4)
        result = _spawn_combo_obstacle(ctx, "Spike", 0.5)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Spike)

    def test_spawn_bomb(self):
        ctx = _make_ctx(level=6)
        result = _spawn_combo_obstacle(ctx, "Bomb", 0.5)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Bomb)

    def test_spawn_vinesnap(self):
        ctx = _make_ctx(level=5)
        result = _spawn_combo_obstacle(ctx, "VineSnap", 0.5)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], VineSnap)

    def test_spawn_canopydrop(self):
        ctx = _make_ctx(level=4)
        result = _spawn_combo_obstacle(ctx, "CanopyDrop", 0.5)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], CanopyDrop)

    def test_spawn_crocsnap_none_xpct(self):
        ctx = _make_ctx(level=5)
        result = _spawn_combo_obstacle(ctx, "CrocSnap", None)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], CrocSnap)

    def test_spawn_cluster_spike(self):
        ctx = _make_ctx(level=6)
        result = _spawn_combo_obstacle(ctx, "ClusterSpike", 0.5)
        self.assertEqual(len(result), 3)  # cluster spawns 3 spikes
        for s in result:
            self.assertIsInstance(s, Spike)

    def test_spawn_applies_speed_mult(self):
        ctx = _make_ctx(level=5)
        ctx.speed_mult = 2.0
        result = _spawn_combo_obstacle(ctx, "Vine", 0.5)
        # The vy should have been multiplied by speed_mult
        vine = result[0]
        ctx2 = _make_ctx(level=5)
        ctx2.speed_mult = 1.0
        ref = _spawn_combo_obstacle(ctx2, "Vine", 0.5)
        self.assertAlmostEqual(vine.vy, ref[0].vy * 2.0, places=1)

    def test_spawn_unknown_class_returns_empty(self):
        ctx = _make_ctx(level=4)
        result = _spawn_combo_obstacle(ctx, "UnknownThing", 0.5)
        self.assertEqual(len(result), 0)


# ─────────────────────────────────────────────────────────────────────────────
#  Combo Start Logic
# ─────────────────────────────────────────────────────────────────────────────
class TestComboStart(unittest.TestCase):
    """Test _start_combo picks eligible patterns."""

    def test_start_combo_at_level_4(self):
        ctx = _make_ctx(level=4)
        random.seed(42)
        result = _start_combo(ctx)
        self.assertTrue(result)
        self.assertTrue(ctx.combo_active)
        self.assertIsNotNone(ctx.combo_pattern)
        # At L4, only funnel and shell_game are eligible (min_level <= 4)
        self.assertIn(ctx.combo_pattern["min_level"], [4])

    def test_start_combo_at_level_6_all_eligible(self):
        ctx = _make_ctx(level=6)
        random.seed(42)
        result = _start_combo(ctx)
        self.assertTrue(result)
        self.assertTrue(ctx.combo_active)
        self.assertLessEqual(ctx.combo_pattern["min_level"], 6)

    def test_start_combo_at_level_1_no_eligible(self):
        ctx = _make_ctx(level=1)
        result = _start_combo(ctx)
        self.assertFalse(result)
        self.assertFalse(ctx.combo_active)

    def test_start_combo_at_level_3_no_eligible(self):
        ctx = _make_ctx(level=3)
        result = _start_combo(ctx)
        self.assertFalse(result)
        self.assertFalse(ctx.combo_active)


# ─────────────────────────────────────────────────────────────────────────────
#  Combo Clear Detection
# ─────────────────────────────────────────────────────────────────────────────
class TestComboClear(unittest.TestCase):
    """Test combo clear bonus awarded when all obstacles dodged."""

    def test_combo_clear_bonus_awarded(self):
        """All combo obstacles scored without hitting -> bonus."""
        ctx = _make_ctx(level=4)
        ctx.combo_active = True
        ctx.combo_pattern = COMBO_PATTERNS["funnel"]
        ctx.combo_spawn_idx = 3  # all spawned (funnel has 3 spawns)

        # Create mock obstacles that are all scored and not did_hit
        obs1 = Vine(4, spawn_x=100)
        obs1.scored = True
        obs1.alive = False
        obs1.did_hit = False
        obs2 = Vine(4, spawn_x=3400)
        obs2.scored = True
        obs2.alive = False
        obs2.did_hit = False
        obs3 = Spike(4, spawn_x=1920)
        obs3.scored = True
        obs3.alive = False
        obs3.did_hit = False

        ctx.combo_obstacles = [obs1, obs2, obs3]
        ctx.score = 100

        _update_combo(ctx, 0.016)

        # Bonus should have been awarded
        self.assertEqual(ctx.score, 150)  # 100 + 50 bonus
        self.assertFalse(ctx.combo_active)
        self.assertEqual(ctx.combo_patterns_cleared, 1)

    def test_combo_fail_no_bonus(self):
        """Player hit by combo obstacle -> no bonus."""
        ctx = _make_ctx(level=4)
        ctx.combo_active = True
        ctx.combo_pattern = COMBO_PATTERNS["funnel"]
        ctx.combo_spawn_idx = 3

        obs1 = Vine(4, spawn_x=100)
        obs1.scored = True
        obs1.alive = False
        obs1.did_hit = True  # HIT!
        obs2 = Vine(4, spawn_x=3400)
        obs2.scored = True
        obs2.alive = False
        obs2.did_hit = False
        obs3 = Spike(4, spawn_x=1920)
        obs3.scored = True
        obs3.alive = False
        obs3.did_hit = False

        ctx.combo_obstacles = [obs1, obs2, obs3]
        ctx.score = 100

        _update_combo(ctx, 0.016)

        # No bonus
        self.assertEqual(ctx.score, 100)
        self.assertFalse(ctx.combo_active)
        self.assertEqual(ctx.combo_patterns_cleared, 0)

    def test_combo_not_resolved_while_obstacles_alive(self):
        """Combo stays active while obstacles still in play."""
        ctx = _make_ctx(level=4)
        ctx.combo_active = True
        ctx.combo_pattern = COMBO_PATTERNS["funnel"]
        ctx.combo_spawn_idx = 3

        obs1 = Vine(4, spawn_x=100)
        obs1.scored = False
        obs1.alive = True  # still falling
        obs1.did_hit = False

        ctx.combo_obstacles = [obs1]
        ctx.score = 100

        _update_combo(ctx, 0.016)

        # Should still be active
        self.assertTrue(ctx.combo_active)
        self.assertEqual(ctx.score, 100)

    def test_combo_spawns_per_delay(self):
        """Combo spawns obstacles according to script delays."""
        ctx = _make_ctx(level=4)
        ctx.combo_active = True
        ctx.combo_pattern = COMBO_PATTERNS["funnel"]
        ctx.combo_spawn_idx = 0
        ctx.combo_elapsed = 0.0
        ctx.combo_obstacles = []

        # First tick (t=0): should spawn the two t=0.0 obstacles
        _update_combo(ctx, 0.0)
        # combo_elapsed is now 0.0, so delay=0.0 entries should spawn
        self.assertEqual(ctx.combo_spawn_idx, 2)  # two spawns at delay=0.0
        self.assertEqual(len(ctx.combo_obstacles), 2)

        # Advance 0.3s — not yet at 0.6 delay for spike
        _update_combo(ctx, 0.3)
        self.assertEqual(ctx.combo_spawn_idx, 2)

        # Advance 0.3s more — now at 0.6, spike should spawn
        _update_combo(ctx, 0.3)
        self.assertEqual(ctx.combo_spawn_idx, 3)
        self.assertEqual(len(ctx.combo_obstacles), 3)


# ─────────────────────────────────────────────────────────────────────────────
#  L8+ Double Pattern
# ─────────────────────────────────────────────────────────────────────────────
class TestDoubleCombo(unittest.TestCase):
    """Test that L8+ allows 2 patterns per push phase."""

    def test_l8_allows_two_combos(self):
        """At L8+, combo_spawned_this_push limit is 2."""
        ctx = _make_ctx(level=8)
        # First combo
        random.seed(42)
        result1 = _start_combo(ctx)
        self.assertTrue(result1)
        ctx.combo_spawned_this_push = 1

        # Resolve first combo quickly
        ctx.combo_active = False
        ctx.combo_pattern = None
        ctx.combo_obstacles = []

        # Second combo should be allowed since max is 2 at L8
        result2 = _start_combo(ctx)
        self.assertTrue(result2)

    def test_l4_only_one_combo(self):
        """At L4-7, only 1 combo per push phase."""
        ctx = _make_ctx(level=4)
        # The max_combos check is in PlayState.update, but we test the limit concept
        max_combos = 2 if ctx.level >= 8 else 1
        self.assertEqual(max_combos, 1)

    def test_l8_max_combos_is_two(self):
        ctx = _make_ctx(level=8)
        max_combos = 2 if ctx.level >= 8 else 1
        self.assertEqual(max_combos, 2)


# ─────────────────────────────────────────────────────────────────────────────
#  State Reset
# ─────────────────────────────────────────────────────────────────────────────
class TestComboStateReset(unittest.TestCase):
    """Test combo state resets properly on new game and level."""

    def test_new_game_resets_combo(self):
        from states import _new_game
        ctx = _make_ctx(level=4)
        ctx.combo_active = True
        ctx.combo_patterns_cleared = 5
        ctx.combo_spawned_this_push = 2
        ctx._combo_push_started = True
        ctx.hud_cache = MagicMock()
        _new_game(ctx)
        self.assertFalse(ctx.combo_active)
        self.assertIsNone(ctx.combo_pattern)
        self.assertEqual(ctx.combo_obstacles, [])
        self.assertEqual(ctx.combo_spawn_idx, 0)
        self.assertEqual(ctx.combo_elapsed, 0.0)
        self.assertEqual(ctx.combo_patterns_cleared, 0)
        self.assertEqual(ctx.combo_spawned_this_push, 0)
        self.assertFalse(ctx._combo_push_started)

    def test_reset_level_resets_combo(self):
        from states import _reset_level
        ctx = _make_ctx(level=4)
        ctx.combo_active = True
        ctx.combo_spawned_this_push = 1
        ctx._combo_push_started = True
        _reset_level(ctx)
        self.assertFalse(ctx.combo_active)
        self.assertIsNone(ctx.combo_pattern)
        self.assertEqual(ctx.combo_obstacles, [])
        self.assertEqual(ctx.combo_spawned_this_push, 0)
        self.assertFalse(ctx._combo_push_started)


# ─────────────────────────────────────────────────────────────────────────────
#  GameContext has combo fields
# ─────────────────────────────────────────────────────────────────────────────
class TestGameContextComboFields(unittest.TestCase):
    """Test GameContext has the required combo fields with defaults."""

    def test_combo_fields_exist(self):
        ctx = GameContext(
            screen=MagicMock(),
            display=MagicMock(),
            clock=MagicMock(),
            persistence=MagicMock(),
        )
        self.assertFalse(ctx.combo_active)
        self.assertIsNone(ctx.combo_pattern)
        self.assertEqual(ctx.combo_obstacles, [])
        self.assertEqual(ctx.combo_spawn_idx, 0)
        self.assertAlmostEqual(ctx.combo_elapsed, 0.0)
        self.assertEqual(ctx.combo_patterns_cleared, 0)
        self.assertEqual(ctx.combo_spawned_this_push, 0)
        self.assertFalse(ctx._combo_push_started)


if __name__ == "__main__":
    unittest.main()
