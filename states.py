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
    LEVEL_TIME, MAX_LIVES, STUN_SECS,
    DODGE_PTS,
    NEAR_MISS_PTS, NEAR_MISS_THRESHOLD,
    BASE_SPAWN, SPAWN_DEC, MIN_SPAWN, SPEED_SCALE,
    OBS_TYPES, OBS_WEIGHTS,
    MAX_NAME_LEN,
    STREAK_TIERS, STREAK_LOST_THRESHOLD,
    WAVE_PHASES, CRESCENDO_SEPARATION,
)
from entities import Player, Obstacle, Vine, Bomb, Spike, Boulder
from particles import ParticleSystem
from persistence import PersistenceManager
import hud
from hud import HudCache
import themes


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
    streak: int = 0
    level: int = 1
    level_timer: float = 0.0
    spawn_timer: float = 0.0
    levelup_t: float = 0.0
    leaderboard: List = field(default_factory=list)
    near_misses: int = 0  # run-stat counter for near-miss events (jd-10)

    # HUD cache (lazy-init)
    hud_cache: Optional[hud.HudCache] = None

    # Name entry
    name_input: str = ""
    cursor_t: float = 0.0
    cursor_on: bool = True

    # Start screen
    start_idle_t: float = 0.0

    # Background
    bg: Optional[pygame.Surface] = None

    # Audio manager (wired in main.py; None = audio unavailable)
    audio: Optional[object] = None

    # Active visual theme (dict from themes.py)
    theme: Optional[dict] = None

    # Pre-allocated HUD surface cache
    hud_cache: Optional[HudCache] = None

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
    ctx.streak       = 0
    ctx.level        = 1
    ctx.streak       = 0
    ctx.near_misses  = 0
    ctx.player       = Player()
    ctx.start_idle_t = 0.0
    if ctx.hud_cache is None:
        ctx.hud_cache = hud.HudCache()
    _reset_level(ctx)


def get_streak_multiplier(streak: int) -> float:
    """Return the score multiplier for the current streak count.

    Uses STREAK_TIERS 4-tuple format: (min_dodges, multiplier, label, color_key).
    Tiers: 0-4 -> 1.0x, 5-9 -> 1.5x, 10-19 -> 2.0x, 20+ -> 3.0x.
    """
    result = STREAK_TIERS[0][1]
    for min_dodges, mult, _label, _color in STREAK_TIERS:
        if streak >= min_dodges:
            result = mult
    return result


def streak_multiplier(streak: int) -> float:
    """Alias for get_streak_multiplier — used by tests and hud module."""
    return get_streak_multiplier(streak)


def streak_tier_info(streak: int):
    """Return (multiplier, label, color_key) for the current streak.

    label/color_key are None at the base tier (no badge shown).
    """
    result = STREAK_TIERS[0]
    for tier in STREAK_TIERS:
        if streak >= tier[0]:
            result = tier
    return result[1], result[2], result[3]


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


def _get_wave_phase_modifier(level_t: float):
    """Return (spawn_interval_modifier, phase_name) for level_t seconds.

    modifier < 1.0 means faster spawns (push), > 1.0 means slower (breather).
    """
    for start, end, name, mod in WAVE_PHASES:
        if start <= level_t < end:
            return mod, name
    return 1.0, "calm"


def _spawn_dual(ctx: GameContext) -> None:
    """Spawn two obstacles simultaneously with CRESCENDO_SEPARATION minimum gap."""
    cls_map = {"vine": Vine, "bomb": Bomb, "spike": Spike, "boulder": Boulder}
    margins = {
        "vine":    int(50  * SX),
        "bomb":    int(60  * SX),
        "spike":   int(40  * SX),
        "boulder": int(80  * SX),
    }
    kind1 = random.choices(OBS_TYPES, OBS_WEIGHTS)[0]
    kind2 = random.choices(OBS_TYPES, OBS_WEIGHTS)[0]
    sx1 = _spawn_x_near_player(ctx.player, margins[kind1], ctx.level)
    ctx.obstacles.append(cls_map[kind1](ctx.level, spawn_x=sx1))
    min_sep = int(W * CRESCENDO_SEPARATION)
    margin2 = margins[kind2]
    if sx1 + min_sep <= W - margin2:
        sx2 = random.randint(sx1 + min_sep, W - margin2)
    elif sx1 - min_sep >= margin2:
        sx2 = random.randint(margin2, sx1 - min_sep)
    else:
        if sx1 < W // 2:
            sx2 = random.randint(W // 2 + margin2, W - margin2)
        else:
            sx2 = random.randint(margin2, W // 2 - margin2)
    ctx.obstacles.append(cls_map[kind2](ctx.level, spawn_x=sx2))


def _draw_scene(ctx: GameContext) -> None:
    """Draw background, obstacles, player, and particles."""
    ctx.screen.blit(ctx.bg, (0, 0))
    for obs in ctx.obstacles:
        obs.draw(ctx.screen, theme=ctx.theme)
    if ctx.player is not None:
        ctx.player.draw(ctx.screen, ctx.particles, theme=ctx.theme)
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
        if ctx.hud_cache is None:
            ctx.hud_cache = hud.HudCache()
        hud.draw_start(ctx.screen, ctx.bg, ctx.hud_cache, ctx.leaderboard, ctx.start_idle_t, t, theme=ctx.theme)


# ─────────────────────────────────────────────────────────────────────────────
#  PlayState
# ─────────────────────────────────────────────────────────────────────────────
class PlayState(State):

    @staticmethod
    def _get_spawn_interval_modifier(level_t: float):
        """Static alias for test compatibility (delegates to module function)."""
        return _get_wave_phase_modifier(level_t)

    def handle_event(self, ctx, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            ctx.toggle_fullscreen()
            return

        if event.key == pygame.K_ESCAPE:
            ctx.manager.push(PauseState())
            return

        if event.key == pygame.K_SPACE:
            ctx.player.start_roll()

    def update(self, ctx, dt):
        keys = pygame.key.get_pressed()
        ctx.player.update(dt, keys)

        # ── Roll trail particles ────────────────────────────────────────────
        if ctx.player.rolling:
            # Emit small trail particles behind the player during roll
            trail_x = ctx.player.x - ctx.player.roll_dir * int(16 * SX)
            trail_y = ctx.player.y + ctx.player.PH // 2
            ctx.particles.emit(
                trail_x, trail_y,
                count=2,
                color=themes.get_color("roll_ready", ctx.theme),
                lifetime=0.25,
                speed_range=(40 * SX, 120 * SX),
                spread=math.pi,
                gravity=0.0,
                drag=3.0,
                size=float(int(5 * S)),
                size_end=0.0,
                alpha=1.0,
                alpha_end=0.0,
                shape="circle",
            )

        ctx.level_timer += dt
        if ctx.level_timer >= LEVEL_TIME:
            ctx.level    += 1
            ctx.manager.replace(LevelUpState())
            return

        # Wave rhythm — get current phase modifier
        wave_mod, wave_phase = _get_wave_phase_modifier(ctx.level_timer)

        # Spawn (apply wave modifier to base interval)
        ctx.spawn_timer += dt
        modified_rate = _spawn_rate(ctx.level) * wave_mod
        if ctx.spawn_timer >= modified_rate:
            ctx.spawn_timer = 0.0
            if wave_phase == "crescendo":
                _spawn_dual(ctx)
            else:
                _spawn(ctx)

        # Hit detection FIRST (BUG-01/02)
        for obs in ctx.obstacles:
            if obs.alive and not obs.did_hit and obs.check_hit(ctx.player):
                obs.did_hit = True
                ctx.player.hit()
                ctx.particles.pop_text(ctx.player.x, ctx.player.y - int(10 * S),
                                       "OUCH!", themes.get_color("warning_color", ctx.theme))
                # Streak break
                if ctx.streak >= STREAK_LOST_THRESHOLD:
                    ctx.particles.pop_text(
                        ctx.player.x, ctx.player.y - int(40 * S),
                        "STREAK LOST", themes.get_color("warning_color", ctx.theme))
                ctx.streak = 0
                break

        # Update obstacles
        for obs in ctx.obstacles:
            obs.update(dt, ctx.player)

        # Scoring (CRIT-01) — streak multiplier applied
        for obs in ctx.obstacles:
            if obs.scored and not obs._pts and not obs.did_hit:
                obs._pts = True
                ctx.streak += 1
                multiplier = get_streak_multiplier(ctx.streak)
                pts = int(DODGE_PTS * multiplier)
                ctx.score += pts
                pop_y = (GROUND_Y - obs.exp_r - int(10 * S)
                         if isinstance(obs, Bomb) else GROUND_Y - int(30 * S))
                label = f"+{pts}" if multiplier <= 1.0 else f"+{pts} x{multiplier:g}"
                ctx.particles.pop_text(obs.x, pop_y, label, themes.get_color("hud_primary", ctx.theme))

        # Near-miss detection (jd-10) — check once per obstacle after it scores
        for obs in ctx.obstacles:
            if obs.scored and not obs._near_miss_checked and not obs.did_hit:
                obs._near_miss_checked = True
                if abs(obs.x - ctx.player.x) < NEAR_MISS_THRESHOLD:
                    ctx.score += NEAR_MISS_PTS
                    ctx.near_misses += 1
                    nm_pop_y = (GROUND_Y - obs.exp_r - int(30 * S)
                                if isinstance(obs, Bomb) else GROUND_Y - int(60 * S))
                    ctx.particles.pop_text(
                        obs.x, nm_pop_y, "CLOSE!",
                        themes.get_color("near_miss", ctx.theme)
                    )

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
        hud.draw_hud(ctx.screen, ctx.hud_cache, ctx.score, ctx.level, ctx.level_timer,
                     ctx.player, streak=ctx.streak, is_levelup=False, theme=ctx.theme)


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
        if ctx.player is None:
            return
        # Draw game underneath
        _draw_scene(ctx)
        hud.draw_hud(ctx.screen, ctx.hud_cache, ctx.score, ctx.level, ctx.level_timer,
                     ctx.player, streak=ctx.streak, is_levelup=False, theme=ctx.theme)
        hud.draw_pause_overlay(ctx.screen, ctx.hud_cache)


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
        if ctx.player is not None:
            ctx.player.tick_timers(dt)
        if ctx.levelup_t <= 0:
            _reset_level(ctx)
            ctx.manager.replace(PlayState())

    def draw(self, ctx):
        if ctx.player is None:
            return
        _draw_scene(ctx)
        hud.draw_hud(ctx.screen, ctx.hud_cache, ctx.score, ctx.level, ctx.level_timer,
                     ctx.player, streak=ctx.streak, is_levelup=True, theme=ctx.theme)
        hud.draw_levelup_overlay(ctx.screen, ctx.hud_cache, ctx.level, ctx.score, theme=ctx.theme)


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
        if ctx.hud_cache is None:
            ctx.hud_cache = hud.HudCache()
        hud.draw_gameover(ctx.screen, ctx.bg, ctx.hud_cache, ctx.leaderboard,
                          ctx.score, ctx.level, t, theme=ctx.theme)


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
        if ctx.hud_cache is None:
            ctx.hud_cache = hud.HudCache()
        hud.draw_name_entry(ctx.screen, ctx.hud_cache, ctx.name_input,
                            ctx.cursor_on, ctx.score, ctx.level, t, theme=ctx.theme)


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
        if ctx.hud_cache is None:
            ctx.hud_cache = hud.HudCache()
        hud.draw_leaderboard(ctx.screen, ctx.bg, ctx.hud_cache, ctx.leaderboard, t, theme=ctx.theme)
