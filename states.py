"""
State machine extracted from jungle_dodge.py (task jd-06c).

Stack-based GameStateManager, GameContext dataclass, and 7 initial states:
StartScreenState, PlayState, PauseState, LevelUpState,
GameOverState, NameEntryState, LeaderboardState.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, field
from typing import List, Optional

import pygame

from constants import (
    W, H, SX, SY, S, FPS,
    GROUND_Y,
    CLR,
    LEVEL_TIME, MAX_LIVES, STUN_SECS,
    DODGE_PTS,
    BASE_SPAWN, SPAWN_DEC, MIN_SPAWN, SPEED_SCALE,
    OBS_TYPES, OBS_WEIGHTS,
    MAX_NAME_LEN,
)
from entities import Player, Obstacle, Vine, Bomb, Spike, Boulder
from particles import ParticleSystem
from persistence import PersistenceManager
import hud


# ─────────────────────────────────────────────────────────────────────────────
#  GameContext — shared state across all states
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class GameContext:
    """Shared state passed to every State subclass."""
    screen: pygame.Surface
    display: pygame.Surface
    clock: pygame.time.Clock
    persistence: PersistenceManager
    particles: ParticleSystem = field(default_factory=ParticleSystem)

    # Gameplay
    player: Optional[Player] = None
    obstacles: List = field(default_factory=list)
    score: int = 0
    level: int = 1
    level_timer: float = 0.0
    spawn_timer: float = 0.0
    levelup_t: float = 0.0
    leaderboard: List = field(default_factory=list)

    # Name entry
    name_input: str = ""
    cursor_t: float = 0.0
    cursor_on: bool = True

    # Start screen
    start_idle_t: float = 0.0

    # Background
    bg: Optional[pygame.Surface] = None

    # Fullscreen
    fullscreen: bool = True

    # Back-reference to the state manager (set by GameStateManager.__init__)
    manager: Optional["GameStateManager"] = None

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.display = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
            pygame.mouse.set_visible(False)
        else:
            self.display = pygame.display.set_mode((1280, 720))
            pygame.mouse.set_visible(True)

    def present(self):
        """Scale internal render surface to actual display and flip."""
        dw, dh = self.display.get_size()
        if (dw, dh) == (W, H):
            self.display.blit(self.screen, (0, 0))
        else:
            pygame.transform.scale(self.screen, (dw, dh), self.display)
        pygame.display.flip()


# ─────────────────────────────────────────────────────────────────────────────
#  State base class
# ─────────────────────────────────────────────────────────────────────────────
class State:
    """Abstract base for game states."""

    def enter(self, ctx: GameContext) -> None:
        """Called when this state is pushed / becomes active."""
        pass

    def exit(self, ctx: GameContext) -> None:
        """Called when this state is popped / replaced."""
        pass

    def handle_event(self, ctx: GameContext, event: pygame.event.Event) -> None:
        """Process a single pygame event."""
        pass

    def update(self, ctx: GameContext, dt: float) -> None:
        """Per-frame logic update."""
        pass

    def draw(self, ctx: GameContext) -> None:
        """Render this state to ctx.screen."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  GameStateManager — stack-based
# ─────────────────────────────────────────────────────────────────────────────
class GameStateManager:
    """Stack-based state manager. The top state receives events/updates/draws."""

    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self._stack: List[State] = []
        ctx.manager = self

    @property
    def current(self) -> Optional[State]:
        return self._stack[-1] if self._stack else None

    def push(self, state: State) -> None:
        self._stack.append(state)
        state.enter(self.ctx)

    def pop(self) -> Optional[State]:
        """Pop the top state, call its exit(), then enter() the new top (if any).

        This ensures that when a pushed overlay (e.g. Pause) is popped, the
        underlying state is properly re-entered / resumed.
        """
        if not self._stack:
            return None
        state = self._stack.pop()
        state.exit(self.ctx)
        if self._stack:
            self._stack[-1].enter(self.ctx)
        return state

    def replace(self, state: State) -> None:
        """Pop current and push new state."""
        if self._stack:
            self._stack.pop().exit(self.ctx)
        self._stack.append(state)
        state.enter(self.ctx)

    def run(self) -> None:
        """Main game loop."""
        while self._stack:
            dt = min(self.ctx.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.current:
                    self.current.handle_event(self.ctx, event)
            if self.current:
                self.current.update(self.ctx, dt)
            if self.current:
                self.current.draw(self.ctx)
                self.ctx.present()


# ─────────────────────────────────────────────────────────────────────────────
#  Helper functions (used by states)
# ─────────────────────────────────────────────────────────────────────────────
def _new_game(ctx: GameContext) -> None:
    """Reset all gameplay state for a fresh game."""
    ctx.score        = 0
    ctx.level        = 1
    ctx.player       = Player()
    ctx.start_idle_t = 0.0
    _reset_level(ctx)


def _reset_level(ctx: GameContext) -> None:
    """Clear obstacles and timers for a new level."""
    ctx.obstacles   = []
    ctx.level_timer = 0.0
    ctx.spawn_timer = 0.0
    ctx.particles.clear()
    ctx.levelup_t   = 0.0


def _spawn_rate(level: int) -> float:
    return max(MIN_SPAWN, BASE_SPAWN - (level - 1) * SPAWN_DEC)


def _spawn_x_near_player(player, margin, level):
    radius = max(int(90 * SX), int(380 * SX) - (level - 1) * int(28 * SX))
    px = int(player.x)
    lo = max(margin, px - radius)
    hi = min(W - margin, px + radius)
    if lo >= hi:
        lo, hi = margin, W - margin
    return random.randint(lo, hi)


def _spawn(ctx: GameContext) -> None:
    kind = random.choices(OBS_TYPES, OBS_WEIGHTS)[0]
    cls  = {"vine": Vine, "bomb": Bomb, "spike": Spike, "boulder": Boulder}[kind]
    margins = {
        "vine":    int(50  * SX),
        "bomb":    int(60  * SX),
        "spike":   int(40  * SX),
        "boulder": int(80  * SX),
    }
    sx = _spawn_x_near_player(ctx.player, margins[kind], ctx.level)
    ctx.obstacles.append(cls(ctx.level, spawn_x=sx))


def _draw_scene(ctx: GameContext) -> None:
    """Draw background, obstacles, player, and particles."""
    ctx.screen.blit(ctx.bg, (0, 0))
    for obs in ctx.obstacles:
        obs.draw(ctx.screen)
    ctx.player.draw(ctx.screen)
    ctx.particles.draw(ctx.screen)


# ─────────────────────────────────────────────────────────────────────────────
#  StartScreenState
# ─────────────────────────────────────────────────────────────────────────────
class StartScreenState(State):

    def enter(self, ctx):
        ctx.leaderboard = ctx.persistence.get_board("normal")

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            ctx.toggle_fullscreen()
            return

        if event.key == pygame.K_ESCAPE:
            pass  # no-op on home screen
            return

        if event.key == pygame.K_SPACE:
            _new_game(ctx)
            ctx.manager.replace(PlayState())
            return

        if event.key == pygame.K_TAB:
            ctx.manager.replace(LeaderboardState())

    def update(self, ctx, dt):
        ctx.start_idle_t += dt

    def draw(self, ctx):
        t = pygame.time.get_ticks()
        hud.draw_start_screen(ctx.screen, t, ctx.bg, ctx.leaderboard, ctx.start_idle_t)


# ─────────────────────────────────────────────────────────────────────────────
#  PlayState
# ─────────────────────────────────────────────────────────────────────────────
class PlayState(State):

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            ctx.toggle_fullscreen()
            return

        if event.key == pygame.K_ESCAPE:
            ctx.manager.push(PauseState())

    def update(self, ctx, dt):
        keys = pygame.key.get_pressed()
        ctx.player.update(dt, keys)

        ctx.level_timer += dt
        if ctx.level_timer >= LEVEL_TIME:
            ctx.level    += 1
            ctx.manager.replace(LevelUpState())
            return

        # Spawn
        ctx.spawn_timer += dt
        if ctx.spawn_timer >= _spawn_rate(ctx.level):
            ctx.spawn_timer = 0.0
            _spawn(ctx)

        # Hit detection FIRST (BUG-01/02)
        for obs in ctx.obstacles:
            if obs.alive and not obs.did_hit and obs.check_hit(ctx.player):
                obs.did_hit = True
                ctx.player.hit()
                ctx.particles.pop_text(ctx.player.x, ctx.player.y - int(10 * S),
                                       "OUCH!", CLR["red"])
                break

        # Update obstacles
        for obs in ctx.obstacles:
            obs.update(dt, ctx.player)

        # Scoring (CRIT-01)
        for obs in ctx.obstacles:
            if obs.scored and not obs._pts and not obs.did_hit:
                obs._pts = True
                ctx.score += DODGE_PTS
                pop_y = GROUND_Y - obs.exp_r - int(10 * S) if isinstance(obs, Bomb) else GROUND_Y - int(30 * S)
                ctx.particles.pop_text(obs.x, pop_y, f"+{DODGE_PTS}", CLR["gold"])

        ctx.obstacles = [o for o in ctx.obstacles if o.alive]
        ctx.particles.update(dt)

        # Game over check
        if ctx.player.lives <= 0:
            if ctx.persistence.is_top_score(ctx.score, "normal"):
                ctx.name_input = ""
                ctx.cursor_t   = 0.0
                ctx.cursor_on  = True
                ctx.manager.replace(NameEntryState())
            else:
                ctx.manager.replace(GameOverState())

    def draw(self, ctx):
        _draw_scene(ctx)
        hud.draw_hud(ctx.screen, ctx.score, ctx.level, ctx.level_timer,
                     ctx.player, is_levelup=False)


# ─────────────────────────────────────────────────────────────────────────────
#  PauseState (overlay — pushed on top of PlayState)
# ─────────────────────────────────────────────────────────────────────────────
class PauseState(State):

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            ctx.toggle_fullscreen()
            return

        if event.key == pygame.K_SPACE:
            ctx.manager.pop()  # resume play
            return

        if event.key == pygame.K_ESCAPE:
            ctx.manager.pop()  # pop pause
            _new_game(ctx)
            ctx.manager.replace(StartScreenState())

    def update(self, ctx, dt):
        pass

    def draw(self, ctx):
        # Draw game underneath
        _draw_scene(ctx)
        hud.draw_hud(ctx.screen, ctx.score, ctx.level, ctx.level_timer,
                     ctx.player, is_levelup=False)
        hud.draw_pause_overlay(ctx.screen)


# ─────────────────────────────────────────────────────────────────────────────
#  LevelUpState
# ─────────────────────────────────────────────────────────────────────────────
class LevelUpState(State):

    def enter(self, ctx):
        ctx.levelup_t = 2.8

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_F11:
            ctx.toggle_fullscreen()

    def update(self, ctx, dt):
        ctx.levelup_t -= dt
        # Keep player timers ticking (delegates to Player.tick_timers to
        # avoid duplicating stun/immune countdown logic — review issue #5).
        ctx.player.tick_timers(dt)
        if ctx.levelup_t <= 0:
            _reset_level(ctx)
            ctx.manager.replace(PlayState())

    def draw(self, ctx):
        _draw_scene(ctx)
        hud.draw_hud(ctx.screen, ctx.score, ctx.level, ctx.level_timer,
                     ctx.player, is_levelup=True)
        hud.draw_levelup_overlay(ctx.screen, ctx.level, ctx.score)


# ─────────────────────────────────────────────────────────────────────────────
#  GameOverState
# ─────────────────────────────────────────────────────────────────────────────
class GameOverState(State):

    def enter(self, ctx):
        ctx.leaderboard = ctx.persistence.get_board("normal")

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            ctx.toggle_fullscreen()
            return

        if event.key == pygame.K_SPACE:
            _new_game(ctx)
            ctx.manager.replace(PlayState())
            return

        if event.key == pygame.K_ESCAPE:
            _new_game(ctx)
            ctx.manager.replace(StartScreenState())

    def update(self, ctx, dt):
        pass

    def draw(self, ctx):
        t = pygame.time.get_ticks()
        hud.draw_gameover(ctx.screen, t, ctx.bg, ctx.score, ctx.level,
                          ctx.leaderboard)


# ─────────────────────────────────────────────────────────────────────────────
#  NameEntryState
# ─────────────────────────────────────────────────────────────────────────────
class NameEntryState(State):

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            name = ctx.name_input if ctx.name_input else "-----"
            ctx.persistence.submit_score(name, ctx.score, ctx.level)
            ctx.leaderboard = ctx.persistence.get_board("normal")
            ctx.manager.replace(LeaderboardState())
            return

        if event.key == pygame.K_ESCAPE:
            ctx.persistence.submit_score("-----", ctx.score, ctx.level)
            ctx.leaderboard = ctx.persistence.get_board("normal")
            ctx.manager.replace(LeaderboardState())
            return

        if event.key == pygame.K_BACKSPACE:
            ctx.name_input = ctx.name_input[:-1]
            return

        ch = event.unicode.upper()
        if ch.isalnum() and len(ctx.name_input) < MAX_NAME_LEN:
            ctx.name_input += ch

    def update(self, ctx, dt):
        ctx.cursor_t += dt
        if ctx.cursor_t >= 0.5:
            ctx.cursor_t  = 0.0
            ctx.cursor_on = not ctx.cursor_on

    def draw(self, ctx):
        t = pygame.time.get_ticks()
        hud.draw_name_entry(ctx.screen, t, ctx.score, ctx.level,
                            ctx.name_input, ctx.cursor_on)


# ─────────────────────────────────────────────────────────────────────────────
#  LeaderboardState
# ─────────────────────────────────────────────────────────────────────────────
class LeaderboardState(State):

    def enter(self, ctx):
        ctx.leaderboard = ctx.persistence.get_board("normal")

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            ctx.toggle_fullscreen()
            return

        if event.key == pygame.K_SPACE:
            _new_game(ctx)
            ctx.manager.replace(PlayState())
            return

        if event.key == pygame.K_TAB:
            ctx.manager.replace(StartScreenState())
            return

        if event.key == pygame.K_ESCAPE:
            _new_game(ctx)
            ctx.start_idle_t = 0.0
            ctx.manager.replace(StartScreenState())
            return

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            ctx.manager.replace(StartScreenState())

    def update(self, ctx, dt):
        pass

    def draw(self, ctx):
        t = pygame.time.get_ticks()
        hud.draw_leaderboard(ctx.screen, t, ctx.bg, ctx.leaderboard)
