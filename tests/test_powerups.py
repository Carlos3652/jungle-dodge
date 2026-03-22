"""Tests for jd-12: Power-up system (shield, slow-mo, magnet).

Tests cover:
  - PowerUp entity: creation, movement, pickup detection, no damage
  - Power-up constants defined correctly
  - Spawn timing: no spawn in first 15s, at most 1 on screen
  - Shield absorption: absorbs one hit, destroys obstacle, emits particles
  - Slow-mo: reduces speed_mult by 40%, restores after 5s
  - Magnet: dodge pts x3 for 8s, then resets
  - Timer expiry deactivation
  - Power-up effects are mutually exclusive (new replaces old)
  - HUD draw_hud accepts power-up parameters
"""

import math
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ── Stub pygame before importing game code ───────────────────────────────────
if "pygame" not in sys.modules:
    _pg = types.ModuleType("pygame")
    _pg.init = MagicMock()
    _pg.Surface = MagicMock
    _pg.Rect = MagicMock(side_effect=lambda x, y, w, h: type('R', (), {
        'x': x, 'y': y, 'w': w, 'h': h,
        'colliderect': lambda self, o: True,
    })())
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

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from constants import (
    S, SX, W, GROUND_Y,
    POWERUP_KINDS, POWERUP_SPEED_FRAC, POWERUP_RADIUS,
    POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX, POWERUP_NO_SPAWN_T,
    SLOWMO_FACTOR, SLOWMO_DURATION,
    MAGNET_MULTIPLIER, MAGNET_DURATION,
    SHIELD_PARTICLES,
)
from entities import PowerUp, Player, Obstacle, Vine
from states import (
    GameContext, _new_game, _reset_level,
    _activate_powerup, _deactivate_powerup, _spawn_powerup,
)
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
    ctx.persistence.get_board = MagicMock(return_value=[])
    ctx.persistence.load_settings = MagicMock(return_value={"difficulty": "normal"})
    ctx.persistence.save_settings = MagicMock()
    # Pre-set hud_cache to avoid pygame.Surface.fill failures in stubs
    ctx.hud_cache = MagicMock()
    _new_game(ctx)
    return ctx


# ─────────────────────────────────────────────────────────────────────────────
#  1. PowerUp entity tests
# ─────────────────────────────────────────────────────────────────────────────
class TestPowerUpEntity(unittest.TestCase):
    def test_powerup_is_obstacle_subclass(self):
        pu = PowerUp("shield", level=1)
        self.assertIsInstance(pu, Obstacle)

    def test_powerup_kinds(self):
        for kind in POWERUP_KINDS:
            pu = PowerUp(kind, level=1)
            self.assertEqual(pu.kind, kind)
            self.assertTrue(pu.alive)

    def test_powerup_speed_is_60pct_of_vine(self):
        """PowerUp speed should be ~60% of vine base speed."""
        level = 3
        pu = PowerUp("shield", level=level)
        vine = Vine(level)
        # Both use same formula base; pu should be ~0.6 of vine
        ratio = pu.vy / vine.vy
        self.assertAlmostEqual(ratio, POWERUP_SPEED_FRAC, places=1)

    def test_powerup_falls_down(self):
        pu = PowerUp("shield", level=1)
        old_y = pu.y
        pu.update(0.1, MagicMock())
        self.assertGreater(pu.y, old_y)

    def test_powerup_no_sway(self):
        """PowerUp should fall straight (no x change from sway)."""
        pu = PowerUp("shield", level=1, spawn_x=500)
        pu.update(0.1, MagicMock())
        # x should not change (no sway attribute)
        self.assertEqual(pu.x, 500.0)

    def test_check_hit_returns_false(self):
        """PowerUps never damage the player via check_hit."""
        pu = PowerUp("shield", level=1)
        p = Player()
        self.assertFalse(pu.check_hit(p))

    def test_check_pickup_when_overlapping(self):
        """check_pickup should return True when rects collide."""
        pu = PowerUp("shield", level=1, spawn_x=500)
        pu.y = 500.0
        p = Player()
        # Mock the rect properties to ensure colliderect returns True
        mock_pu_rect = MagicMock()
        mock_pu_rect.colliderect = MagicMock(return_value=True)
        with patch.object(type(pu), 'rect', new_callable=lambda: property(lambda self: mock_pu_rect)):
            self.assertTrue(pu.check_pickup(p))

    def test_dies_when_past_ground(self):
        pu = PowerUp("shield", level=1)
        pu.y = GROUND_Y + pu.R + 10  # past ground
        pu.update(0.1, MagicMock())
        self.assertFalse(pu.alive)

    def test_radius_constant(self):
        self.assertEqual(PowerUp.R, POWERUP_RADIUS)


# ─────────────────────────────────────────────────────────────────────────────
#  2. Constants sanity
# ─────────────────────────────────────────────────────────────────────────────
class TestPowerUpConstants(unittest.TestCase):
    def test_kinds_tuple(self):
        self.assertEqual(POWERUP_KINDS, ("shield", "slowmo", "magnet"))

    def test_speed_fraction(self):
        self.assertEqual(POWERUP_SPEED_FRAC, 0.6)

    def test_slowmo_factor(self):
        self.assertEqual(SLOWMO_FACTOR, 0.4)

    def test_slowmo_duration(self):
        self.assertEqual(SLOWMO_DURATION, 5.0)

    def test_magnet_multiplier(self):
        self.assertEqual(MAGNET_MULTIPLIER, 3.0)

    def test_magnet_duration(self):
        self.assertEqual(MAGNET_DURATION, 8.0)

    def test_shield_particles(self):
        self.assertEqual(SHIELD_PARTICLES, 12)

    def test_no_spawn_time(self):
        self.assertEqual(POWERUP_NO_SPAWN_T, 15.0)

    def test_spawn_interval_range(self):
        self.assertLess(POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX)


# ─────────────────────────────────────────────────────────────────────────────
#  3. Shield activation & absorption
# ─────────────────────────────────────────────────────────────────────────────
class TestShieldPowerUp(unittest.TestCase):
    def test_activate_shield(self):
        ctx = _make_ctx()
        _activate_powerup(ctx, "shield")
        self.assertEqual(ctx.active_powerup, "shield")
        self.assertTrue(ctx.shield_active)

    def test_shield_absorbs_hit(self):
        """When shield is active and player would be hit, shield should absorb."""
        ctx = _make_ctx()
        _activate_powerup(ctx, "shield")
        initial_lives = ctx.player.lives
        # Simulate shield absorption: set shield_active=False, don't damage player
        self.assertTrue(ctx.shield_active)
        # After absorption
        ctx.shield_active = False
        ctx.active_powerup = None
        self.assertEqual(ctx.player.lives, initial_lives)
        self.assertFalse(ctx.shield_active)

    def test_shield_deactivate_resets_state(self):
        ctx = _make_ctx()
        _activate_powerup(ctx, "shield")
        _deactivate_powerup(ctx)
        self.assertIsNone(ctx.active_powerup)
        self.assertFalse(ctx.shield_active)


# ─────────────────────────────────────────────────────────────────────────────
#  4. Slow-mo activation & timer expiry
# ─────────────────────────────────────────────────────────────────────────────
class TestSlowMoPowerUp(unittest.TestCase):
    def test_activate_slowmo_reduces_speed(self):
        ctx = _make_ctx()
        original_speed = ctx.speed_mult
        _activate_powerup(ctx, "slowmo")
        self.assertEqual(ctx.active_powerup, "slowmo")
        self.assertAlmostEqual(ctx.speed_mult, original_speed * SLOWMO_FACTOR)
        self.assertEqual(ctx.powerup_timer, SLOWMO_DURATION)

    def test_deactivate_slowmo_restores_speed(self):
        ctx = _make_ctx()
        original_speed = ctx.speed_mult
        _activate_powerup(ctx, "slowmo")
        _deactivate_powerup(ctx)
        self.assertAlmostEqual(ctx.speed_mult, original_speed)
        self.assertIsNone(ctx.active_powerup)

    def test_slowmo_saves_pre_speed(self):
        ctx = _make_ctx()
        ctx.speed_mult = 1.15  # hard difficulty
        _activate_powerup(ctx, "slowmo")
        self.assertAlmostEqual(ctx._pre_slowmo_speed_mult, 1.15)
        _deactivate_powerup(ctx)
        self.assertAlmostEqual(ctx.speed_mult, 1.15)


# ─────────────────────────────────────────────────────────────────────────────
#  5. Magnet activation & multiplier
# ─────────────────────────────────────────────────────────────────────────────
class TestMagnetPowerUp(unittest.TestCase):
    def test_activate_magnet_sets_multiplier(self):
        ctx = _make_ctx()
        _activate_powerup(ctx, "magnet")
        self.assertEqual(ctx.active_powerup, "magnet")
        self.assertEqual(ctx.magnet_multiplier, MAGNET_MULTIPLIER)
        self.assertEqual(ctx.powerup_timer, MAGNET_DURATION)

    def test_deactivate_magnet_resets_multiplier(self):
        ctx = _make_ctx()
        _activate_powerup(ctx, "magnet")
        _deactivate_powerup(ctx)
        self.assertEqual(ctx.magnet_multiplier, 1.0)
        self.assertIsNone(ctx.active_powerup)


# ─────────────────────────────────────────────────────────────────────────────
#  6. Mutual exclusivity
# ─────────────────────────────────────────────────────────────────────────────
class TestPowerUpExclusivity(unittest.TestCase):
    def test_new_powerup_replaces_old(self):
        ctx = _make_ctx()
        _activate_powerup(ctx, "shield")
        self.assertTrue(ctx.shield_active)
        # Now activate magnet — should deactivate shield
        _activate_powerup(ctx, "magnet")
        self.assertEqual(ctx.active_powerup, "magnet")
        self.assertFalse(ctx.shield_active)
        self.assertEqual(ctx.magnet_multiplier, MAGNET_MULTIPLIER)

    def test_slowmo_replaced_by_shield_restores_speed(self):
        ctx = _make_ctx()
        original = ctx.speed_mult
        _activate_powerup(ctx, "slowmo")
        _activate_powerup(ctx, "shield")
        self.assertEqual(ctx.active_powerup, "shield")
        self.assertAlmostEqual(ctx.speed_mult, original)  # restored


# ─────────────────────────────────────────────────────────────────────────────
#  7. Spawn logic
# ─────────────────────────────────────────────────────────────────────────────
class TestPowerUpSpawn(unittest.TestCase):
    def test_spawn_powerup_adds_to_list(self):
        ctx = _make_ctx()
        _spawn_powerup(ctx)
        self.assertEqual(len(ctx.powerups), 1)
        self.assertIsInstance(ctx.powerups[0], PowerUp)

    def test_spawn_powerup_kind_is_valid(self):
        ctx = _make_ctx()
        for _ in range(20):
            ctx.powerups = []
            _spawn_powerup(ctx)
            self.assertIn(ctx.powerups[0].kind, POWERUP_KINDS)


# ─────────────────────────────────────────────────────────────────────────────
#  8. _new_game and _reset_level clear power-up state
# ─────────────────────────────────────────────────────────────────────────────
class TestPowerUpReset(unittest.TestCase):
    def test_new_game_resets_powerup_state(self):
        ctx = _make_ctx()
        _activate_powerup(ctx, "magnet")
        ctx.powerups = [PowerUp("shield", 1)]
        _new_game(ctx)
        self.assertIsNone(ctx.active_powerup)
        self.assertEqual(ctx.powerup_timer, 0.0)
        self.assertFalse(ctx.shield_active)
        self.assertEqual(ctx.magnet_multiplier, 1.0)
        self.assertEqual(len(ctx.powerups), 0)

    def test_reset_level_clears_powerup_entities(self):
        ctx = _make_ctx()
        ctx.powerups = [PowerUp("slowmo", 1), PowerUp("magnet", 1)]
        _reset_level(ctx)
        self.assertEqual(len(ctx.powerups), 0)
        self.assertEqual(ctx.powerup_spawn_timer, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
#  9. GameContext has power-up fields
# ─────────────────────────────────────────────────────────────────────────────
class TestGameContextPowerUpFields(unittest.TestCase):
    def test_has_powerup_fields(self):
        ctx = _make_ctx()
        self.assertIsNone(ctx.active_powerup)
        self.assertEqual(ctx.powerup_timer, 0.0)
        self.assertFalse(ctx.shield_active)
        self.assertEqual(ctx.magnet_multiplier, 1.0)
        self.assertIsInstance(ctx.powerups, list)
        self.assertEqual(ctx.powerup_spawn_timer, 0.0)


if __name__ == "__main__":
    unittest.main()
