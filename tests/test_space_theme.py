"""
Tests for jd-19: Space theme (full implementation)

Verifies:
- Space theme exists in THEMES dict
- All required keys are present in the space theme
- All colour keys are valid RGB tuples
- All themes (jungle + space) satisfy REQUIRED_KEYS
- Key spot-checks match spec values
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import themes


# ── Helpers ───────────────────────────────────────────────────────────────────

STRING_KEYS = {"name", "hud_style", "transition_style", "audio_prefix"}


def _is_rgb_tuple(v):
    """Return True if v is a 3-element tuple of ints in [0, 255]."""
    return (
        isinstance(v, tuple)
        and len(v) == 3
        and all(isinstance(c, int) and 0 <= c <= 255 for c in v)
    )


# ── All-themes gate ───────────────────────────────────────────────────────────

def test_all_themes_have_required_keys():
    """Every theme must define every key in REQUIRED_KEYS."""
    for name in themes.list_themes():
        theme = themes.get_theme(name)
        for key in themes.REQUIRED_KEYS:
            assert key in theme, f"Theme '{name}' missing key '{key}'"


def test_all_themes_color_keys_are_valid_rgb():
    """Every colour key in every theme must be a valid (R, G, B) tuple."""
    color_keys = themes.REQUIRED_KEYS - STRING_KEYS
    for name in themes.list_themes():
        theme = themes.get_theme(name)
        for key in color_keys:
            val = theme.get(key)
            assert val is not None, f"Theme '{name}' key '{key}' is None"
            assert _is_rgb_tuple(val), (
                f"Theme '{name}' key '{key}' value {val!r} is not a valid RGB tuple"
            )


# ── Space theme existence + completeness ─────────────────────────────────────

class TestSpaceThemeExists:

    def test_space_in_themes(self):
        assert "space" in themes.THEMES

    def test_list_themes_includes_space(self):
        assert "space" in themes.list_themes()

    def test_get_theme_space_returns_dict(self):
        t = themes.get_theme("space")
        assert isinstance(t, dict)

    def test_space_has_no_extra_keys(self):
        """Space theme must define exactly the REQUIRED_KEYS."""
        defined = set(themes.THEMES["space"].keys())
        assert defined == themes.REQUIRED_KEYS, (
            f"Key mismatch — extra: {defined - themes.REQUIRED_KEYS}, "
            f"missing: {themes.REQUIRED_KEYS - defined}"
        )


# ── Space theme spec values ───────────────────────────────────────────────────

class TestSpaceThemeValues:

    def setup_method(self):
        self.t = themes.get_theme("space")

    # Identity
    def test_name(self):
        assert self.t["name"] == "Space"

    def test_accent_color(self):
        assert self.t["accent_color"] == (0, 220, 255)

    def test_secondary_color(self):
        assert self.t["secondary_color"] == (255, 80, 180)

    def test_warning_color(self):
        assert self.t["warning_color"] == (255, 60, 60)

    # Sky
    def test_sky_top(self):
        assert self.t["sky_top"] == (2, 2, 12)

    def test_sky_horizon(self):
        assert self.t["sky_horizon"] == (8, 8, 25)

    # Ground
    def test_ground_base(self):
        assert self.t["ground_base"] == (40, 42, 50)

    def test_ground_edge(self):
        assert self.t["ground_edge"] == (55, 58, 68)

    # Character
    def test_char_jacket_grey_suit(self):
        assert self.t["char_jacket"] == (160, 165, 175)

    def test_char_hat_helmet(self):
        assert self.t["char_hat"] == (80, 85, 95)

    def test_char_hat_band_cyan_visor(self):
        assert self.t["char_hat_band"] == (0, 220, 255)

    def test_char_iframe_glow_cyan(self):
        assert self.t["char_iframe_glow"] == (0, 220, 255)

    # Obstacles
    def test_vine_base_tether_cable(self):
        assert self.t["vine_base"] == (0, 200, 240)

    def test_bomb_body_proximity_mine(self):
        assert self.t["bomb_body"] == (40, 20, 20)

    def test_spike_base_silver(self):
        assert self.t["spike_base"] == (200, 200, 220)

    def test_boulder_base_asteroid(self):
        assert self.t["boulder_base"] == (100, 95, 85)

    def test_croc_base_jaw_trap(self):
        assert self.t["croc_base"] == (80, 40, 40)

    def test_poison_puddle_radiation_green(self):
        assert self.t["poison_puddle"] == (40, 200, 80)

    # HUD
    def test_hud_bg_dark_blue(self):
        assert self.t["hud_bg"] == (10, 15, 35)

    def test_hud_border_cyan(self):
        assert self.t["hud_border"] == (0, 180, 220)

    def test_hud_style_holographic(self):
        assert self.t["hud_style"] == "holographic"

    def test_hud_primary_cyan(self):
        assert self.t["hud_primary"] == (0, 220, 255)

    def test_lives_full_cyan(self):
        assert self.t["lives_full"] == (0, 220, 255)

    # Transitions + audio
    def test_transition_style_star_jump(self):
        assert self.t["transition_style"] == "star_jump"

    def test_audio_prefix_space(self):
        assert self.t["audio_prefix"] == "space"

    # No magenta fallback from get_color
    def test_no_fallback_magenta(self):
        FALLBACK = (255, 0, 255)
        spot_keys = (
            "accent_color", "sky_top", "ground_base", "char_jacket",
            "char_hat_band", "vine_base", "spike_base", "boulder_base",
            "hud_bg", "hud_border", "hud_primary", "lives_full",
        )
        for key in spot_keys:
            assert themes.get_color(key, self.t) != FALLBACK, (
                f"get_color('{key}') returned magenta fallback for space theme"
            )
