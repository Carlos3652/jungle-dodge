"""
Tests for jd-18: Jungle theme refresh (parallax, palette, FX)

Verifies:
- Updated theme color values are valid RGB tuples
- Specific key values match the new spec (warmer palette)
- build_background() returns a Surface of the correct size
- build_background() completes without errors with the jungle theme
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from themes import THEMES, get_color, get_theme, REQUIRED_KEYS
from hud import build_background
from constants import W, H


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_rgb_tuple(v):
    """Return True if v is a 3-element tuple of ints in [0, 255]."""
    return (
        isinstance(v, tuple)
        and len(v) == 3
        and all(isinstance(c, int) and 0 <= c <= 255 for c in v)
    )


# ── Theme color validity ──────────────────────────────────────────────────────

class TestJungleThemeColors:

    def test_all_color_keys_are_valid_rgb(self):
        """Every colour key in the jungle theme must be a valid (R, G, B) tuple."""
        theme = get_theme("jungle")
        color_keys = REQUIRED_KEYS - {"name", "hud_style", "transition_style",
                                       "audio_prefix"}
        for key in color_keys:
            val = theme.get(key)
            assert val is not None, f"Key '{key}' missing from jungle theme"
            assert _is_rgb_tuple(val), (
                f"Key '{key}' value {val!r} is not a valid RGB tuple"
            )

    def test_no_extra_or_missing_keys(self):
        """Jungle theme must define exactly the REQUIRED_KEYS (no additions/removals)."""
        theme = THEMES["jungle"]
        defined = set(theme.keys())
        assert defined == REQUIRED_KEYS, (
            f"Key mismatch — extra: {defined - REQUIRED_KEYS}, "
            f"missing: {REQUIRED_KEYS - defined}"
        )


class TestJungleThemePaletteValues:
    """Verify the specific updated values from the spec."""

    def setup_method(self):
        self.t = get_theme("jungle")

    def test_sky_top_updated(self):
        assert self.t["sky_top"] == (4, 10, 6), (
            f"sky_top expected (4, 10, 6), got {self.t['sky_top']}"
        )

    def test_sky_horizon_updated(self):
        assert self.t["sky_horizon"] == (10, 25, 10), (
            f"sky_horizon expected (10, 25, 10), got {self.t['sky_horizon']}"
        )

    def test_ground_base_updated(self):
        assert self.t["ground_base"] == (55, 35, 18), (
            f"ground_base expected (55, 35, 18), got {self.t['ground_base']}"
        )

    def test_ground_edge_updated(self):
        assert self.t["ground_edge"] == (75, 50, 25), (
            f"ground_edge expected (75, 50, 25), got {self.t['ground_edge']}"
        )

    def test_grass_main_updated(self):
        assert self.t["grass_main"] == (38, 85, 28), (
            f"grass_main expected (38, 85, 28), got {self.t['grass_main']}"
        )

    def test_grass_highlight_updated(self):
        assert self.t["grass_highlight"] == (55, 115, 35), (
            f"grass_highlight expected (55, 115, 35), got {self.t['grass_highlight']}"
        )

    def test_char_jacket_warmer(self):
        assert self.t["char_jacket"] == (185, 155, 90), (
            f"char_jacket expected (185, 155, 90), got {self.t['char_jacket']}"
        )

    def test_char_hat_updated(self):
        assert self.t["char_hat"] == (130, 90, 45), (
            f"char_hat expected (130, 90, 45), got {self.t['char_hat']}"
        )

    def test_char_hat_band_gold(self):
        assert self.t["char_hat_band"] == (190, 145, 45), (
            f"char_hat_band expected (190, 145, 45), got {self.t['char_hat_band']}"
        )

    def test_vine_base_natural_green(self):
        assert self.t["vine_base"] == (32, 195, 65), (
            f"vine_base expected (32, 195, 65), got {self.t['vine_base']}"
        )

    def test_spike_base_updated(self):
        assert self.t["spike_base"] == (190, 65, 240), (
            f"spike_base expected (190, 65, 240), got {self.t['spike_base']}"
        )

    def test_boulder_base_updated(self):
        assert self.t["boulder_base"] == (130, 108, 80), (
            f"boulder_base expected (130, 108, 80), got {self.t['boulder_base']}"
        )

    def test_get_color_fallback_not_triggered(self):
        """get_color must not return magenta for any standard colour key."""
        FALLBACK = (255, 0, 255)
        t = get_theme("jungle")
        for key in ("sky_top", "sky_horizon", "ground_base", "grass_main",
                    "char_jacket", "char_hat_band", "vine_base",
                    "spike_base", "boulder_base"):
            assert get_color(key, t) != FALLBACK, (
                f"get_color('{key}') returned magenta fallback"
            )


# ── build_background surface tests ───────────────────────────────────────────

class TestBuildBackground:

    def test_returns_pygame_surface(self):
        """build_background must return a pygame.Surface."""
        surf = build_background()
        assert isinstance(surf, pygame.Surface)

    def test_surface_correct_size(self):
        """Returned surface must be W×H."""
        surf = build_background()
        assert surf.get_width()  == W
        assert surf.get_height() == H

    def test_surface_correct_size_with_theme(self):
        """build_background with explicit jungle theme must also be W×H."""
        theme = get_theme("jungle")
        surf = build_background(theme=theme)
        assert surf.get_width()  == W
        assert surf.get_height() == H

    def test_no_exception_raised(self):
        """build_background must complete without raising any exception."""
        try:
            build_background()
        except Exception as exc:
            pytest.fail(f"build_background() raised {exc!r}")

    def test_no_exception_with_theme(self):
        """build_background with theme must complete without raising any exception."""
        theme = get_theme("jungle")
        try:
            build_background(theme=theme)
        except Exception as exc:
            pytest.fail(f"build_background(theme=...) raised {exc!r}")

    def test_surface_not_empty(self):
        """Returned surface should contain non-zero pixels (not all black)."""
        surf = build_background()
        # Sample a pixel from the sky region — should not be pure black
        pixel = surf.get_at((W // 2, 10))
        assert pixel[:3] != (0, 0, 0), "Sky region appears to be all black"

    def test_ground_region_colored(self):
        """Ground region (below GROUND_Y) must use the theme ground color."""
        from constants import GROUND_Y
        theme = get_theme("jungle")
        surf = build_background(theme=theme)
        ground_col = theme["ground_base"]
        px = surf.get_at((W // 2, GROUND_Y + int(40 * 3.6)))[:3]
        # Ground color should be close to ground_base (within ±15 per channel)
        for c_expected, c_actual in zip(ground_col, px):
            assert abs(int(c_expected) - int(c_actual)) <= 15, (
                f"Ground pixel {px} diverges from ground_base {ground_col}"
            )
