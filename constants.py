"""
Jungle Dodge shared constants (jd-01).
"""

import os
import types
import pygame

if not getattr(pygame.font, "get_init", lambda: True)():
    pygame.font.init()

W, H   = 3840, 2160
SX     = W / 900
SY     = H / 600
S      = SY
FPS    = 60

GROUND_Y     = H - int(90 * S)
PLAYER_FLOOR = GROUND_Y

CLR = types.MappingProxyType({
    "sky_top"    : (  6,  14,   8),
    "sky_bot"    : ( 14,  30,  12),
    "ground"     : ( 60,  40,  20),
    "grass"      : ( 44,  92,  32),
    "white"      : (255, 255, 255),
    "black"      : (  0,   0,   0),
    "red"        : (220,  50,  50),
    "yellow"     : (255, 210,  30),
    "orange"     : (255, 140,   0),
    "gold"       : (212, 160,  32),
    "heart"      : (140,  26,  26),
    "heart_empty": ( 40,  10,  10),
    "teal"       : (  0, 200, 160),
    "skin"       : (220, 180, 130),
    "shirt"      : (200, 170, 100),
    "pants"      : ( 80,  60,  40),
    "hat"        : (140, 100,  50),
    "lb_bg"      : ( 10,  25,  10),
    "lb_row_a"   : ( 18,  45,  18),
    "lb_row_b"   : ( 12,  32,  12),
    "silver"     : (192, 192, 192),
    "bronze"     : (205, 127,  50),
    "stone"      : ( 42,  46,  38),
    "stone_hi"   : ( 62,  68,  56),
    "olive"      : (120, 130,  90),
    "vine"       : ( 38, 212,  72),
    "vine_dk"    : ( 15, 110,  35),
    "lb_border"  : ( 38, 212,  72),
    "bomb"       : ( 25,  25,  25),
    "fuse"       : (255,  90,  20),
    "spark"      : (255, 200,  50),
    "spike"      : (200,  70, 255),
    "spike_dk"   : (130,  35, 180),
    "boulder"    : (140, 115,  85),
    "boulder_dk" : (100,  80,  60),
})

LEVEL_TIME       = 45
MAX_LIVES        = 3
STUN_SECS        = 3.0
IMMUNE_EXTRA     = 0.15
PLAYER_SPD       = int(360 * SX)
DODGE_PTS            = 10
NEAR_MISS_PTS        = 5
NEAR_MISS_THRESHOLD  = int(40 * S)
BASE_SPAWN       = 1.5
SPAWN_DEC        = 0.12
MIN_SPAWN        = 0.35
SPEED_SCALE      = 0.25

ROLL_DURATION    = 0.4
ROLL_SPEED_MULT  = 2.5
ROLL_IFRAME      = 0.25
ROLL_COOLDOWN    = 2.0

STREAK_TIERS = (
    ( 0, 1.0, None,     None),
    ( 5, 1.5, "bronze", "bronze"),
    (10, 2.0, "silver", "silver"),
    (20, 3.0, "gold",   "gold"),
)
STREAK_LOST_THRESHOLD = 5

WAVE_PHASES = (
    ( 0, 15, "calm",      1.0),
    (15, 23, "push",      0.75),
    (23, 27, "breather",  1.40),
    (27, 35, "push",      0.70),
    (35, 39, "breather",  1.0),
    (39, 44, "crescendo", 0.50),
)
CRESCENDO_SEPARATION = 0.5

OBS_TYPES        = ("vine", "bomb", "spike", "boulder")
OBS_WEIGHTS      = (3, 2, 3, 2)
MAX_NAME_LEN     = 5
LEADERBOARD_SIZE = 10

ST_START       = "start"
ST_PLAYING     = "playing"
ST_PAUSED      = "paused"
ST_LEVELUP     = "levelup"
ST_GAMEOVER    = "gameover"
ST_NAME_ENTRY  = "name_entry"
ST_LEADERBOARD = "leaderboard"

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
F_SERIF = _font("Times New Roman", int(28 * S), bold=True)
F_SKULL = _font("Segoe UI Symbol", int(24 * S))
