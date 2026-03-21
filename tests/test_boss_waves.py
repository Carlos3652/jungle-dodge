"""Tests for boss wave system and L10+ personality upgrades (jd-15)."""

import sys
import types
import math
import unittest
from unittest.mock import MagicMock

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

from boss_data import get_boss_wave, is_boss_level, BOSS_WAVES, get_mini_boss
from entities import Player, Spike, Vine, Bomb, Boulder
from constants import W, GROUND_Y, S, SX, SY


class TestBossWaveDetection(unittest.TestCase):
    """Test boss wave level detection."""

    def test_level_5_is_boss(self):
        self.assertTrue(is_boss_level(5))

    def test_level_10_is_boss(self):
        self.assertTrue(is_boss_level(10))

    def test_level_15_is_boss(self):
        self.assertTrue(is_boss_level(15))

    def test_level_20_is_mini_boss(self):
        self.assertTrue(is_boss_level(20))

    def test_level_25_is_mini_boss(self):
        self.assertTrue(is_boss_level(25))

    def test_level_3_not_boss(self):
        self.assertFalse(is_boss_level(3))

    def test_level_7_not_boss(self):
        self.assertFalse(is_boss_level(7))

    def test_level_12_not_boss(self):
        self.assertFalse(is_boss_level(12))

    def test_level_16_not_boss(self):
        """16 is >= 16 but 16 % 5 != 0"""
        self.assertFalse(is_boss_level(16))

    def test_level_1_not_boss(self):
        self.assertFalse(is_boss_level(1))


class TestBossWaveData(unittest.TestCase):
    """Test boss wave script data integrity."""

    def test_stampede_exists(self):
        boss = get_boss_wave(5)
        self.assertIsNotNone(boss)
        self.assertEqual(boss["name"], "STAMPEDE")
        self.assertEqual(boss["duration"], 20)
        self.assertEqual(boss["reward"], 500)

    def test_predator_run_exists(self):
        boss = get_boss_wave(10)
        self.assertIsNotNone(boss)
        self.assertEqual(boss["name"], "PREDATOR RUN")
        self.assertEqual(boss["duration"], 25)
        self.assertEqual(boss["reward"], 750)

    def test_everything_exists(self):
        boss = get_boss_wave(15)
        self.assertIsNotNone(boss)
        self.assertEqual(boss["name"], "EVERYTHING")
        self.assertEqual(boss["duration"], 30)
        self.assertEqual(boss["reward"], 1000)

    def test_scripts_have_entries(self):
        for level in [5, 10, 15]:
            boss = get_boss_wave(level)
            self.assertGreater(len(boss["script"]), 10,
                               f"Boss L{level} script too short")

    def test_script_entries_are_sorted_by_time(self):
        for level in [5, 10, 15]:
            boss = get_boss_wave(level)
            times = [entry[0] for entry in boss["script"]]
            self.assertEqual(times, sorted(times),
                             f"Boss L{level} script not sorted by time")

    def test_script_class_names_valid(self):
        valid_classes = {"Vine", "Bomb", "Spike", "Boulder"}
        for level in [5, 10, 15]:
            boss = get_boss_wave(level)
            for delay, cls_name, x_pct in boss["script"]:
                self.assertIn(cls_name, valid_classes,
                              f"Invalid class {cls_name} in L{level} script")

    def test_script_x_pct_in_range(self):
        for level in [5, 10, 15]:
            boss = get_boss_wave(level)
            for delay, cls_name, x_pct in boss["script"]:
                self.assertGreaterEqual(x_pct, 0.0)
                self.assertLessEqual(x_pct, 1.0)

    def test_script_times_within_duration(self):
        for level in [5, 10, 15]:
            boss = get_boss_wave(level)
            for delay, cls_name, x_pct in boss["script"]:
                self.assertLessEqual(delay, boss["duration"],
                                     f"Script entry at t={delay} exceeds duration {boss['duration']}")


class TestMiniBoss(unittest.TestCase):
    """Test mini-boss generation for L16+."""

    def test_mini_boss_at_level_20(self):
        boss = get_boss_wave(20)
        self.assertIsNotNone(boss)
        self.assertEqual(boss["duration"], 15)
        self.assertEqual(boss["reward"], 300)
        self.assertIn("MINI-BOSS", boss["name"])

    def test_mini_boss_deterministic(self):
        b1 = get_mini_boss(20)
        b2 = get_mini_boss(20)
        self.assertEqual(b1["script"], b2["script"])

    def test_mini_boss_different_per_level(self):
        b20 = get_mini_boss(20)
        b25 = get_mini_boss(25)
        self.assertNotEqual(b20["script"], b25["script"])

    def test_mini_boss_has_15_entries(self):
        boss = get_mini_boss(20)
        self.assertEqual(len(boss["script"]), 15)


class TestBossReward(unittest.TestCase):
    """Test boss reward values."""

    def test_level_5_reward(self):
        self.assertEqual(get_boss_wave(5)["reward"], 500)

    def test_level_10_reward(self):
        self.assertEqual(get_boss_wave(10)["reward"], 750)

    def test_level_15_reward(self):
        self.assertEqual(get_boss_wave(15)["reward"], 1000)

    def test_mini_boss_reward(self):
        self.assertEqual(get_boss_wave(20)["reward"], 300)


class TestWobbleSpike(unittest.TestCase):
    """Test wobble functionality on Spike class."""

    def test_spike_has_wobble_attrs(self):
        s = Spike(level=10, spawn_x=1000)
        self.assertFalse(s.wobble)
        self.assertEqual(s.wobble_amp, 0.0)
        self.assertEqual(s.wobble_freq, 0.0)

    def test_wobble_disabled_no_x_change(self):
        s = Spike(level=10, spawn_x=1000)
        s.wobble = False
        initial_x = s.x
        s.update(0.05, Player())
        # X should not change (no wobble, no sway)
        self.assertEqual(s.x, initial_x)

    def test_wobble_enabled_causes_x_oscillation(self):
        s = Spike(level=10, spawn_x=1000)
        s.wobble = True
        s.wobble_amp = 100.0
        s.wobble_freq = 10.0
        initial_x = s.x
        # Run several frames to accumulate wobble
        x_values = []
        for _ in range(20):
            s.update(0.02, Player())
            x_values.append(s.x)
        # X should have varied from initial position
        x_spread = max(x_values) - min(x_values)
        self.assertGreater(x_spread, 0, "Wobble should cause X variation")

    def test_wobble_stays_in_bounds(self):
        s = Spike(level=10, spawn_x=50)  # near left edge
        s.wobble = True
        s.wobble_amp = 500.0
        s.wobble_freq = 20.0
        for _ in range(100):
            s.update(0.02, Player())
            if not s.alive:
                break
            self.assertGreaterEqual(s.x, float(s.SW))
            self.assertLessEqual(s.x, float(W - s.SW))


class TestBossIntroStateTiming(unittest.TestCase):
    """Test BossIntroState duration and transition."""

    def test_boss_intro_state_exists(self):
        from states import BossIntroState
        bis = BossIntroState("TEST BOSS")
        self.assertEqual(bis._boss_name, "TEST BOSS")

    def test_boss_intro_duration(self):
        from states import BossIntroState
        self.assertAlmostEqual(BossIntroState.DURATION, 3.5)


if __name__ == "__main__":
    unittest.main()
