"""
Tests for the state machine (task jd-06).
Validates GameStateManager push/pop/swap, GameContext reset, and state transitions.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
import pygame

# Ensure pygame is initialized before importing game modules
pygame.init()

from states import (
    GameContext, GameStateManager, State,
    StartScreenState, PlayState, LevelUpState,
)
from constants import LEVEL_TIME, MAX_LIVES


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


def test_push_pop(mgr):
    """Push/pop should maintain correct stack order."""
    s1 = State(mgr)
    s2 = State(mgr)

    mgr.push(s1)
    assert mgr.current is s1

    mgr.push(s2)
    assert mgr.current is s2
    assert len(mgr._stack) == 2

    mgr.pop()
    assert mgr.current is s1
    assert len(mgr._stack) == 1


def test_swap(mgr):
    """Swap should replace top state without growing the stack."""
    s1 = State(mgr)
    s2 = State(mgr)

    mgr.push(s1)
    assert mgr.current is s1

    mgr.swap(s2)
    assert mgr.current is s2
    assert len(mgr._stack) == 1


def test_new_game_resets(ctx):
    """new_game() should reset score, level, player, and timers."""
    ctx.score = 999
    ctx.level = 7
    ctx.player.lives = 0
    ctx.level_timer = 30.0
    ctx.start_idle_t = 10.0

    ctx.new_game()

    assert ctx.score == 0
    assert ctx.level == 1
    assert ctx.player.lives == MAX_LIVES
    assert ctx.level_timer == 0.0
    assert ctx.start_idle_t == 0.0
    assert ctx.obstacles == []


def test_play_level_up_transition(mgr):
    """When level timer expires in PlayState, should swap to LevelUpState."""
    mgr.push(PlayState(mgr))
    ctx = mgr.ctx

    # Set timer just below threshold — next update should trigger level-up
    ctx.level_timer = LEVEL_TIME - 0.01
    starting_level = ctx.level

    # Advance past the level boundary
    mgr.update(0.05)

    assert isinstance(mgr.current, LevelUpState), \
        f"Expected LevelUpState, got {type(mgr.current).__name__}"
    assert ctx.level == starting_level + 1
