"""
Tests for the wave rhythm system (task jd-09).
Validates _get_spawn_interval_modifier returns correct phases and modifiers,
and that crescendo triggers dual spawns.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
import pygame

# Ensure pygame is initialized before importing game modules
pygame.init()

from states import PlayState, GameContext, GameStateManager
from constants import WAVE_PHASES, LEVEL_TIME


@pytest.fixture
def ctx():
    """Create a minimal GameContext for testing."""
    screen  = pygame.Surface((100, 100))
    display = pygame.Surface((100, 100))
    clock   = pygame.time.Clock()
    return GameContext(screen, display, clock)


@pytest.fixture
def mgr(ctx):
    return GameStateManager(ctx)


class TestGetSpawnIntervalModifier:
    """Test _get_spawn_interval_modifier returns correct (modifier, phase) tuples."""

    def test_calm_phase_at_start(self):
        mod, phase = PlayState._get_spawn_interval_modifier(0.0)
        assert phase == "calm"
        assert mod == 1.0

    def test_calm_phase_mid(self):
        mod, phase = PlayState._get_spawn_interval_modifier(10.0)
        assert phase == "calm"
        assert mod == 1.0

    def test_first_push_phase(self):
        mod, phase = PlayState._get_spawn_interval_modifier(15.0)
        assert phase == "push"
        assert mod == 0.75

    def test_first_push_phase_mid(self):
        mod, phase = PlayState._get_spawn_interval_modifier(20.0)
        assert phase == "push"
        assert mod == 0.75

    def test_first_breather_phase(self):
        mod, phase = PlayState._get_spawn_interval_modifier(23.0)
        assert phase == "breather"
        assert mod == 1.40

    def test_second_push_phase(self):
        mod, phase = PlayState._get_spawn_interval_modifier(30.0)
        assert phase == "push"
        assert mod == 0.70

    def test_second_breather_phase(self):
        mod, phase = PlayState._get_spawn_interval_modifier(36.0)
        assert phase == "breather"
        assert mod == 1.0

    def test_crescendo_phase(self):
        mod, phase = PlayState._get_spawn_interval_modifier(40.0)
        assert phase == "crescendo"
        assert mod == 0.50

    def test_crescendo_near_end(self):
        mod, phase = PlayState._get_spawn_interval_modifier(43.9)
        assert phase == "crescendo"
        assert mod == 0.50

    def test_after_all_phases_returns_calm(self):
        """After 44s (before level end at 45s), should default to calm."""
        mod, phase = PlayState._get_spawn_interval_modifier(44.5)
        assert phase == "calm"
        assert mod == 1.0

    def test_phase_boundaries_are_exclusive_on_end(self):
        """End times are exclusive — exactly at boundary should be in next phase."""
        # 15s is start of push, not calm
        _, phase = PlayState._get_spawn_interval_modifier(15.0)
        assert phase == "push"
        # 23s is start of breather, not push
        _, phase = PlayState._get_spawn_interval_modifier(23.0)
        assert phase == "breather"

    def test_all_phases_covered(self):
        """Sample every second from 0 to 44 and verify we get a valid phase."""
        valid_phases = {"calm", "push", "breather", "crescendo"}
        for t in range(0, 44):
            mod, phase = PlayState._get_spawn_interval_modifier(float(t))
            assert phase in valid_phases, f"Invalid phase '{phase}' at t={t}"
            assert 0 < mod <= 2.0, f"Unreasonable modifier {mod} at t={t}"


class TestWaveSpawnBehavior:
    """Integration tests for wave rhythm affecting spawn behavior."""

    def test_crescendo_spawns_two_obstacles(self, mgr):
        """During crescendo phase, spawning should produce two obstacles."""
        mgr.push(PlayState(mgr))
        ctx = mgr.ctx
        ctx.obstacles = []

        play = mgr.current
        play._spawn_dual()

        assert len(ctx.obstacles) == 2, \
            f"Expected 2 obstacles from dual spawn, got {len(ctx.obstacles)}"

    def test_crescendo_obstacles_are_separated(self, mgr):
        """Dual-spawned obstacles should have meaningful separation."""
        from constants import W
        mgr.push(PlayState(mgr))
        ctx = mgr.ctx

        # Run multiple trials — most should show some separation
        separations = []
        for _ in range(20):
            ctx.obstacles = []
            play = mgr.current
            play._spawn_dual()
            assert len(ctx.obstacles) == 2
            sep = abs(ctx.obstacles[0].x - ctx.obstacles[1].x)
            separations.append(sep)

        avg_sep = sum(separations) / len(separations)
        # The dual spawn logic attempts W*0.5 separation; with near-player
        # constraints it may be less, but on average should be meaningful
        assert avg_sep > 100, \
            f"Average separation {avg_sep} is too small — obstacles not being separated"

    def test_push_phase_increases_spawn_frequency(self, mgr):
        """During push phase, modified spawn rate should be less than base rate."""
        mgr.push(PlayState(mgr))
        play = mgr.current
        base_rate = play._spawn_rate()

        # Push modifier is 0.75
        mod, _ = PlayState._get_spawn_interval_modifier(16.0)
        modified = base_rate * mod
        assert modified < base_rate

    def test_breather_phase_decreases_spawn_frequency(self, mgr):
        """During breather phase, modified spawn rate should be more than base rate."""
        mgr.push(PlayState(mgr))
        play = mgr.current
        base_rate = play._spawn_rate()

        # Breather modifier is 1.40
        mod, _ = PlayState._get_spawn_interval_modifier(24.0)
        modified = base_rate * mod
        assert modified > base_rate
