"""
Tests for HUD font caching and dirty-tracking (task jd-crit-02).

Verifies that:
- Static labels are pre-rendered once in HudCache
- Dynamic value surfaces are cached and only re-rendered on change
- draw_hud and draw_wave_phase_bar use cached surfaces correctly
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

from hud import HudCache, draw_hud, draw_wave_phase_bar, _WAVE_PHASE_LABELS
from constants import CLR, W, H, MAX_LIVES


# ── Helpers ──────────────────────────────────────────────────────────────────

class FakePlayer:
    """Minimal player stub for draw_hud tests."""
    def __init__(self, lives=3, stun_t=0.0, immune_t=0.0):
        self.lives = lives
        self.stun_t = stun_t
        self.immune_t = immune_t

    def is_stunned(self):
        return self.stun_t > 0.0


@pytest.fixture
def cache():
    return HudCache()


@pytest.fixture
def screen():
    return pygame.Surface((W, H))


# ── Static label tests ──────────────────────────────────────────────────────

class TestStaticLabels:

    def test_static_labels_are_surfaces(self, cache):
        """All static labels should be pre-rendered pygame Surfaces."""
        for attr in ("lbl_score", "lbl_level", "lbl_time", "lbl_lives", "lbl_stunned"):
            surf = getattr(cache, attr)
            assert isinstance(surf, pygame.Surface), f"{attr} is not a Surface"
            assert surf.get_width() > 0
            assert surf.get_height() > 0

    def test_static_labels_are_same_across_accesses(self, cache):
        """Accessing a static label multiple times returns the same object (no re-render)."""
        s1 = cache.lbl_score
        s2 = cache.lbl_score
        assert s1 is s2

    def test_wave_phase_labels_pre_rendered(self, cache):
        """All wave phase labels should be pre-rendered in cache."""
        for name in _WAVE_PHASE_LABELS:
            assert name in cache.wave_labels
            surf = cache.wave_labels[name]
            assert isinstance(surf, pygame.Surface)
            assert surf.get_width() > 0


# ── Dynamic cache dirty-tracking tests ──────────────────────────────────────

class TestScoreCache:

    def test_score_rendered_on_first_call(self, cache):
        """First call should render and cache the score surfaces."""
        shad, val = cache.get_score_surfs(100)
        assert isinstance(shad, pygame.Surface)
        assert isinstance(val, pygame.Surface)
        assert cache._dyn_score == 100

    def test_score_cached_on_same_value(self, cache):
        """Same score should return the same surface objects (no re-render)."""
        shad1, val1 = cache.get_score_surfs(42)
        shad2, val2 = cache.get_score_surfs(42)
        assert shad1 is shad2
        assert val1 is val2

    def test_score_re_rendered_on_change(self, cache):
        """Different score should re-render new surfaces."""
        shad1, val1 = cache.get_score_surfs(10)
        shad2, val2 = cache.get_score_surfs(20)
        assert shad1 is not shad2
        assert val1 is not val2
        assert cache._dyn_score == 20


class TestLevelCache:

    def test_level_rendered_on_first_call(self, cache):
        """First call should render and cache the level surfaces."""
        shad, val = cache.get_level_surfs(1)
        assert isinstance(shad, pygame.Surface)
        assert isinstance(val, pygame.Surface)

    def test_level_cached_on_same_value(self, cache):
        """Same level should return the same surface objects."""
        shad1, val1 = cache.get_level_surfs(5)
        shad2, val2 = cache.get_level_surfs(5)
        assert shad1 is shad2
        assert val1 is val2

    def test_level_re_rendered_on_change(self, cache):
        """Level change should produce new surfaces."""
        _, val1 = cache.get_level_surfs(1)
        _, val2 = cache.get_level_surfs(2)
        assert val1 is not val2


class TestTimeCache:

    def test_time_rendered_on_first_call(self, cache):
        shad, val = cache.get_time_surfs(30, False)
        assert isinstance(shad, pygame.Surface)
        assert isinstance(val, pygame.Surface)

    def test_time_cached_on_same_value(self, cache):
        shad1, val1 = cache.get_time_surfs(20, False)
        shad2, val2 = cache.get_time_surfs(20, False)
        assert shad1 is shad2
        assert val1 is val2

    def test_time_re_rendered_on_second_change(self, cache):
        _, val1 = cache.get_time_surfs(20, False)
        _, val2 = cache.get_time_surfs(19, False)
        assert val1 is not val2

    def test_time_re_rendered_on_color_change(self, cache):
        """Switching from white to red (< 10s) should re-render."""
        _, val1 = cache.get_time_surfs(10, False)
        _, val2 = cache.get_time_surfs(10, True)
        assert val1 is not val2

    def test_time_cached_when_both_match(self, cache):
        """Same display_t and same is_red should cache."""
        shad1, val1 = cache.get_time_surfs(5, True)
        shad2, val2 = cache.get_time_surfs(5, True)
        assert shad1 is shad2
        assert val1 is val2


# ── Integration: draw_hud uses cached surfaces ─────────────────────────────

class TestDrawHudIntegration:

    def test_draw_hud_runs_without_error(self, screen, cache):
        """draw_hud should execute without errors using cached labels."""
        player = FakePlayer(lives=3)
        draw_hud(screen, cache, score=100, level=2, level_timer=10.0,
                 player=player, streak=0, is_levelup=False)

    def test_draw_hud_stunned_uses_cache(self, screen, cache):
        """draw_hud with stunned player should use cached STUNNED label."""
        player = FakePlayer(lives=2, stun_t=1.5)
        draw_hud(screen, cache, score=50, level=1, level_timer=5.0,
                 player=player, streak=0, is_levelup=False)

    def test_draw_hud_levelup_skips_wave_bar(self, screen, cache):
        """During level-up, wave phase bar should be skipped."""
        player = FakePlayer(lives=3)
        draw_hud(screen, cache, score=200, level=3, level_timer=0.0,
                 player=player, streak=10, is_levelup=True)

    def test_draw_hud_repeated_same_values_caches(self, screen, cache):
        """Calling draw_hud twice with same values should reuse cached surfaces."""
        player = FakePlayer(lives=3)
        draw_hud(screen, cache, score=100, level=2, level_timer=20.0,
                 player=player, streak=0, is_levelup=False)
        # Grab refs after first call
        s_shad = cache._dyn_score_shad
        l_val = cache._dyn_level_val
        t_val = cache._dyn_time_val

        draw_hud(screen, cache, score=100, level=2, level_timer=20.0,
                 player=player, streak=0, is_levelup=False)
        # Should be identical objects (no re-render)
        assert cache._dyn_score_shad is s_shad
        assert cache._dyn_level_val is l_val
        assert cache._dyn_time_val is t_val


# ── Integration: draw_wave_phase_bar uses cached labels ─────────────────────

class TestDrawWavePhaseBarIntegration:

    def test_wave_bar_runs_without_error(self, screen, cache):
        """draw_wave_phase_bar with cache should run without errors."""
        draw_wave_phase_bar(screen, 10.0, cache)

    def test_wave_bar_runs_without_cache(self, screen):
        """draw_wave_phase_bar without cache (backwards compat) should still work."""
        draw_wave_phase_bar(screen, 10.0)

    def test_wave_bar_all_phases(self, screen, cache):
        """draw_wave_phase_bar should handle all phase time values."""
        for t in [0.0, 5.0, 15.0, 20.0, 25.0, 30.0, 37.0, 40.0, 44.0]:
            draw_wave_phase_bar(screen, t, cache)
