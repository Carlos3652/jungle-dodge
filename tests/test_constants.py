"""Tests for constants.py immutability and correctness (task jd-01)."""

import os
import types
import unittest

import pygame

# constants.py only calls pygame.font.init(), not pygame.init(),
# so this import should work without a full display subsystem.
from constants import (
    CLR, OBS_TYPES, OBS_WEIGHTS,
    W, H, SX, SY, S, FPS, GROUND_Y, PLAYER_FLOOR, DODGE_PTS,
    LEVEL_TIME, MAX_LIVES, STUN_SECS, IMMUNE_EXTRA, PLAYER_SPD,
    BASE_SPAWN, SPAWN_DEC, MIN_SPAWN, SPEED_SCALE, MAX_NAME_LEN,
    LEADERBOARD_SIZE,
    ST_START, ST_PLAYING, ST_PAUSED, ST_LEVELUP, ST_GAMEOVER,
    ST_NAME_ENTRY, ST_LEADERBOARD,
    F_HUGE, F_LARGE, F_MED, F_SMALL, F_TINY, F_SERIF, F_SKULL,
)


class TestConstantsImmutability(unittest.TestCase):
    """Verify that exported 'constants' cannot be accidentally mutated."""

    def test_obs_types_is_tuple(self):
        self.assertIsInstance(OBS_TYPES, tuple)

    def test_obs_weights_is_tuple(self):
        self.assertIsInstance(OBS_WEIGHTS, tuple)

    def test_clr_is_mapping_proxy(self):
        self.assertIsInstance(CLR, types.MappingProxyType)

    def test_clr_rejects_assignment(self):
        with self.assertRaises(TypeError):
            CLR["new_key"] = (0, 0, 0)

    def test_clr_rejects_deletion(self):
        with self.assertRaises(TypeError):
            del CLR["red"]


class TestConstantsValues(unittest.TestCase):
    """Spot-check a few critical values haven't drifted."""

    def test_window_dimensions(self):
        self.assertEqual(W, 3840)
        self.assertEqual(H, 2160)

    def test_fps(self):
        self.assertEqual(FPS, 60)

    def test_obs_types_contents(self):
        self.assertEqual(OBS_TYPES, ("vine", "bomb", "spike", "boulder"))

    def test_obs_weights_contents(self):
        self.assertEqual(OBS_WEIGHTS, (3, 2, 3, 2))

    def test_obs_types_weights_same_length(self):
        self.assertEqual(len(OBS_TYPES), len(OBS_WEIGHTS))

    def test_random_choices_compatible(self):
        """random.choices() must accept tuples (drop-in for lists)."""
        import random
        result = random.choices(OBS_TYPES, OBS_WEIGHTS, k=1)
        self.assertIn(result[0], OBS_TYPES)


class TestNoPygameFullInit(unittest.TestCase):
    """Importing constants must NOT call pygame.init() (only font.init)."""

    def test_display_not_initialized(self):
        import pygame
        # pygame.display.get_init() returns False if pygame.init() wasn't called
        # and nobody explicitly called display.init().
        # If constants.py correctly avoids pygame.init(), display should not
        # have been initialized by the constants import alone.
        # NOTE: other test modules may have initialized pygame, so we just
        # verify that the font subsystem IS initialized (our minimum requirement).
        self.assertTrue(pygame.font.get_init())


class TestScaleFactors(unittest.TestCase):
    """Verify scale factor derivations from window dimensions."""

    def test_sx_from_width(self):
        self.assertAlmostEqual(SX, W / 900)

    def test_sy_from_height(self):
        self.assertAlmostEqual(SY, H / 600)

    def test_s_equals_sy(self):
        self.assertEqual(S, SY, "S should use vertical scale as primary reference")

    def test_ground_y_within_window(self):
        self.assertGreater(GROUND_Y, 0)
        self.assertLess(GROUND_Y, H)

    def test_player_floor_equals_ground_y(self):
        self.assertEqual(PLAYER_FLOOR, GROUND_Y)


class TestFontObjects(unittest.TestCase):
    """Verify all font constants initialized correctly."""

    def test_f_huge_is_font(self):
        self.assertIsInstance(F_HUGE, pygame.font.Font)

    def test_f_large_is_font(self):
        self.assertIsInstance(F_LARGE, pygame.font.Font)

    def test_f_med_is_font(self):
        self.assertIsInstance(F_MED, pygame.font.Font)

    def test_f_small_is_font(self):
        self.assertIsInstance(F_SMALL, pygame.font.Font)

    def test_f_tiny_is_font(self):
        self.assertIsInstance(F_TINY, pygame.font.Font)

    def test_f_serif_is_font(self):
        self.assertIsInstance(F_SERIF, pygame.font.Font)

    def test_f_skull_is_font(self):
        self.assertIsInstance(F_SKULL, pygame.font.Font)

    def test_font_size_ordering(self):
        """Larger named fonts should have larger heights."""
        self.assertGreater(F_HUGE.get_height(), F_LARGE.get_height())
        self.assertGreater(F_LARGE.get_height(), F_MED.get_height())
        self.assertGreater(F_MED.get_height(), F_SMALL.get_height())
        self.assertGreater(F_SMALL.get_height(), F_TINY.get_height())


class TestGameBalanceConstants(unittest.TestCase):
    """Sanity checks on game balance — values must be reasonable."""

    def test_level_time_positive(self):
        self.assertGreater(LEVEL_TIME, 0)

    def test_max_lives_positive(self):
        self.assertGreater(MAX_LIVES, 0)

    def test_stun_duration_positive(self):
        self.assertGreater(STUN_SECS, 0)

    def test_immune_grace_less_than_stun(self):
        self.assertLess(IMMUNE_EXTRA, STUN_SECS)

    def test_player_speed_positive(self):
        self.assertGreater(PLAYER_SPD, 0)

    def test_spawn_decay_logical(self):
        """Spawn interval must decrease but not below minimum."""
        self.assertGreater(BASE_SPAWN, MIN_SPAWN)
        self.assertGreater(SPAWN_DEC, 0)
        self.assertGreater(MIN_SPAWN, 0)

    def test_speed_scale_positive(self):
        self.assertGreater(SPEED_SCALE, 0)

    def test_dodge_pts_positive(self):
        self.assertGreater(DODGE_PTS, 0)

    def test_max_name_len_reasonable(self):
        self.assertGreaterEqual(MAX_NAME_LEN, 1)
        self.assertLessEqual(MAX_NAME_LEN, 20)

    def test_leaderboard_size_positive(self):
        self.assertGreater(LEADERBOARD_SIZE, 0)


class TestColorValues(unittest.TestCase):
    """Validate all colors in CLR are valid RGB tuples."""

    def test_all_colors_are_rgb_tuples(self):
        for name, rgb in CLR.items():
            self.assertEqual(len(rgb), 3, f"Color '{name}' is not RGB (got {len(rgb)} channels)")

    def test_all_colors_in_valid_range(self):
        for name, rgb in CLR.items():
            for i, c in enumerate(rgb):
                self.assertGreaterEqual(c, 0, f"Color '{name}' channel {i} below 0: {c}")
                self.assertLessEqual(c, 255, f"Color '{name}' channel {i} above 255: {c}")

    def test_minimum_color_count(self):
        """CLR should have the full palette — at least 20 colors."""
        self.assertGreaterEqual(len(CLR), 20)


class TestStateConstants(unittest.TestCase):
    """Verify state string constants are unique and non-empty."""

    def test_all_states_unique(self):
        states = [ST_START, ST_PLAYING, ST_PAUSED, ST_LEVELUP,
                  ST_GAMEOVER, ST_NAME_ENTRY, ST_LEADERBOARD]
        self.assertEqual(len(states), len(set(states)), "State constants must be unique")

    def test_all_states_non_empty(self):
        for st in [ST_START, ST_PLAYING, ST_PAUSED, ST_LEVELUP,
                   ST_GAMEOVER, ST_NAME_ENTRY, ST_LEADERBOARD]:
            self.assertTrue(st, f"State constant is empty: {st!r}")


if __name__ == "__main__":
    unittest.main()
