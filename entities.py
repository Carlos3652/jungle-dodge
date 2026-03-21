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
    ROLL_DURATION, ROLL_SPEED_MULT, ROLL_IFRAME, ROLL_COOLDOWN,
    POWERUP_RADIUS, POWERUP_SPEED_FRAC,
)
from themes import get_color


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
        # Roll state
        self.rolling  = False        # True while roll is active
        self.roll_t   = 0.0          # remaining roll duration
        self.roll_dir = 1            # locked direction at roll start
        self.roll_cd  = 0.0          # cooldown timer (counts down to 0)

    @property
    def rect(self):
        return pygame.Rect(self.x - self.PW // 2, self.y, self.PW, self.PH)

    def is_stunned(self):
        return self.stun_t > 0

    def tick_timers(self, dt):
        """Advance stun/immune/flash timers without processing movement."""
        if self.stun_t > 0:
            self.stun_t  = max(0.0, self.stun_t - dt)
            self.flash_t += dt * 12
        if self.immune_t > 0:
            self.immune_t = max(0.0, self.immune_t - dt)

    def is_hit_immune(self):
        """True during stun AND brief grace period after (CRIT-03)."""
        return self.immune_t > 0

    def can_roll(self):
        """True if roll is off cooldown and player is not already rolling or stunned."""
        return not self.rolling and self.roll_cd <= 0 and not self.is_stunned()

    def start_roll(self):
        """Begin a side roll in the current facing direction."""
        if not self.can_roll():
            return
        self.rolling  = True
        self.roll_t   = ROLL_DURATION
        self.roll_dir = self.facing
        self.roll_cd  = ROLL_COOLDOWN
        # Grant i-frames for the first portion of the roll
        self.immune_t = max(self.immune_t, ROLL_IFRAME)

    def hit(self):
        if self.is_hit_immune():
            return
        self.lives    = max(0, self.lives - 1)   # floor clamp (BUG-03)
        self.stun_t   = STUN_SECS
        self.immune_t = STUN_SECS + IMMUNE_EXTRA
        self.flash_t  = 0.0

    def tick_timers(self, dt):
        """Advance stun/immune/roll timers without processing movement.

        Extracted so callers (e.g. LevelUpState) can keep timers ticking
        without duplicating the logic that lives inside update().
        """
        if self.stun_t > 0:
            self.stun_t  = max(0.0, self.stun_t - dt)
            self.flash_t += dt * 12
        if self.immune_t > 0:
            self.immune_t = max(0.0, self.immune_t - dt)
        # Roll duration
        if self.rolling:
            self.roll_t = max(0.0, self.roll_t - dt)
            if self.roll_t <= 0:
                self.rolling = False
        # Roll cooldown (ticks even when not rolling)
        if self.roll_cd > 0:
            self.roll_cd = max(0.0, self.roll_cd - dt)

    def update(self, dt, keys):
        if self.rolling:
            # During roll: move at 2.5x speed in locked direction, ignore input
            dx = self.roll_dir * PLAYER_SPD * ROLL_SPEED_MULT * dt
        else:
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

    def _draw_character(self, surf, cx, top_y, stunned=False, theme=None):
        """Draw the explorer character at the given center-x and top-y."""
        boty = top_y + self.PH
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
        pants_col = get_color("char_pants", theme)
        pygame.draw.line(surf, pants_col, (cx - o5, top_y + o36), lleg, max(1, int(5 * S)))
        pygame.draw.line(surf, pants_col, (cx + o5, top_y + o36), rleg, max(1, int(5 * S)))
        boots_col = get_color("char_boots", theme)
        pygame.draw.circle(surf, boots_col, lleg, o4)
        pygame.draw.circle(surf, boots_col, rleg, o4)

        # Arms
        aw = math.sin(self.walk_t + math.pi) * o7 if self.walk_t else 0
        ay = top_y + o22
        shirt_col = get_color("char_jacket", theme)
        pygame.draw.line(surf, shirt_col, (cx - o12, ay), (cx - o20, ay + o14 + int(aw)), max(1, int(4 * S)))
        pygame.draw.line(surf, shirt_col, (cx + o12, ay), (cx + o20, ay + o14 - int(aw)), max(1, int(4 * S)))

        # Body
        bcol = shirt_col if not stunned else (255, 255, 100)
        pygame.draw.rect(surf, bcol, (cx - o13, top_y + o16, o26, o22), border_radius=o4)

        # Head
        hcy  = top_y + o10
        hcol = get_color("char_skin", theme) if not stunned else (255, 230, 150)
        pygame.draw.circle(surf, hcol, (cx, hcy), o12)
        pygame.draw.circle(surf, (30, 20, 10), (cx + o4 * self.facing, hcy), o2)

        # Explorer hat
        hcol2 = get_color("char_hat", theme) if not stunned else (180, 140, 70)
        pygame.draw.ellipse(surf, hcol2, (cx - o17, hcy - o5, int(34 * S), o9))
        pygame.draw.rect(surf,   hcol2, (cx - o9, hcy - o17, o18, o13), border_radius=o3)
        hat_band_col = get_color("char_hat_band", theme)
        pygame.draw.rect(surf, hat_band_col, (cx - o9, hcy - int(6 * S), o18, o3))

        # Stun stars
        if stunned:
            for i in range(3):
                angle = self.flash_t + i * (2 * math.pi / 3)
                sx = cx + int(int(22 * S) * math.cos(angle))
                sy = top_y - o4 + int(o9 * math.sin(angle))
                pygame.draw.circle(surf, CLR["yellow"], (sx, sy), o4)
                pygame.draw.circle(surf, CLR["white"],  (sx, sy), o2)

    def draw(self, surf, particles=None, theme=None):
        """Draw player to surf. Pass an optional ParticleSystem for roll trail effects."""
        stunned = self.is_stunned()
        if stunned and int(self.flash_t) % 2 == 1:
            return

        # ── Roll cooldown arc (drawn under player) ──────────────────────────
        if self.roll_cd > 0:
            cd_frac = 1.0 - (self.roll_cd / ROLL_COOLDOWN)  # 0→1 as recharge fills
            arc_r = int(24 * S)
            arc_rect = pygame.Rect(self.x - arc_r, self.y + self.PH - int(4 * S),
                                   arc_r * 2, arc_r * 2)
            end_angle = -math.pi / 2 + cd_frac * 2 * math.pi
            pygame.draw.arc(surf, get_color("roll_ready", theme), arc_rect,
                            -math.pi / 2, end_angle, max(1, int(3 * S)))

        # ── Roll tilt transform ─────────────────────────────────────────────
        if self.rolling:
            # Emit trail particles during roll
            if particles is not None:
                trail_col = (180, 220, 255)
                for _ in range(2):
                    px = self.x - self.roll_dir * int(15 * S) + random.uniform(-5, 5) * S
                    py = self.y + self.PH * 0.6 + random.uniform(-5, 5) * S
                    particles.emit(px, py, count=1,
                                   vx=-self.roll_dir * random.uniform(20, 60) * S,
                                   vy=random.uniform(-30, 30) * S,
                                   size=random.uniform(3, 6) * S,
                                   color=trail_col, lifetime=0.2)
            # Render player to a temporary surface, tilt 45°, squash Y to 0.85
            pw_full = self.PW + int(20 * S)  # extra margin for tilt
            ph_full = self.PH + int(20 * S)
            tmp = pygame.Surface((pw_full, ph_full), pygame.SRCALPHA)
            offset_x = pw_full // 2
            offset_y = int(10 * S)
            self._draw_character(tmp, offset_x, offset_y, stunned, theme=theme)
            # Rotate 45° in roll direction
            angle = -45 * self.roll_dir
            rotated = pygame.transform.rotate(tmp, angle)
            # Squash Y to 85%
            rw, rh = rotated.get_size()
            squashed = pygame.transform.scale(rotated, (rw, max(1, int(rh * 0.85))))
            # Blit centered on player position
            sw2, sh2 = squashed.get_size()
            surf.blit(squashed, (self.x - sw2 // 2, self.y + self.PH // 2 - sh2 // 2))
            return

        self._draw_character(surf, self.x, self.y, stunned, theme=theme)


# ─────────────────────────────────────────────────────────────────────────────
#  Obstacle Base
# ─────────────────────────────────────────────────────────────────────────────
class Obstacle:
    def __init__(self):
        self.alive               = True
        self.scored              = False   # True once obstacle reaches ground
        self._pts                = False   # True once points have been awarded
        self.did_hit             = False   # True if this obstacle hit the player (CRIT-01)
        self._near_miss_checked  = False   # True once near-miss check has been done (jd-10)

    def update(self, dt, player): pass
    def draw(self, surf, theme=None): pass
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

    def draw(self, surf, theme=None):
        segs  = 9
        seg_h = self.BH // segs
        sway_off = int(3 * S)
        leaf_w = int(11 * S)
        leaf_h = int(6  * S)
        vine_col = get_color("vine_base", theme)
        vine_dk  = get_color("vine_highlight", theme)
        for i in range(segs):
            sy  = int(self.y) + i * seg_h
            off = int(math.sin(self.sway_t + i * 0.5) * sway_off)
            col = vine_col if i % 2 == 0 else vine_dk
            pygame.draw.rect(surf, col,
                             (int(self.x) - self.BW // 2 + off, sy, self.BW, seg_h + 1))
            if i % 3 == 1:
                lx = int(self.x) + self.BW // 2 + off
                pygame.draw.ellipse(surf, vine_col, (lx, sy + 1, leaf_w, leaf_h))
        pygame.draw.circle(surf, vine_dk,
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

    def draw(self, surf, theme=None):
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

        pygame.draw.circle(surf, get_color("bomb_body", theme),  (cx, cy), self.R)
        pygame.draw.circle(surf, (55, 55, 55), (cx - o5, cy - o5), o6)
        fuse_top = (cx + o4, cy - self.R - o10)
        pygame.draw.lines(surf, get_color("bomb_fuse", theme), False,
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

    def draw(self, surf, theme=None):
        cx  = int(self.x)
        top = int(self.y)
        tip = int(self.y + self.SH)
        hw  = self.SW // 2
        pts = [(cx - hw, top), (cx + hw, top), (cx, tip)]
        pygame.draw.polygon(surf, get_color("spike_base", theme),    pts)
        pygame.draw.polygon(surf, get_color("spike_tip", theme), pts, max(1, int(2 * S)))
        pygame.draw.line(surf, (220, 220, 240),
                         (cx - hw // 2, top + int(4 * S)), (cx - int(2 * S), tip - int(6 * S)), 1)
        pygame.draw.rect(surf, get_color("spike_tip", theme), (cx - hw, top, self.SW, int(5 * S)))


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

    def draw(self, surf, theme=None):
        cx, cy = int(self.x), int(self.y)
        boulder_col = get_color("boulder_base", theme)
        boulder_dk  = get_color("boulder_crack", theme)
        pygame.draw.ellipse(surf, (30, 55, 20),
                            (cx - self.R, cy + self.R - int(8 * S), self.R * 2, int(12 * S)))
        pygame.draw.circle(surf, boulder_col,    (cx, cy), self.R)
        pygame.draw.circle(surf, boulder_dk, (cx + int(5 * S), cy + int(5 * S)), self.R - int(6 * S))
        for x1, y1, x2, y2 in self.cracks:
            pygame.draw.line(surf, boulder_dk,
                             self._rot_pt(x1, y1), self._rot_pt(x1 + x2, y1 + y2), max(1, int(2 * S)))
        pygame.draw.circle(surf, boulder_dk, (cx, cy), self.R, max(1, int(2 * S)))
        pygame.draw.circle(surf, (165, 145, 120),
                           (cx - self.R // 3, cy - self.R // 3), self.R // 4)


# ─────────────────────────────────────────────────────────────────────────────
#  PowerUp (jd-12)
# ─────────────────────────────────────────────────────────────────────────────
_POWERUP_COLOR_KEYS = {
    "shield": "powerup_shield",
    "slowmo": "powerup_slowmo",
    "magnet": "powerup_magnet",
}

class PowerUp(Obstacle):
    """Collectible power-up that falls straight down at 60% vine speed.

    kind: "shield" | "slowmo" | "magnet"
    """
    R = POWERUP_RADIUS  # radius of the circle

    def __init__(self, kind, level, spawn_x=None):
        super().__init__()
        self.kind = kind
        self.x = float(
            spawn_x if spawn_x is not None
            else random.randint(int(50 * SX), W - int(50 * SX))
        )
        self.y = float(-self.R * 2)
        # 60% of vine base speed (vine base = 90 + level*15, mult applied)
        vine_base_vy = (90 + level * 15) * (1 + (level - 1) * SPEED_SCALE * 0.8) * SY
        self.vy = vine_base_vy * POWERUP_SPEED_FRAC
        self.glow_angle = random.uniform(0, math.pi * 2)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - self.R, int(self.y) - self.R,
                           self.R * 2, self.R * 2)

    def update(self, dt, player):
        self.y += self.vy * dt
        self.glow_angle += dt * 3.0  # rotating ring speed
        if self.y - self.R > GROUND_Y:
            self.alive = False  # fell off screen without pickup

    def check_hit(self, player):
        # Power-ups don't damage the player; pickup is handled separately
        return False

    def check_pickup(self, player):
        """Return True if the player overlaps this power-up."""
        return self.alive and self.rect.colliderect(player.rect)

    def draw(self, surf, theme=None):
        cx, cy = int(self.x), int(self.y)
        color_key = _POWERUP_COLOR_KEYS.get(self.kind, "powerup_shield")
        col = get_color(color_key, theme)

        # Outer glow ring (rotating dashed effect)
        ring_r = self.R + int(6 * S)
        num_dashes = 8
        dash_len = math.pi / (num_dashes * 2)
        for i in range(num_dashes):
            start_angle = self.glow_angle + i * (2 * math.pi / num_dashes)
            end_angle = start_angle + dash_len
            # Draw arc segment as short line
            ax1 = cx + int(ring_r * math.cos(start_angle))
            ay1 = cy + int(ring_r * math.sin(start_angle))
            ax2 = cx + int(ring_r * math.cos(end_angle))
            ay2 = cy + int(ring_r * math.sin(end_angle))
            pygame.draw.line(surf, col, (ax1, ay1), (ax2, ay2), max(1, int(2 * S)))

        # Inner filled circle
        pygame.draw.circle(surf, col, (cx, cy), self.R)

        # Kind icon (simple distinguishing marks)
        inner_col = (255, 255, 255)
        if self.kind == "shield":
            # Small shield shape (chevron)
            hw = self.R // 2
            pts = [(cx - hw, cy - hw), (cx + hw, cy - hw),
                   (cx + hw, cy + int(2 * S)), (cx, cy + hw),
                   (cx - hw, cy + int(2 * S))]
            pygame.draw.polygon(surf, inner_col, pts, max(1, int(2 * S)))
        elif self.kind == "slowmo":
            # Clock icon (circle + hands)
            ir = self.R // 2
            pygame.draw.circle(surf, inner_col, (cx, cy), ir, max(1, int(2 * S)))
            pygame.draw.line(surf, inner_col, (cx, cy), (cx, cy - ir + int(2 * S)),
                             max(1, int(2 * S)))
            pygame.draw.line(surf, inner_col, (cx, cy),
                             (cx + ir - int(3 * S), cy), max(1, int(2 * S)))
        elif self.kind == "magnet":
            # U-shape magnet
            hw = self.R // 2
            pygame.draw.arc(surf, inner_col,
                            (cx - hw, cy - int(2 * S), hw * 2, hw * 2),
                            math.pi, 2 * math.pi, max(1, int(3 * S)))
            pygame.draw.line(surf, inner_col, (cx - hw, cy + hw - int(2 * S)),
                             (cx - hw, cy - hw), max(1, int(2 * S)))
            pygame.draw.line(surf, inner_col, (cx + hw, cy + hw - int(2 * S)),
                             (cx + hw, cy - hw), max(1, int(2 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Obstacle Variants (jd-13)
# ─────────────────────────────────────────────────────────────────────────────

class VineSnap(Vine):
    """Vine variant (L4+): lunges sideways at a random point during fall."""

    def __init__(self, level, spawn_x=None):
        super().__init__(level, spawn_x=spawn_x)
        # Lunge parameters
        self._lunge_progress = random.uniform(0.3, 0.7)  # 30-70% of travel
        self._lunge_dist = random.uniform(120, 180) * SX
        self._lunge_dir = random.choice([-1, 1])
        self._lunge_dur = 0.15  # seconds
        self._lunge_started = False
        self._lunge_done = False
        self._lunge_t = 0.0
        self._total_fall = float(GROUND_Y - self.BH + self.BH)  # total distance to ground

    def update(self, dt, player):
        if not self.landed and not self._lunge_done:
            # Check if we've reached the lunge trigger point
            fall_frac = (self.y + self.BH) / GROUND_Y  # 0 at top, 1 at ground
            if fall_frac >= self._lunge_progress and not self._lunge_started:
                self._lunge_started = True
                self._lunge_t = 0.0

            if self._lunge_started and not self._lunge_done:
                self._lunge_t += dt
                # Fast lateral movement during lunge
                lunge_frac = min(1.0, self._lunge_t / self._lunge_dur)
                lateral_speed = self._lunge_dist / self._lunge_dur
                self.x += self._lunge_dir * lateral_speed * dt
                self.x = max(float(self.BW), min(float(W - self.BW), self.x))
                if lunge_frac >= 1.0:
                    self._lunge_done = True

        super().update(dt, player)


class BombDelay(Bomb):
    """Bomb variant (L5+): 0.8s fuse delay before ground explosion."""

    FUSE_DELAY = 0.8

    def __init__(self, level, spawn_x=None):
        super().__init__(level, spawn_x=spawn_x)
        self._delay_active = False
        self._delay_timer = 0.0

    def update(self, dt, player):
        if self._delay_active:
            self._delay_timer += dt
            if self._delay_timer >= self.FUSE_DELAY:
                # Now actually explode
                self._delay_active = False
                self.exploded = True
                self.scored = True
            return

        if self.exploded:
            self.exp_t += dt
            if self.exp_t >= self.exp_dur:
                self.alive = False
            return

        # Normal falling
        self.y += self.vy * dt
        self.fuse_t += dt * 6
        self.spark_t += dt * 14

        if self.y >= GROUND_Y - self.R:
            self.y = float(GROUND_Y - self.R)
            # Start delay instead of immediate explosion
            self._delay_active = True
            self._delay_timer = 0.0

    def check_hit(self, player):
        if player.is_hit_immune():
            return False
        if self._delay_active:
            # During fuse delay, only the bomb body can hit (not explosion radius)
            return self.rect.colliderect(player.rect)
        return super().check_hit(player)

    def draw(self, surf, theme=None):
        if self._delay_active:
            cx, cy = int(self.x), int(self.y)
            # Draw warning circle on ground
            warning_surf = pygame.Surface((self.exp_r * 2, self.exp_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(warning_surf, (255, 0, 0, 102),  # 40% alpha
                               (self.exp_r, self.exp_r), self.exp_r)
            surf.blit(warning_surf, (cx - self.exp_r, cy - self.exp_r))
            # Draw the bomb body on top
            o4 = int(4 * S)
            o5 = int(5 * S)
            o6 = int(6 * S)
            o10 = int(10 * S)
            o2 = int(2 * S)
            o3 = int(3 * S)
            pygame.draw.circle(surf, get_color("bomb_body", theme), (cx, cy), self.R)
            pygame.draw.circle(surf, (55, 55, 55), (cx - o5, cy - o5), o6)
            fuse_top = (cx + o4, cy - self.R - o10)
            pygame.draw.lines(surf, get_color("bomb_fuse", theme), False,
                              [(cx, cy - self.R), (cx + o2, cy - self.R - o5), fuse_top], max(1, o2))
            # Pulsing spark during delay
            pulse = abs(math.sin(self._delay_timer * 12))
            spark_r = int(o4 * (1 + pulse))
            pygame.draw.circle(surf, (255, 100, 20), fuse_top, spark_r)
            return
        super().draw(surf, theme=theme)


def spawn_cluster_spike(level, spawn_x):
    """Factory: returns a list of 3 Spikes in triangle formation (L3+).

    Center spike at spawn_x, two flanking at +/-30*S px.
    Each spike is 80% of normal size, flanks staggered higher.
    """
    spikes = []
    offsets = [0, -30 * S, 30 * S]
    for i, x_off in enumerate(offsets):
        s = Spike(level, spawn_x=int(spawn_x + x_off))
        # Scale down to 80%
        s.SW = int(18 * S * 0.8)
        s.SH = int(44 * S * 0.8)
        if i > 0:
            # Flanking spikes start higher
            s.y = float(-s.SH * 1.3)
        spikes.append(s)
    return spikes


class BouncingSpike(Spike):
    """Spike variant (L6+): bounces 60*S px upward once on ground contact."""

    def __init__(self, level, spawn_x=None):
        super().__init__(level, spawn_x=spawn_x)
        self._has_bounced = False
        self._original_vy = self.vy
        # Gravity to pull the spike back down after bounce
        self._gravity = abs(self.vy) * 2.5  # strong enough to arc back quickly

    def update(self, dt, player):
        if self._has_bounced:
            # Apply gravity during bounce arc
            self.vy += self._gravity * dt
        self.y += self.vy * dt
        if self.y >= GROUND_Y:
            if not self._has_bounced:
                self._has_bounced = True
                self.y = float(GROUND_Y)
                # Bounce upward at 60% of original speed
                self.vy = -abs(self._original_vy) * 0.6
                self.scored = True
            else:
                # Second ground contact — die
                self.scored = True
                self.alive = False

    def check_hit(self, player):
        return not player.is_hit_immune() and self.rect.colliderect(player.rect)


# ─────────────────────────────────────────────────────────────────────────────
#  CanopyDrop (jd-14) — L2+: falling leaves with one hidden spike
# ─────────────────────────────────────────────────────────────────────────────
class CanopyDrop(Obstacle):
    """8-12 leaves fall from top; one random leaf hides a spike.

    Telegraph: 0.3s shadow on ground before leaves start falling.
    Hidden spike reveals at 70% of fall (color change + size increase).
    Only the spike-leaf does damage.
    """
    TELEGRAPH_DUR = 0.3
    REVEAL_FRAC = 0.7  # reveal spike at 70% of fall

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x = float(spawn_x if spawn_x is not None else
                        random.randint(int(50 * SX), W - int(50 * SX)))
        self.num_leaves = random.randint(8, 12)
        self.spike_idx = random.randint(0, self.num_leaves - 1)

        # Vine base speed at 60%
        vine_base = (90 + level * 15) * (1 + (level - 1) * SPEED_SCALE * 0.8) * SY
        base_vy = vine_base * 0.6

        # Each leaf: (x, y, vy, sway_t, sway_a, sway_s)
        self.leaves = []
        for i in range(self.num_leaves):
            lx = self.x + random.uniform(-80, 80) * SX
            lx = max(int(20 * SX), min(W - int(20 * SX), lx))
            ly = float(-random.uniform(10, 60) * SY)
            lvy = base_vy * random.uniform(0.8, 1.2)
            sway_t = random.uniform(0, math.pi * 2)
            sway_a = random.uniform(6, 14) * SX
            sway_s = random.uniform(1.5, 3.0)
            self.leaves.append([float(lx), ly, lvy, sway_t, sway_a, sway_s])

        self.telegraph_t = 0.0
        self.started = False  # leaves start falling after telegraph
        self.revealed = False  # spike-leaf revealed
        self._level = level
        # vy attribute for speed_mult application (apply to all leaves)
        self.vy = base_vy
        self.leaf_w = int(15 * S)
        self.leaf_h = int(10 * S)

    def update(self, dt, player):
        if not self.started:
            self.telegraph_t += dt
            if self.telegraph_t >= self.TELEGRAPH_DUR:
                self.started = True
            return

        all_done = True
        for i, leaf in enumerate(self.leaves):
            lx, ly, lvy, sway_t, sway_a, sway_s = leaf
            ly += lvy * dt
            sway_t += dt * sway_s
            lx += math.sin(sway_t) * sway_a * dt
            lx = max(float(self.leaf_w), min(float(W - self.leaf_w), lx))
            leaf[0], leaf[1], leaf[3] = lx, ly, sway_t

            if ly < GROUND_Y:
                all_done = False

            # Check reveal threshold for spike leaf
            if i == self.spike_idx and not self.revealed:
                fall_frac = (ly + 60 * SY) / (GROUND_Y + 60 * SY)
                if fall_frac >= self.REVEAL_FRAC:
                    self.revealed = True

        if all_done:
            self.scored = True
            self.alive = False

    def check_hit(self, player):
        if not self.started or player.is_hit_immune():
            return False
        # Only the spike leaf can hit
        leaf = self.leaves[self.spike_idx]
        lx, ly = leaf[0], leaf[1]
        if ly >= GROUND_Y:
            return False
        spike_r = int(12 * S) if self.revealed else int(8 * S)
        dist = math.hypot(lx - player.x, ly - (player.y + player.PH // 2))
        return dist < spike_r + max(player.PW, player.PH) // 2

    def draw(self, surf, theme=None):
        base_col = get_color("canopy_drop_base", theme)
        warn_col = get_color("warning_color", theme)

        # Telegraph: shadow on ground
        if not self.started:
            alpha = int(80 * (self.telegraph_t / self.TELEGRAPH_DUR))
            shadow_w = int(120 * SX)
            shadow_h = int(16 * SY)
            shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha),
                                (0, 0, shadow_w, shadow_h))
            surf.blit(shadow_surf, (int(self.x) - shadow_w // 2,
                                     GROUND_Y - shadow_h // 2))
            return

        for i, leaf in enumerate(self.leaves):
            lx, ly = int(leaf[0]), int(leaf[1])
            if ly >= GROUND_Y:
                continue
            if i == self.spike_idx and self.revealed:
                # Spike leaf: bigger, warning color
                sw = int(self.leaf_w * 1.4)
                sh = int(self.leaf_h * 1.4)
                pygame.draw.ellipse(surf, warn_col,
                                    (lx - sw // 2, ly - sh // 2, sw, sh))
                # Small spike triangle
                tri_h = int(8 * S)
                pts = [(lx - int(4 * S), ly + sh // 2),
                       (lx + int(4 * S), ly + sh // 2),
                       (lx, ly + sh // 2 + tri_h)]
                pygame.draw.polygon(surf, warn_col, pts)
            else:
                pygame.draw.ellipse(surf, base_col,
                                    (lx - self.leaf_w // 2, ly - self.leaf_h // 2,
                                     self.leaf_w, self.leaf_h))


# ─────────────────────────────────────────────────────────────────────────────
#  CrocSnap (jd-14) — L4+: horizontal ground-level sweep
# ─────────────────────────────────────────────────────────────────────────────
class CrocSnap(Obstacle):
    """Ground-level horizontal sweep at 600*SX px/s. Roll counters it.

    Telegraph: 0.5s — glowing eyes at screen edge before sweep.
    """
    TELEGRAPH_DUR = 0.5
    CROC_H = int(30 * S)
    CROC_W = int(100 * S)

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.direction = random.choice([-1, 1])
        self.speed = 600 * SX
        if self.direction == 1:
            self.x = float(-self.CROC_W)
        else:
            self.x = float(W + self.CROC_W)
        self.y = float(GROUND_Y - self.CROC_H)
        self.telegraph_t = 0.0
        self.started = False
        # vy attribute for compatibility (not really vertical)
        self.vy = self.speed

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.CROC_W, self.CROC_H)

    def update(self, dt, player):
        if not self.started:
            self.telegraph_t += dt
            if self.telegraph_t >= self.TELEGRAPH_DUR:
                self.started = True
            return

        self.x += self.direction * self.speed * dt

        # Off-screen on the far side -> done
        if self.direction == 1 and self.x > W + self.CROC_W:
            self.scored = True
            self.alive = False
        elif self.direction == -1 and self.x < -self.CROC_W * 2:
            self.scored = True
            self.alive = False

    def check_hit(self, player):
        if not self.started or player.is_hit_immune():
            return False
        return self.rect.colliderect(player.rect)

    def draw(self, surf, theme=None):
        croc_col = get_color("croc_base", theme)
        teeth_col = get_color("croc_teeth", theme)

        if not self.started:
            # Telegraph: glowing eyes at edge
            eye_x = 0 if self.direction == 1 else W
            eye_y = int(self.y + self.CROC_H // 3)
            eye_r = int(6 * S)
            pulse = 0.5 + 0.5 * math.sin(self.telegraph_t * 10)
            eye_col = (int(200 * pulse), int(120 * pulse), 0)
            offset = int(15 * SX) * self.direction
            pygame.draw.circle(surf, eye_col, (eye_x + offset, eye_y), eye_r)
            pygame.draw.circle(surf, eye_col,
                               (eye_x + offset, eye_y + int(12 * S)), eye_r)
            return

        cx, cy = int(self.x), int(self.y)
        # Body rectangle
        pygame.draw.rect(surf, croc_col,
                         (cx, cy, self.CROC_W, self.CROC_H),
                         border_radius=int(4 * S))

        # Teeth along the top edge
        tooth_w = int(6 * S)
        tooth_h = int(8 * S)
        num_teeth = self.CROC_W // (tooth_w * 2)
        for i in range(num_teeth):
            tx = cx + tooth_w + i * tooth_w * 2
            pts = [(tx, cy), (tx + tooth_w, cy), (tx + tooth_w // 2, cy - tooth_h)]
            pygame.draw.polygon(surf, teeth_col, pts)

        # Eye
        eye_off = int(20 * S) if self.direction == 1 else self.CROC_W - int(20 * S)
        pygame.draw.circle(surf, (200, 120, 0),
                           (cx + eye_off, cy + int(8 * S)), int(5 * S))


# ─────────────────────────────────────────────────────────────────────────────
#  PoisonPuddle (jd-14) — L5+: ground hazard with standing timer
# ─────────────────────────────────────────────────────────────────────────────
class PoisonPuddle(Obstacle):
    """Ground puddle. Standing in it for 1.5s cumulative -> stun.

    Max 2 on screen (enforced by spawn logic). Lifetime 8-12s.
    Telegraph: 0.3s ground crack before puddle appears.
    """
    TELEGRAPH_DUR = 0.3
    STUN_THRESHOLD = 1.5
    RADIUS = int(80 * S)

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x = float(spawn_x if spawn_x is not None else
                        random.randint(int(100 * SX), W - int(100 * SX)))
        self.y = float(GROUND_Y)
        self.telegraph_t = 0.0
        self.active = False
        self.overlap_t = 0.0  # cumulative time player stands in puddle
        self.lifetime = random.uniform(8.0, 12.0)
        self.age = 0.0
        self.vy = 0.0  # no vertical speed, for compatibility

    def update(self, dt, player):
        if not self.active:
            self.telegraph_t += dt
            if self.telegraph_t >= self.TELEGRAPH_DUR:
                self.active = True
            return

        self.age += dt
        if self.age >= self.lifetime:
            self.scored = True
            self.alive = False
            return

        # Check overlap with player
        dist = math.hypot(self.x - player.x,
                          self.y - (player.y + player.PH))
        if dist < self.RADIUS + max(player.PW, player.PH) // 2:
            self.overlap_t += dt
            if self.overlap_t >= self.STUN_THRESHOLD:
                self.overlap_t = 0.0  # reset for next stun
                if not player.is_hit_immune():
                    player.hit()
                    self.did_hit = True
        else:
            # Reset overlap timer when player leaves
            self.overlap_t = max(0.0, self.overlap_t - dt * 0.5)

    def check_hit(self, player):
        # Damage is handled in update() via standing timer
        return False

    def draw(self, surf, theme=None):
        puddle_col = get_color("poison_puddle", theme)

        if not self.active:
            # Telegraph: ground crack/bubbles
            cx, cy = int(self.x), int(self.y)
            alpha = int(120 * (self.telegraph_t / self.TELEGRAPH_DUR))
            crack_len = int(40 * S)
            crack_col = (puddle_col[0], puddle_col[1], puddle_col[2])
            for angle in [0, math.pi * 0.6, math.pi * 1.3]:
                ex = cx + int(crack_len * math.cos(angle))
                ey = cy + int(crack_len * 0.3 * math.sin(angle))
                pygame.draw.line(surf, crack_col, (cx, cy), (ex, ey),
                                 max(1, int(2 * S)))
            return

        cx, cy = int(self.x), int(self.y)
        # Fade out near end of lifetime
        fade = 1.0
        if self.lifetime - self.age < 2.0:
            fade = max(0.0, (self.lifetime - self.age) / 2.0)

        alpha = int(100 * fade)
        puddle_surf = pygame.Surface((self.RADIUS * 2, self.RADIUS), pygame.SRCALPHA)
        pygame.draw.ellipse(puddle_surf,
                            (puddle_col[0], puddle_col[1], puddle_col[2], alpha),
                            (0, 0, self.RADIUS * 2, self.RADIUS))
        surf.blit(puddle_surf, (cx - self.RADIUS, cy - self.RADIUS // 2))

        # Bubbles
        bubble_t = self.age * 3
        for i in range(3):
            bx = cx + int(math.sin(bubble_t + i * 2.1) * self.RADIUS * 0.5)
            by = cy - int(abs(math.sin(bubble_t * 0.7 + i)) * int(12 * S))
            br = int((2 + math.sin(bubble_t + i)) * S)
            pygame.draw.circle(surf, (puddle_col[0], puddle_col[1], puddle_col[2]),
                               (bx, by), max(1, br))


# ─────────────────────────────────────────────────────────────────────────────
#  ScreechBat (jd-14) — L7+: diving arc with 1s tracking
# ─────────────────────────────────────────────────────────────────────────────
class ScreechBat(Obstacle):
    """Spawns at top, tracks player X for 1s, then dives in an arc.

    Telegraph: 0.5s exclamation mark at spawn point.
    """
    TELEGRAPH_DUR = 0.5
    TRACK_DUR = 1.0
    HIT_R = int(25 * S)

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x = float(spawn_x if spawn_x is not None else
                        random.randint(int(80 * SX), W - int(80 * SX)))
        self.y = float(-int(30 * SY))
        self.speed = 200 * SY
        self.vy = self.speed  # for speed_mult compatibility
        self.telegraph_t = 0.0
        self.tracking = False
        self.diving = False
        self.track_t = 0.0
        self.target_x = self.x  # updated during tracking
        self.flap_t = 0.0

        # Dive arc control points (set when dive begins)
        self._dive_start_x = self.x
        self._dive_start_y = self.y
        self._dive_t = 0.0
        self._dive_dur = 0.0  # computed when dive starts

    def update(self, dt, player):
        self.flap_t += dt * 6

        if not self.tracking and not self.diving:
            self.telegraph_t += dt
            if self.telegraph_t >= self.TELEGRAPH_DUR:
                self.tracking = True
            return

        if self.tracking:
            self.track_t += dt
            self.target_x = player.x
            # Hover near top, slowly drifting toward player
            self.x += (self.target_x - self.x) * 2.0 * dt
            self.y = float(-int(30 * SY)) + math.sin(self.track_t * 3) * int(10 * SY)

            if self.track_t >= self.TRACK_DUR:
                self.tracking = False
                self.diving = True
                self._dive_start_x = self.x
                self._dive_start_y = self.y
                self._dive_t = 0.0
                # Dive duration based on distance
                dist = math.hypot(self.target_x - self.x,
                                  GROUND_Y - self.y)
                self._dive_dur = max(0.5, dist / self.speed)
            return

        if self.diving:
            self._dive_t += dt
            t = min(1.0, self._dive_t / self._dive_dur)

            # Quadratic bezier arc: start -> control (mid-high) -> target ground
            ctrl_x = (self._dive_start_x + self.target_x) / 2
            ctrl_y = self._dive_start_y - int(100 * SY)  # arc upward first

            # B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
            omt = 1.0 - t
            self.x = omt * omt * self._dive_start_x + 2 * omt * t * ctrl_x + t * t * self.target_x
            self.y = omt * omt * self._dive_start_y + 2 * omt * t * ctrl_y + t * t * GROUND_Y

            if t >= 1.0:
                self.scored = True
                self.alive = False

    def check_hit(self, player):
        if not self.diving or player.is_hit_immune():
            return False
        dist = math.hypot(self.x - player.x,
                          self.y - (player.y + player.PH // 2))
        return dist < self.HIT_R + max(player.PW, player.PH) // 2

    def draw(self, surf, theme=None):
        body_col = get_color("bat_body", theme)
        wing_col = get_color("bat_wing", theme)

        if not self.tracking and not self.diving:
            # Telegraph: exclamation mark at spawn
            cx, cy = int(self.x), max(int(20 * SY), int(self.y))
            warn_col = get_color("warning_color", theme)
            pulse = 0.5 + 0.5 * math.sin(self.telegraph_t * 12)
            size = int(18 * S * pulse)
            pygame.draw.circle(surf, warn_col, (cx, cy), max(2, size))
            # Exclamation line
            pygame.draw.line(surf, warn_col,
                             (cx, cy - int(20 * S)),
                             (cx, cy - int(8 * S)),
                             max(1, int(3 * S)))
            pygame.draw.circle(surf, warn_col,
                               (cx, cy - int(4 * S)), int(2 * S))
            return

        cx, cy = int(self.x), int(self.y)
        # Body
        body_r = int(10 * S)
        pygame.draw.circle(surf, body_col, (cx, cy), body_r)

        # Wings (flapping)
        wing_span = int(20 * S)
        wing_y_off = int(math.sin(self.flap_t) * 8 * S)
        # Left wing
        pts_l = [(cx - int(3 * S), cy),
                 (cx - wing_span, cy - wing_y_off),
                 (cx - wing_span + int(5 * S), cy + int(5 * S))]
        pygame.draw.polygon(surf, wing_col, pts_l)
        # Right wing
        pts_r = [(cx + int(3 * S), cy),
                 (cx + wing_span, cy - wing_y_off),
                 (cx + wing_span - int(5 * S), cy + int(5 * S))]
        pygame.draw.polygon(surf, wing_col, pts_r)

        # Eyes
        pygame.draw.circle(surf, (200, 0, 0),
                           (cx - int(3 * S), cy - int(3 * S)), int(2 * S))
        pygame.draw.circle(surf, (200, 0, 0),
                           (cx + int(3 * S), cy - int(3 * S)), int(2 * S))


# ─────────────────────────────────────────────────────────────────────────────
#  GroundHazard (jd-14) — L5+: column rising from ground
# ─────────────────────────────────────────────────────────────────────────────
class GroundHazard(Obstacle):
    """Vertical column: 60*SX wide, 120*SY tall, rises from ground.

    Phases: 0.5s telegraph -> 0.3s rise -> 1.0s active -> 0.3s retract.
    Damage only during active phase.
    """
    COL_W = int(60 * SX)
    COL_H = int(120 * SY)
    TELEGRAPH_DUR = 0.5
    RISE_DUR = 0.3
    ACTIVE_DUR = 1.0
    RETRACT_DUR = 0.3

    def __init__(self, level, spawn_x=None):
        super().__init__()
        self.x = float(spawn_x if spawn_x is not None else
                        random.randint(int(80 * SX), W - int(80 * SX)))
        self.y = float(GROUND_Y)
        self.phase = "telegraph"  # telegraph -> rise -> active -> retract -> done
        self.phase_t = 0.0
        self.height_frac = 0.0  # 0 = flush with ground, 1 = fully extended
        self.vy = 0.0  # compatibility

    def update(self, dt, player):
        self.phase_t += dt

        if self.phase == "telegraph":
            if self.phase_t >= self.TELEGRAPH_DUR:
                self.phase = "rise"
                self.phase_t = 0.0
        elif self.phase == "rise":
            self.height_frac = min(1.0, self.phase_t / self.RISE_DUR)
            if self.phase_t >= self.RISE_DUR:
                self.phase = "active"
                self.phase_t = 0.0
                self.height_frac = 1.0
        elif self.phase == "active":
            if self.phase_t >= self.ACTIVE_DUR:
                self.phase = "retract"
                self.phase_t = 0.0
        elif self.phase == "retract":
            self.height_frac = max(0.0, 1.0 - self.phase_t / self.RETRACT_DUR)
            if self.phase_t >= self.RETRACT_DUR:
                self.scored = True
                self.alive = False

    def check_hit(self, player):
        if self.phase != "active" or player.is_hit_immune():
            return False
        col_rect = pygame.Rect(int(self.x) - self.COL_W // 2,
                                int(GROUND_Y - self.COL_H),
                                self.COL_W, self.COL_H)
        return col_rect.colliderect(player.rect)

    def draw(self, surf, theme=None):
        warn_col = get_color("warning_color", theme)
        cx = int(self.x)

        if self.phase == "telegraph":
            # Glowing crack line on ground
            alpha = int(180 * (self.phase_t / self.TELEGRAPH_DUR))
            pulse = 0.5 + 0.5 * math.sin(self.phase_t * 14)
            crack_col = (int(warn_col[0] * pulse),
                         int(warn_col[1] * pulse),
                         int(warn_col[2] * pulse))
            pygame.draw.line(surf, crack_col,
                             (cx - self.COL_W // 2, GROUND_Y),
                             (cx + self.COL_W // 2, GROUND_Y),
                             max(1, int(3 * S)))
            # Small cracks
            for i in range(3):
                off = int((i - 1) * 15 * SX)
                pygame.draw.line(surf, crack_col,
                                 (cx + off, GROUND_Y),
                                 (cx + off + int(5 * SX),
                                  GROUND_Y - int(10 * SY)),
                                 max(1, int(2 * S)))
            return

        # Draw column based on height_frac
        h = int(self.COL_H * self.height_frac)
        if h <= 0:
            return

        col_y = GROUND_Y - h
        # Gradient effect: darker at base, lighter at top
        base_col = warn_col
        top_col = (min(255, warn_col[0] + 40),
                   min(255, warn_col[1] + 20),
                   min(255, warn_col[2] + 20))

        # Draw column
        pygame.draw.rect(surf, base_col,
                         (cx - self.COL_W // 2, col_y, self.COL_W, h))
        # Lighter inner rect
        inner_w = self.COL_W - int(8 * SX)
        pygame.draw.rect(surf, top_col,
                         (cx - inner_w // 2, col_y, inner_w, h))
        # Top cap
        pygame.draw.rect(surf, top_col,
                         (cx - self.COL_W // 2 - int(4 * SX), col_y,
                          self.COL_W + int(8 * SX), int(6 * SY)))


class SplitBoulder(Boulder):
    """Boulder variant (L5+): 1.4x radius, splits into 2 normal boulders on ground."""

    def __init__(self, level, spawn_x=None):
        super().__init__(level, spawn_x=spawn_x)
        self.R = int(30 * S * 1.4)
        self._has_split = False
        self._level = level

    def update(self, dt, player):
        if not self.rolling:
            self.y += self.vy * dt
            self.rot += self.vy * dt * 0.03
            if self.y >= GROUND_Y - self.R:
                self.y = float(GROUND_Y - self.R)
                self._has_split = True
                self.scored = True
                self.alive = False
        # SplitBoulder never rolls — it splits on ground contact

    def split(self):
        """Return 2 child Boulder objects going left and right."""
        children = []
        for direction in [-1, 1]:
            child = Boulder(self._level, spawn_x=int(self.x))
            child.y = float(GROUND_Y - child.R)
            child.rolling = True
            child.scored = True
            child.roll_dir = direction
            children.append(child)
        return children
