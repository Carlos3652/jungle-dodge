"""
HUD and screen-drawing functions extracted from jungle_dodge.py (task jd-06b).

Each function receives the target surface and relevant state data as arguments.
pulse_color is defined here as a visual helper used by draw functions.
"""

import math

import pygame

from constants import (
    W, H, SX, SY, S,
    GROUND_Y,
    CLR,
    LEVEL_TIME, MAX_LIVES, STUN_SECS,
    MAX_NAME_LEN, LEADERBOARD_SIZE,
    STREAK_TIERS,
    WAVE_PHASES,
    F_HUGE, F_LARGE, F_MED, F_SMALL, F_TINY, F_SERIF, F_SKULL,
    DIFFICULTIES, DIFFICULTY_ORDER,
)
from themes import get_color


# ── Helper ────────────────────────────────────────────────────────────────────
def pulse_color(base_col, ticks, speed=0.004, lo=0.65):
    p = lo + (1 - lo) * (0.5 + 0.5 * math.sin(ticks * speed))
    return tuple(int(c * p) for c in base_col)


# ─────────────────────────────────────────────────────────────────────────────
#  Pre-allocated surface cache (avoids per-frame SRCALPHA allocations)
# ─────────────────────────────────────────────────────────────────────────────
class HudCache:
    """Pre-allocated overlay and HUD surfaces."""

    def __init__(self, theme=None):
        # Controls hint panel (start screen)
        self.ctrl_panel = pygame.Surface((int(250 * SX), int(80 * S)), pygame.SRCALPHA)
        self.ctrl_panel.fill((0, 18, 0, 210))

        # Stone HUD bar
        self.hud_panel = pygame.Surface((W, int(72 * S)), pygame.SRCALPHA)
        self.hud_panel.fill((*get_color("hud_bg", theme), 238))

        # Full-screen overlays
        self.ov_start = pygame.Surface((W, H), pygame.SRCALPHA)
        self.ov_start.fill((0, 6, 0, 210))

        self.ov_levelup = pygame.Surface((W, H), pygame.SRCALPHA)
        self.ov_levelup.fill((0, 30, 5, 165))

        self.ov_pause = pygame.Surface((W, H), pygame.SRCALPHA)
        self.ov_pause.fill((0, 0, 0, 160))

        self.ov_lb = pygame.Surface((W, H), pygame.SRCALPHA)
        self.ov_lb.fill((0, 15, 0, 170))

        self.ov_gameover = pygame.Surface((W, H), pygame.SRCALPHA)
        self.ov_gameover.fill((28, 5, 5, 185))

        # Name-entry slot surfaces
        _sw = int(72 * S); _sh = int(80 * S)
        self.slot_filled = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self.slot_filled.fill((20, 40, 20, 220))
        self.slot_empty = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self.slot_empty.fill((10, 22, 10, 220))

        # ── Pre-rendered static HUD labels (never change) ───────────────
        lbl_col = get_color("hud_label", theme)
        self.lbl_score   = F_TINY.render("SCORE", True, lbl_col)
        self.lbl_level   = F_TINY.render("LEVEL", True, lbl_col)
        self.lbl_time    = F_TINY.render("TIME",  True, lbl_col)
        self.lbl_lives   = F_TINY.render("LIVES", True, lbl_col)
        self.lbl_stunned = F_TINY.render("STUNNED", True, get_color("roll_ready", theme))

        # Pre-rendered wave phase label surfaces
        hud_text = get_color("hud_text", theme)
        self.wave_labels = {
            name: F_TINY.render(label, True, hud_text)
            for name, label in _WAVE_PHASE_LABELS.items()
        }

        # ── Pre-rendered overlay / screen static labels ───────────────
        # Pause overlay
        self.lbl_paused       = F_LARGE.render("PAUSED", True, hud_text)
        self.lbl_pause_h1     = F_MED.render("SPACE \u2014 resume", True, (195, 215, 195))
        self.lbl_pause_h2     = F_MED.render("ESC \u2014 return to home screen", True, (195, 215, 195))

        # Level-up overlay
        self.lbl_levelup_sub  = F_MED.render("Things are getting faster...", True, hud_text)

        # Start screen
        gold_col = get_color("streak_gold", theme)
        self.lbl_title        = F_HUGE.render("JUNGLE DODGE", True, gold_col)
        self.lbl_title_shad   = F_HUGE.render("JUNGLE DODGE", True, (28, 16, 0))
        self.lbl_tagline      = F_SMALL.render("SURVIVE. DODGE. OUTLAST.", True, (185, 210, 185))
        self.lbl_tab_hint     = F_TINY.render("TAB \u2014 view leaderboard", True, (80, 110, 80))
        self.lbl_quit_hint    = F_TINY.render("Close window to quit", True, (55, 75, 55))
        self.lbl_question     = F_SMALL.render("?", True, (100, 140, 100))
        self.lbl_ctrl_hints   = [
            F_TINY.render(t, True, (175, 210, 175)) for t in [
                "Arrow keys / A-D  \u2014 move",
                "3 lives  |  45 s per level",
                "ESC \u2014 pause / home",
            ]
        ]

        # Game-over screen
        warning_col = get_color("warning_color", theme)
        self.lbl_gameover       = F_HUGE.render("GAME OVER", True, warning_col)
        self.lbl_gameover_shad  = F_HUGE.render("GAME OVER", True, (80, 0, 0))
        self.lbl_go_top10       = F_SMALL.render("Current Top 10:", True, (190, 210, 190))

        # Leaderboard screen
        self.lbl_lb_title       = F_LARGE.render("TOP 10 LEADERBOARD", True, gold_col)
        self.lbl_lb_title_shad  = F_LARGE.render("TOP 10 LEADERBOARD", True, (50, 35, 0))

        # Name-entry screen
        self.lbl_ne_title       = F_LARGE.render("YOU MADE THE TOP 10!", True, gold_col)
        self.lbl_ne_title_shad  = F_LARGE.render("YOU MADE THE TOP 10!", True, (50, 30, 0))
        self.lbl_ne_prompt      = F_MED.render("Enter your name:", True, (190, 210, 190))
        self.lbl_ne_hint1       = F_SMALL.render(
            "A-Z  /  0-9  to type     BACKSPACE to delete", True, (140, 170, 140))
        self.lbl_ne_hint2       = F_SMALL.render(
            "ENTER to confirm     ESC to skip", True, (140, 170, 140))

        # ── Pre-rendered skull icons (2 states: alive / lost) ────────
        self.skull_alive = F_SKULL.render("\u2620", True, (190, 30, 30))
        self.skull_lost  = F_SKULL.render("\u2620", True, (55, 55, 55))

        # Store theme for dynamic rendering methods
        self._theme = theme

        # ── Dynamic value cache (dirty-tracked) ────────────────────────
        self._dyn_score      = None   # cached score int
        self._dyn_score_shad = None
        self._dyn_score_val  = None
        self._dyn_level      = None
        self._dyn_level_shad = None
        self._dyn_level_val  = None
        self._dyn_time_key   = None   # (display_t, is_red)
        self._dyn_time_shad  = None
        self._dyn_time_val   = None
        self._dyn_streak_key  = None  # (streak, tier_label)
        self._dyn_streak_surf = None

        # ── Leaderboard table surface cache (dirty-tracked by hash) ──────
        self._lb_hash_full  = None
        self._lb_hash_compact = None
        self._lb_hdr_full   = None   # header surface (full mode)
        self._lb_hdr_compact = None  # header surface (compact mode)
        self._lb_rows_full  = []     # list of row surfaces (full mode)
        self._lb_rows_compact = []   # list of row surfaces (compact mode)
        self._lb_empty_full = None   # "no scores" surface (full mode)
        self._lb_empty_compact = None

    # ── Dynamic value helpers with dirty-tracking ───────────────────────
    def get_score_surfs(self, score):
        """Return (shadow, value) surfaces for score, re-rendering only on change."""
        if score != self._dyn_score:
            self._dyn_score = score
            s = str(score)
            self._dyn_score_shad = F_SERIF.render(s, True, (18, 18, 12))
            self._dyn_score_val  = F_SERIF.render(s, True, get_color("streak_gold", self._theme))
        return self._dyn_score_shad, self._dyn_score_val

    def get_level_surfs(self, level):
        """Return (shadow, value) surfaces for level, re-rendering only on change."""
        if level != self._dyn_level:
            self._dyn_level = level
            s = str(level)
            self._dyn_level_shad = F_SERIF.render(s, True, (18, 18, 12))
            self._dyn_level_val  = F_SERIF.render(s, True, get_color("hud_text", self._theme))
        return self._dyn_level_shad, self._dyn_level_val

    def get_time_surfs(self, display_t, is_red):
        """Return (shadow, value) surfaces for time, re-rendering only on change."""
        key = (display_t, is_red)
        if key != self._dyn_time_key:
            self._dyn_time_key = key
            s = f"{display_t:02d}s"
            tcol = get_color("warning_color", self._theme) if is_red else get_color("hud_text", self._theme)
            self._dyn_time_shad = F_SERIF.render(s, True, (18, 18, 12))
            self._dyn_time_val  = F_SERIF.render(s, True, tcol)
        return self._dyn_time_shad, self._dyn_time_val

    def get_streak_surf(self, streak, tier_label, text_color):
        """Return cached badge text surface, re-rendering only on change."""
        key = (streak, tier_label)
        if key != self._dyn_streak_key:
            self._dyn_streak_key = key
            mult, _, _ = _streak_tier_info(streak)
            badge_str = f"x{mult:g}  {streak}"
            self._dyn_streak_surf = F_TINY.render(badge_str, True, text_color)
        return self._dyn_streak_surf

    def get_lb_table_surfs(self, leaderboard, full=True):
        """Return (header_surf, row_surfs_list, empty_surf) for the leaderboard table.

        Re-renders only when the leaderboard data hash changes.
        *empty_surf* is non-None only when leaderboard is empty.
        """
        lb_hash = hash(tuple(
            (e.get("name", "?"), e.get("score", 0), e.get("level", "-"))
            for e in (leaderboard or [])[:LEADERBOARD_SIZE]
        ))

        if full:
            cached_hash = self._lb_hash_full
        else:
            cached_hash = self._lb_hash_compact

        if lb_hash == cached_hash:
            if full:
                return self._lb_hdr_full, self._lb_rows_full, self._lb_empty_full
            else:
                return self._lb_hdr_compact, self._lb_rows_compact, self._lb_empty_compact

        # ── Re-bake surfaces ──────────────────────────────────────────
        col_w = int(620 * SX)
        row_h = int(36 * S) if full else int(26 * S)
        font  = F_SMALL if full else F_TINY

        x1 = int(14  * SX)
        x2 = int(70  * SX)
        x3 = col_w - int(200 * SX)
        x4 = col_w - int(60  * SX)

        # Header
        hdr = pygame.Surface((col_w, row_h))
        hdr.fill((30, 70, 30))
        hdr.set_alpha(220)
        gold_c   = get_color("streak_gold", self._theme)
        silver_c = get_color("streak_silver", self._theme)
        bronze_c = get_color("streak_bronze", self._theme)
        white_c  = get_color("hud_text", self._theme)
        lb_row_a = get_color("lb_player_row", self._theme)
        for text, x_off in [("#", x1), ("NAME", x2), ("SCORE", x3), ("LVL", x4)]:
            s = font.render(text, True, gold_c)
            hdr.blit(s, (x_off, (row_h - s.get_height()) // 2))

        # Empty message
        empty_surf = None
        if not leaderboard:
            empty_surf = font.render("No scores yet \u2014 be the first!", True, (160, 190, 160))

        # Row surfaces
        medal_bg = [(60, 45, 0), (35, 35, 45), (45, 25, 10)]
        medal_fc = [gold_c, silver_c, bronze_c]
        rows = []
        for i, entry in enumerate((leaderboard or [])[:LEADERBOARD_SIZE]):
            bg_col = medal_bg[i] if i < 3 else (
                lb_row_a if (i - 3) % 2 == 0 else CLR["lb_row_b"])
            rs = pygame.Surface((col_w, row_h))
            rs.fill(bg_col)
            rs.set_alpha(220)

            fc = medal_fc[i] if i < 3 else white_c
            cy = (row_h - font.get_height()) // 2
            for text, x_off, color in [
                (str(i + 1),                  x1, fc),
                (entry.get("name", "?"),      x2, white_c),
                (str(entry.get("score", 0)),  x3, gold_c),
                (str(entry.get("level", "-")),x4, (160, 200, 160)),
            ]:
                s = font.render(text, True, color)
                rs.blit(s, (x_off, cy))
            rows.append(rs)

        # Store in the correct slot
        if full:
            self._lb_hash_full   = lb_hash
            self._lb_hdr_full    = hdr
            self._lb_rows_full   = rows
            self._lb_empty_full  = empty_surf
        else:
            self._lb_hash_compact   = lb_hash
            self._lb_hdr_compact    = hdr
            self._lb_rows_compact   = rows
            self._lb_empty_compact  = empty_surf

        return hdr, rows, empty_surf


# ─────────────────────────────────────────────────────────────────────────────
#  Background — Jungle Cliff Face (Lost Temple Ruins)
# ─────────────────────────────────────────────────────────────────────────────
def build_background(theme=None):
    """Build and return the static background surface."""
    bg  = pygame.Surface((W, H))
    sy  = GROUND_Y / 340
    def svy(v): return int(v * sy)
    def svx(v): return int(v * W / 900)

    # 1. Cliff gradient fill
    c_top = (26, 24, 16); c_mid = (42, 36, 24); c_bot = (34, 30, 20)
    for y in range(GROUND_Y):
        t = y / GROUND_Y
        if t < 0.4:
            r,g,b = [int(c_top[i]+(c_mid[i]-c_top[i])*(t/0.4)) for i in range(3)]
        else:
            r,g,b = [int(c_mid[i]+(c_bot[i]-c_mid[i])*((t-0.4)/0.6)) for i in range(3)]
        pygame.draw.line(bg, (r, g, b), (0, y), (W, y))

    # 2. Horizontal strata lines
    sc = (26, 24, 8)
    for svg_y in [55, 95, 140, 185, 230, 275]:
        pygame.draw.line(bg, sc, (0, svy(svg_y)), (W, svy(svg_y)), 1)

    # 3. Crack network
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

    # 4. Deity face
    FACE   = (37, 32, 24)
    CROWN  = (34, 30, 20)
    TRICRN = (42, 36, 24)
    DARK   = (14, 12,  8)
    cx0 = W // 2
    fw = int(176 * SX / 2)
    pygame.draw.ellipse(bg, FACE,
        (cx0 - fw, svy(175) - svy(95), fw * 2, svy(190)))
    pygame.draw.ellipse(bg, (26, 22, 16),
        (cx0 - fw, svy(175) - svy(95), fw * 2, svy(190)), 3)
    pygame.draw.rect(bg, CROWN, (svx(370), svy(82), svx(160), svy(22)))
    pygame.draw.rect(bg, CROWN, (svx(385), svy(60), svx(22),  svy(26)))
    pygame.draw.rect(bg, CROWN, (svx(430), svy(55), svx(40),  svy(30)))
    pygame.draw.rect(bg, CROWN, (svx(493), svy(60), svx(22),  svy(26)))
    pygame.draw.polygon(bg, TRICRN, [(svx(388),svy(82)),(svx(399),svy(58)),(svx(410),svy(82))])
    pygame.draw.polygon(bg, TRICRN, [(svx(432),svy(82)),(svx(450),svy(50)),(svx(468),svy(82))])
    pygame.draw.polygon(bg, TRICRN, [(svx(490),svy(82)),(svx(501),svy(58)),(svx(512),svy(82))])
    pygame.draw.rect(bg, DARK, (svx(390), svy(145), svx(48), svy(30)), border_radius=4)
    pygame.draw.rect(bg, DARK, (svx(462), svy(145), svx(48), svy(30)), border_radius=4)
    gw, gh = svx(32), max(1, svy(16))
    eye_s = pygame.Surface((gw, gh), pygame.SRCALPHA)
    pygame.draw.ellipse(eye_s, (0, 200, 160, 46), (0, 0, gw, gh))
    bg.blit(eye_s, (svx(414) - gw // 2, svy(160) - gh // 2))
    bg.blit(eye_s, (svx(486) - gw // 2, svy(160) - gh // 2))
    pygame.draw.lines(bg, (26, 24, 16), False,
        [(svx(440), svy(175)), (svx(450), svy(200)), (svx(460), svy(175))], 4)
    pygame.draw.rect(bg, DARK, (svx(410), svy(215), svx(80), svy(22)), border_radius=3)
    for tx in [424, 438, 452, 466, 480]:
        pygame.draw.line(bg, (26, 24, 8),
            (svx(tx), svy(215)), (svx(tx), svy(215) + svy(22)), 2)
    pygame.draw.rect(bg, (46, 40, 24), (svx(352), svy(78), svx(196), svy(202)), 4)
    pygame.draw.rect(bg, (38, 32, 14), (svx(358), svy(84), svx(184), svy(190)), 1)
    crack([(395,105),(420,140),(408,165),(425,195),(415,230)], 3)
    crack([(420,140),(438,148)], 1)

    # 5. Vine cascades
    VDK = (26, 96, 16)
    VBR = get_color("accent_color", theme)
    def vine(pts, col, w):
        pygame.draw.lines(bg, col, False, [(svx(x), svy(y)) for x,y in pts], w)
    vine([(0,0),(8,40),(4,80),(11,120),(4,160),(9,200),(3,245),(9,285),(4,340)], VDK, 9)
    vine([(13,0),(19,45),(14,90),(21,130),(13,175),(19,215),(12,260)], VBR, 3)
    vine([(100,0),(93,28),(97,58),(90,88),(94,120),(87,155),(92,190),(85,225),(90,265),(83,300),(88,340)], VDK, 6)
    vine([(900,0),(892,40),(896,80),(889,120),(893,160),(887,200),(891,245),(885,285),(892,340)], VDK, 9)
    vine([(887,0),(880,45),(884,90),(878,135),(883,178),(877,220),(882,260),(876,300)], VBR, 3)
    vine([(800,0),(806,30),(803,65),(810,100),(804,135),(812,170),(805,210),(813,250),(806,290),(815,340)], VDK, 6)
    for lx, lsvy, lrx, lry, lcol in [
        (18,  100, 25, 12, VDK), (8,   200, 28, 12, VBR), (92,  160, 22, 10, VDK),
        (880, 110, 25, 12, VDK), (892, 210, 28, 12, VBR), (808, 170, 22, 10, VDK),
    ]:
        lrx_s = svx(lrx); lry_s = max(1, svy(lry))
        pygame.draw.ellipse(bg, lcol,
            (svx(lx) - lrx_s, svy(lsvy) - lry_s, lrx_s * 2, lry_s * 2))

    # 6. Canopy overhang
    for cx, csv_y, crx, cry, rgb in [
        (100, 10, 140, 50, (14, 32,  8)), (300,  5, 180, 45, (12, 28,  6)),
        (550,  8, 200, 48, (14, 32,  8)), (800, 12, 150, 50, (12, 28,  6)),
        (450,  0, 120, 35, (18, 40,  8)),
    ]:
        crxs = svx(crx); crys = max(1, svy(cry))
        cs = pygame.Surface((crxs * 2, crys * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(cs, (*rgb, 230), (0, 0, crxs * 2, crys * 2))
        bg.blit(cs, (svx(cx) - crxs, max(0, svy(csv_y) - crys)))
    for cx, csv_y, crx, cry, rgb in [
        ( 80, 25,  60, 30, (20, 48, 16)), (220, 18,  80, 32, (22, 46, 14)),
        (420, 15,  90, 28, (20, 48, 16)), (680, 20, 100, 35, (22, 46, 14)),
        (880, 28,  60, 28, (20, 48, 16)),
    ]:
        crxs = svx(crx); crys = max(1, svy(cry))
        cs = pygame.Surface((crxs * 2, crys * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(cs, (*rgb, 178), (0, 0, crxs * 2, crys * 2))
        bg.blit(cs, (svx(cx) - crxs, max(0, svy(csv_y) - crys)))

    # 7. Ground
    pygame.draw.rect(bg, get_color("ground_base", theme), (0, GROUND_Y, W, H - GROUND_Y))
    FLAG = (26, 18, 8)
    flagstones = [(0,120),(120,140),(260,110),(370,160),(530,130),(660,120),(780,120)]
    for fx, fw in flagstones:
        pygame.draw.rect(bg, FLAG, (svx(fx), GROUND_Y, svx(fw), H - GROUND_Y), 1)
    for pts in [[(60,3),(70,28),(62,50)],[(340,3),(352,25),(344,50)],[(620,3),(610,30),(622,50)]]:
        pygame.draw.lines(bg, (12,10,6), False,
            [(svx(x), GROUND_Y + int(y * S)) for x,y in pts], 1)
    pygame.draw.rect(bg, get_color("grass_main", theme), (0, GROUND_Y, W, int(14 * S)))

    # 8. Ground mist
    mist_h = int(80 * S)
    mist = pygame.Surface((W, mist_h), pygame.SRCALPHA)
    for my in range(mist_h):
        a = int(70 * (1.0 - my / mist_h))
        pygame.draw.line(mist, (26, 48, 20, a), (0, my), (W, my))
    bg.blit(mist, (0, GROUND_Y - int(60 * S)))

    return bg


# ─────────────────────────────────────────────────────────────────────────────
#  Tree silhouettes (start screen cinematic layer)
# ─────────────────────────────────────────────────────────────────────────────
def draw_tree_silhouettes(screen):
    sil  = (5, 16, 5)
    tw   = int(7  * S)
    th   = int(90 * S)
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


def draw_game(screen, bg, obstacles, player, particles, theme=None):
    """Draw background, obstacles, player, and particles to screen."""
    screen.blit(bg, (0, 0))
    for obs in obstacles:
        obs.draw(screen, theme=theme)
    if player is None:
        return
    player.draw(screen, particles, theme=theme)
    particles.draw(screen)


# ─────────────────────────────────────────────────────────────────────────────
#  HUD — Stone Tablet (bottom, Variant A)
# ─────────────────────────────────────────────────────────────────────────────

# Badge pill colors — built lazily per-theme via _get_badge_colors()
_BADGE_COLORS_CACHE = {}

def _get_badge_colors(theme=None):
    """Return badge color dict, using theme colors."""
    return {
        "bronze": {"bg": (90, 60, 20),  "border": get_color("streak_bronze", theme), "text": get_color("streak_bronze", theme)},
        "silver": {"bg": (60, 60, 70),  "border": get_color("streak_silver", theme), "text": get_color("streak_silver", theme)},
        "gold":   {"bg": (80, 60,  0),  "border": get_color("streak_gold", theme),   "text": get_color("streak_gold", theme)},
    }

# Wave phase bar colors and labels
_WAVE_PHASE_COLORS = {
    "calm":      (60, 120,  60),
    "push":      (200,  80,  40),
    "breather":  (60, 140, 180),
    "crescendo": (220,  40,  40),
}

_WAVE_PHASE_LABELS = {
    "calm":      "CALM",
    "push":      "PUSH",
    "breather":  "BREATHER",
    "crescendo": "CRESCENDO",
}


def _streak_tier_info(streak):
    """Return (multiplier, tier_label, color_key) for the given streak count.

    Uses the 4-tuple STREAK_TIERS: (min_dodges, multiplier, label, color_key).
    label/color_key are None at the base tier (no badge shown).
    """
    result = STREAK_TIERS[0]
    for tier in STREAK_TIERS:
        if streak >= tier[0]:
            result = tier
    return result[1], result[2], result[3]


def _get_wave_phase(level_t):
    """Return (phase_name, phase_progress 0-1) for level_t seconds."""
    for start, end, name, _mod in WAVE_PHASES:
        if start <= level_t < end:
            progress = (level_t - start) / (end - start)
            return name, progress
    return "calm", 1.0


def draw_wave_phase_bar(screen, level_timer, cache=None):
    """Draw the wave phase segmented bar above the HUD panel.

    cache is an optional HudCache; if provided, uses pre-rendered label surfaces.
    """
    ph    = int(72 * S)
    bar_h = int(12 * S)
    bar_y = H - ph - bar_h - int(4 * S)

    phase_name, phase_progress = _get_wave_phase(level_timer)

    pygame.draw.rect(screen, (20, 20, 20), (0, bar_y, W, bar_h))

    total_time = LEVEL_TIME
    for start, end, name, _mod in WAVE_PHASES:
        seg_x     = int(W * start / total_time)
        seg_w     = int(W * (end - start) / total_time)
        seg_color = _WAVE_PHASE_COLORS.get(name, (60, 120, 60))

        if level_timer >= end:
            pygame.draw.rect(screen, seg_color, (seg_x, bar_y, seg_w, bar_h))
        elif level_timer >= start:
            fill_w = int(seg_w * phase_progress)
            dim = tuple(c // 4 for c in seg_color)
            pygame.draw.rect(screen, dim, (seg_x, bar_y, seg_w, bar_h))
            if fill_w > 0:
                pygame.draw.rect(screen, seg_color, (seg_x, bar_y, fill_w, bar_h))
        else:
            dim = tuple(c // 6 for c in seg_color)
            pygame.draw.rect(screen, dim, (seg_x, bar_y, seg_w, bar_h))

    for start, _end, _name, _mod in WAVE_PHASES:
        div_x = int(W * start / total_time)
        if div_x > 0:
            pygame.draw.line(screen, (40, 40, 40), (div_x, bar_y), (div_x, bar_y + bar_h), 1)

    # Phase label (centered on current phase segment)
    if phase_name in _WAVE_PHASE_LABELS:
        for start, end, name, _mod in WAVE_PHASES:
            if name == phase_name and start <= level_timer < end:
                seg_cx = int(W * (start + end) / 2 / total_time)
                if cache is not None and phase_name in cache.wave_labels:
                    lbl_surf = cache.wave_labels[phase_name]
                else:
                    lbl_surf = F_TINY.render(
                        _WAVE_PHASE_LABELS[phase_name], True, get_color("hud_text"))
                lbl_x = seg_cx - lbl_surf.get_width() // 2
                lbl_y = bar_y + (bar_h - lbl_surf.get_height()) // 2
                screen.blit(lbl_surf, (lbl_x, lbl_y))
                break

    pygame.draw.rect(screen, (80, 80, 80), (0, bar_y, W, bar_h), 1)


def draw_hud(screen, cache, score, level, level_timer, player, streak=0, is_levelup=False, theme=None, max_lives=None,
             active_powerup=None, powerup_timer=0.0, shield_active=False):
    """Draw the bottom HUD bar with score, level, time, lives, streak badge, wave phase bar, and progress bar."""
    if player is None:
        return
    if max_lives is None:
        max_lives = MAX_LIVES
    ph  = int(72 * S)
    py  = H - ph

    screen.blit(cache.hud_panel, (0, py))
    step = int(10 * S)
    for ty in range(py + step, H, step):
        pygame.draw.line(screen, get_color("hud_border", theme), (0, ty), (W, ty), 1)
    pygame.draw.line(screen, get_color("vine_base", theme),    (0, py),          (W, py),          max(1, int(2 * S)))
    pygame.draw.line(screen, get_color("vine_highlight", theme), (0, py + int(2 * S)), (W, py + int(2 * S)), 1)

    # SCORE (left)
    screen.blit(cache.lbl_score, (int(14 * SX), py + int(6 * S)))
    sc_shad, sc_val = cache.get_score_surfs(score)
    screen.blit(sc_shad, (int(15 * SX), py + int(28 * S)))
    screen.blit(sc_val,  (int(14 * SX), py + int(27 * S)))

    # STREAK BADGE (right of score) — only visible at tier >= 5 dodges
    mult, tier_label, color_key = _streak_tier_info(streak)
    badge_colors = _get_badge_colors(theme)
    if tier_label is not None and color_key in badge_colors:
        bc = badge_colors[color_key]
        badge_surf = cache.get_streak_surf(streak, tier_label, bc["text"])
        pad_x = int(8 * SX)
        pad_y = int(3 * S)
        bw = badge_surf.get_width() + pad_x * 2
        bh = badge_surf.get_height() + pad_y * 2
        bx = sc_val.get_width() + int(24 * SX)
        by = py + int(27 * S)
        if color_key == "gold":
            t = pygame.time.get_ticks()
            pulse      = 0.85 + 0.15 * math.sin(t * 0.006)
            bg_col     = tuple(min(255, int(c * pulse)) for c in bc["bg"])
            border_col = tuple(min(255, int(c * pulse)) for c in bc["border"])
        else:
            bg_col     = bc["bg"]
            border_col = bc["border"]
        pill = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pill.fill((*bg_col, 220))
        pygame.draw.rect(pill, border_col, (0, 0, bw, bh), max(1, int(2 * S)),
                         border_radius=int(bh // 2))
        screen.blit(pill, (bx, by))
        screen.blit(badge_surf, (bx + pad_x, by + pad_y))

    # LEVEL (center-left)
    lv_lbl = cache.lbl_level
    lv_label_x = W // 2 - lv_lbl.get_width() // 2 - int(60 * SX)
    screen.blit(lv_lbl, (lv_label_x, py + int(6 * S)))
    lv_shad, lv_val = cache.get_level_surfs(level)
    lv_x = W // 2 - lv_val.get_width() // 2 - int(60 * SX)
    screen.blit(lv_shad, (lv_x + 1, py + int(28 * S)))
    screen.blit(lv_val,  (lv_x,     py + int(27 * S)))

    # TIME (center-right)
    time_left  = max(0.0, LEVEL_TIME - level_timer)
    display_t  = math.ceil(time_left)
    is_red = time_left < 10
    screen.blit(cache.lbl_time, (W // 2 + int(40 * SX), py + int(6 * S)))
    tm_shad, tm_val = cache.get_time_surfs(display_t, is_red)
    screen.blit(tm_shad, (W // 2 + int(41 * SX), py + int(28 * S)))
    screen.blit(tm_val,  (W // 2 + int(40 * SX), py + int(27 * S)))

    # LIVES — pre-rendered skull icons from cache (right)
    screen.blit(cache.lbl_lives, (W - int(122 * SX), py + int(6 * S)))
    skull_gap = int(36 * S)
    for i in range(max_lives):
        sk = cache.skull_alive if i < player.lives else cache.skull_lost
        screen.blit(sk, (W - int(120 * SX) + i * skull_gap, py + int(26 * S)))

    # Vine growth bar / stun bar
    bar_w = int(W * 0.60)
    bar_x = W // 2 - bar_w // 2
    bar_y = H - int(12 * S)
    bar_h = int(8 * S)
    brd   = max(1, int(4 * S))

    if player.is_stunned():
        stun_pct   = max(0.0, player.stun_t / STUN_SECS)
        stun_bar_w = int(bar_w * stun_pct)
        pygame.draw.rect(screen, (20, 60, 55),  (bar_x, bar_y, bar_w, bar_h), border_radius=brd)
        if stun_bar_w > 0:
            pygame.draw.rect(screen, get_color("roll_ready", theme), (bar_x, bar_y, stun_bar_w, bar_h), border_radius=brd)
        pygame.draw.rect(screen, (0, 140, 120), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=brd)
        st = cache.lbl_stunned
        screen.blit(st, (W // 2 - st.get_width() // 2, bar_y - int(16 * S)))
    else:
        prog   = 0.0 if is_levelup else min(1.0, level_timer / LEVEL_TIME)
        fill_w = int(bar_w * prog)
        seg_w  = int(18 * S)
        pygame.draw.rect(screen, (18, 32, 18), (bar_x, bar_y, bar_w, bar_h), border_radius=brd)
        for sx in range(0, fill_w, max(1, seg_w)):
            seg = min(seg_w - 1, fill_w - sx)
            col = get_color("vine_base", theme) if (sx // max(1, seg_w)) % 2 == 0 else get_color("vine_highlight", theme)
            pygame.draw.rect(screen, col, (bar_x + sx, bar_y, seg, bar_h))
        leaf_s = int(4 * S)
        if fill_w > leaf_s:
            lx = bar_x + fill_w
            pygame.draw.polygon(screen, (80, 255, 110),
                                [(lx - leaf_s, bar_y),
                                 (lx + leaf_s, bar_y + bar_h // 2),
                                 (lx - leaf_s, bar_y + bar_h)])
        pygame.draw.rect(screen, get_color("vine_highlight", theme), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=brd)

    # ── Power-up status pill (jd-12) ─────────────────────────────────────
    if active_powerup is not None:
        _pu_color_keys = {
            "shield": "powerup_shield",
            "slowmo": "powerup_slowmo",
            "magnet": "powerup_magnet",
        }
        pu_col = get_color(_pu_color_keys.get(active_powerup, "powerup_shield"), theme)

        if active_powerup == "shield" and shield_active:
            pu_label = "SHIELD"
        elif active_powerup == "shield" and not shield_active:
            pu_label = ""  # shield used, will be deactivated next frame
        elif active_powerup == "slowmo":
            pu_label = f"SLOW {powerup_timer:.1f}s"
        elif active_powerup == "magnet":
            pu_label = f"x3 {powerup_timer:.1f}s"
        else:
            pu_label = active_powerup.upper()

        if pu_label:
            pu_txt = F_TINY.render(pu_label, True, (255, 255, 255))
            pu_pad_x = int(10 * SX)
            pu_pad_y = int(4 * S)
            pu_w = pu_txt.get_width() + pu_pad_x * 2
            pu_h = pu_txt.get_height() + pu_pad_y * 2
            pu_x = W - int(122 * SX) - pu_w - int(16 * SX)
            pu_y = py + int(6 * S)
            pill_s = pygame.Surface((pu_w, pu_h), pygame.SRCALPHA)
            pill_s.fill((*pu_col, 180))
            pygame.draw.rect(pill_s, pu_col, (0, 0, pu_w, pu_h),
                             max(1, int(2 * S)), border_radius=int(pu_h // 2))
            screen.blit(pill_s, (pu_x, pu_y))
            screen.blit(pu_txt, (pu_x + pu_pad_x, pu_y + pu_pad_y))

    # Wave phase bar (above HUD panel, only during active gameplay)
    if not is_levelup:
        draw_wave_phase_bar(screen, level_timer, cache)


# ─────────────────────────────────────────────────────────────────────────────
#  Level-up overlay
# ─────────────────────────────────────────────────────────────────────────────
def draw_levelup_overlay(screen, cache, level, score, theme=None):
    screen.blit(cache.ov_levelup, (0, 0))
    gold = get_color("streak_gold", theme)
    lt  = F_LARGE.render(f"LEVEL {level}!", True, gold)
    sub = cache.lbl_levelup_sub
    sc  = F_SMALL.render(f"Score so far: {score}", True, gold)
    screen.blit(lt,  (W // 2 - lt.get_width()  // 2, H // 2 - int(50 * S)))
    screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + int(20 * S)))
    screen.blit(sc,  (W // 2 - sc.get_width()  // 2, H // 2 + int(65 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Pause overlay
# ─────────────────────────────────────────────────────────────────────────────
def draw_pause_overlay(screen, cache):
    screen.blit(cache.ov_pause, (0, 0))
    pt = cache.lbl_paused
    h1 = cache.lbl_pause_h1
    h2 = cache.lbl_pause_h2
    screen.blit(pt,  (W // 2 - pt.get_width()  // 2, H // 2 - int(60 * S)))
    screen.blit(h1,  (W // 2 - h1.get_width()  // 2, H // 2 + int(10 * S)))
    screen.blit(h2,  (W // 2 - h2.get_width()  // 2, H // 2 + int(50 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Name Entry
# ─────────────────────────────────────────────────────────────────────────────
def draw_name_entry(screen, cache, name_input, cursor_on, score, level, t, theme=None):
    screen.fill((0, 12, 0))

    pygame.draw.line(screen, get_color("vine_highlight", theme),
                     (W // 2 - int(320 * SX), H // 2 - int(120 * S)),
                     (W // 2 + int(320 * SX), H // 2 - int(120 * S)), 1)
    pygame.draw.line(screen, get_color("vine_highlight", theme),
                     (W // 2 - int(320 * SX), H // 2 + int(130 * S)),
                     (W // 2 + int(320 * SX), H // 2 + int(130 * S)), 1)

    # Title
    trop = cache.lbl_ne_title
    shad = cache.lbl_ne_title_shad
    title_y = H // 2 - int(218 * S)
    screen.blit(shad, (W // 2 - trop.get_width() // 2 + int(3 * S), title_y + int(3 * S)))
    screen.blit(trop, (W // 2 - trop.get_width() // 2,              title_y))

    # Score / level
    sc = F_SMALL.render(f"Score: {score}   |   Level {level}", True, (200, 220, 200))
    screen.blit(sc, (W // 2 - sc.get_width() // 2, H // 2 - int(148 * S)))

    # Input prompt
    prompt = cache.lbl_ne_prompt
    screen.blit(prompt, (W // 2 - prompt.get_width() // 2, H // 2 - int(105 * S)))

    # Letter slots
    slot_w   = int(72 * S)
    slot_h   = int(80 * S)
    gap      = int(10 * S)
    total_w  = MAX_NAME_LEN * slot_w + (MAX_NAME_LEN - 1) * gap
    sx_start = W // 2 - total_w // 2
    sy       = H // 2 - int(72 * S)

    for i in range(MAX_NAME_LEN):
        sx = sx_start + i * (slot_w + gap)
        filled = i < len(name_input)
        bd_col = get_color("vine_base", theme) if filled else get_color("vine_highlight", theme)
        screen.blit(cache.slot_filled if filled else cache.slot_empty, (sx, sy))
        pygame.draw.rect(screen, bd_col, (sx, sy, slot_w, slot_h), max(1, int(2 * S)), border_radius=int(6 * S))

        if filled:
            ch_surf = F_LARGE.render(name_input[i], True, get_color("streak_gold", theme))
            screen.blit(ch_surf, (sx + slot_w // 2 - ch_surf.get_width() // 2,
                                  sy + slot_h // 2 - ch_surf.get_height() // 2))
        elif i == len(name_input):
            if cursor_on:
                pygame.draw.rect(screen, get_color("streak_gold", theme),
                                 (sx + slot_w // 2 - int(3 * S), sy + int(16 * S),
                                  int(6 * S), int(48 * S)),
                                 border_radius=int(2 * S))

    # Hints
    h1 = cache.lbl_ne_hint1
    h2 = cache.lbl_ne_hint2
    screen.blit(h1, (W // 2 - h1.get_width() // 2, sy + slot_h + int(18 * S)))
    screen.blit(h2, (W // 2 - h2.get_width() // 2, sy + slot_h + int(46 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Leaderboard table (shared by leaderboard and gameover screens)
# ─────────────────────────────────────────────────────────────────────────────
def draw_lb_table(screen, leaderboard, start_y, full=True, cache=None, theme=None):
    col_w = int(620 * SX)
    row_h = int(36 * S) if full else int(26 * S)
    tx    = W // 2 - col_w // 2

    if cache is not None:
        hdr, rows, empty_surf = cache.get_lb_table_surfs(leaderboard, full)

        # Header
        screen.blit(hdr, (tx, start_y))
        pygame.draw.rect(screen, get_color("tab_active", theme), (tx, start_y, col_w, row_h), 1)

        if empty_surf is not None:
            screen.blit(empty_surf, (W // 2 - empty_surf.get_width() // 2,
                                     start_y + row_h + int(8 * S)))
            return

        for i, rs in enumerate(rows):
            ry = start_y + row_h * (i + 1)
            screen.blit(rs, (tx, ry))
            pygame.draw.rect(screen, (40, 80, 40), (tx, ry, col_w, row_h), 1)
        return

    # ── Fallback: no cache (backwards-compat) ────────────────────────────
    font = F_SMALL if full else F_TINY

    x1 = int(14  * SX)
    x2 = int(70  * SX)
    x3 = col_w - int(200 * SX)
    x4 = col_w - int(60  * SX)

    hdr = pygame.Surface((col_w, row_h), pygame.SRCALPHA)
    hdr.fill((30, 70, 30, 220))
    screen.blit(hdr, (tx, start_y))
    pygame.draw.rect(screen, get_color("tab_active", theme), (tx, start_y, col_w, row_h), 1)
    for text, x_off in [("#", x1), ("NAME", x2), ("SCORE", x3), ("LVL", x4)]:
        s = font.render(text, True, get_color("streak_gold", theme))
        screen.blit(s, (tx + x_off, start_y + (row_h - s.get_height()) // 2))

    if not leaderboard:
        e = font.render("No scores yet \u2014 be the first!", True, (160, 190, 160))
        screen.blit(e, (W // 2 - e.get_width() // 2, start_y + row_h + int(8 * S)))
        return

    medal_bg = [(60, 45, 0), (35, 35, 45), (45, 25, 10)]
    gold_c   = get_color("streak_gold", theme)
    silver_c = get_color("streak_silver", theme)
    bronze_c = get_color("streak_bronze", theme)
    white_c  = get_color("hud_text", theme)
    lb_row_a = get_color("lb_player_row", theme)
    medal_fc = [gold_c, silver_c, bronze_c]

    for i, entry in enumerate(leaderboard[:LEADERBOARD_SIZE]):
        ry     = start_y + row_h * (i + 1)
        bg_col = medal_bg[i] if i < 3 else (lb_row_a if (i - 3) % 2 == 0 else CLR["lb_row_b"])
        rs = pygame.Surface((col_w, row_h), pygame.SRCALPHA)
        rs.fill((*bg_col, 220))
        screen.blit(rs, (tx, ry))
        pygame.draw.rect(screen, (40, 80, 40), (tx, ry, col_w, row_h), 1)

        fc = medal_fc[i] if i < 3 else white_c
        cy = ry + (row_h - font.get_height()) // 2
        for text, x_off, color in [
            (str(i + 1),                 x1, fc),
            (entry.get("name", "?"),     x2, white_c),
            (str(entry.get("score", 0)),  x3, gold_c),
            (str(entry.get("level","-")),x4, (160, 200, 160)),
        ]:
            s = font.render(text, True, color)
            screen.blit(s, (tx + x_off, cy))


# ─────────────────────────────────────────────────────────────────────────────
#  Full Leaderboard screen
# ─────────────────────────────────────────────────────────────────────────────
def draw_leaderboard(screen, bg, cache, leaderboard, t, theme=None):
    screen.blit(bg, (0, 0))
    screen.blit(cache.ov_lb, (0, 0))

    title  = cache.lbl_lb_title
    shadow = cache.lbl_lb_title_shad
    screen.blit(shadow, (W // 2 - title.get_width() // 2 + int(3 * S), int(28 * S)))
    screen.blit(title,  (W // 2 - title.get_width() // 2,              int(25 * S)))

    draw_lb_table(screen, leaderboard, int(95 * S), full=True, cache=cache, theme=theme)

    cta = F_MED.render("SPACE to play again  |  TAB / ESC to home", True,
                       pulse_color(get_color("streak_gold", theme), t))
    screen.blit(cta, (W // 2 - cta.get_width() // 2, H - int(48 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Game Over (not top 10)
# ─────────────────────────────────────────────────────────────────────────────
def draw_gameover(screen, bg, cache, leaderboard, score, level, t, theme=None):
    screen.blit(bg, (0, 0))
    screen.blit(cache.ov_gameover, (0, 0))

    go   = cache.lbl_gameover
    shad = cache.lbl_gameover_shad
    screen.blit(shad, (W // 2 - go.get_width() // 2 + int(4 * S), int(32 * S)))
    screen.blit(go,   (W // 2 - go.get_width() // 2,              int(28 * S)))

    gold = get_color("streak_gold", theme)
    warning = get_color("warning_color", theme)
    sc = F_MED.render(f"Score: {score}   |   Level {level}", True, gold)
    screen.blit(sc, (W // 2 - sc.get_width() // 2, int(128 * S)))

    if leaderboard:
        msg = F_MED.render("Not in the top 10 \u2014 keep trying!", True, warning)
    else:
        msg = F_MED.render("Score some points to get on the leaderboard!", True, warning)
    screen.blit(msg, (W // 2 - msg.get_width() // 2, int(170 * S)))

    lb_lbl = cache.lbl_go_top10
    screen.blit(lb_lbl, (W // 2 - lb_lbl.get_width() // 2, int(208 * S)))

    draw_lb_table(screen, leaderboard, int(234 * S), full=False, cache=cache, theme=theme)

    cta = F_MED.render("SPACE to play again  |  ESC to home", True,
                       pulse_color(gold, t))
    screen.blit(cta, (W // 2 - cta.get_width() // 2, H - int(48 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Start screen — Minimal Impact / Cinematic
# ─────────────────────────────────────────────────────────────────────────────
def draw_start(screen, bg, cache, leaderboard, start_idle_t, t, theme=None,
               difficulty="normal", diff_idx=1):
    screen.blit(bg, (0, 0))

    # Cinematic overlay (cached in HudCache — avoids per-frame SRCALPHA allocation)
    screen.blit(cache.ov_start, (0, 0))

    # Tree silhouette layer
    draw_tree_silhouettes(screen)

    # Best score badge (top-right)
    if leaderboard:
        best      = leaderboard[0]
        badge_txt = F_TINY.render(
            f"BEST  {best.get('name','?')}  {best['score']} pts", True, get_color("streak_gold", theme))
        pad_x = int(10 * SX); pad_y = int(5 * S)
        bw = badge_txt.get_width() + pad_x * 2
        bh = badge_txt.get_height() + pad_y * 2
        bx = W - bw - int(12 * SX)
        by = int(12 * S)
        pygame.draw.rect(screen, (28, 22, 4),  (bx, by, bw, bh), border_radius=int(4 * S))
        pygame.draw.rect(screen, get_color("streak_gold", theme),   (bx, by, bw, bh), 1, border_radius=int(4 * S))
        screen.blit(badge_txt, (bx + pad_x, by + pad_y))

    # ? icon (top-left)
    icon_s = int(28 * S)
    icon_x = int(10 * SX)
    icon_y = int(10 * S)
    pygame.draw.rect(screen, (18, 32, 18), (icon_x, icon_y, icon_s, icon_s), border_radius=int(4 * S))
    pygame.draw.rect(screen, (55, 85, 55), (icon_x, icon_y, icon_s, icon_s), 1, border_radius=int(4 * S))
    qi = cache.lbl_question
    screen.blit(qi, (icon_x + icon_s // 2 - qi.get_width() // 2,
                     icon_y + icon_s // 2 - qi.get_height() // 2))

    if start_idle_t >= 5.0:
        screen.blit(cache.ctrl_panel, (icon_x + icon_s + int(6 * SX), icon_y - int(2 * S)))
        row_h = int(22 * S)
        for row, s in enumerate(cache.lbl_ctrl_hints):
            screen.blit(s, (icon_x + icon_s + int(12 * SX), icon_y + row * row_h))

    # Title
    title  = cache.lbl_title
    shadow = cache.lbl_title_shad
    cy_title = H // 2 - int(100 * S)
    screen.blit(shadow, (W // 2 - title.get_width() // 2 + int(4 * S), cy_title + int(4 * S)))
    screen.blit(title,  (W // 2 - title.get_width() // 2,              cy_title))

    # Tagline
    tag = cache.lbl_tagline
    screen.blit(tag, (W // 2 - tag.get_width() // 2, cy_title + int(106 * S)))

    # ── Difficulty selector row (jd-11) ──────────────────────────────────
    diff_y = cy_title + int(130 * S)
    diff_gap = int(12 * SX)
    diff_pill_h = int(32 * S)
    diff_pad_x = int(18 * SX)
    diff_pad_y = int(5 * S)

    # Pre-measure pill widths
    diff_color_keys = ("diff_easy", "diff_normal", "diff_hard")
    diff_labels = [DIFFICULTIES[d]["label"] for d in DIFFICULTY_ORDER]
    diff_surfs = [F_SMALL.render(lbl, True, (255, 255, 255)) for lbl in diff_labels]
    pill_widths = [surf.get_width() + diff_pad_x * 2 for surf in diff_surfs]
    total_diff_w = sum(pill_widths) + diff_gap * (len(DIFFICULTY_ORDER) - 1)
    diff_x = W // 2 - total_diff_w // 2

    for i, d_key in enumerate(DIFFICULTY_ORDER):
        pw = pill_widths[i]
        is_sel = (i == diff_idx)
        d_color = get_color(diff_color_keys[i], theme)
        sel_color = get_color("diff_selected", theme)

        if is_sel:
            # Full brightness pill with selected border
            pill_bg = (*d_color, 180)
            border_col = sel_color
        else:
            # Dimmed pill
            pill_bg = (*(c // 3 for c in d_color), 120)
            border_col = tuple(c // 2 for c in d_color)

        pill_surf = pygame.Surface((pw, diff_pill_h), pygame.SRCALPHA)
        pill_surf.fill(pill_bg)
        pygame.draw.rect(pill_surf, border_col, (0, 0, pw, diff_pill_h),
                         max(1, int(2 * S)), border_radius=int(diff_pill_h // 2))
        screen.blit(pill_surf, (diff_x, diff_y))

        # Label text
        txt_surf = diff_surfs[i]
        if not is_sel:
            # Dim text by rendering with reduced color
            txt_surf = F_SMALL.render(diff_labels[i], True, tuple(c // 2 for c in (255, 255, 255)))
        screen.blit(txt_surf, (diff_x + diff_pad_x,
                               diff_y + diff_pill_h // 2 - txt_surf.get_height() // 2))
        diff_x += pw + diff_gap

    # Personal best for selected difficulty
    pb = None
    if leaderboard:
        pb = leaderboard[0].get("score", 0) if leaderboard else 0
    diff_hint = F_TINY.render("UP/DOWN to change difficulty", True, (80, 110, 80))
    screen.blit(diff_hint, (W // 2 - diff_hint.get_width() // 2, diff_y + diff_pill_h + int(4 * S)))

    # Bordered CTA
    cta_col = pulse_color(get_color("streak_gold", theme), t)
    cta_txt = F_MED.render(">> PRESS SPACE TO START <<", True, cta_col)
    cta_w   = cta_txt.get_width() + int(44 * SX)
    cta_h   = cta_txt.get_height() + int(18 * S)
    cta_x   = W // 2 - cta_w // 2
    cta_y   = cy_title + int(186 * S)
    pygame.draw.rect(screen, (28, 22, 4),  (cta_x, cta_y, cta_w, cta_h), border_radius=int(6 * S))
    pygame.draw.rect(screen, cta_col,       (cta_x, cta_y, cta_w, cta_h), max(1, int(2 * S)), border_radius=int(6 * S))
    screen.blit(cta_txt, (cta_x + int(22 * SX), cta_y + int(9 * S)))

    # TAB + close hints
    lb_hint   = cache.lbl_tab_hint
    quit_hint = cache.lbl_quit_hint
    screen.blit(lb_hint,   (W // 2 - lb_hint.get_width()   // 2, cta_y + cta_h + int(10 * S)))
    screen.blit(quit_hint, (W // 2 - quit_hint.get_width() // 2, cta_y + cta_h + int(30 * S)))
