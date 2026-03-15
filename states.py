"""
Jungle Dodge — State machine and game states (task jd-06)
Stack-based GameStateManager, GameContext shared dataclass, and 7 initial states.
"""

import pygame
import random
import math
import sys

from constants import (
    W, H, SX, SY, S, FPS,
    GROUND_Y,
    CLR,
    LEVEL_TIME, MAX_LIVES, STUN_SECS,
    PLAYER_SPD, DODGE_PTS,
    BASE_SPAWN, SPAWN_DEC, MIN_SPAWN, SPEED_SCALE,
    OBS_TYPES, OBS_WEIGHTS,
    MAX_NAME_LEN,
    STREAK_TIERS,
)
from entities import Player, Vine, Bomb, Spike, Boulder
from hud import (
    HudCache, build_bg,
    draw_game, draw_hud, draw_levelup_overlay, draw_pause_overlay,
    draw_name_entry, draw_leaderboard, draw_gameover, draw_start,
)
from persistence import PersistenceManager
from particles import ParticleSystem


# ─────────────────────────────────────────────────────────────────────────────
#  Streak helpers
# ─────────────────────────────────────────────────────────────────────────────
def streak_multiplier(streak):
    """Return the score multiplier for the current streak count.

    Tiers (from STREAK_TIERS):  0-4 → 1x, 5-9 → 1.5x, 10-19 → 2x, 20+ → 3x.
    """
    result = STREAK_TIERS[0][1]  # default 1.0
    for min_dodges, mult, _label, _color in STREAK_TIERS:
        if streak >= min_dodges:
            result = mult
    return result


def streak_tier_info(streak):
    """Return (multiplier, label, color_key) for the current streak.

    label/color_key are None for the base tier (no badge shown).
    """
    result = STREAK_TIERS[0]
    for tier in STREAK_TIERS:
        if streak >= tier[0]:
            result = tier
    return result[1], result[2], result[3]


# ─────────────────────────────────────────────────────────────────────────────
#  GameContext — shared state passed to all states
# ─────────────────────────────────────────────────────────────────────────────
class GameContext:
    """Holds all shared game state: surfaces, managers, gameplay data."""

    def __init__(self, screen, display, clock):
        # Display
        self.screen     = screen
        self.display    = display
        self.clock      = clock
        self.fullscreen = True

        # Managers
        self.persist   = PersistenceManager()
        self.particles = ParticleSystem()

        # Cached drawing surfaces
        self.hud_cache = HudCache()
        self.bg        = build_bg()

        # Leaderboard (cached from persistence)
        self.leaderboard = self.persist.get_board("normal")

        # Gameplay state
        self.player      = Player()
        self.obstacles   = []
        self.score       = 0
        self.streak      = 0
        self.level       = 1
        self.level_timer = 0.0
        self.spawn_timer = 0.0
        self.levelup_t   = 0.0

        # Name entry
        self.name_input = ""
        self.cursor_t   = 0.0
        self.cursor_on  = True

        # Start screen
        self.start_idle_t = 0.0

    def new_game(self):
        """Reset all gameplay state for a fresh run."""
        self.score        = 0
        self.streak       = 0
        self.level        = 1
        self.player       = Player()
        self.start_idle_t = 0.0
        self.reset_level()

    def reset_level(self):
        """Clear obstacles and timers for a new level."""
        self.obstacles   = []
        self.level_timer = 0.0
        self.spawn_timer = 0.0
        self.particles.clear()
        self.levelup_t   = 0.0

    def present(self):
        """Scale internal render surface to actual display and flip."""
        dw, dh = self.display.get_size()
        if (dw, dh) == (W, H):
            self.display.blit(self.screen, (0, 0))
        else:
            pygame.transform.scale(self.screen, (dw, dh), self.display)
        pygame.display.flip()

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.display = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
            pygame.mouse.set_visible(False)
        else:
            self.display = pygame.display.set_mode((1280, 720))
            pygame.mouse.set_visible(True)


# ─────────────────────────────────────────────────────────────────────────────
#  State base class
# ─────────────────────────────────────────────────────────────────────────────
class State:
    """Base class for all game states."""

    def __init__(self, mgr):
        self.mgr = mgr
        self.ctx = mgr.ctx

    def enter(self):
        """Called when this state becomes active (pushed or swapped in)."""
        pass

    def exit(self):
        """Called when this state is removed (popped or swapped out)."""
        pass

    def handle_event(self, event):
        """Process a single pygame event."""
        pass

    def update(self, dt):
        """Advance state logic by dt seconds."""
        pass

    def draw(self):
        """Render this state to ctx.screen."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  GameStateManager — stack-based state management
# ─────────────────────────────────────────────────────────────────────────────
class GameStateManager:
    """Manages a stack of game states. Delegates events/update/draw to top."""

    def __init__(self, ctx):
        self.ctx    = ctx
        self._stack = []

    def push(self, state):
        """Push a new state onto the stack and enter it."""
        self._stack.append(state)
        state.enter()

    def pop(self):
        """Pop the top state, call exit, and enter the new top (if any)."""
        if self._stack:
            self._stack[-1].exit()
            self._stack.pop()

    def swap(self, state):
        """Replace the top state with a new one."""
        if self._stack:
            self._stack[-1].exit()
            self._stack[-1] = state
        else:
            self._stack.append(state)
        state.enter()

    @property
    def current(self):
        """The currently active (top) state, or None."""
        return self._stack[-1] if self._stack else None

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def draw(self):
        if self.current:
            self.current.draw()


# ─────────────────────────────────────────────────────────────────────────────
#  StartScreenState
# ─────────────────────────────────────────────────────────────────────────────
class StartScreenState(State):

    def enter(self):
        self.ctx.start_idle_t = 0.0

    def update(self, dt):
        self.ctx.start_idle_t += dt

    def draw(self):
        t = pygame.time.get_ticks()
        draw_start(self.ctx.screen, self.ctx.bg, self.ctx.hud_cache,
                   self.ctx.leaderboard, self.ctx.start_idle_t, t)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            self.ctx.toggle_fullscreen()
            return

        if event.key == pygame.K_SPACE:
            self.ctx.new_game()
            self.mgr.swap(PlayState(self.mgr))
        elif event.key == pygame.K_TAB:
            self.mgr.swap(LeaderboardState(self.mgr))
        elif event.key == pygame.K_ESCAPE:
            pass  # ESC on home is a no-op


# ─────────────────────────────────────────────────────────────────────────────
#  PlayState
# ─────────────────────────────────────────────────────────────────────────────
class PlayState(State):

    def _spawn_rate(self):
        return max(MIN_SPAWN, BASE_SPAWN - (self.ctx.level - 1) * SPAWN_DEC)

    def _spawn_x_near_player(self, margin):
        ctx = self.ctx
        radius = max(int(90 * SX), int(380 * SX) - (ctx.level - 1) * int(28 * SX))
        px = int(ctx.player.x)
        lo = max(margin, px - radius)
        hi = min(W - margin, px + radius)
        if lo >= hi:
            lo, hi = margin, W - margin
        return random.randint(lo, hi)

    def _spawn(self):
        ctx  = self.ctx
        kind = random.choices(OBS_TYPES, OBS_WEIGHTS)[0]
        cls  = {"vine": Vine, "bomb": Bomb, "spike": Spike, "boulder": Boulder}[kind]
        margins = {
            "vine":    int(50  * SX),
            "bomb":    int(60  * SX),
            "spike":   int(40  * SX),
            "boulder": int(80  * SX),
        }
        sx = self._spawn_x_near_player(margins[kind])
        ctx.obstacles.append(cls(ctx.level, spawn_x=sx))

    def update(self, dt):
        ctx = self.ctx

        # Player movement
        keys = pygame.key.get_pressed()
        ctx.player.update(dt, keys)

        # Level timer
        ctx.level_timer += dt
        if ctx.level_timer >= LEVEL_TIME:
            ctx.level    += 1
            ctx.levelup_t = 2.8
            self.mgr.swap(LevelUpState(self.mgr))
            return

        # Spawn
        ctx.spawn_timer += dt
        if ctx.spawn_timer >= self._spawn_rate():
            ctx.spawn_timer = 0.0
            self._spawn()

        # Hit detection FIRST (BUG-01/02)
        for obs in ctx.obstacles:
            if obs.alive and not obs.did_hit and obs.check_hit(ctx.player):
                obs.did_hit = True
                # Streak break — emit "STREAK LOST" if streak was notable
                if ctx.streak >= 5:
                    ctx.particles.pop_text(
                        ctx.player.x,
                        ctx.player.y - int(40 * S),
                        "STREAK LOST", CLR["red"],
                    )
                ctx.streak = 0
                ctx.player.hit()
                ctx.particles.pop_text(ctx.player.x, ctx.player.y - int(10 * S),
                                       "OUCH!", CLR["red"])
                break

        # Update obstacles
        for obs in ctx.obstacles:
            obs.update(dt, ctx.player)

        # Scoring (skip obstacles that hit the player — CRIT-01)
        for obs in ctx.obstacles:
            if obs.scored and not obs._pts and not obs.did_hit:
                obs._pts = True
                ctx.streak += 1
                mult = streak_multiplier(ctx.streak)
                pts = int(DODGE_PTS * mult)
                ctx.score += pts
                pop_y = (GROUND_Y - obs.exp_r - int(10 * S)
                         if isinstance(obs, Bomb) else GROUND_Y - int(30 * S))
                label = f"+{pts}" if mult <= 1.0 else f"+{pts} x{mult:g}"
                ctx.particles.pop_text(obs.x, pop_y, label, CLR["gold"])

        ctx.obstacles = [o for o in ctx.obstacles if o.alive]

        # Update particles
        ctx.particles.update(dt)

        # Game over check
        if ctx.player.lives <= 0:
            if ctx.persist.is_top_score(ctx.score, "normal"):
                ctx.name_input = ""
                ctx.cursor_t   = 0.0
                ctx.cursor_on  = True
                self.mgr.swap(NameEntryState(self.mgr))
            else:
                self.mgr.swap(GameOverState(self.mgr))

    def draw(self):
        ctx = self.ctx
        draw_game(ctx.screen, ctx.bg, ctx.obstacles, ctx.player, ctx.particles)
        draw_hud(ctx.screen, ctx.hud_cache, ctx.score, ctx.level,
                 ctx.level_timer, ctx.player, streak=ctx.streak, is_levelup=False)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            self.ctx.toggle_fullscreen()
        elif event.key == pygame.K_ESCAPE:
            self.mgr.swap(PauseState(self.mgr))
        elif event.key == pygame.K_SPACE:
            self.ctx.player.start_roll()


# ─────────────────────────────────────────────────────────────────────────────
#  PauseState
# ─────────────────────────────────────────────────────────────────────────────
class PauseState(State):

    def draw(self):
        ctx = self.ctx
        # Draw the game underneath
        draw_game(ctx.screen, ctx.bg, ctx.obstacles, ctx.player, ctx.particles)
        draw_hud(ctx.screen, ctx.hud_cache, ctx.score, ctx.level,
                 ctx.level_timer, ctx.player, streak=ctx.streak, is_levelup=False)
        draw_pause_overlay(ctx.screen, ctx.hud_cache)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            self.ctx.toggle_fullscreen()
        elif event.key == pygame.K_SPACE:
            self.mgr.swap(PlayState(self.mgr))  # resume (no reset)
        elif event.key == pygame.K_ESCAPE:
            self.ctx.new_game()
            self.mgr.swap(StartScreenState(self.mgr))


# ─────────────────────────────────────────────────────────────────────────────
#  LevelUpState
# ─────────────────────────────────────────────────────────────────────────────
class LevelUpState(State):

    def update(self, dt):
        ctx = self.ctx
        ctx.levelup_t -= dt

        # Keep player stun timers ticking
        p = ctx.player
        if p.stun_t > 0:
            p.stun_t   = max(0.0, p.stun_t - dt)
            p.flash_t += dt * 12
        if p.immune_t > 0:
            p.immune_t = max(0.0, p.immune_t - dt)

        if ctx.levelup_t <= 0:
            ctx.reset_level()
            self.mgr.swap(PlayState(self.mgr))

    def draw(self):
        ctx = self.ctx
        draw_game(ctx.screen, ctx.bg, ctx.obstacles, ctx.player, ctx.particles)
        draw_hud(ctx.screen, ctx.hud_cache, ctx.score, ctx.level,
                 ctx.level_timer, ctx.player, streak=ctx.streak, is_levelup=True)
        draw_levelup_overlay(ctx.screen, ctx.hud_cache, ctx.level, ctx.score)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_F11:
            self.ctx.toggle_fullscreen()
        # ESC during level-up is a no-op


# ─────────────────────────────────────────────────────────────────────────────
#  GameOverState
# ─────────────────────────────────────────────────────────────────────────────
class GameOverState(State):

    def draw(self):
        ctx = self.ctx
        t = pygame.time.get_ticks()
        draw_gameover(ctx.screen, ctx.bg, ctx.hud_cache,
                      ctx.leaderboard, ctx.score, ctx.level, t)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            self.ctx.toggle_fullscreen()
        elif event.key == pygame.K_SPACE:
            self.ctx.new_game()
            self.mgr.swap(PlayState(self.mgr))
        elif event.key == pygame.K_ESCAPE:
            self.ctx.new_game()
            self.ctx.start_idle_t = 0.0
            self.mgr.swap(StartScreenState(self.mgr))


# ─────────────────────────────────────────────────────────────────────────────
#  NameEntryState
# ─────────────────────────────────────────────────────────────────────────────
class NameEntryState(State):

    def update(self, dt):
        ctx = self.ctx
        ctx.cursor_t += dt
        if ctx.cursor_t >= 0.5:
            ctx.cursor_t  = 0.0
            ctx.cursor_on = not ctx.cursor_on

    def draw(self):
        ctx = self.ctx
        t = pygame.time.get_ticks()
        draw_name_entry(ctx.screen, ctx.hud_cache,
                        ctx.name_input, ctx.cursor_on, ctx.score, ctx.level, t)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        ctx = self.ctx

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            name = ctx.name_input if ctx.name_input else "-----"
            self._submit(name)
        elif event.key == pygame.K_BACKSPACE:
            ctx.name_input = ctx.name_input[:-1]
        elif event.key == pygame.K_ESCAPE:
            self._submit("-----")
        else:
            ch = event.unicode.upper()
            if ch.isalnum() and len(ctx.name_input) < MAX_NAME_LEN:
                ctx.name_input += ch

    def _submit(self, name):
        ctx = self.ctx
        ctx.persist.submit_score(name, ctx.score, ctx.level)
        ctx.leaderboard = ctx.persist.get_board("normal")
        self.mgr.swap(LeaderboardState(self.mgr))


# ─────────────────────────────────────────────────────────────────────────────
#  LeaderboardState
# ─────────────────────────────────────────────────────────────────────────────
class LeaderboardState(State):

    def draw(self):
        ctx = self.ctx
        t = pygame.time.get_ticks()
        draw_leaderboard(ctx.screen, ctx.bg, ctx.hud_cache,
                         ctx.leaderboard, t)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_F11:
            self.ctx.toggle_fullscreen()
        elif event.key == pygame.K_SPACE:
            self.ctx.new_game()
            self.mgr.swap(PlayState(self.mgr))
        elif event.key == pygame.K_TAB:
            self.mgr.swap(StartScreenState(self.mgr))
        elif event.key == pygame.K_ESCAPE:
            self.ctx.new_game()
            self.ctx.start_idle_t = 0.0
            self.mgr.swap(StartScreenState(self.mgr))
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.mgr.swap(StartScreenState(self.mgr))
