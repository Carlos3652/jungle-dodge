"""
Tests for null player guard in PauseState, LevelUpState, and hud functions
(jd-crit-03).

Verifies that PauseState.draw(), LevelUpState.draw(), LevelUpState.update(),
hud.draw_game(), and hud.draw_hud() do not crash when player is None.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
import pygame
from unittest.mock import patch, MagicMock

pygame.init()

from entities import Player
from persistence import PersistenceManager
from states import (
    GameContext, GameStateManager,
    PauseState, LevelUpState, PlayState,
)
import hud


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def persistence(tmp_path):
    """Create a real PersistenceManager backed by a temp directory."""
    return PersistenceManager(base_dir=str(tmp_path))


@pytest.fixture
def ctx(persistence):
    """Create a minimal GameContext for testing."""
    screen  = pygame.Surface((100, 100))
    display = pygame.Surface((100, 100))
    clock   = pygame.time.Clock()
    gc = GameContext(screen, display, clock, persistence)
    gc.bg = pygame.Surface((100, 100))  # needed by _draw_scene
    return gc


@pytest.fixture
def mgr(ctx):
    return GameStateManager(ctx)


# ── PauseState.draw() ───────────────────────────────────────────────────────

def test_pause_draw_no_crash_when_player_none(mgr):
    """PauseState.draw() should return early (no crash) when ctx.player is None."""
    mgr.ctx.player = None
    pause = PauseState()
    mgr.push(pause)
    # Should not raise
    pause.draw(mgr.ctx)


@patch("states.hud.draw_pause_overlay")
@patch("states.hud.draw_hud")
@patch("states._draw_scene")
def test_pause_draw_skips_rendering_when_player_none(
    mock_scene, mock_hud, mock_overlay, mgr
):
    """When player is None, PauseState.draw() should not call any draw functions."""
    mgr.ctx.player = None
    pause = PauseState()
    mgr.push(pause)
    pause.draw(mgr.ctx)
    mock_scene.assert_not_called()
    mock_hud.assert_not_called()
    mock_overlay.assert_not_called()


@patch("states.hud.draw_pause_overlay")
@patch("states.hud.draw_hud")
@patch("states._draw_scene")
def test_pause_draw_renders_when_player_exists(
    mock_scene, mock_hud, mock_overlay, mgr
):
    """When player exists, PauseState.draw() should call all draw functions."""
    mgr.ctx.player = Player()
    pause = PauseState()
    mgr.push(pause)
    pause.draw(mgr.ctx)
    mock_scene.assert_called_once()
    mock_hud.assert_called_once()
    mock_overlay.assert_called_once()


# ── LevelUpState.draw() ─────────────────────────────────────────────────────

def test_levelup_draw_no_crash_when_player_none(mgr):
    """LevelUpState.draw() should return early (no crash) when ctx.player is None."""
    mgr.ctx.player = None
    mgr.ctx.levelup_t = 2.8
    lu = LevelUpState()
    mgr.push(lu)
    lu.draw(mgr.ctx)


@patch("states.hud.draw_levelup_overlay")
@patch("states.hud.draw_hud")
@patch("states._draw_scene")
def test_levelup_draw_skips_rendering_when_player_none(
    mock_scene, mock_hud, mock_overlay, mgr
):
    """When player is None, LevelUpState.draw() should not call any draw functions."""
    mgr.ctx.player = None
    mgr.ctx.levelup_t = 2.8
    lu = LevelUpState()
    mgr.push(lu)
    lu.draw(mgr.ctx)
    mock_scene.assert_not_called()
    mock_hud.assert_not_called()
    mock_overlay.assert_not_called()


@patch("states.hud.draw_levelup_overlay")
@patch("states.hud.draw_hud")
@patch("states._draw_scene")
def test_levelup_draw_renders_when_player_exists(
    mock_scene, mock_hud, mock_overlay, mgr
):
    """When player exists, LevelUpState.draw() should call all draw functions."""
    mgr.ctx.player = Player()
    mgr.ctx.levelup_t = 2.8
    lu = LevelUpState()
    mgr.push(lu)
    lu.draw(mgr.ctx)
    mock_scene.assert_called_once()
    mock_hud.assert_called_once()
    mock_overlay.assert_called_once()


# ── LevelUpState.update() ───────────────────────────────────────────────────

def test_levelup_update_no_crash_when_player_none(mgr):
    """LevelUpState.update() should not crash when ctx.player is None."""
    mgr.ctx.player = None
    mgr.ctx.levelup_t = 2.8
    lu = LevelUpState()
    mgr.push(lu)
    # Should not raise AttributeError
    lu.update(mgr.ctx, 0.1)


def test_levelup_update_still_decrements_timer_when_player_none(mgr):
    """LevelUpState.update() should still count down levelup_t even without a player."""
    mgr.ctx.player = None
    mgr.ctx.levelup_t = 2.8
    lu = LevelUpState()
    mgr.push(lu)
    lu.update(mgr.ctx, 1.0)
    assert mgr.ctx.levelup_t == pytest.approx(1.8)


def test_levelup_update_transitions_to_play_when_timer_expires_player_none(mgr):
    """LevelUpState should still transition to PlayState when timer expires, even if player is None."""
    mgr.ctx.player = None
    lu = LevelUpState()
    mgr.push(lu)  # enter() sets levelup_t = 2.8
    mgr.ctx.levelup_t = 0.5  # override after push
    lu.update(mgr.ctx, 1.0)
    assert isinstance(mgr.current, PlayState)


def test_levelup_update_ticks_stun_when_player_exists(mgr):
    """LevelUpState.update() should tick stun timers when player exists."""
    mgr.ctx.player = Player()
    mgr.ctx.player.stun_t = 1.0
    mgr.ctx.player.flash_t = 0.0
    mgr.ctx.player.immune_t = 1.0
    mgr.ctx.levelup_t = 5.0
    lu = LevelUpState()
    mgr.push(lu)
    lu.update(mgr.ctx, 0.5)
    assert mgr.ctx.player.stun_t == pytest.approx(0.5)
    assert mgr.ctx.player.immune_t == pytest.approx(0.5)
    assert mgr.ctx.player.flash_t > 0.0


# ── hud.draw_game() with player=None ────────────────────────────────────────

def test_draw_game_no_crash_when_player_none():
    """hud.draw_game() should not crash when player is None."""
    screen = pygame.Surface((100, 100))
    bg = pygame.Surface((100, 100))
    particles = MagicMock()
    # Should not raise
    hud.draw_game(screen, bg, [], None, particles)


def test_draw_game_still_draws_bg_when_player_none():
    """hud.draw_game() should still blit the background even when player is None."""
    screen = MagicMock()
    bg = pygame.Surface((100, 100))
    particles = MagicMock()
    hud.draw_game(screen, bg, [], None, particles)
    # Background blit should still happen
    screen.blit.assert_called()


def test_draw_game_draws_player_when_present():
    """hud.draw_game() should call player.draw() when player is not None."""
    screen = pygame.Surface((100, 100))
    bg = pygame.Surface((100, 100))
    player = MagicMock()
    particles = MagicMock()
    hud.draw_game(screen, bg, [], player, particles)
    player.draw.assert_called_once_with(screen, particles, theme=None)


# ── hud.draw_hud() with player=None ─────────────────────────────────────────

def test_draw_hud_no_crash_when_player_none():
    """hud.draw_hud() should not crash when player is None."""
    screen = pygame.Surface((100, 100))
    cache = MagicMock()
    # Should not raise
    hud.draw_hud(screen, cache, 0, 1, 0.0, None)


def test_draw_hud_skips_rendering_when_player_none():
    """hud.draw_hud() should return early and not blit anything when player is None."""
    screen = MagicMock()
    cache = MagicMock()
    hud.draw_hud(screen, cache, 0, 1, 0.0, None)
    # No blit calls should happen since we return early
    screen.blit.assert_not_called()


def test_draw_hud_renders_when_player_exists():
    """hud.draw_hud() should render the HUD when player is provided."""
    screen = pygame.Surface((100, 100))
    cache = hud.HudCache()
    player = Player()
    # Should not raise
    hud.draw_hud(screen, cache, 100, 1, 10.0, player)
