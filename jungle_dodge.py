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
W, H   = 900, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Jungle Dodge")
clock  = pygame.time.Clock()
FPS    = 60

# ── Layout ────────────────────────────────────────────────────────────────────
GROUND_Y     = H - 90
PLAYER_FLOOR = GROUND_Y

# ── Palette ───────────────────────────────────────────────────────────────────
CLR = {
    "sky_top"    : (15,  55,  20),
    "sky_bot"    : (40, 100,  30),
    "ground"     : (90,  60,  30),
    "grass"      : (55, 140,  40),
    "white"      : (255, 255, 255),
    "black"      : (  0,   0,   0),
    "red"        : (220,  50,  50),
    "yellow"     : (255, 210,  30),
    "orange"     : (255, 140,   0),
    "vine"       : ( 70, 160,  50),
    "vine_dk"    : ( 40, 100,  30),
    "bomb"       : ( 25,  25,  25),
    "fuse"       : (200, 150,  50),
    "spark"      : (255, 200,  50),
    "spike"      : (180, 180, 200),
    "spike_dk"   : (120, 120, 140),
    "boulder"    : (140, 115,  85),   # slightly lighter per UX review
    "boulder_dk" : (100,  80,  60),
    "heart"      : (220,  50,  80),
    "heart_empty": ( 60,  25,  25),
    "gold"       : (255, 215,   0),
    "skin"       : (220, 180, 130),
    "shirt"      : (200, 170, 100),
    "pants"      : ( 80,  60,  40),
    "hat"        : (140, 100,  50),
    "teal"       : (  0, 201, 177),   # stun colour per UX
    "lb_bg"      : ( 10,  25,  10),
    "lb_row_a"   : ( 18,  45,  18),
    "lb_row_b"   : ( 12,  32,  12),
    "lb_border"  : ( 70, 160,  50),
    "silver"     : (192, 192, 192),
    "bronze"     : (205, 127,  50),
}

# ── Game Constants ─────────────────────────────────────────────────────────────
LEVEL_TIME       = 45       # seconds per level
MAX_LIVES        = 3
STUN_SECS        = 3.0
IMMUNE_EXTRA     = 0.15     # grace period after stun visual ends (CRIT-03)
PLAYER_SPD       = 360      # pixels/second (dt-scaled — BUG-07)
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

F_HUGE  = _font("Impact",   90)
F_LARGE = _font("Impact",   54)
F_MED   = _font("Arial",    30, bold=True)
F_SMALL = _font("Arial",    22)
F_TINY  = _font("Arial",    17)
F_MONO  = _font("Consolas", 26, bold=True)   # HUD numbers (UX rec)


# ─────────────────────────────────────────────────────────────────────────────
#  Player
# ─────────────────────────────────────────────────────────────────────────────
class Player:
    PW = 32
    PH = 50

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
        sw   = math.sin(self.walk_t) * 9 if self.walk_t else 0

        # Legs
        lleg = (cx - 5 + int(sw), boty)
        rleg = (cx + 5 - int(sw), boty)
        pygame.draw.line(surf, CLR["pants"], (cx - 5, self.y + 36), lleg, 5)
        pygame.draw.line(surf, CLR["pants"], (cx + 5, self.y + 36), rleg, 5)
        pygame.draw.circle(surf, (50, 35, 20), lleg, 4)
        pygame.draw.circle(surf, (50, 35, 20), rleg, 4)

        # Arms
        aw = math.sin(self.walk_t + math.pi) * 7 if self.walk_t else 0
        ay = self.y + 22
        pygame.draw.line(surf, CLR["shirt"], (cx - 12, ay), (cx - 20, ay + 14 + int(aw)), 4)
        pygame.draw.line(surf, CLR["shirt"], (cx + 12, ay), (cx + 20, ay + 14 - int(aw)), 4)

        # Body
        bcol = CLR["shirt"] if not stunned else (255, 255, 100)
        pygame.draw.rect(surf, bcol, (cx - 13, self.y + 16, 26, 22), border_radius=4)

        # Head
        hcy  = self.y + 10
        hcol = CLR["skin"] if not stunned else (255, 230, 150)
        pygame.draw.circle(surf, hcol, (cx, hcy), 12)
        pygame.draw.circle(surf, (30, 20, 10), (cx + 4 * self.facing, hcy), 2)

        # Explorer hat
        hcol2 = CLR["hat"] if not stunned else (180, 140, 70)
        pygame.draw.ellipse(surf, hcol2, (cx - 17, hcy - 5, 34, 9))
        pygame.draw.rect(surf,   hcol2, (cx - 9, hcy - 17, 18, 13), border_radius=3)
        pygame.draw.rect(surf, (100, 70, 30), (cx - 9, hcy - 6, 18, 3))

        # Stun stars
        if stunned:
            for i in range(3):
                angle = self.flash_t + i * (2 * math.pi / 3)
                sx = cx + int(22 * math.cos(angle))
                sy = self.y - 4 + int(9 * math.sin(angle))
                pygame.draw.circle(surf, CLR["yellow"], (sx, sy), 4)
                pygame.draw.circle(surf, CLR["white"],  (sx, sy), 2)


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
    BW = 14
    BH = 65

    def __init__(self, level):
        super().__init__()
        self.x        = float(random.randint(50, W - 50))
        self.y        = float(-self.BH)
        mult          = 1 + (level - 1) * SPEED_SCALE * 0.8
        self.vy       = (90 + level * 15) * mult
        self.sway_t   = random.uniform(0, math.pi * 2)
        self.sway_s   = random.uniform(1.5, 3.0)
        self.sway_a   = random.uniform(8, 18)
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
            self.x       = max(20, min(W - 20, self.x))
            if self.y + self.BH >= GROUND_Y:
                self.y      = float(GROUND_Y - self.BH)
                self.landed = True
                self.scored = True
        else:
            self.land_t += dt
            if self.land_t >= self.land_dur:
                self.alive = False

    def check_hit(self, player):
        return not player.is_hit_immune() and self.rect.colliderect(player.rect)

    def draw(self, surf):
        segs  = 9
        seg_h = self.BH // segs
        for i in range(segs):
            sy  = int(self.y) + i * seg_h
            off = int(math.sin(self.sway_t + i * 0.5) * 3)
            col = CLR["vine"] if i % 2 == 0 else CLR["vine_dk"]
            pygame.draw.rect(surf, col,
                             (int(self.x) - self.BW // 2 + off, sy, self.BW, seg_h + 1))
            if i % 3 == 1:
                lx = int(self.x) + self.BW // 2 + off
                pygame.draw.ellipse(surf, CLR["vine"], (lx, sy + 1, 11, 6))
        pygame.draw.circle(surf, CLR["vine_dk"],
                           (int(self.x), int(self.y + self.BH)), 5)


# ─────────────────────────────────────────────────────────────────────────────
#  Bomb
# ─────────────────────────────────────────────────────────────────────────────
class Bomb(Obstacle):
    R = 18

    def __init__(self, level):
        super().__init__()
        self.x             = float(random.randint(60, W - 60))
        self.y             = float(-self.R * 2)
        mult               = 1 + (level - 1) * SPEED_SCALE * 1.1
        self.vy            = (175 + level * 22) * mult
        self.fuse_t        = 0.0
        self.spark_t       = 0.0
        self.exploded      = False
        self.exp_t         = 0.0
        self.exp_dur       = 0.55
        self.exp_r         = 72
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
            if not self._exp_hit_done:
                self._exp_hit_done = True
                if not player.is_hit_immune():
                    dist = math.hypot(self.x - player.x,
                                      self.y - (player.y + Player.PH // 2))
                    if dist < self.exp_r:
                        self.did_hit = True   # mark before hitting (CRIT-01)
                        player.hit()

    def check_hit(self, player):
        return (not player.is_hit_immune() and not self.exploded
                and self.rect.colliderect(player.rect))

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

        pygame.draw.circle(surf, CLR["bomb"],  (cx, cy), self.R)
        pygame.draw.circle(surf, (55, 55, 55), (cx - 5, cy - 5), 6)
        fuse_top = (cx + 4, cy - self.R - 10)
        pygame.draw.lines(surf, CLR["fuse"], False,
                          [(cx, cy - self.R), (cx + 2, cy - self.R - 5), fuse_top], 2)
        sa  = self.spark_t
        spx = fuse_top[0] + int(3 * math.cos(sa))
        spy = fuse_top[1] + int(3 * math.sin(sa))
        pygame.draw.circle(surf, CLR["spark"],  (spx, spy), 4)
        pygame.draw.circle(surf, CLR["yellow"], (spx, spy), 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Spike
# ─────────────────────────────────────────────────────────────────────────────
class Spike(Obstacle):
    SW = 18
    SH = 44

    def __init__(self, level):
        super().__init__()
        self.x  = float(random.randint(40, W - 40))
        self.y  = float(-self.SH)
        mult    = 1 + (level - 1) * SPEED_SCALE * 1.3
        self.vy = (260 + level * 38) * mult

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
        pygame.draw.polygon(surf, CLR["spike_dk"], pts, 2)
        pygame.draw.line(surf, (220, 220, 240),
                         (cx - hw // 2, top + 4), (cx - 2, tip - 6), 1)
        pygame.draw.rect(surf, CLR["spike_dk"], (cx - hw, top, self.SW, 5))


# ─────────────────────────────────────────────────────────────────────────────
#  Boulder
# ─────────────────────────────────────────────────────────────────────────────
class Boulder(Obstacle):
    R = 30

    def __init__(self, level):
        super().__init__()
        self.x        = float(random.randint(80, W - 80))
        self.y        = float(-self.R * 2)
        mult          = 1 + (level - 1) * SPEED_SCALE * 0.7
        self.vy       = (100 + level * 12) * mult
        self.rolling  = False
        self.roll_dir = random.choice([-1, 1])
        self.roll_spd = random.uniform(130, 210)
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
                            (cx - self.R, cy + self.R - 8, self.R * 2, 12))
        pygame.draw.circle(surf, CLR["boulder"],    (cx, cy), self.R)
        pygame.draw.circle(surf, CLR["boulder_dk"], (cx + 5, cy + 5), self.R - 6)
        for x1, y1, x2, y2 in self.cracks:
            pygame.draw.line(surf, CLR["boulder_dk"],
                             self._rot_pt(x1, y1), self._rot_pt(x1 + x2, y1 + y2), 2)
        pygame.draw.circle(surf, CLR["boulder_dk"], (cx, cy), self.R, 2)
        pygame.draw.circle(surf, (165, 145, 120),
                           (cx - self.R // 3, cy - self.R // 3), self.R // 4)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def draw_heart(surf, cx, cy, r, filled):
    col = CLR["heart"] if filled else CLR["heart_empty"]
    pygame.draw.circle(surf, col, (cx - r // 2, cy), r // 2 + 1)
    pygame.draw.circle(surf, col, (cx + r // 2, cy), r // 2 + 1)
    pygame.draw.polygon(surf, col, [(cx - r, cy + 2), (cx, cy + r + 3), (cx + r, cy + 2)])

def draw_panel(surf, x, y, w, h, col, alpha=210, radius=8):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((*col, alpha))
    surf.blit(s, (x, y))
    pygame.draw.rect(surf, CLR["lb_border"], (x, y, w, h), 2, border_radius=radius)

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
        self.name_input  = ""
        self.cursor_t    = 0.0
        self.cursor_on   = True
        self._reset_level()
        self.player      = Player()

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
            "name": name.upper() or "?????",
            "score": self.score,
            "level": self.level,
        })
        self.leaderboard.sort(key=lambda e: e["score"], reverse=True)
        self.leaderboard = self.leaderboard[:LEADERBOARD_SIZE]
        self._save_leaderboard()

    def _session_best(self):
        return self.leaderboard[0]["score"] if self.leaderboard else 0

    # ── Init helpers ─────────────────────────────────────────────────────────
    def _reset_level(self):
        self.obstacles   = []
        self.level_timer = 0.0
        self.spawn_timer = 0.0
        self.particles   = []
        self.levelup_t   = 0.0

    def _new_game(self):
        self.score  = 0
        self.level  = 1
        self.player = Player()
        self._reset_level()

    def _spawn_rate(self):
        return max(MIN_SPAWN, BASE_SPAWN - (self.level - 1) * SPAWN_DEC)

    # ── Background ───────────────────────────────────────────────────────────
    def _build_bg(self):
        bg = pygame.Surface((W, H))
        for y in range(GROUND_Y):
            t = y / GROUND_Y
            pygame.draw.line(bg,
                             (int(15 + t * 25), int(55 + t * 45), int(20 + t * 10)),
                             (0, y), (W, y))
        pygame.draw.rect(bg, CLR["ground"], (0, GROUND_Y, W, H - GROUND_Y))
        pygame.draw.rect(bg, CLR["grass"],  (0, GROUND_Y, W, 14))
        for tx in [70, 200, 360, 490, 640, 770, 870]:
            pygame.draw.rect(bg, (75, 50, 22), (tx - 5, GROUND_Y - 65, 10, 65))
            for dy, r, col in [(65, 36, (28, 95, 22)),
                               (88, 28, (38, 118, 28)),
                               (108, 20, (50, 140, 35))]:
                pygame.draw.circle(bg, col, (tx, GROUND_Y - dy), r)
        for vx in [130, 310, 560, 720]:
            for i in range(6):
                col = CLR["vine"] if i % 2 == 0 else CLR["vine_dk"]
                pygame.draw.rect(bg, col, (vx - 4, i * 14, 8, 14))
        return bg

    # ── Spawning ─────────────────────────────────────────────────────────────
    def _spawn(self):
        kind = random.choices(OBS_TYPES, OBS_WEIGHTS)[0]
        cls  = {"vine": Vine, "bomb": Bomb, "spike": Spike, "boulder": Boulder}[kind]
        self.obstacles.append(cls(self.level))

    def _pop(self, x, y, text, color):
        self.particles.append({
            "text": text, "x": float(x), "y": float(y),
            "vy": -55, "t": 0.0, "dur": 1.1, "col": color,
        })

    # ── Update ───────────────────────────────────────────────────────────────
    def update(self, dt):
        if self.state == ST_NAME_ENTRY:
            self.cursor_t += dt
            if self.cursor_t >= 0.5:
                self.cursor_t  = 0.0
                self.cursor_on = not self.cursor_on
            return

        if self.state in (ST_START, ST_GAMEOVER, ST_LEADERBOARD, ST_PAUSED):
            return

        if self.state == ST_LEVELUP:
            self.levelup_t -= dt
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
                self._pop(self.player.x, self.player.y - 10, "OUCH!", CLR["red"])
                break   # one hit per frame max

        # Update obstacles
        for obs in self.obstacles:
            obs.update(dt, self.player)

        # Scoring — skip obstacles that hit the player (CRIT-01)
        for obs in self.obstacles:
            if obs.scored and not obs._pts and not obs.did_hit:
                obs._pts = True
                self.score += DODGE_PTS
                self._pop(obs.x, GROUND_Y - 30, f"+{DODGE_PTS}", CLR["gold"])

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
        pygame.display.flip()

    # ── Game screen ──────────────────────────────────────────────────────────
    def _draw_game(self):
        screen.blit(self.bg, (0, 0))
        for obs in self.obstacles:
            obs.draw(screen)
        self.player.draw(screen)
        for p in self.particles:
            a = max(0.0, 1.0 - p["t"] / p["dur"])
            if a < 0.02:            # BUG-11: skip near-zero alpha
                continue
            col = tuple(int(c * a) for c in p["col"])
            txt = F_MED.render(p["text"], True, col)
            screen.blit(txt, (int(p["x"]) - txt.get_width() // 2, int(p["y"])))
        self._draw_hud()

    # ── HUD ──────────────────────────────────────────────────────────────────
    def _draw_hud(self):
        # Panel (64px height per UX review)
        panel = pygame.Surface((W, 64), pygame.SRCALPHA)
        panel.fill((8, 28, 8, 215))
        screen.blit(panel, (0, 0))
        pygame.draw.line(screen, CLR["vine"], (0, 64), (W, 64), 2)

        # Score
        sc = F_MED.render(f"Score: {self.score}", True, CLR["gold"])
        screen.blit(sc, (14, 16))

        # Level
        lv = F_MED.render(f"Level {self.level}", True, CLR["white"])
        screen.blit(lv, (W // 2 - lv.get_width() // 2, 16))

        # Timer — clean integer format (UX review)
        time_left = max(0.0, LEVEL_TIME - self.level_timer)
        tcol = CLR["red"] if time_left < 10 else CLR["white"]
        tm = F_MONO.render(f"{int(time_left):02d}s", True, tcol)
        screen.blit(tm, (W - 200, 18))

        # Hearts
        for i in range(MAX_LIVES):
            draw_heart(screen, W - 80 + i * 30, 26, 10, i < self.player.lives)

        # Progress bar / stun bar (bottom strip)
        bar_w = int(W * 0.55)
        bar_x = W // 2 - bar_w // 2

        if self.player.is_stunned():
            # Replace progress bar with teal stun bar during stun (UX review)
            stun_pct   = max(0.0, self.player.stun_t / STUN_SECS)
            stun_bar_w = int(bar_w * stun_pct)
            pygame.draw.rect(screen, (20, 60, 55),  (bar_x, H - 14, bar_w, 10), border_radius=4)
            pygame.draw.rect(screen, CLR["teal"],   (bar_x, H - 14, stun_bar_w, 10), border_radius=4)
            pygame.draw.rect(screen, (0, 140, 120), (bar_x, H - 14, bar_w, 10), 1, border_radius=4)
            st = F_SMALL.render("STUNNED", True, CLR["teal"])
            screen.blit(st, (W // 2 - st.get_width() // 2, H - 36))
        else:
            prog = min(1.0, self.level_timer / LEVEL_TIME)
            pygame.draw.rect(screen, (35, 70, 35),  (bar_x, H - 14, bar_w, 10), border_radius=4)
            pygame.draw.rect(screen, CLR["gold"],   (bar_x, H - 14, int(bar_w * prog), 10), border_radius=4)
            pygame.draw.rect(screen, CLR["vine_dk"],(bar_x, H - 14, bar_w, 10), 1, border_radius=4)

    # ── Level-up overlay ─────────────────────────────────────────────────────
    def _draw_levelup_overlay(self):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 30, 5, 165))
        screen.blit(ov, (0, 0))
        lt  = F_LARGE.render(f"LEVEL {self.level}!", True, CLR["gold"])  # already incremented (BUG-06)
        sub = F_MED.render("Things are getting faster...", True, CLR["white"])
        sc  = F_SMALL.render(f"Score so far: {self.score}", True, CLR["gold"])
        screen.blit(lt,  (W // 2 - lt.get_width()  // 2, H // 2 - 50))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + 20))
        screen.blit(sc,  (W // 2 - sc.get_width()  // 2, H // 2 + 65))

    # ── Pause overlay ─────────────────────────────────────────────────────────
    def _draw_pause_overlay(self):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        screen.blit(ov, (0, 0))
        pt  = F_LARGE.render("PAUSED", True, CLR["white"])
        h1  = F_MED.render("SPACE — resume", True, (195, 215, 195))
        h2  = F_MED.render("ESC — quit game", True, (195, 215, 195))
        screen.blit(pt,  (W // 2 - pt.get_width()  // 2, H // 2 - 60))
        screen.blit(h1,  (W // 2 - h1.get_width()  // 2, H // 2 + 10))
        screen.blit(h2,  (W // 2 - h2.get_width()  // 2, H // 2 + 50))

    # ── Name Entry ───────────────────────────────────────────────────────────
    def _draw_name_entry(self, t):
        screen.blit(self.bg, (0, 0))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 20, 0, 160))
        screen.blit(ov, (0, 0))

        trop  = F_LARGE.render("YOU MADE THE TOP 10!", True, CLR["gold"])
        shad  = F_LARGE.render("YOU MADE THE TOP 10!", True, (60, 40, 0))
        screen.blit(shad, (W // 2 - trop.get_width() // 2 + 3, 48))
        screen.blit(trop, (W // 2 - trop.get_width() // 2, 45))

        sc = F_MED.render(f"Score: {self.score}   |   Level {self.level}", True, CLR["white"])
        screen.blit(sc, (W // 2 - sc.get_width() // 2, 116))

        prompt = F_MED.render("Enter your name (up to 5 characters):", True, (195, 215, 195))
        screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 174))

        # Input box
        bw, bh = 320, 60
        bx = W // 2 - bw // 2
        by = 214
        draw_panel(screen, bx, by, bw, bh, CLR["lb_bg"], alpha=230)
        display = self.name_input + ("|" if self.cursor_on else " ")
        inp = F_LARGE.render(display, True, CLR["gold"])
        screen.blit(inp, (W // 2 - inp.get_width() // 2, by + 8))
        cnt = F_TINY.render(f"{len(self.name_input)}/{MAX_NAME_LEN}", True, (130, 160, 130))
        screen.blit(cnt, (bx + bw - cnt.get_width() - 8, by + bh + 4))

        h1 = F_SMALL.render("A-Z / 0-9 to type   BACKSPACE to delete", True, (160, 185, 160))
        h2 = F_SMALL.render("ENTER to confirm   ESC to skip", True, (160, 185, 160))
        screen.blit(h1, (W // 2 - h1.get_width() // 2, 300))
        screen.blit(h2, (W // 2 - h2.get_width() // 2, 326))

        self._draw_mini_leaderboard(368)

    # ── Full Leaderboard ─────────────────────────────────────────────────────
    def _draw_leaderboard(self, t):
        screen.blit(self.bg, (0, 0))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 15, 0, 170))
        screen.blit(ov, (0, 0))

        title  = F_LARGE.render("TOP 10 LEADERBOARD", True, CLR["gold"])
        shadow = F_LARGE.render("TOP 10 LEADERBOARD", True, (50, 35, 0))
        screen.blit(shadow, (W // 2 - title.get_width() // 2 + 3, 28))
        screen.blit(title,  (W // 2 - title.get_width() // 2, 25))

        self._draw_lb_table(95, full=True)

        # CTA in gold (consistent with start screen)
        cta = F_MED.render("SPACE to play again  |  ESC to quit", True,
                           pulse_color(CLR["gold"], t))
        screen.blit(cta, (W // 2 - cta.get_width() // 2, H - 48))

    # ── Game Over (not top 10) ────────────────────────────────────────────────
    def _draw_gameover(self, t):
        screen.blit(self.bg, (0, 0))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((28, 5, 5, 185))
        screen.blit(ov, (0, 0))

        go   = F_HUGE.render("GAME OVER", True, CLR["red"])
        shad = F_HUGE.render("GAME OVER", True, (80, 0, 0))
        screen.blit(shad, (W // 2 - go.get_width() // 2 + 4, 32))
        screen.blit(go,   (W // 2 - go.get_width() // 2, 28))

        sc = F_MED.render(f"Score: {self.score}   |   Level {self.level}", True, CLR["gold"])
        screen.blit(sc, (W // 2 - sc.get_width() // 2, 128))

        msg = F_MED.render("Not in the top 10 — keep trying!", True, CLR["red"])
        screen.blit(msg, (W // 2 - msg.get_width() // 2, 170))

        lb_lbl = F_SMALL.render("Current Top 10:", True, (190, 210, 190))
        screen.blit(lb_lbl, (W // 2 - lb_lbl.get_width() // 2, 208))

        self._draw_lb_table(234, full=False)

        cta = F_MED.render("SPACE to play again  |  ESC to quit", True,
                           pulse_color(CLR["gold"], t))  # gold, not white (UX rec)
        screen.blit(cta, (W // 2 - cta.get_width() // 2, H - 48))

    # ── Leaderboard table ─────────────────────────────────────────────────────
    def _draw_lb_table(self, start_y, full=True):
        col_w  = 620
        row_h  = 36 if full else 26
        font   = F_SMALL if full else F_TINY
        tx     = W // 2 - col_w // 2

        # Header row
        hdr = pygame.Surface((col_w, row_h), pygame.SRCALPHA)
        hdr.fill((30, 70, 30, 220))
        screen.blit(hdr, (tx, start_y))
        pygame.draw.rect(screen, CLR["lb_border"], (tx, start_y, col_w, row_h), 1)
        for text, x_off in [("#", 14), ("NAME", 70), ("SCORE", col_w - 200), ("LVL", col_w - 60)]:
            s = font.render(text, True, CLR["gold"])
            screen.blit(s, (tx + x_off, start_y + (row_h - s.get_height()) // 2))

        if not self.leaderboard:
            e = font.render("No scores yet — be the first!", True, (160, 190, 160))
            screen.blit(e, (W // 2 - e.get_width() // 2, start_y + row_h + 8))
            return

        medal_bg = [(60, 45, 0), (35, 35, 45), (45, 25, 10)]
        medal_fc = [CLR["gold"], CLR["silver"], CLR["bronze"]]

        for i, entry in enumerate(self.leaderboard[:LEADERBOARD_SIZE]):
            ry     = start_y + row_h * (i + 1)
            bg_col = medal_bg[i] if i < 3 else (CLR["lb_row_a"] if i % 2 == 0 else CLR["lb_row_b"])
            rs = pygame.Surface((col_w, row_h), pygame.SRCALPHA)
            rs.fill((*bg_col, 220))
            screen.blit(rs, (tx, ry))
            pygame.draw.rect(screen, (40, 80, 40), (tx, ry, col_w, row_h), 1)

            fc = medal_fc[i] if i < 3 else CLR["white"]
            cy = ry + (row_h - font.render("#", True, fc).get_height()) // 2
            for text, x_off, color in [
                (str(i + 1),                 14,          fc),
                (entry.get("name", "?"),     70,          CLR["white"]),
                (str(entry["score"]),         col_w - 200, CLR["gold"]),
                (str(entry.get("level","-")),col_w - 60,  (160, 200, 160)),
            ]:
                s = font.render(text, True, color)
                screen.blit(s, (tx + x_off, cy))

    # ── Mini leaderboard ─────────────────────────────────────────────────────
    def _draw_mini_leaderboard(self, start_y):
        if not self.leaderboard:
            return
        lbl = F_TINY.render("Current top scores:", True, (160, 185, 160))
        screen.blit(lbl, (W // 2 - lbl.get_width() // 2, start_y))
        for i, entry in enumerate(self.leaderboard[:5]):
            col = CLR["gold"] if i == 0 else CLR["white"]
            txt = F_TINY.render(
                f"{i+1}. {entry.get('name','?'):<5}  {entry['score']:>6}", True, col)
            screen.blit(txt, (W // 2 - txt.get_width() // 2, start_y + 22 + i * 22))

    # ── Start screen ─────────────────────────────────────────────────────────
    def _draw_start(self, t):
        screen.blit(self.bg, (0, 0))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 18, 0, 145))
        screen.blit(ov, (0, 0))

        title  = F_HUGE.render("JUNGLE DODGE", True, CLR["gold"])
        shadow = F_HUGE.render("JUNGLE DODGE", True, (40, 22, 0))
        screen.blit(shadow, (W // 2 - title.get_width() // 2 + 4, 48))  # tighter y (UX rec)
        screen.blit(title,  (W // 2 - title.get_width() // 2, 44))

        sub = F_MED.render("Survive the jungle — dodge everything that falls!", True, CLR["white"])
        screen.blit(sub, (W // 2 - sub.get_width() // 2, 148))

        # Divider
        pygame.draw.line(screen, CLR["vine_dk"], (W // 2 - 280, 186), (W // 2 + 280, 186), 1)

        legend = [
            ("VINE",    CLR["vine"],    "Slow — sways as it drops"),
            ("BOMB",    CLR["orange"],  "Explodes on impact — watch the blast radius"),
            ("SPIKE",   CLR["spike"],   "Fast — barely any time to react"),
            ("BOULDER", CLR["boulder"], "Slow fall, then rolls across the ground"),
        ]
        ly = 198
        for name, col, desc in legend:
            ns = F_MED.render(name,   True, col)
            ds = F_SMALL.render(desc, True, (195, 215, 195))
            screen.blit(ns, (W // 2 - 210, ly))
            screen.blit(ds, (W // 2 - 10,  ly + 5))
            ly += 40

        # Divider
        pygame.draw.line(screen, CLR["vine_dk"], (W // 2 - 280, ly + 2), (W // 2 + 280, ly + 2), 1)

        ctrl = F_SMALL.render(
            "Arrow keys / A-D to move  |  3 lives  |  45 seconds per level",
            True, (170, 195, 170))
        screen.blit(ctrl, (W // 2 - ctrl.get_width() // 2, ly + 10))

        if self.leaderboard:
            best = self.leaderboard[0]
            hi = F_SMALL.render(
                f"Best: {best.get('name','?')}  {best['score']} pts", True, CLR["gold"])
            screen.blit(hi, (W // 2 - hi.get_width() // 2, ly + 36))
            lb_hint = F_TINY.render("TAB — view full leaderboard", True, (130, 160, 130))
            screen.blit(lb_hint, (W // 2 - lb_hint.get_width() // 2, ly + 58))

        # Pulsing CTA
        cta = F_LARGE.render(">> PRESS SPACE TO START <<", True, pulse_color(CLR["gold"], t))
        screen.blit(cta, (W // 2 - cta.get_width() // 2, H - 70))

    # ── Event handling ───────────────────────────────────────────────────────
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        # ── Name entry ────────────────────────────────────────────────────────
        if self.state == ST_NAME_ENTRY:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.name_input:
                    self._submit_score(self.name_input)
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

        # ── ESC ───────────────────────────────────────────────────────────────
        if event.key == pygame.K_ESCAPE:
            if self.state == ST_PLAYING:
                self.state = ST_PAUSED        # ESC during play → pause (CRIT-04)
            elif self.state == ST_PAUSED:
                pygame.quit(); sys.exit()     # ESC again → quit
            else:
                pygame.quit(); sys.exit()
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

        # ── TAB — leaderboard from start ──────────────────────────────────────
        if event.key == pygame.K_TAB and self.state == ST_START:
            self.state = ST_LEADERBOARD

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
