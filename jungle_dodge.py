"""
Jungle Dodge — Pygame side-scroller dodge game
Controls: Arrow keys / A-D to move | SPACE to start/restart | ESC to pause/quit
"""

import pygame
import random
import math
import sys
import json
import os

pygame.init()
pygame.font.init()

# ── Window ────────────────────────────────────────────────────────────────────
W, H   = 3840, 2160
SX     = W / 900          # horizontal scale  (≈ 4.267)
SY     = H / 600          # vertical scale    (= 3.6)
S      = SY               # uniform size scale (use vertical as reference)
_fullscreen = True
_display = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
screen   = pygame.Surface((W, H))   # all game drawing targets this surface
pygame.display.set_caption("Jungle Dodge")
pygame.mouse.set_visible(False)
clock  = pygame.time.Clock()
FPS    = 60

def _toggle_fullscreen():
    global _fullscreen, _display
    _fullscreen = not _fullscreen
    if _fullscreen:
        _display = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
        pygame.mouse.set_visible(False)
    else:
        _display = pygame.display.set_mode((1280, 720))
        pygame.mouse.set_visible(True)

def _present():
    """Scale internal render surface to actual display and flip."""
    dw, dh = _display.get_size()
    if (dw, dh) == (W, H):
        _display.blit(screen, (0, 0))
    else:
        pygame.transform.scale(screen, (dw, dh), _display)
    pygame.display.flip()

# ── Layout ────────────────────────────────────────────────────────────────────
GROUND_Y     = H - int(90 * S)   # 2160 - 324 = 1836
PLAYER_FLOOR = GROUND_Y

# ── Palette ───────────────────────────────────────────────────────────────────
CLR = {
    # ── Palette B — Ancient Temple (env + UI) ─────────────────────────────────
    "sky_top"    : (  6,  14,   8),
    "sky_bot"    : ( 14,  30,  12),
    "ground"     : ( 60,  40,  20),
    "grass"      : ( 44,  92,  32),
    "white"      : (255, 255, 255),
    "black"      : (  0,   0,   0),
    "red"        : (220,  50,  50),
    "yellow"     : (255, 210,  30),
    "orange"     : (255, 140,   0),
    "gold"       : (212, 160,  32),   # ancient gold
    "heart"      : (140,  26,  26),
    "heart_empty": ( 40,  10,  10),
    "teal"       : (  0, 200, 160),   # stun bar
    "skin"       : (220, 180, 130),
    "shirt"      : (200, 170, 100),
    "pants"      : ( 80,  60,  40),
    "hat"        : (140, 100,  50),
    "lb_bg"      : ( 10,  25,  10),
    "lb_row_a"   : ( 18,  45,  18),
    "lb_row_b"   : ( 12,  32,  12),
    "silver"     : (192, 192, 192),
    "bronze"     : (205, 127,  50),
    # HUD stone panel
    "stone"      : ( 42,  46,  38),
    "stone_hi"   : ( 62,  68,  56),
    "olive"      : (120, 130,  90),   # HUD muted label colour
    # ── Palette A — Neon Jungle (obstacles only) ──────────────────────────────
    "vine"       : ( 38, 212,  72),   # neon green
    "vine_dk"    : ( 15, 110,  35),
    "lb_border"  : ( 38, 212,  72),   # matches vine
    "bomb"       : ( 25,  25,  25),
    "fuse"       : (255,  90,  20),   # neon orange fuse/explosion
    "spark"      : (255, 200,  50),
    "spike"      : (200,  70, 255),   # electric purple
    "spike_dk"   : (130,  35, 180),
    "boulder"    : (140, 115,  85),
    "boulder_dk" : (100,  80,  60),
}

# ── Game Constants ─────────────────────────────────────────────────────────────
LEVEL_TIME       = 45       # seconds per level
MAX_LIVES        = 3
STUN_SECS        = 3.0
IMMUNE_EXTRA     = 0.15     # grace period after stun visual ends (CRIT-03)
PLAYER_SPD       = int(360 * SX)   # pixels/second (dt-scaled)
DODGE_PTS        = 10
BASE_SPAWN       = 1.5
SPAWN_DEC        = 0.12
MIN_SPAWN        = 0.35
SPEED_SCALE      = 0.25
OBS_TYPES        = ["vine", "bomb", "spike", "boulder"]
OBS_WEIGHTS      = [3, 2, 3, 2]
MAX_NAME_LEN     = 5
LEADERBOARD_SIZE = 10
LB_FILE          = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaderboard.json")

# ── States ─────────────────────────────────────────────────────────────────────
ST_START       = "start"
ST_PLAYING     = "playing"
ST_PAUSED      = "paused"
ST_LEVELUP     = "levelup"
ST_GAMEOVER    = "gameover"
ST_NAME_ENTRY  = "name_entry"
ST_LEADERBOARD = "leaderboard"

# ── Fonts ──────────────────────────────────────────────────────────────────────
def _font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)

F_HUGE  = _font("Impact",          int(90 * S))
F_LARGE = _font("Impact",          int(54 * S))
F_MED   = _font("Arial",           int(30 * S), bold=True)
F_SMALL = _font("Arial",           int(22 * S))
F_TINY  = _font("Arial",           int(17 * S))
F_SERIF = _font("Times New Roman", int(28 * S), bold=True)   # Stone Tablet HUD values
F_SKULL = _font("Segoe UI Symbol", int(24 * S))               # Skull life icons ☠


# ─────────────────────────────────────────────────────────────────────────────
#  Player
# ─────────────────────────────────────────────────────────────────────────────
class Player:
    PW = int(32 * S)
    PH = int(50 * S)

    def __init__(self):
        self.x        = W // 2
        self.y        = PLAYER_FLOOR - self.PH
        self.lives    = MAX_LIVES
        self.stun_t   = 0.0          # visual stun timer
        self.immune_t = 0.0          # hit immunity (slightly longer than stun)
        self.flash_t  = 0.0
        self.walk_t   = 0.0
        self.facing   = 1

    @property
    def rect(self):
        return pygame.Rect(self.x - self.PW // 2, self.y, self.PW, self.PH)

    def is_stunned(self):
        return self.stun_t > 0

    def is_hit_immune(self):
        """True during stun AND brief grace period after (CRIT-03)."""
        return self.immune_t > 0

    def hit(self):
        if self.is_hit_immune():
            return
        self.lives    = max(0, self.lives - 1)   # floor clamp (BUG-03)
        self.stun_t   = STUN_SECS
        self.immune_t = STUN_SECS + IMMUNE_EXTRA
        self.flash_t  = 0.0

    def update(self, dt, keys):
        # Both keys held → neutral (BUG-08)
        ml = keys[pygame.K_LEFT]  or keys[pygame.K_a]
        mr = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        dx = 0.0
        if ml and not mr:
            dx = -PLAYER_SPD * dt   # dt-scaled (BUG-07)
            self.facing = -1
        elif mr and not ml:
            dx =  PLAYER_SPD * dt
            self.facing =  1

        self.walk_t = (self.walk_t + dt * 8) if dx != 0 else 0.0
        self.x = max(self.PW // 2, min(W - self.PW // 2, self.x + dx))

        if self.stun_t > 0:
            self.stun_t  = max(0.0, self.stun_t - dt)
            self.flash_t += dt * 12
        if self.immune_t > 0:
            self.immune_t = max(0.0, self.immune_t - dt)

    def draw(self, surf):
        stunned = self.is_stunned()
        if stunned and int(self.flash_t) % 2 == 1:
            return

        cx   = self.x
        boty = self.y + self.PH
        sw   = math.sin(self.walk_t) * int(9 * S) if self.walk_t else 0

        o5  = int(5  * S)
        o36 = int(36 * S)
        o4  = int(4  * S)
        o7  = int(7  * S)
        o22 = int(22 * S)
        o12 = int(12 * S)
        o20 = int(20 * S)
        o14 = int(14 * S)
        o16 = int(16 * S)
        o13 = int(13 * S)
        o26 = int(26 * S)
        o10 = int(10 * S)
        o2  = int(2  * S)
        o17 = int(17 * S)
        o18 = int(18 * S)
        o9  = int(9  * S)
        o3  = int(3  * S)

        # Legs
        lleg = (cx - o5 + int(sw), boty)
        rleg = (cx + o5 - int(sw), boty)
        pygame.draw.line(surf, CLR["pants"], (cx - o5, self.y + o36), lleg, max(1, int(5 * S)))
        pygame.draw.line(surf, CLR["pants"], (cx + o5, self.y + o36), rleg, max(1, int(5 * S)))
        pygame.draw.circle(surf, (50, 35, 20), lleg, o4)
        pygame.draw.circle(surf, (50, 35, 20), rleg, o4)

        # Arms
        aw = math.sin(self.walk_t + math.pi) * o7 if self.walk_t else 0
        ay = self.y + o22
        pygame.draw.line(surf, CLR["shirt"], (cx - o12, ay), (cx - o20, ay + o14 + int(aw)), max(1, int(4 * S)))
        pygame.draw.line(surf, CLR["shirt"], (cx + o12, ay), (cx + o20, ay + o14 - int(aw)), max(1, int(4 * S)))

        # Body
        bcol = CLR["shirt"] if not stunned else (255, 255, 100)
        pygame.draw.rect(surf, bcol, (cx - o13, self.y + o16, o26, o22), border_radius=o4)

        # Head
        hcy  = self.y + o10
        hcol = CLR["skin"] if not stunned else (255, 230, 150)
        pygame.draw.circle(surf, hcol, (cx, hcy), o12)
        pygame.draw.circle(surf, (30, 20, 10), (cx + o4 * self.facing, hcy), o2)

        # Explorer hat
        hcol2 = CLR["hat"] if not stunned else (180, 140, 70)
        pygame.draw.ellipse(surf, hcol2, (cx - o17, hcy - o5, int(34 * S), o9))
        pygame.draw.rect(surf,   hcol2, (cx - o9, hcy - o17, o18, o13), border_radius=o3)
        pygame.draw.rect(surf, (100, 70, 30), (cx - o9, hcy - int(6 * S), o18, o3))

        # Stun stars
        if stunned:
            for i in range(3):
                angle = self.flash_t + i * (2 * math.pi / 3)
                sx = cx + int(int(22 * S) * math.cos(angle))
                sy = self.y - o4 + int(o9 * math.sin(angle))
                pygame.draw.circle(surf, CLR["yellow"], (sx, sy), o4)
                pygame.draw.circle(surf, CLR["white"],  (sx, sy), o2)


# ─────────────────────────────────────────────────────────────────────────────
#  Obstacle Base
# ─────────────────────────────────────────────────────────────────────────────
class Obstacle:
    def __init__(self):
        self.alive   = True
        self.scored  = False   # True once obstacle reaches ground
        self._pts    = False   # True once points have been awarded
        self.did_hit = False   # True if this obstacle hit the player (CRIT-01)

    def update(self, dt, player): pass
    def draw(self, surf):         pass
    def check_hit(self, player):  return False


# ─────────────────────────────────────────────────────────────────────────────
#  Vine
# ─────────────────────────────────────────────────────────────────────────────
class Vine(Obstacle):
    BW = int(14 * S)
    BH = int(65 * S)

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x        = float(spawn_x if spawn_x is not None else random.randint(int(50 * SX), W - int(50 * SX)))
        self.y        = float(-self.BH)
        mult          = 1 + (level - 1) * SPEED_SCALE * 0.8
        self.vy       = (90 + level * 15) * mult * SY
        self.sway_t   = random.uniform(0, math.pi * 2)
        self.sway_s   = random.uniform(1.5, 3.0)
        self.sway_a   = random.uniform(8, 18) * SX
        self.landed   = False
        self.land_t   = 0.0
        self.land_dur = 0.8

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - self.BW // 2, int(self.y), self.BW, self.BH)

    def update(self, dt, player):
        if not self.landed:
            self.y      += self.vy * dt
            self.sway_t += dt * self.sway_s
            self.x      += math.sin(self.sway_t) * self.sway_a * dt
            self.x       = max(self.BW, min(W - self.BW, self.x))
            if self.y + self.BH >= GROUND_Y:
                self.y      = float(GROUND_Y - self.BH)
                self.landed = True
                self.scored = True
        else:
            self.land_t += dt
            if self.land_t >= self.land_dur:
                self.alive = False

    def check_hit(self, player):
        return (not self.landed and not player.is_hit_immune()
                and self.rect.colliderect(player.rect))

    def draw(self, surf):
        segs  = 9
        seg_h = self.BH // segs
        sway_off = int(3 * S)
        leaf_w = int(11 * S)
        leaf_h = int(6  * S)
        for i in range(segs):
            sy  = int(self.y) + i * seg_h
            off = int(math.sin(self.sway_t + i * 0.5) * sway_off)
            col = CLR["vine"] if i % 2 == 0 else CLR["vine_dk"]
            pygame.draw.rect(surf, col,
                             (int(self.x) - self.BW // 2 + off, sy, self.BW, seg_h + 1))
            if i % 3 == 1:
                lx = int(self.x) + self.BW // 2 + off
                pygame.draw.ellipse(surf, CLR["vine"], (lx, sy + 1, leaf_w, leaf_h))
        pygame.draw.circle(surf, CLR["vine_dk"],
                           (int(self.x), int(self.y + self.BH)), int(5 * S))


# ─────────────────────────────────────────────────────────────────────────────
#  Bomb
# ─────────────────────────────────────────────────────────────────────────────
class Bomb(Obstacle):
    R = int(18 * S)

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x             = float(spawn_x if spawn_x is not None else random.randint(int(60 * SX), W - int(60 * SX)))
        self.y             = float(-self.R * 2)
        mult               = 1 + (level - 1) * SPEED_SCALE * 1.1
        self.vy            = (175 + level * 22) * mult * SY
        self.fuse_t        = 0.0
        self.spark_t       = 0.0
        self.exploded      = False
        self.exp_t         = 0.0
        self.exp_dur       = 0.55
        self.exp_r         = int(72 * S)
        self._exp_hit_done = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - self.R, int(self.y) - self.R,
                           self.R * 2, self.R * 2)

    def update(self, dt, player):
        if self.exploded:
            self.exp_t += dt
            if self.exp_t >= self.exp_dur:
                self.alive = False
            return

        self.y       += self.vy * dt
        self.fuse_t  += dt * 6
        self.spark_t += dt * 14

        if self.y >= GROUND_Y - self.R:
            self.y        = float(GROUND_Y - self.R)
            self.exploded = True
            self.scored   = True

    def check_hit(self, player):
        if player.is_hit_immune():
            return False
        if not self.exploded:
            return self.rect.colliderect(player.rect)
        # Explosion radius — checked once on the frame explosion starts
        if not self._exp_hit_done:
            self._exp_hit_done = True
            dist = math.hypot(self.x - player.x,
                              self.y - (player.y + player.PH // 2))
            return dist < self.exp_r
        return False

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        if self.exploded:
            prog = self.exp_t / max(self.exp_dur, 0.001)
            r    = int(self.exp_r * prog)
            if r > 0:
                c1 = (255, max(0, 160 - int(160 * prog)), 20)
                pygame.draw.circle(surf, c1,             (cx, cy), r)
                pygame.draw.circle(surf, (255, 240, 100), (cx, cy), max(1, r // 2))
            return

        o4  = int(4 * S)
        o5  = int(5 * S)
        o6  = int(6 * S)
        o10 = int(10 * S)
        o2  = int(2 * S)
        o3  = int(3 * S)

        pygame.draw.circle(surf, CLR["bomb"],  (cx, cy), self.R)
        pygame.draw.circle(surf, (55, 55, 55), (cx - o5, cy - o5), o6)
        fuse_top = (cx + o4, cy - self.R - o10)
        pygame.draw.lines(surf, CLR["fuse"], False,
                          [(cx, cy - self.R), (cx + o2, cy - self.R - o5), fuse_top], max(1, o2))
        sa  = self.spark_t
        spx = fuse_top[0] + int(o3 * math.cos(sa))
        spy = fuse_top[1] + int(o3 * math.sin(sa))
        pygame.draw.circle(surf, CLR["spark"],  (spx, spy), o4)
        pygame.draw.circle(surf, CLR["yellow"], (spx, spy), o2)


# ─────────────────────────────────────────────────────────────────────────────
#  Spike
# ─────────────────────────────────────────────────────────────────────────────
class Spike(Obstacle):
    SW = int(18 * S)
    SH = int(44 * S)

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x  = float(spawn_x if spawn_x is not None else random.randint(int(40 * SX), W - int(40 * SX)))
        self.y  = float(-self.SH)
        mult    = 1 + (level - 1) * SPEED_SCALE * 1.3
        self.vy = (260 + level * 38) * mult * SY

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - self.SW // 2, int(self.y), self.SW, self.SH)

    def update(self, dt, player):
        self.y += self.vy * dt
        if self.y >= GROUND_Y:
            self.scored = True
            self.alive  = False

    def check_hit(self, player):
        return not player.is_hit_immune() and self.rect.colliderect(player.rect)

    def draw(self, surf):
        cx  = int(self.x)
        top = int(self.y)
        tip = int(self.y + self.SH)
        hw  = self.SW // 2
        pts = [(cx - hw, top), (cx + hw, top), (cx, tip)]
        pygame.draw.polygon(surf, CLR["spike"],    pts)
        pygame.draw.polygon(surf, CLR["spike_dk"], pts, max(1, int(2 * S)))
        pygame.draw.line(surf, (220, 220, 240),
                         (cx - hw // 2, top + int(4 * S)), (cx - int(2 * S), tip - int(6 * S)), 1)
        pygame.draw.rect(surf, CLR["spike_dk"], (cx - hw, top, self.SW, int(5 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Boulder
# ─────────────────────────────────────────────────────────────────────────────
class Boulder(Obstacle):
    R = int(30 * S)

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x        = float(spawn_x if spawn_x is not None else random.randint(int(80 * SX), W - int(80 * SX)))
        self.y        = float(-self.R * 2)
        mult          = 1 + (level - 1) * SPEED_SCALE * 0.7
        self.vy       = (100 + level * 12) * mult * SY
        self.rolling  = False
        self.roll_dir = random.choice([-1, 1])
        self.roll_spd = random.uniform(130, 210) * SX
        self.roll_t   = 0.0
        self.roll_dur = max(0.1, random.uniform(1.2, 2.2))
        self.rot      = 0.0
        rng = random.Random(id(self))
        self.cracks = [
            (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6),
             rng.uniform(0.15, 0.45), rng.uniform(0.15, 0.45))
            for _ in range(5)
        ]

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - self.R, int(self.y) - self.R,
                           self.R * 2, self.R * 2)

    def update(self, dt, player):
        if not self.rolling:
            self.y   += self.vy * dt
            self.rot += self.vy * dt * 0.03
            if self.y >= GROUND_Y - self.R:
                self.y       = float(GROUND_Y - self.R)
                self.rolling = True
                self.scored  = True
        else:
            self.roll_t += dt
            spd = self.roll_spd * max(0.0, 1 - self.roll_t / self.roll_dur)
            self.x   += self.roll_dir * spd * dt
            self.rot += self.roll_dir * spd * dt * 0.03
            if self.x < self.R:
                self.x = float(self.R)
                self.roll_dir = 1
            elif self.x > W - self.R:
                self.x = float(W - self.R)
                self.roll_dir = -1
            if self.roll_t >= self.roll_dur:
                self.alive = False

    def check_hit(self, player):
        return not player.is_hit_immune() and self.rect.colliderect(player.rect)

    def _rot_pt(self, px, py):
        c, s = math.cos(self.rot), math.sin(self.rot)
        return (int(self.x + (px * c - py * s) * self.R),
                int(self.y + (px * s + py * c) * self.R))

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        pygame.draw.ellipse(surf, (30, 55, 20),
                            (cx - self.R, cy + self.R - int(8 * S), self.R * 2, int(12 * S)))
        pygame.draw.circle(surf, CLR["boulder"],    (cx, cy), self.R)
        pygame.draw.circle(surf, CLR["boulder_dk"], (cx + int(5 * S), cy + int(5 * S)), self.R - int(6 * S))
        for x1, y1, x2, y2 in self.cracks:
            pygame.draw.line(surf, CLR["boulder_dk"],
                             self._rot_pt(x1, y1), self._rot_pt(x1 + x2, y1 + y2), max(1, int(2 * S)))
        pygame.draw.circle(surf, CLR["boulder_dk"], (cx, cy), self.R, max(1, int(2 * S)))
        pygame.draw.circle(surf, (165, 145, 120),
                           (cx - self.R // 3, cy - self.R // 3), self.R // 4)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def pulse_color(base_col, ticks, speed=0.004, lo=0.65):
    p = lo + (1 - lo) * (0.5 + 0.5 * math.sin(ticks * speed))
    return tuple(int(c * p) for c in base_col)


# ─────────────────────────────────────────────────────────────────────────────
#  Main Game
# ─────────────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.state       = ST_START
        self.bg          = self._build_bg()
        self.score       = 0
        self.level       = 1
        self.leaderboard = self._load_leaderboard()
        self.name_input      = ""
        self.cursor_t        = 0.0
        self.cursor_on       = True
        self.start_idle_t    = 0.0   # seconds idle on start screen (? hint)
        # Cached surfaces (avoid per-frame allocations)
        self._ctrl_panel     = pygame.Surface((int(250 * SX), int(80 * S)), pygame.SRCALPHA)
        self._ctrl_panel.fill((0, 18, 0, 210))
        self._hud_panel      = pygame.Surface((W, int(72 * S)), pygame.SRCALPHA)
        self._hud_panel.fill((*CLR["stone"], 238))
        # Pre-cached overlay surfaces — avoid 33 MB SRCALPHA alloc per frame
        self._ov_levelup  = pygame.Surface((W, H), pygame.SRCALPHA)
        self._ov_levelup.fill((0, 30, 5, 165))
        self._ov_pause    = pygame.Surface((W, H), pygame.SRCALPHA)
        self._ov_pause.fill((0, 0, 0, 160))
        self._ov_lb       = pygame.Surface((W, H), pygame.SRCALPHA)
        self._ov_lb.fill((0, 15, 0, 170))
        self._ov_gameover = pygame.Surface((W, H), pygame.SRCALPHA)
        self._ov_gameover.fill((28, 5, 5, 185))
        # Pre-cached name-entry slot backgrounds (filled / empty)
        _sw = int(72 * S); _sh = int(80 * S)
        self._slot_filled = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self._slot_filled.fill((20, 40, 20, 220))
        self._slot_empty  = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self._slot_empty.fill((10, 22, 10, 220))
        self._reset_level()
        self.player          = Player()

    # ── Leaderboard ──────────────────────────────────────────────────────────
    def _load_leaderboard(self):
        try:
            with open(LB_FILE, "r") as f:
                data = json.load(f)
            return sorted(data, key=lambda e: e["score"], reverse=True)[:LEADERBOARD_SIZE]
        except Exception:
            return []

    def _save_leaderboard(self):
        try:
            with open(LB_FILE, "w") as f:
                json.dump(self.leaderboard, f, indent=2)
        except Exception:
            pass

    def _is_top10(self, score):
        if score <= 0:
            return False
        if len(self.leaderboard) < LEADERBOARD_SIZE:
            return True
        return score > self.leaderboard[-1]["score"]

    def _submit_score(self, name):
        self.leaderboard.append({
            "name": name.upper() or "-----",
            "score": self.score,
            "level": self.level,
        })
        self.leaderboard.sort(key=lambda e: e["score"], reverse=True)
        self.leaderboard = self.leaderboard[:LEADERBOARD_SIZE]
        self._save_leaderboard()

    # ── Init helpers ─────────────────────────────────────────────────────────
    def _reset_level(self):
        self.obstacles   = []
        self.level_timer = 0.0
        self.spawn_timer = 0.0
        self.particles   = []
        self.levelup_t   = 0.0

    def _new_game(self):
        self.score        = 0
        self.level        = 1
        self.player       = Player()
        self.start_idle_t = 0.0
        self._reset_level()

    def _spawn_rate(self):
        return max(MIN_SPAWN, BASE_SPAWN - (self.level - 1) * SPAWN_DEC)

    # ── Background — Jungle Cliff Face (Lost Temple Ruins) ───────────────────
    def _build_bg(self):
        bg  = pygame.Surface((W, H))
        sy  = GROUND_Y / 340      # SVG cliff is 340 tall; game play area is GROUND_Y
        def svy(v): return int(v * sy)
        def svx(v): return int(v * W / 900)   # scale SVG x (900 wide) to game width

        # ── 1. Cliff gradient fill (y=0 → GROUND_Y) ──────────────────────────
        c_top = (26, 24, 16); c_mid = (42, 36, 24); c_bot = (34, 30, 20)
        for y in range(GROUND_Y):
            t = y / GROUND_Y
            if t < 0.4:
                r,g,b = [int(c_top[i]+(c_mid[i]-c_top[i])*(t/0.4)) for i in range(3)]
            else:
                r,g,b = [int(c_mid[i]+(c_bot[i]-c_mid[i])*((t-0.4)/0.6)) for i in range(3)]
            pygame.draw.line(bg, (r, g, b), (0, y), (W, y))

        # ── 2. Horizontal strata lines ────────────────────────────────────────
        sc = (26, 24, 8)
        for svg_y in [55, 95, 140, 185, 230, 275]:
            pygame.draw.line(bg, sc, (0, svy(svg_y)), (W, svy(svg_y)), 1)

        # ── 3. Crack network ──────────────────────────────────────────────────
        cc = (12, 10, 6)
        def crack(pts, w=2):
            pygame.draw.lines(bg, cc, False, [(svx(x), svy(y)) for x,y in pts], w)
        crack([(50,60),(65,95),(55,140),(70,185),(60,230),(72,275),(65,330)], 2)
        crack([(65,120),(82,145)], 1)
        crack([(200,55),(188,95),(198,140),(185,175)], 1)
        crack([(700,65),(715,110),(705,155),(718,200),(708,245),(720,290)], 2)
        crack([(715,155),(730,175)], 1)
        crack([(830,80),(818,125),(828,170)], 1)
        crack([(400,100),(388,140),(400,170),(390,210),(402,245)], 1)

        # ── 4. Deity face ─────────────────────────────────────────────────────
        FACE   = (37, 32, 24)
        CROWN  = (34, 30, 20)
        TRICRN = (42, 36, 24)
        DARK   = (14, 12,  8)

        cx0 = W // 2   # face center x (scaled)

        # Face ellipse (width scaled by SX, height by svy)
        fw = int(176 * SX / 2)   # half-width
        pygame.draw.ellipse(bg, FACE,
            (cx0 - fw, svy(175) - svy(95), fw * 2, svy(190)))
        pygame.draw.ellipse(bg, (26, 22, 16),
            (cx0 - fw, svy(175) - svy(95), fw * 2, svy(190)), 3)

        # Crown base + pillars
        pygame.draw.rect(bg, CROWN, (svx(370), svy(82), svx(160), svy(22)))
        pygame.draw.rect(bg, CROWN, (svx(385), svy(60), svx(22),  svy(26)))
        pygame.draw.rect(bg, CROWN, (svx(430), svy(55), svx(40),  svy(30)))
        pygame.draw.rect(bg, CROWN, (svx(493), svy(60), svx(22),  svy(26)))

        # Crown triangle points
        pygame.draw.polygon(bg, TRICRN, [(svx(388),svy(82)),(svx(399),svy(58)),(svx(410),svy(82))])
        pygame.draw.polygon(bg, TRICRN, [(svx(432),svy(82)),(svx(450),svy(50)),(svx(468),svy(82))])
        pygame.draw.polygon(bg, TRICRN, [(svx(490),svy(82)),(svx(501),svy(58)),(svx(512),svy(82))])

        # Eye sockets
        pygame.draw.rect(bg, DARK, (svx(390), svy(145), svx(48), svy(30)), border_radius=4)
        pygame.draw.rect(bg, DARK, (svx(462), svy(145), svx(48), svy(30)), border_radius=4)

        # Eye teal glow (SRCALPHA — pre-rendered once into bg)
        gw, gh = svx(32), max(1, svy(16))
        eye_s = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.ellipse(eye_s, (0, 200, 160, 46), (0, 0, gw, gh))
        bg.blit(eye_s, (svx(414) - gw // 2, svy(160) - gh // 2))
        bg.blit(eye_s, (svx(486) - gw // 2, svy(160) - gh // 2))

        # Nose ridge
        pygame.draw.lines(bg, (26, 24, 16), False,
            [(svx(440), svy(175)), (svx(450), svy(200)), (svx(460), svy(175))], 4)

        # Mouth + teeth
        pygame.draw.rect(bg, DARK, (svx(410), svy(215), svx(80), svy(22)), border_radius=3)
        for tx in [424, 438, 452, 466, 480]:
            pygame.draw.line(bg, (26, 24, 8),
                (svx(tx), svy(215)), (svx(tx), svy(215) + svy(22)), 2)

        # Geometric frame around face
        pygame.draw.rect(bg, (46, 40, 24), (svx(352), svy(78), svx(196), svy(202)), 4)
        pygame.draw.rect(bg, (38, 32, 14), (svx(358), svy(84), svx(184), svy(190)), 1)

        # Face diagonal damage crack
        crack([(395,105),(420,140),(408,165),(425,195),(415,230)], 3)
        crack([(420,140),(438,148)], 1)

        # ── 5. Vine cascades ──────────────────────────────────────────────────
        VDK = (26, 96, 16)
        VBR = CLR["vine"]   # neon green
        def vine(pts, col, w):
            pygame.draw.lines(bg, col, False, [(svx(x), svy(y)) for x,y in pts], w)

        # Left wall cascade (dark body + bright highlight)
        vine([(0,0),(8,40),(4,80),(11,120),(4,160),(9,200),(3,245),(9,285),(4,340)], VDK, 9)
        vine([(13,0),(19,45),(14,90),(21,130),(13,175),(19,215),(12,260)], VBR, 3)
        # Left secondary cluster
        vine([(100,0),(93,28),(97,58),(90,88),(94,120),(87,155),(92,190),(85,225),(90,265),(83,300),(88,340)], VDK, 6)

        # Right wall cascade
        vine([(900,0),(892,40),(896,80),(889,120),(893,160),(887,200),(891,245),(885,285),(892,340)], VDK, 9)
        vine([(887,0),(880,45),(884,90),(878,135),(883,178),(877,220),(882,260),(876,300)], VBR, 3)
        # Right secondary cluster
        vine([(800,0),(806,30),(803,65),(810,100),(804,135),(812,170),(805,210),(813,250),(806,290),(815,340)], VDK, 6)

        # Vine leaf clusters
        for lx, lsvy, lrx, lry, lcol in [
            (18,  100, 25, 12, VDK),
            (8,   200, 28, 12, VBR),
            (92,  160, 22, 10, VDK),
            (880, 110, 25, 12, VDK),
            (892, 210, 28, 12, VBR),
            (808, 170, 22, 10, VDK),
        ]:
            lrx_s = svx(lrx); lry_s = max(1, svy(lry))
            pygame.draw.ellipse(bg, lcol,
                (svx(lx) - lrx_s, svy(lsvy) - lry_s, lrx_s * 2, lry_s * 2))

        # ── 6. Canopy overhang at cliff top ───────────────────────────────────
        for cx, csv_y, crx, cry, rgb in [
            (100, 10, 140, 50, (14, 32,  8)),
            (300,  5, 180, 45, (12, 28,  6)),
            (550,  8, 200, 48, (14, 32,  8)),
            (800, 12, 150, 50, (12, 28,  6)),
            (450,  0, 120, 35, (18, 40,  8)),
        ]:
            crxs = svx(crx); crys = max(1, svy(cry))
            cs = pygame.Surface((crxs * 2, crys * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(cs, (*rgb, 230), (0, 0, crxs * 2, crys * 2))
            bg.blit(cs, (svx(cx) - crxs, max(0, svy(csv_y) - crys)))
        # Canopy leaf detail
        for cx, csv_y, crx, cry, rgb in [
            ( 80, 25,  60, 30, (20, 48, 16)),
            (220, 18,  80, 32, (22, 46, 14)),
            (420, 15,  90, 28, (20, 48, 16)),
            (680, 20, 100, 35, (22, 46, 14)),
            (880, 28,  60, 28, (20, 48, 16)),
        ]:
            crxs = svx(crx); crys = max(1, svy(cry))
            cs = pygame.Surface((crxs * 2, crys * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(cs, (*rgb, 178), (0, 0, crxs * 2, crys * 2))
            bg.blit(cs, (svx(cx) - crxs, max(0, svy(csv_y) - crys)))

        # ── 7. Ground — flagstone path + grass strip ──────────────────────────
        pygame.draw.rect(bg, CLR["ground"], (0, GROUND_Y, W, H - GROUND_Y))
        FLAG = (26, 18, 8)
        flagstones = [(0,120),(120,140),(260,110),(370,160),(530,130),(660,120),(780,120)]
        for fx, fw in flagstones:
            pygame.draw.rect(bg, FLAG, (svx(fx), GROUND_Y, svx(fw), H - GROUND_Y), 1)
        for pts in [[(60,3),(70,28),(62,50)],[(340,3),(352,25),(344,50)],[(620,3),(610,30),(622,50)]]:
            pygame.draw.lines(bg, (12,10,6), False,
                [(svx(x), GROUND_Y + int(y * S)) for x,y in pts], 1)
        pygame.draw.rect(bg, CLR["grass"], (0, GROUND_Y, W, int(14 * S)))

        # ── 8. Ground mist ────────────────────────────────────────────────────
        mist_h = int(80 * S)
        mist = pygame.Surface((W, mist_h), pygame.SRCALPHA)
        for my in range(mist_h):
            a = int(70 * (1.0 - my / mist_h))
            pygame.draw.line(mist, (26, 48, 20, a), (0, my), (W, my))
        bg.blit(mist, (0, GROUND_Y - int(60 * S)))

        return bg

    # ── Spawning ─────────────────────────────────────────────────────────────
    def _spawn_x_near_player(self, margin):
        """Return an x biased toward the player; radius tightens each level."""
        radius = max(int(90 * SX), int(380 * SX) - (self.level - 1) * int(28 * SX))
        px = int(self.player.x)
        lo = max(margin, px - radius)
        hi = min(W - margin, px + radius)
        if lo >= hi:
            lo, hi = margin, W - margin
        return random.randint(lo, hi)

    def _spawn(self):
        kind = random.choices(OBS_TYPES, OBS_WEIGHTS)[0]
        cls  = {"vine": Vine, "bomb": Bomb, "spike": Spike, "boulder": Boulder}[kind]
        margins = {
            "vine":    int(50  * SX),
            "bomb":    int(60  * SX),
            "spike":   int(40  * SX),
            "boulder": int(80  * SX),
        }
        sx = self._spawn_x_near_player(margins[kind])
        self.obstacles.append(cls(self.level, spawn_x=sx))

    def _pop(self, x, y, text, color):
        self.particles.append({
            "text": text, "x": float(x), "y": float(y),
            "vy": int(-55 * SY), "t": 0.0, "dur": 1.1, "col": color,
        })

    # ── Update ───────────────────────────────────────────────────────────────
    def update(self, dt):
        if self.state == ST_NAME_ENTRY:
            self.cursor_t += dt
            if self.cursor_t >= 0.5:
                self.cursor_t  = 0.0
                self.cursor_on = not self.cursor_on
            return

        if self.state == ST_START:
            self.start_idle_t += dt
            return

        if self.state in (ST_GAMEOVER, ST_LEADERBOARD, ST_PAUSED):
            return

        if self.state == ST_LEVELUP:
            self.levelup_t -= dt
            # Keep player timers ticking so stun doesn't extend by 2.8 s across boundary
            p = self.player
            if p.stun_t > 0:
                p.stun_t   = max(0.0, p.stun_t - dt)
                p.flash_t += dt * 12
            if p.immune_t > 0:
                p.immune_t = max(0.0, p.immune_t - dt)
            if self.levelup_t <= 0:
                self._reset_level()
                self.state = ST_PLAYING
            return

        # ── Playing ──────────────────────────────────────────────────────────
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)

        self.level_timer += dt
        if self.level_timer >= LEVEL_TIME:
            self.level    += 1          # increment immediately (BUG-06)
            self.state     = ST_LEVELUP
            self.levelup_t = 2.8
            return

        # Spawn
        self.spawn_timer += dt
        if self.spawn_timer >= self._spawn_rate():
            self.spawn_timer = 0.0
            self._spawn()

        # Hit detection FIRST — before update, so damaged obstacles don't score (BUG-01/02)
        for obs in self.obstacles:
            if obs.alive and not obs.did_hit and obs.check_hit(self.player):
                obs.did_hit = True
                self.player.hit()
                self._pop(self.player.x, self.player.y - int(10 * S), "OUCH!", CLR["red"])
                break   # one hit per frame max

        # Update obstacles
        for obs in self.obstacles:
            obs.update(dt, self.player)

        # Scoring — skip obstacles that hit the player (CRIT-01)
        for obs in self.obstacles:
            if obs.scored and not obs._pts and not obs.did_hit:
                obs._pts = True
                self.score += DODGE_PTS
                # Pop above explosion fireball for bombs; ground level for others
                pop_y = GROUND_Y - obs.exp_r - int(10 * S) if isinstance(obs, Bomb) else GROUND_Y - int(30 * S)
                self._pop(obs.x, pop_y, f"+{DODGE_PTS}", CLR["gold"])

        self.obstacles = [o for o in self.obstacles if o.alive]

        # Float text
        for p in self.particles:
            p["t"] += dt
            p["y"] += p["vy"] * dt
        self.particles = [p for p in self.particles if p["t"] < p["dur"]]

        # Game over check
        if self.player.lives <= 0:
            if self._is_top10(self.score):
                self.name_input = ""
                self.cursor_t   = 0.0
                self.cursor_on  = True
                self.state = ST_NAME_ENTRY
            else:
                self.state = ST_GAMEOVER

    # ── Draw dispatcher ──────────────────────────────────────────────────────
    def draw(self):
        t = pygame.time.get_ticks()
        if self.state == ST_START:
            self._draw_start(t)
        elif self.state in (ST_PLAYING, ST_LEVELUP):
            self._draw_game()
            if self.state == ST_LEVELUP:
                self._draw_levelup_overlay()
        elif self.state == ST_PAUSED:
            self._draw_game()
            self._draw_pause_overlay()
        elif self.state == ST_NAME_ENTRY:
            self._draw_name_entry(t)
        elif self.state == ST_LEADERBOARD:
            self._draw_leaderboard(t)
        elif self.state == ST_GAMEOVER:
            self._draw_gameover(t)
        _present()

    # ── Game screen ──────────────────────────────────────────────────────────
    def _draw_game(self):
        screen.blit(self.bg, (0, 0))
        for obs in self.obstacles:
            obs.draw(screen)
        self.player.draw(screen)
        for p in self.particles:
            a = max(0.0, 1.0 - p["t"] / p["dur"])
            if a < 0.02:
                continue
            if "_surf" not in p:
                p["_surf"] = F_MED.render(p["text"], True, p["col"])
            surf = p["_surf"]
            surf.set_alpha(int(a * 255))
            screen.blit(surf, (int(p["x"]) - surf.get_width() // 2, int(p["y"])))
        self._draw_hud()

    # ── HUD — Stone Tablet (bottom, Variant A) ───────────────────────────────
    def _draw_hud(self):
        ph  = int(72 * S)     # panel height
        py  = H - ph          # panel top y

        # Stone panel (cached surface — no per-frame allocation)
        screen.blit(self._hud_panel, (0, py))
        # Carved stone texture: subtle horizontal lines
        step = int(10 * S)
        for ty in range(py + step, H, step):
            pygame.draw.line(screen, CLR["stone_hi"], (0, ty), (W, ty), 1)
        # Top border (vine double line)
        pygame.draw.line(screen, CLR["vine"],    (0, py),          (W, py),          max(1, int(2 * S)))
        pygame.draw.line(screen, CLR["vine_dk"], (0, py + int(2 * S)), (W, py + int(2 * S)), 1)

        # ── SCORE (left) ──────────────────────────────────────────────────────
        sc_lbl = F_TINY.render("SCORE", True, CLR["olive"])
        screen.blit(sc_lbl, (int(14 * SX), py + int(6 * S)))
        sc_shad = F_SERIF.render(str(self.score), True, (18, 18, 12))
        sc_val  = F_SERIF.render(str(self.score), True, CLR["gold"])
        screen.blit(sc_shad, (int(15 * SX), py + int(28 * S)))
        screen.blit(sc_val,  (int(14 * SX), py + int(27 * S)))

        # ── LEVEL (center-left) ───────────────────────────────────────────────
        lv_lbl = F_TINY.render("LEVEL", True, CLR["olive"])
        lv_label_x = W // 2 - lv_lbl.get_width() // 2 - int(60 * SX)
        screen.blit(lv_lbl, (lv_label_x, py + int(6 * S)))
        lv_shad = F_SERIF.render(str(self.level), True, (18, 18, 12))
        lv_val  = F_SERIF.render(str(self.level), True, CLR["white"])
        lv_x = W // 2 - lv_val.get_width() // 2 - int(60 * SX)
        screen.blit(lv_shad, (lv_x + 1, py + int(28 * S)))
        screen.blit(lv_val,  (lv_x,     py + int(27 * S)))

        # ── TIME (center-right) ───────────────────────────────────────────────
        time_left  = max(0.0, LEVEL_TIME - self.level_timer)
        display_t  = math.ceil(time_left)   # show 01s until actually expired
        tcol = CLR["red"] if time_left < 10 else CLR["white"]
        tm_lbl  = F_TINY.render("TIME", True, CLR["olive"])
        screen.blit(tm_lbl, (W // 2 + int(40 * SX), py + int(6 * S)))
        tm_shad = F_SERIF.render(f"{display_t:02d}s", True, (18, 18, 12))
        tm_val  = F_SERIF.render(f"{display_t:02d}s", True, tcol)
        screen.blit(tm_shad, (W // 2 + int(41 * SX), py + int(28 * S)))
        screen.blit(tm_val,  (W // 2 + int(40 * SX), py + int(27 * S)))

        # ── LIVES — skull icons (right) ───────────────────────────────────────
        lv2_lbl = F_TINY.render("LIVES", True, CLR["olive"])
        screen.blit(lv2_lbl, (W - int(122 * SX), py + int(6 * S)))
        skull_gap = int(36 * S)
        for i in range(MAX_LIVES):
            sk_col = (190, 30, 30) if i < self.player.lives else (55, 55, 55)
            sk = F_SKULL.render("\u2620", True, sk_col)   # ☠
            screen.blit(sk, (W - int(120 * SX) + i * skull_gap, py + int(26 * S)))

        # ── Vine growth bar / stun bar (bottom strip inside panel) ────────────
        bar_w = int(W * 0.60)
        bar_x = W // 2 - bar_w // 2
        bar_y = H - int(12 * S)
        bar_h = int(8 * S)
        brd   = max(1, int(4 * S))

        if self.player.is_stunned():
            stun_pct   = max(0.0, self.player.stun_t / STUN_SECS)
            stun_bar_w = int(bar_w * stun_pct)
            pygame.draw.rect(screen, (20, 60, 55),  (bar_x, bar_y, bar_w, bar_h), border_radius=brd)
            if stun_bar_w > 0:   # guard: border_radius crashes on width=0
                pygame.draw.rect(screen, CLR["teal"], (bar_x, bar_y, stun_bar_w, bar_h), border_radius=brd)
            pygame.draw.rect(screen, (0, 140, 120), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=brd)
            # STUNNED label sits above the bar, inside the panel
            st = F_TINY.render("STUNNED", True, CLR["teal"])
            screen.blit(st, (W // 2 - st.get_width() // 2, bar_y - int(16 * S)))
        else:
            # Show empty bar during level-up overlay (level_timer > LEVEL_TIME)
            prog   = 0.0 if self.state == ST_LEVELUP else min(1.0, self.level_timer / LEVEL_TIME)
            fill_w = int(bar_w * prog)
            seg_w  = int(18 * S)
            pygame.draw.rect(screen, (18, 32, 18), (bar_x, bar_y, bar_w, bar_h), border_radius=brd)
            for sx in range(0, fill_w, max(1, seg_w)):
                seg = min(seg_w - 1, fill_w - sx)
                col = CLR["vine"] if (sx // max(1, seg_w)) % 2 == 0 else CLR["vine_dk"]
                pygame.draw.rect(screen, col, (bar_x + sx, bar_y, seg, bar_h))
            leaf_s = int(4 * S)
            if fill_w > leaf_s:
                lx = bar_x + fill_w
                pygame.draw.polygon(screen, (80, 255, 110),
                                    [(lx - leaf_s, bar_y),
                                     (lx + leaf_s, bar_y + bar_h // 2),
                                     (lx - leaf_s, bar_y + bar_h)])
            pygame.draw.rect(screen, CLR["vine_dk"], (bar_x, bar_y, bar_w, bar_h), 1, border_radius=brd)

    # ── Level-up overlay ─────────────────────────────────────────────────────
    def _draw_levelup_overlay(self):
        screen.blit(self._ov_levelup, (0, 0))
        lt  = F_LARGE.render(f"LEVEL {self.level}!", True, CLR["gold"])
        sub = F_MED.render("Things are getting faster...", True, CLR["white"])
        sc  = F_SMALL.render(f"Score so far: {self.score}", True, CLR["gold"])
        screen.blit(lt,  (W // 2 - lt.get_width()  // 2, H // 2 - int(50 * S)))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + int(20 * S)))
        screen.blit(sc,  (W // 2 - sc.get_width()  // 2, H // 2 + int(65 * S)))

    # ── Pause overlay ─────────────────────────────────────────────────────────
    def _draw_pause_overlay(self):
        screen.blit(self._ov_pause, (0, 0))
        pt  = F_LARGE.render("PAUSED", True, CLR["white"])
        h1  = F_MED.render("SPACE — resume", True, (195, 215, 195))
        h2  = F_MED.render("ESC — return to home screen", True, (195, 215, 195))
        screen.blit(pt,  (W // 2 - pt.get_width()  // 2, H // 2 - int(60 * S)))
        screen.blit(h1,  (W // 2 - h1.get_width()  // 2, H // 2 + int(10 * S)))
        screen.blit(h2,  (W // 2 - h2.get_width()  // 2, H // 2 + int(50 * S)))

    # ── Name Entry ───────────────────────────────────────────────────────────
    def _draw_name_entry(self, t):
        # Full clean slate — solid fill, no SRCALPHA overhead
        screen.fill((0, 12, 0))

        # Gold vine dividers for structure
        pygame.draw.line(screen, CLR["vine_dk"],
                         (W // 2 - int(320 * SX), H // 2 - int(120 * S)),
                         (W // 2 + int(320 * SX), H // 2 - int(120 * S)), 1)
        pygame.draw.line(screen, CLR["vine_dk"],
                         (W // 2 - int(320 * SX), H // 2 + int(130 * S)),
                         (W // 2 + int(320 * SX), H // 2 + int(130 * S)), 1)

        # ── Title ────────────────────────────────────────────────────────────
        trop = F_LARGE.render("YOU MADE THE TOP 10!", True, CLR["gold"])
        shad = F_LARGE.render("YOU MADE THE TOP 10!", True, (50, 30, 0))
        title_y = H // 2 - int(218 * S)
        screen.blit(shad, (W // 2 - trop.get_width() // 2 + int(3 * S), title_y + int(3 * S)))
        screen.blit(trop, (W // 2 - trop.get_width() // 2,              title_y))

        # ── Score / level ──────────────────────────────────────────────────────
        sc = F_SMALL.render(f"Score: {self.score}   |   Level {self.level}", True, (200, 220, 200))
        screen.blit(sc, (W // 2 - sc.get_width() // 2, H // 2 - int(148 * S)))

        # ── Input prompt ──────────────────────────────────────────────────────
        prompt = F_MED.render("Enter your name:", True, (190, 210, 190))
        screen.blit(prompt, (W // 2 - prompt.get_width() // 2, H // 2 - int(105 * S)))

        # ── Letter slots ──────────────────────────────────────────────────────
        slot_w   = int(72 * S)
        slot_h   = int(80 * S)
        gap      = int(10 * S)
        total_w  = MAX_NAME_LEN * slot_w + (MAX_NAME_LEN - 1) * gap
        sx_start = W // 2 - total_w // 2
        sy       = H // 2 - int(72 * S)

        for i in range(MAX_NAME_LEN):
            sx = sx_start + i * (slot_w + gap)
            filled = i < len(self.name_input)
            bd_col = CLR["vine"] if filled else CLR["vine_dk"]
            screen.blit(self._slot_filled if filled else self._slot_empty, (sx, sy))
            pygame.draw.rect(screen, bd_col, (sx, sy, slot_w, slot_h), max(1, int(2 * S)), border_radius=int(6 * S))

            if filled:
                ch_surf = F_LARGE.render(self.name_input[i], True, CLR["gold"])
                screen.blit(ch_surf, (sx + slot_w // 2 - ch_surf.get_width() // 2,
                                      sy + slot_h // 2 - ch_surf.get_height() // 2))
            elif i == len(self.name_input):
                # Blinking cursor
                if self.cursor_on:
                    pygame.draw.rect(screen, CLR["gold"],
                                     (sx + slot_w // 2 - int(3 * S), sy + int(16 * S),
                                      int(6 * S), int(48 * S)),
                                     border_radius=int(2 * S))

        # ── Hints ─────────────────────────────────────────────────────────────
        h1 = F_SMALL.render("A-Z  /  0-9  to type     BACKSPACE to delete", True, (140, 170, 140))
        h2 = F_SMALL.render("ENTER to confirm     ESC to skip", True, (140, 170, 140))
        screen.blit(h1, (W // 2 - h1.get_width() // 2, sy + slot_h + int(18 * S)))
        screen.blit(h2, (W // 2 - h2.get_width() // 2, sy + slot_h + int(46 * S)))

    # ── Full Leaderboard ─────────────────────────────────────────────────────
    def _draw_leaderboard(self, t):
        screen.blit(self.bg, (0, 0))
        screen.blit(self._ov_lb, (0, 0))

        title  = F_LARGE.render("TOP 10 LEADERBOARD", True, CLR["gold"])
        shadow = F_LARGE.render("TOP 10 LEADERBOARD", True, (50, 35, 0))
        screen.blit(shadow, (W // 2 - title.get_width() // 2 + int(3 * S), int(28 * S)))
        screen.blit(title,  (W // 2 - title.get_width() // 2,              int(25 * S)))

        self._draw_lb_table(int(95 * S), full=True)

        # CTA in gold (consistent with start screen)
        cta = F_MED.render("SPACE to play again  |  TAB / ESC to home", True,
                           pulse_color(CLR["gold"], t))
        screen.blit(cta, (W // 2 - cta.get_width() // 2, H - int(48 * S)))

    # ── Game Over (not top 10) ────────────────────────────────────────────────
    def _draw_gameover(self, t):
        screen.blit(self.bg, (0, 0))
        screen.blit(self._ov_gameover, (0, 0))

        go   = F_HUGE.render("GAME OVER", True, CLR["red"])
        shad = F_HUGE.render("GAME OVER", True, (80, 0, 0))
        screen.blit(shad, (W // 2 - go.get_width() // 2 + int(4 * S), int(32 * S)))
        screen.blit(go,   (W // 2 - go.get_width() // 2,              int(28 * S)))

        sc = F_MED.render(f"Score: {self.score}   |   Level {self.level}", True, CLR["gold"])
        screen.blit(sc, (W // 2 - sc.get_width() // 2, int(128 * S)))

        if self.leaderboard:
            msg = F_MED.render("Not in the top 10 — keep trying!", True, CLR["red"])
        else:
            msg = F_MED.render("Score some points to get on the leaderboard!", True, CLR["red"])
        screen.blit(msg, (W // 2 - msg.get_width() // 2, int(170 * S)))

        lb_lbl = F_SMALL.render("Current Top 10:", True, (190, 210, 190))
        screen.blit(lb_lbl, (W // 2 - lb_lbl.get_width() // 2, int(208 * S)))

        self._draw_lb_table(int(234 * S), full=False)

        cta = F_MED.render("SPACE to play again  |  ESC to home", True,
                           pulse_color(CLR["gold"], t))
        screen.blit(cta, (W // 2 - cta.get_width() // 2, H - int(48 * S)))

    # ── Leaderboard table ─────────────────────────────────────────────────────
    def _draw_lb_table(self, start_y, full=True):
        col_w  = int(620 * SX)
        row_h  = int(36 * S) if full else int(26 * S)
        font   = F_SMALL if full else F_TINY
        tx     = W // 2 - col_w // 2

        # x-offsets within the table (scaled)
        x1  = int(14  * SX)
        x2  = int(70  * SX)
        x3  = col_w - int(200 * SX)
        x4  = col_w - int(60  * SX)

        # Header row
        hdr = pygame.Surface((col_w, row_h), pygame.SRCALPHA)
        hdr.fill((30, 70, 30, 220))
        screen.blit(hdr, (tx, start_y))
        pygame.draw.rect(screen, CLR["lb_border"], (tx, start_y, col_w, row_h), 1)
        for text, x_off in [("#", x1), ("NAME", x2), ("SCORE", x3), ("LVL", x4)]:
            s = font.render(text, True, CLR["gold"])
            screen.blit(s, (tx + x_off, start_y + (row_h - s.get_height()) // 2))

        if not self.leaderboard:
            e = font.render("No scores yet — be the first!", True, (160, 190, 160))
            screen.blit(e, (W // 2 - e.get_width() // 2, start_y + row_h + int(8 * S)))
            return

        medal_bg = [(60, 45, 0), (35, 35, 45), (45, 25, 10)]
        medal_fc = [CLR["gold"], CLR["silver"], CLR["bronze"]]

        for i, entry in enumerate(self.leaderboard[:LEADERBOARD_SIZE]):
            ry     = start_y + row_h * (i + 1)
            bg_col = medal_bg[i] if i < 3 else (CLR["lb_row_a"] if (i - 3) % 2 == 0 else CLR["lb_row_b"])
            rs = pygame.Surface((col_w, row_h), pygame.SRCALPHA)
            rs.fill((*bg_col, 220))
            screen.blit(rs, (tx, ry))
            pygame.draw.rect(screen, (40, 80, 40), (tx, ry, col_w, row_h), 1)

            fc = medal_fc[i] if i < 3 else CLR["white"]
            cy = ry + (row_h - font.get_height()) // 2
            for text, x_off, color in [
                (str(i + 1),                 x1, fc),
                (entry.get("name", "?"),     x2, CLR["white"]),
                (str(entry.get("score", 0)),  x3, CLR["gold"]),
                (str(entry.get("level","-")),x4, (160, 200, 160)),
            ]:
                s = font.render(text, True, color)
                screen.blit(s, (tx + x_off, cy))

    # ── Tree silhouettes (start screen cinematic layer) ───────────────────────
    def _draw_tree_silhouettes(self):
        sil  = (5, 16, 5)
        tw   = int(7  * S)   # half-width of trunk
        th   = int(90 * S)   # trunk height
        dy1  = int(90  * S)
        dy2  = int(120 * S)
        dy3  = int(148 * S)
        r1   = int(48  * S)
        r2   = int(38  * S)
        r3   = int(26  * S)
        tx_positions = [int(v * SX) for v in [55, 175, 340, 490, 640, 795, 875]]
        for tx in tx_positions:
            pygame.draw.rect(screen, sil, (tx - tw, GROUND_Y - th, tw * 2, th))
            for dy, r in [(dy1, r1), (dy2, r2), (dy3, r3)]:
                pygame.draw.circle(screen, sil, (tx, GROUND_Y - dy), r)

    # ── Start screen — Minimal Impact / Cinematic (Option 1) ──────────────────
    def _draw_start(self, t):
        screen.blit(self.bg, (0, 0))

        # Heavy cinematic overlay
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 6, 0, 210))
        screen.blit(ov, (0, 0))

        # Tree silhouette layer near bottom
        self._draw_tree_silhouettes()

        # ── Best score badge (top-right) ──────────────────────────────────────
        if self.leaderboard:
            best      = self.leaderboard[0]
            badge_txt = F_TINY.render(
                f"BEST  {best.get('name','?')}  {best['score']} pts", True, CLR["gold"])
            pad_x = int(10 * SX); pad_y = int(5 * S)
            bw = badge_txt.get_width() + pad_x * 2
            bh = badge_txt.get_height() + pad_y * 2
            bx = W - bw - int(12 * SX)
            by = int(12 * S)
            pygame.draw.rect(screen, (28, 22, 4),  (bx, by, bw, bh), border_radius=int(4 * S))
            pygame.draw.rect(screen, CLR["gold"],   (bx, by, bw, bh), 1, border_radius=int(4 * S))
            screen.blit(badge_txt, (bx + pad_x, by + pad_y))

        # ── ? icon (top-left) — reveals controls after 5 s idle ───────────────
        icon_s = int(28 * S)
        icon_x = int(10 * SX)
        icon_y = int(10 * S)
        pygame.draw.rect(screen, (18, 32, 18), (icon_x, icon_y, icon_s, icon_s), border_radius=int(4 * S))
        pygame.draw.rect(screen, (55, 85, 55), (icon_x, icon_y, icon_s, icon_s), 1, border_radius=int(4 * S))
        qi = F_SMALL.render("?", True, (100, 140, 100))
        screen.blit(qi, (icon_x + icon_s // 2 - qi.get_width() // 2,
                         icon_y + icon_s // 2 - qi.get_height() // 2))

        if self.start_idle_t >= 5.0:
            screen.blit(self._ctrl_panel, (icon_x + icon_s + int(6 * SX), icon_y - int(2 * S)))
            row_h = int(22 * S)
            for row, txt in enumerate([
                "Arrow keys / A-D  — move",
                "3 lives  |  45 s per level",
                "ESC — pause / home",
            ]):
                s = F_TINY.render(txt, True, (175, 210, 175))
                screen.blit(s, (icon_x + icon_s + int(12 * SX), icon_y + row * row_h))

        # ── Title ─────────────────────────────────────────────────────────────
        title  = F_HUGE.render("JUNGLE DODGE", True, CLR["gold"])
        shadow = F_HUGE.render("JUNGLE DODGE", True, (28, 16, 0))
        cy_title = H // 2 - int(100 * S)
        screen.blit(shadow, (W // 2 - title.get_width() // 2 + int(4 * S), cy_title + int(4 * S)))
        screen.blit(title,  (W // 2 - title.get_width() // 2,              cy_title))

        # ── Tagline ───────────────────────────────────────────────────────────
        tag = F_SMALL.render("SURVIVE. DODGE. OUTLAST.", True, (185, 210, 185))
        screen.blit(tag, (W // 2 - tag.get_width() // 2, cy_title + int(106 * S)))

        # ── Bordered CTA ──────────────────────────────────────────────────────
        cta_col = pulse_color(CLR["gold"], t)
        cta_txt = F_MED.render(">> PRESS SPACE TO START <<", True, cta_col)
        cta_w   = cta_txt.get_width() + int(44 * SX)
        cta_h   = cta_txt.get_height() + int(18 * S)
        cta_x   = W // 2 - cta_w // 2
        cta_y   = cy_title + int(148 * S)
        pygame.draw.rect(screen, (28, 22, 4),  (cta_x, cta_y, cta_w, cta_h), border_radius=int(6 * S))
        pygame.draw.rect(screen, cta_col,       (cta_x, cta_y, cta_w, cta_h), max(1, int(2 * S)), border_radius=int(6 * S))
        screen.blit(cta_txt, (cta_x + int(22 * SX), cta_y + int(9 * S)))

        # TAB + close hints (bottom)
        lb_hint   = F_TINY.render("TAB — view leaderboard", True, (80, 110, 80))
        quit_hint = F_TINY.render("Close window to quit", True, (55, 75, 55))
        screen.blit(lb_hint,   (W // 2 - lb_hint.get_width()   // 2, cta_y + cta_h + int(10 * S)))
        screen.blit(quit_hint, (W // 2 - quit_hint.get_width() // 2, cta_y + cta_h + int(30 * S)))

    # ── Event handling ───────────────────────────────────────────────────────
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        # ── Name entry ────────────────────────────────────────────────────────
        if self.state == ST_NAME_ENTRY:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                # CRIT-01: always submit — use "-----" if nothing typed
                name = self.name_input if self.name_input else "-----"
                self._submit_score(name)
                self.state = ST_LEADERBOARD
            elif event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif event.key == pygame.K_ESCAPE:
                self._submit_score("-----")
                self.state = ST_LEADERBOARD
            else:
                ch = event.unicode.upper()
                if ch.isalnum() and len(self.name_input) < MAX_NAME_LEN:
                    self.name_input += ch
            return

        # ── F11 — toggle fullscreen / windowed ───────────────────────────────
        if event.key == pygame.K_F11:
            _toggle_fullscreen()
            return

        # ── ESC — always navigate toward home, never force-quit ───────────────
        if event.key == pygame.K_ESCAPE:
            if self.state == ST_PLAYING:
                self.state = ST_PAUSED            # playing   → pause
            elif self.state == ST_PAUSED:
                self._new_game()
                self.state = ST_START             # paused    → home
            elif self.state == ST_START:
                pass                              # ESC on home is a no-op — close window to quit
            elif self.state == ST_LEVELUP:
                pass                              # ESC during level-up is a no-op — let timer expire
            else:
                self._new_game()                  # reset stale game data
                self.start_idle_t = 0.0           # restart idle timer for ? hint
                self.state = ST_START             # anywhere  → home
            return

        # ── SPACE ─────────────────────────────────────────────────────────────
        if event.key == pygame.K_SPACE:
            if self.state == ST_START:
                self._new_game()
                self.state = ST_PLAYING
            elif self.state == ST_PAUSED:
                self.state = ST_PLAYING
            elif self.state in (ST_GAMEOVER, ST_LEADERBOARD):
                self._new_game()
                self.state = ST_PLAYING

        # ── TAB — toggle between start and leaderboard ────────────────────────
        if event.key == pygame.K_TAB:
            if self.state == ST_START:
                self.state = ST_LEADERBOARD
            elif self.state == ST_LEADERBOARD:
                self.state = ST_START

        # ── ENTER — back to start from leaderboard ────────────────────────────
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state == ST_LEADERBOARD:
            self.state = ST_START

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)  # cap dt — prevents physics tunnelling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.handle_event(event)
            self.update(dt)
            self.draw()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
