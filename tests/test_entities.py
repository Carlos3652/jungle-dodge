"""Tests for entities.py — Player and Obstacle subclasses."""

import sys
import types
import unittest
from unittest.mock import MagicMock

# ── Stub pygame before importing game code ───────────────────────────────────
if "pygame" not in sys.modules:
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
        'colliderect': lambda self, o: True,
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
    _pg.transform.rotate = MagicMock(return_value=MagicMock(
        get_size=MagicMock(return_value=(100, 100))))
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
    _pg.K_UP = 273
    _pg.K_DOWN = 274
    _pg.K_a = 97
    _pg.K_d = 100
    _pg.K_SPACE = 32
    _pg.K_ESCAPE = 27
    _pg.K_F11 = 292
    _pg.K_TAB = 9
    _pg.K_RETURN = 13
    _pg.K_KP_ENTER = 271
    _pg.K_BACKSPACE = 8
    _pg.K_1 = 49
    _pg.K_2 = 50
    _pg.K_3 = 51
    _pg.key = types.ModuleType("pygame.key")
    _pg.key.get_pressed = MagicMock(return_value={})
    _pg.event = types.ModuleType("pygame.event")
    _pg.event.get = MagicMock(return_value=[])
    _pg.quit = MagicMock()
    sys.modules["pygame"] = _pg
    sys.modules["pygame.font"] = _pg.font
    sys.modules["pygame.display"] = _pg.display
    sys.modules["pygame.mixer"] = _pg.mixer

_pg = sys.modules["pygame"]

from entities import Player, Obstacle, Vine, Bomb, Spike, Boulder
from constants import (
    MAX_LIVES, STUN_SECS, IMMUNE_EXTRA, W, GROUND_Y, S, SX, SY,
    ROLL_DURATION, ROLL_SPEED_MULT, ROLL_IFRAME, ROLL_COOLDOWN, PLAYER_SPD,
)

# Use the pygame module that entities.py actually sees (may be real or stub)
import pygame as _game_pg


class TestPlayerInit(unittest.TestCase):
    def test_initial_lives(self):
        p = Player()
        self.assertEqual(p.lives, MAX_LIVES)

    def test_initial_position_centered(self):
        p = Player()
        self.assertEqual(p.x, W // 2)

    def test_not_stunned_initially(self):
        p = Player()
        self.assertFalse(p.is_stunned())
        self.assertFalse(p.is_hit_immune())


class TestPlayerHit(unittest.TestCase):
    def test_hit_reduces_lives(self):
        p = Player()
        initial = p.lives
        p.hit()
        self.assertEqual(p.lives, initial - 1)

    def test_hit_sets_stun(self):
        p = Player()
        p.hit()
        self.assertTrue(p.is_stunned())
        self.assertTrue(p.is_hit_immune())

    def test_hit_while_immune_does_nothing(self):
        p = Player()
        p.hit()
        lives_after_first = p.lives
        p.hit()  # should be ignored (immune)
        self.assertEqual(p.lives, lives_after_first)

    def test_lives_floor_clamp_at_zero(self):
        p = Player()
        for _ in range(MAX_LIVES + 5):
            p.immune_t = 0.0  # force non-immune
            p.stun_t = 0.0
            p.hit()
        self.assertEqual(p.lives, 0)


class TestPlayerTickTimers(unittest.TestCase):
    def test_stun_decreases(self):
        p = Player()
        p.hit()
        initial_stun = p.stun_t
        p.tick_timers(0.5)
        self.assertLess(p.stun_t, initial_stun)

    def test_immune_lasts_longer_than_stun(self):
        """CRIT-03: immune timer extends beyond stun."""
        p = Player()
        p.hit()
        self.assertGreater(p.immune_t, p.stun_t)

    def test_timers_reach_zero(self):
        p = Player()
        p.hit()
        p.tick_timers(STUN_SECS + IMMUNE_EXTRA + 1.0)
        self.assertEqual(p.stun_t, 0.0)
        self.assertEqual(p.immune_t, 0.0)


class TestPlayerUpdate(unittest.TestCase):
    def test_move_right(self):
        p = Player()
        start_x = p.x
        keys = {_game_pg.K_LEFT: False, _game_pg.K_RIGHT: True, _game_pg.K_a: False, _game_pg.K_d: False}
        p.update(0.016, keys)
        self.assertGreater(p.x, start_x)
        self.assertEqual(p.facing, 1)

    def test_move_left(self):
        p = Player()
        start_x = p.x
        keys = {_game_pg.K_LEFT: True, _game_pg.K_RIGHT: False, _game_pg.K_a: False, _game_pg.K_d: False}
        p.update(0.016, keys)
        self.assertLess(p.x, start_x)
        self.assertEqual(p.facing, -1)

    def test_both_keys_neutral(self):
        """BUG-08: both keys held = no movement."""
        p = Player()
        start_x = p.x
        keys = {_game_pg.K_LEFT: True, _game_pg.K_RIGHT: True, _game_pg.K_a: False, _game_pg.K_d: False}
        p.update(0.016, keys)
        self.assertEqual(p.x, start_x)

    def test_clamped_to_screen(self):
        p = Player()
        p.x = -1000
        keys = {_game_pg.K_LEFT: True, _game_pg.K_RIGHT: False, _game_pg.K_a: False, _game_pg.K_d: False}
        p.update(0.016, keys)
        self.assertGreaterEqual(p.x, p.PW // 2)

        p.x = W + 1000
        keys = {_game_pg.K_LEFT: False, _game_pg.K_RIGHT: True, _game_pg.K_a: False, _game_pg.K_d: False}
        p.update(0.016, keys)
        self.assertLessEqual(p.x, W - p.PW // 2)


class TestObstacleBase(unittest.TestCase):
    def test_defaults(self):
        o = Obstacle()
        self.assertTrue(o.alive)
        self.assertFalse(o.scored)
        self.assertFalse(o._pts)
        self.assertFalse(o.did_hit)

    def test_check_hit_returns_false(self):
        o = Obstacle()
        self.assertFalse(o.check_hit(Player()))


class TestVine(unittest.TestCase):
    def test_falls_down(self):
        v = Vine(level=1, spawn_x=400)
        start_y = v.y
        v.update(0.1, Player())
        self.assertGreater(v.y, start_y)

    def test_lands_and_dies(self):
        v = Vine(level=1, spawn_x=400)
        # Fast-forward until landed
        for _ in range(500):
            v.update(0.05, Player())
        # Should have landed and eventually died
        self.assertTrue(v.landed or not v.alive)


class TestBomb(unittest.TestCase):
    def test_falls_and_explodes(self):
        b = Bomb(level=1, spawn_x=400)
        for _ in range(500):
            b.update(0.05, Player())
            if b.exploded:
                break
        self.assertTrue(b.exploded)

    def test_exploded_bomb_dies(self):
        b = Bomb(level=1, spawn_x=400)
        for _ in range(1000):
            b.update(0.05, Player())
            if not b.alive:
                break
        self.assertFalse(b.alive)


class TestSpike(unittest.TestCase):
    def test_falls_and_dies(self):
        s = Spike(level=1, spawn_x=400)
        for _ in range(500):
            s.update(0.05, Player())
            if not s.alive:
                break
        self.assertFalse(s.alive)
        self.assertTrue(s.scored)


class TestBoulder(unittest.TestCase):
    def test_falls_and_rolls(self):
        b = Boulder(level=1, spawn_x=400)
        for _ in range(500):
            b.update(0.05, Player())
            if b.rolling:
                break
        self.assertTrue(b.rolling)

    def test_boulder_eventually_dies(self):
        b = Boulder(level=1, spawn_x=400)
        for _ in range(2000):
            b.update(0.05, Player())
            if not b.alive:
                break
        self.assertFalse(b.alive)

    def test_boulder_bounces_at_edges(self):
        b = Boulder(level=1, spawn_x=400)
        # Force rolling near left edge
        b.rolling = True
        b.y = float(GROUND_Y - b.R)
        b.x = float(b.R - 1)
        b.roll_dir = -1
        b.update(0.05, Player())
        self.assertEqual(b.roll_dir, 1)


class TestPlayerRoll(unittest.TestCase):
    """Tests for the side roll mechanic (jd-07)."""

    def _neutral_keys(self):
        return {_game_pg.K_LEFT: False, _game_pg.K_RIGHT: False,
                _game_pg.K_a: False, _game_pg.K_d: False}

    def test_roll_grants_iframes(self):
        """start_roll() must grant i-frames (immune_t >= ROLL_IFRAME)."""
        p = Player()
        p.facing = 1
        self.assertTrue(p.can_roll())
        p.start_roll()
        self.assertTrue(p.rolling)
        self.assertTrue(p.is_hit_immune())
        self.assertGreaterEqual(p.immune_t, ROLL_IFRAME)

    def test_iframes_expire_before_roll_ends(self):
        """I-frames last 0.25s, roll lasts 0.4s — verify i-frames end first."""
        p = Player()
        p.start_roll()
        # Advance past i-frame window but not roll duration
        p.tick_timers(ROLL_IFRAME + 0.01)
        self.assertFalse(p.is_hit_immune())
        self.assertTrue(p.rolling)

    def test_roll_cooldown_prevents_spam(self):
        """After rolling, player cannot roll again until cooldown expires."""
        p = Player()
        p.start_roll()
        # End the roll
        p.tick_timers(ROLL_DURATION + 0.01)
        self.assertFalse(p.rolling)
        # Cooldown should still be active
        self.assertGreater(p.roll_cd, 0)
        self.assertFalse(p.can_roll())
        # Second start_roll should be no-op
        p.start_roll()
        self.assertFalse(p.rolling)

    def test_roll_available_after_cooldown(self):
        """After full cooldown, player can roll again."""
        p = Player()
        p.start_roll()
        p.tick_timers(ROLL_DURATION + ROLL_COOLDOWN + 0.01)
        self.assertFalse(p.rolling)
        self.assertLessEqual(p.roll_cd, 0)
        self.assertTrue(p.can_roll())

    def test_roll_speed_multiplied(self):
        """During roll, player moves at ROLL_SPEED_MULT × normal speed."""
        p = Player()
        dt = 0.016
        start_x = p.x
        p.facing = 1

        # Normal movement
        keys = {_game_pg.K_LEFT: False, _game_pg.K_RIGHT: True,
                _game_pg.K_a: False, _game_pg.K_d: False}
        p.update(dt, keys)
        normal_dx = p.x - start_x

        # Reset and do roll movement
        p2 = Player()
        p2.facing = 1
        start_x2 = p2.x
        p2.start_roll()
        p2.update(dt, self._neutral_keys())
        roll_dx = p2.x - start_x2

        # Roll should move ROLL_SPEED_MULT times farther
        self.assertAlmostEqual(roll_dx / normal_dx, ROLL_SPEED_MULT, places=1)

    def test_roll_locks_direction(self):
        """Roll direction is locked to facing at roll start, ignores input."""
        p = Player()
        p.facing = -1  # facing left
        p.start_roll()
        self.assertEqual(p.roll_dir, -1)
        # Even with right key pressed, should move left
        keys = {_game_pg.K_LEFT: False, _game_pg.K_RIGHT: True,
                _game_pg.K_a: False, _game_pg.K_d: False}
        start_x = p.x
        p.update(0.016, keys)
        self.assertLess(p.x, start_x)

    def test_cannot_roll_while_stunned(self):
        """Player cannot start a roll while stunned."""
        p = Player()
        p.hit()
        self.assertTrue(p.is_stunned())
        self.assertFalse(p.can_roll())
        p.start_roll()
        self.assertFalse(p.rolling)

    def test_cannot_roll_while_already_rolling(self):
        """Player cannot start another roll mid-roll."""
        p = Player()
        p.start_roll()
        self.assertTrue(p.rolling)
        # Attempting to roll again should be a no-op
        old_roll_t = p.roll_t
        p.start_roll()
        self.assertEqual(p.roll_t, old_roll_t)

    def test_roll_ends_after_duration(self):
        """Rolling state ends when roll_t reaches zero."""
        p = Player()
        p.start_roll()
        self.assertTrue(p.rolling)
        p.tick_timers(ROLL_DURATION + 0.01)
        self.assertFalse(p.rolling)

    def test_hit_blocked_during_roll_iframes(self):
        """Player cannot be hit during roll i-frame window."""
        p = Player()
        initial_lives = p.lives
        p.start_roll()
        p.hit()  # should be blocked by i-frames
        self.assertEqual(p.lives, initial_lives)

    def test_hit_possible_after_roll_iframes(self):
        """Player CAN be hit after i-frame window expires (roll still active)."""
        p = Player()
        initial_lives = p.lives
        p.start_roll()
        # Advance past i-frames but roll still active
        p.tick_timers(ROLL_IFRAME + 0.01)
        self.assertTrue(p.rolling)
        self.assertFalse(p.is_hit_immune())
        p.hit()
        self.assertEqual(p.lives, initial_lives - 1)


if __name__ == "__main__":
    unittest.main()
