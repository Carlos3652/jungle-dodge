"""
Entity classes extracted from jungle_dodge.py (task jd-06a).

Player, Obstacle base, and four obstacle subclasses: Vine, Bomb, Spike, Boulder.
"""

import math
import random

import pygame

from constants import (
    W, H, SX, SY, S,
    GROUND_Y, PLAYER_FLOOR,
    CLR,
    MAX_LIVES, STUN_SECS, IMMUNE_EXTRA,
    PLAYER_SPD, SPEED_SCALE,
)


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

    def tick_timers(self, dt):
        """Advance stun/immune timers without processing movement.

        Extracted so callers (e.g. LevelUpState) can keep timers ticking
        without duplicating the logic that lives inside update().
        """
        if self.stun_t > 0:
            self.stun_t  = max(0.0, self.stun_t - dt)
            self.flash_t += dt * 12
        if self.immune_t > 0:
            self.immune_t = max(0.0, self.immune_t - dt)

    def update(self, dt, keys):
        # Both keys held -> neutral (BUG-08)
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

        self.tick_timers(dt)

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
        # Explosion radius -- checked once on the frame explosion starts
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
