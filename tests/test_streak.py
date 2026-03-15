"""
Tests for streak combo multiplier (task jd-08).

Covers streak increment on dodge, multiplier tiers, and streak reset on hit.
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

from states import (
    GameContext, GameStateManager, PlayState,
    streak_multiplier, streak_tier_info,
)
from constants import DODGE_PTS, STREAK_TIERS


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx():
    """Create a minimal GameContext for testing."""
    screen  = pygame.Surface((100, 100))
    display = pygame.Surface((100, 100))
    clock   = pygame.time.Clock()
    return GameContext(screen, display, clock)


@pytest.fixture
def mgr(ctx):
    """Create a GameStateManager with the test context."""
    return GameStateManager(ctx)


# ── Multiplier tier tests ────────────────────────────────────────────────────

class TestMultiplierTiers:

    def test_base_tier_0(self):
        """Streak 0 should give 1x multiplier."""
        assert streak_multiplier(0) == 1.0

    def test_base_tier_4(self):
        """Streak 4 (below threshold) should give 1x multiplier."""
        assert streak_multiplier(4) == 1.0

    def test_bronze_tier_5(self):
        """Streak 5 should give 1.5x multiplier."""
        assert streak_multiplier(5) == 1.5

    def test_bronze_tier_9(self):
        """Streak 9 (top of bronze) should give 1.5x multiplier."""
        assert streak_multiplier(9) == 1.5

    def test_silver_tier_10(self):
        """Streak 10 should give 2x multiplier."""
        assert streak_multiplier(10) == 2.0

    def test_silver_tier_19(self):
        """Streak 19 (top of silver) should give 2x multiplier."""
        assert streak_multiplier(19) == 2.0

    def test_gold_tier_20(self):
        """Streak 20 should give 3x multiplier."""
        assert streak_multiplier(20) == 3.0

    def test_gold_tier_100(self):
        """Very high streak should still give 3x (max tier)."""
        assert streak_multiplier(100) == 3.0

    def test_all_tier_boundaries(self):
        """Verify every boundary defined in STREAK_TIERS."""
        expected = [
            (0, 1.0), (4, 1.0),
            (5, 1.5), (9, 1.5),
            (10, 2.0), (19, 2.0),
            (20, 3.0), (50, 3.0),
        ]
        for streak_val, expected_mult in expected:
            assert streak_multiplier(streak_val) == expected_mult, \
                f"streak={streak_val} expected {expected_mult}x, got {streak_multiplier(streak_val)}x"


# ── Tier info tests ──────────────────────────────────────────────────────────

class TestTierInfo:

    def test_no_badge_below_5(self):
        """Streak < 5 should have no badge label."""
        mult, label, color = streak_tier_info(3)
        assert mult == 1.0
        assert label is None
        assert color is None

    def test_bronze_badge(self):
        """Streak 5-9 should show bronze badge."""
        mult, label, color = streak_tier_info(7)
        assert mult == 1.5
        assert label == "bronze"
        assert color == "bronze"

    def test_silver_badge(self):
        """Streak 10-19 should show silver badge."""
        mult, label, color = streak_tier_info(15)
        assert mult == 2.0
        assert label == "silver"
        assert color == "silver"

    def test_gold_badge(self):
        """Streak 20+ should show gold badge."""
        mult, label, color = streak_tier_info(25)
        assert mult == 3.0
        assert label == "gold"
        assert color == "gold"


# ── Streak increment on dodge ────────────────────────────────────────────────

class TestStreakIncrement:

    def test_streak_starts_at_zero(self, ctx):
        """New game should start with streak = 0."""
        ctx.new_game()
        assert ctx.streak == 0

    def test_streak_increments_on_dodge(self, ctx, mgr):
        """When an obstacle scores (dodged), streak should increment."""
        mgr.push(PlayState(mgr))
        ctx.streak = 0

        # Simulate an obstacle that has been dodged (scored, no hit)
        from entities import Spike
        obs = Spike(1, spawn_x=100)
        obs.scored = True
        obs._pts   = False
        obs.did_hit = False
        ctx.obstacles.append(obs)

        # Run one update tick — scoring path should fire
        # We need to disable spawning/level timer to isolate scoring
        ctx.level_timer = 0.0
        ctx.spawn_timer = -999  # prevent spawn
        mgr.update(0.016)

        assert ctx.streak == 1

    def test_streak_increments_multiple(self, ctx, mgr):
        """Multiple dodges in sequence should build streak."""
        mgr.push(PlayState(mgr))
        ctx.streak = 0
        ctx.level_timer = 0.0
        ctx.spawn_timer = -999

        from entities import Spike
        for _ in range(5):
            obs = Spike(1, spawn_x=100)
            obs.scored = True
            obs._pts   = False
            obs.did_hit = False
            ctx.obstacles.append(obs)

        mgr.update(0.016)
        assert ctx.streak == 5

    def test_dodge_score_uses_multiplier(self, ctx, mgr):
        """Score awarded should reflect streak multiplier."""
        mgr.push(PlayState(mgr))
        ctx.streak = 9    # next dodge makes it 10 → 2x tier
        ctx.score  = 0
        ctx.level_timer = 0.0
        ctx.spawn_timer = -999

        from entities import Spike
        obs = Spike(1, spawn_x=100)
        obs.scored = True
        obs._pts   = False
        obs.did_hit = False
        ctx.obstacles.append(obs)

        mgr.update(0.016)

        # Streak becomes 10, multiplier = 2.0, pts = 10 * 2.0 = 20
        assert ctx.streak == 10
        assert ctx.score == int(DODGE_PTS * 2.0)


# ── Streak reset on hit ─────────────────────────────────────────────────────

class TestStreakReset:

    def test_streak_resets_on_hit(self, ctx, mgr):
        """Getting hit should reset streak to 0."""
        mgr.push(PlayState(mgr))
        ctx.streak = 15

        # Place an obstacle that will collide with the player
        from entities import Spike
        obs = Spike(1, spawn_x=int(ctx.player.x))
        # Force it on top of the player
        obs.y = float(ctx.player.y)
        obs.alive   = True
        obs.did_hit = False
        ctx.obstacles.append(obs)

        # Clear any immunity
        ctx.player.immune_t = 0.0
        ctx.player.stun_t   = 0.0

        ctx.level_timer = 0.0
        ctx.spawn_timer = -999
        mgr.update(0.016)

        assert ctx.streak == 0

    def test_new_game_resets_streak(self, ctx):
        """new_game() should reset streak to 0."""
        ctx.streak = 42
        ctx.new_game()
        assert ctx.streak == 0
