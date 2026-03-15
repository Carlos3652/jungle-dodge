"""
Jungle Dodge — shared constants
All module-level constants extracted from jungle_dodge.py (task jd-01).
"""

import os
import pygame

pygame.init()
pygame.font.init()

# ── Window ────────────────────────────────────────────────────────────────────
W, H   = 3840, 2160
SX     = W / 900          # horizontal scale  (≈ 4.267)
SY     = H / 600          # vertical scale    (= 3.6)
S      = SY               # uniform size scale (use vertical as reference)
FPS    = 60

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

# ── Roll ──────────────────────────────────────────────────────────────────────
ROLL_DURATION    = 0.4        # total roll time in seconds
ROLL_SPEED_MULT  = 2.5        # speed multiplier during roll
ROLL_IFRAME      = 0.25       # i-frame duration at start of roll (seconds)
ROLL_COOLDOWN    = 2.0        # cooldown between rolls (seconds)
# ── Streak Combo ─────────────────────────────────────────────────────────────
STREAK_TIERS = (
    # (min_dodges, multiplier, label, color_key)
    ( 0, 1.0, None,     None),       # 0–4:  no indicator
    ( 5, 1.5, "bronze", "bronze"),    # 5–9:  bronze badge
    (10, 2.0, "silver", "silver"),    # 10–19: silver badge
    (20, 3.0, "gold",   "gold"),      # 20+:  gold badge
)

# ── Wave Rhythm Phases ───────────────────────────────────────────────────────
# Each phase: (start_time, end_time, name, spawn_interval_modifier)
# modifier < 1.0 = faster spawns (push), > 1.0 = slower spawns (breather)
WAVE_PHASES = (
    ( 0, 15, "calm",      1.0),
    (15, 23, "push",      0.75),   # -25% interval
    (23, 27, "breather",  1.40),   # +40% interval
    (27, 35, "push",      0.70),   # -30% interval
    (35, 39, "breather",  1.0),    # standard
    (39, 44, "crescendo", 0.50),   # max rate + dual spawns
)
# Crescendo dual-spawn minimum separation (fraction of W)
CRESCENDO_SEPARATION = 0.5

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
