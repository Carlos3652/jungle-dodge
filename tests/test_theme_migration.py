"""
Tests for CLR-to-theme migration (jd-high-04).

Verifies that:
- GameContext has a theme field
- Entity draw methods accept and forward the theme parameter
- HUD functions accept and forward the theme parameter
- themes.get_color is called with the correct keys during drawing
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock, call

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from themes import get_theme, get_color, THEMES
from constants import CLR


# ── GameContext theme field ──────────────────────────────────────────────────

def test_game_context_has_theme_field():
    """GameContext dataclass should have an optional theme field."""
    from states import GameContext
    import dataclasses
    fields = {f.name for f in dataclasses.fields(GameContext)}
    assert "theme" in fields


def test_game_context_theme_defaults_to_none():
    """GameContext.theme should default to None."""
    from states import GameContext
    # Create minimal context (need required fields)
    ctx = GameContext(
        screen=MagicMock(),
        display=MagicMock(),
        clock=MagicMock(),
        persistence=MagicMock(),
    )
    assert ctx.theme is None


# ── Theme color value parity ─────────────────────────────────────────────────

class TestThemeColorParity:
    """Verify that jungle theme colors are valid and match expected values.

    Note: Several colour values were deliberately updated in jd-18 (jungle
    theme refresh) to use a warmer, richer palette.  Tests that previously
    pinned to the old CLR constants have been updated to reflect the new spec
    values.  Keys unchanged by jd-18 still pin to CLR for regression safety.
    """

    JUNGLE = get_theme("jungle")

    # ── Character — unchanged keys still pin to CLR ──────────────────────
    def test_char_pants(self):
        assert get_color("char_pants", self.JUNGLE) == CLR["pants"]

    def test_char_skin(self):
        assert get_color("char_skin", self.JUNGLE) == CLR["skin"]

    def test_char_boots(self):
        assert get_color("char_boots", self.JUNGLE) == (50, 35, 20)

    # ── Character — updated by jd-18 (warmer leather palette) ────────────
    def test_char_jacket(self):
        assert get_color("char_jacket", self.JUNGLE) == (185, 155, 90)

    def test_char_hat(self):
        assert get_color("char_hat", self.JUNGLE) == (130, 90, 45)

    def test_char_hat_band(self):
        assert get_color("char_hat_band", self.JUNGLE) == (190, 145, 45)

    # ── Obstacles — unchanged keys ────────────────────────────────────────
    def test_vine_highlight(self):
        assert get_color("vine_highlight", self.JUNGLE) == CLR["vine_dk"]

    def test_bomb_body(self):
        assert get_color("bomb_body", self.JUNGLE) == CLR["bomb"]

    def test_bomb_fuse(self):
        assert get_color("bomb_fuse", self.JUNGLE) == CLR["fuse"]

    def test_spike_tip(self):
        assert get_color("spike_tip", self.JUNGLE) == CLR["spike_dk"]

    def test_boulder_crack(self):
        assert get_color("boulder_crack", self.JUNGLE) == CLR["boulder_dk"]

    # ── Obstacles — updated by jd-18 ─────────────────────────────────────
    def test_vine_base(self):
        assert get_color("vine_base", self.JUNGLE) == (32, 195, 65)

    def test_spike_base(self):
        assert get_color("spike_base", self.JUNGLE) == (190, 65, 240)

    def test_boulder_base(self):
        assert get_color("boulder_base", self.JUNGLE) == (130, 108, 80)

    # ── HUD — unchanged ───────────────────────────────────────────────────
    def test_hud_bg(self):
        assert get_color("hud_bg", self.JUNGLE) == CLR["stone"]

    def test_hud_border(self):
        assert get_color("hud_border", self.JUNGLE) == CLR["stone_hi"]

    def test_hud_label(self):
        assert get_color("hud_label", self.JUNGLE) == CLR["olive"]

    def test_hud_text(self):
        assert get_color("hud_text", self.JUNGLE) == CLR["white"]

    def test_warning_color(self):
        assert get_color("warning_color", self.JUNGLE) == CLR["red"]

    def test_roll_ready(self):
        assert get_color("roll_ready", self.JUNGLE) == CLR["teal"]

    def test_lives_full(self):
        assert get_color("lives_full", self.JUNGLE) == CLR["heart"]

    def test_streak_gold(self):
        assert get_color("streak_gold", self.JUNGLE) == CLR["gold"]

    def test_streak_silver(self):
        assert get_color("streak_silver", self.JUNGLE) == CLR["silver"]

    def test_streak_bronze(self):
        assert get_color("streak_bronze", self.JUNGLE) == CLR["bronze"]

    # ── Background — updated by jd-18 ────────────────────────────────────
    def test_ground_base(self):
        assert get_color("ground_base", self.JUNGLE) == (55, 35, 18)

    def test_grass_main(self):
        assert get_color("grass_main", self.JUNGLE) == (38, 85, 28)

    def test_sky_top(self):
        assert get_color("sky_top", self.JUNGLE) == (4, 10, 6)

    # ── Leaderboard — unchanged ───────────────────────────────────────────
    def test_lb_player_row(self):
        assert get_color("lb_player_row", self.JUNGLE) == CLR["lb_row_a"]

    def test_tab_active(self):
        assert get_color("tab_active", self.JUNGLE) == CLR["lb_border"]


# ── Entity draw accepts theme ───────────────────────────────────────────────

class TestEntityDrawAcceptsTheme:
    """Verify that entity draw methods accept a theme kwarg and call get_color."""

    JUNGLE = get_theme("jungle")

    def _draw_safe(self, entity, theme):
        """Call entity.draw() with a mock surface, capturing get_color calls.

        Some test suites stub pygame.Surface globally, so we use a MagicMock
        for the surface and patch pygame.draw to avoid TypeError on mock surfaces.
        """
        surf = MagicMock()
        with patch("entities.pygame.draw", MagicMock()):
            with patch("entities.pygame.transform", MagicMock()):
                with patch("entities.get_color", wraps=get_color) as mock_gc:
                    try:
                        entity.draw(surf, theme=theme)
                    except (TypeError, AttributeError):
                        pass  # mock surface issues are OK — we only care about get_color calls
                    return {c.args[0] for c in mock_gc.call_args_list}

    def test_vine_draw_calls_get_color(self):
        from entities import Vine
        v = Vine(1, spawn_x=100)
        v.y = 50.0
        keys = self._draw_safe(v, self.JUNGLE)
        assert "vine_base" in keys
        assert "vine_highlight" in keys

    def test_bomb_draw_calls_get_color(self):
        from entities import Bomb
        b = Bomb(1, spawn_x=100)
        b.y = 50.0
        keys = self._draw_safe(b, self.JUNGLE)
        assert "bomb_body" in keys
        assert "bomb_fuse" in keys

    def test_spike_draw_calls_get_color(self):
        from entities import Spike
        s = Spike(1, spawn_x=100)
        s.y = 50.0
        keys = self._draw_safe(s, self.JUNGLE)
        assert "spike_base" in keys
        assert "spike_tip" in keys

    def test_boulder_draw_calls_get_color(self):
        from entities import Boulder
        b = Boulder(1, spawn_x=100)
        b.y = 50.0
        keys = self._draw_safe(b, self.JUNGLE)
        assert "boulder_base" in keys
        assert "boulder_crack" in keys

    def test_player_draw_calls_get_color(self):
        from entities import Player
        p = Player()
        keys = self._draw_safe(p, self.JUNGLE)
        assert "char_pants" in keys
        assert "char_jacket" in keys
        assert "char_skin" in keys
        assert "char_hat" in keys
        assert "char_boots" in keys
        assert "char_hat_band" in keys


# ── HUD draw accepts theme ──────────────────────────────────────────────────

class TestHudDrawAcceptsTheme:
    """Verify that hud draw functions accept and use a theme kwarg."""

    JUNGLE = get_theme("jungle")

    def test_draw_hud_accepts_theme(self):
        """draw_hud should accept a theme= keyword argument."""
        from hud import draw_hud
        import inspect
        sig = inspect.signature(draw_hud)
        assert "theme" in sig.parameters, "draw_hud must accept a 'theme' parameter"

    def test_hud_cache_accepts_theme(self):
        """HudCache should accept a theme parameter."""
        from hud import HudCache
        cache = HudCache(theme=self.JUNGLE)
        assert cache._theme is self.JUNGLE

    def test_build_background_accepts_theme(self):
        """build_background should accept an optional theme parameter."""
        from hud import build_background
        # Just verify it doesn't crash
        bg = build_background(theme=self.JUNGLE)
        assert bg is not None
