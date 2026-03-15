"""
Jungle Dodge — HUD and screen drawing functions (task jd-06)
All draw_* functions extracted from the monolith.
Never imports entities.py or states.py (receives data via parameters).
"""

import pygame
import math

from constants import (
    W, H, SX, SY, S,
    GROUND_Y,
    CLR,
    LEVEL_TIME, MAX_LIVES, STUN_SECS,
    MAX_NAME_LEN, LEADERBOARD_SIZE,
    F_HUGE, F_LARGE, F_MED, F_SMALL, F_TINY, F_SERIF, F_SKULL,
)
from entities import pulse_color


# ─────────────────────────────────────────────────────────────────────────────
#  Pre-allocated surface cache (avoids per-frame SRCALPHA allocations)
# ─────────────────────────────────────────────────────────────────────────────
class HudCache:
    """Pre-allocated overlay and HUD surfaces."""

    def __init__(self):
        # Controls hint panel (start screen)
        self.ctrl_panel = pygame.Surface((int(250 * SX), int(80 * S)), pygame.SRCALPHA)
        self.ctrl_panel.fill((0, 18, 0, 210))

        # Stone HUD bar
        self.hud_panel = pygame.Surface((W, int(72 * S)), pygame.SRCALPHA)
        self.hud_panel.fill((*CLR["stone"], 238))

        # Full-screen overlays
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


# ─────────────────────────────────────────────────────────────────────────────
#  Background — Jungle Cliff Face (Lost Temple Ruins)
# ─────────────────────────────────────────────────────────────────────────────
def build_bg():
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
    VBR = CLR["vine"]
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
    pygame.draw.rect(bg, CLR["ground"], (0, GROUND_Y, W, H - GROUND_Y))
    FLAG = (26, 18, 8)
    flagstones = [(0,120),(120,140),(260,110),(370,160),(530,130),(660,120),(780,120)]
    for fx, fw in flagstones:
        pygame.draw.rect(bg, FLAG, (svx(fx), GROUND_Y, svx(fw), H - GROUND_Y), 1)
    for pts in [[(60,3),(70,28),(62,50)],[(340,3),(352,25),(344,50)],[(620,3),(610,30),(622,50)]]:
        pygame.draw.lines(bg, (12,10,6), False,
            [(svx(x), GROUND_Y + int(y * S)) for x,y in pts], 1)
    pygame.draw.rect(bg, CLR["grass"], (0, GROUND_Y, W, int(14 * S)))

    # 8. Ground mist
    mist_h = int(80 * S)
    mist = pygame.Surface((W, mist_h), pygame.SRCALPHA)
    for my in range(mist_h):
        a = int(70 * (1.0 - my / mist_h))
        pygame.draw.line(mist, (26, 48, 20, a), (0, my), (W, my))
    bg.blit(mist, (0, GROUND_Y - int(60 * S)))

    return bg


# ─────────────────────────────────────────────────────────────────────────────
#  Game screen (gameplay area)
# ─────────────────────────────────────────────────────────────────────────────
def draw_game(screen, bg, obstacles, player, particles):
    """Draw background, obstacles, player, and particles."""
    screen.blit(bg, (0, 0))
    for obs in obstacles:
        obs.draw(screen)
    player.draw(screen, particles)
    particles.draw(screen)


# ─────────────────────────────────────────────────────────────────────────────
#  HUD — Stone Tablet (bottom bar)
# ─────────────────────────────────────────────────────────────────────────────
def draw_hud(screen, cache, score, level, level_timer, player, is_levelup=False):
    """Draw the bottom HUD bar with score, level, time, lives, and progress bar."""
    ph  = int(72 * S)
    py  = H - ph

    # Stone panel
    screen.blit(cache.hud_panel, (0, py))
    step = int(10 * S)
    for ty in range(py + step, H, step):
        pygame.draw.line(screen, CLR["stone_hi"], (0, ty), (W, ty), 1)
    pygame.draw.line(screen, CLR["vine"],    (0, py),          (W, py),          max(1, int(2 * S)))
    pygame.draw.line(screen, CLR["vine_dk"], (0, py + int(2 * S)), (W, py + int(2 * S)), 1)

    # SCORE (left)
    sc_lbl = F_TINY.render("SCORE", True, CLR["olive"])
    screen.blit(sc_lbl, (int(14 * SX), py + int(6 * S)))
    sc_shad = F_SERIF.render(str(score), True, (18, 18, 12))
    sc_val  = F_SERIF.render(str(score), True, CLR["gold"])
    screen.blit(sc_shad, (int(15 * SX), py + int(28 * S)))
    screen.blit(sc_val,  (int(14 * SX), py + int(27 * S)))

    # LEVEL (center-left)
    lv_lbl = F_TINY.render("LEVEL", True, CLR["olive"])
    lv_label_x = W // 2 - lv_lbl.get_width() // 2 - int(60 * SX)
    screen.blit(lv_lbl, (lv_label_x, py + int(6 * S)))
    lv_shad = F_SERIF.render(str(level), True, (18, 18, 12))
    lv_val  = F_SERIF.render(str(level), True, CLR["white"])
    lv_x = W // 2 - lv_val.get_width() // 2 - int(60 * SX)
    screen.blit(lv_shad, (lv_x + 1, py + int(28 * S)))
    screen.blit(lv_val,  (lv_x,     py + int(27 * S)))

    # TIME (center-right)
    time_left  = max(0.0, LEVEL_TIME - level_timer)
    display_t  = math.ceil(time_left)
    tcol = CLR["red"] if time_left < 10 else CLR["white"]
    tm_lbl  = F_TINY.render("TIME", True, CLR["olive"])
    screen.blit(tm_lbl, (W // 2 + int(40 * SX), py + int(6 * S)))
    tm_shad = F_SERIF.render(f"{display_t:02d}s", True, (18, 18, 12))
    tm_val  = F_SERIF.render(f"{display_t:02d}s", True, tcol)
    screen.blit(tm_shad, (W // 2 + int(41 * SX), py + int(28 * S)))
    screen.blit(tm_val,  (W // 2 + int(40 * SX), py + int(27 * S)))

    # LIVES — skull icons (right)
    lv2_lbl = F_TINY.render("LIVES", True, CLR["olive"])
    screen.blit(lv2_lbl, (W - int(122 * SX), py + int(6 * S)))
    skull_gap = int(36 * S)
    for i in range(MAX_LIVES):
        sk_col = (190, 30, 30) if i < player.lives else (55, 55, 55)
        sk = F_SKULL.render("\u2620", True, sk_col)
        screen.blit(sk, (W - int(120 * SX) + i * skull_gap, py + int(26 * S)))

    # Vine growth bar / stun bar (bottom strip)
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
            pygame.draw.rect(screen, CLR["teal"], (bar_x, bar_y, stun_bar_w, bar_h), border_radius=brd)
        pygame.draw.rect(screen, (0, 140, 120), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=brd)
        st = F_TINY.render("STUNNED", True, CLR["teal"])
        screen.blit(st, (W // 2 - st.get_width() // 2, bar_y - int(16 * S)))
    else:
        prog   = 0.0 if is_levelup else min(1.0, level_timer / LEVEL_TIME)
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


# ─────────────────────────────────────────────────────────────────────────────
#  Level-up overlay
# ─────────────────────────────────────────────────────────────────────────────
def draw_levelup_overlay(screen, cache, level, score):
    screen.blit(cache.ov_levelup, (0, 0))
    lt  = F_LARGE.render(f"LEVEL {level}!", True, CLR["gold"])
    sub = F_MED.render("Things are getting faster...", True, CLR["white"])
    sc  = F_SMALL.render(f"Score so far: {score}", True, CLR["gold"])
    screen.blit(lt,  (W // 2 - lt.get_width()  // 2, H // 2 - int(50 * S)))
    screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + int(20 * S)))
    screen.blit(sc,  (W // 2 - sc.get_width()  // 2, H // 2 + int(65 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Pause overlay
# ─────────────────────────────────────────────────────────────────────────────
def draw_pause_overlay(screen, cache):
    screen.blit(cache.ov_pause, (0, 0))
    pt  = F_LARGE.render("PAUSED", True, CLR["white"])
    h1  = F_MED.render("SPACE \u2014 resume", True, (195, 215, 195))
    h2  = F_MED.render("ESC \u2014 return to home screen", True, (195, 215, 195))
    screen.blit(pt,  (W // 2 - pt.get_width()  // 2, H // 2 - int(60 * S)))
    screen.blit(h1,  (W // 2 - h1.get_width()  // 2, H // 2 + int(10 * S)))
    screen.blit(h2,  (W // 2 - h2.get_width()  // 2, H // 2 + int(50 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Name Entry screen
# ─────────────────────────────────────────────────────────────────────────────
def draw_name_entry(screen, cache, name_input, cursor_on, score, level, t):
    screen.fill((0, 12, 0))

    # Gold vine dividers
    pygame.draw.line(screen, CLR["vine_dk"],
                     (W // 2 - int(320 * SX), H // 2 - int(120 * S)),
                     (W // 2 + int(320 * SX), H // 2 - int(120 * S)), 1)
    pygame.draw.line(screen, CLR["vine_dk"],
                     (W // 2 - int(320 * SX), H // 2 + int(130 * S)),
                     (W // 2 + int(320 * SX), H // 2 + int(130 * S)), 1)

    # Title
    trop = F_LARGE.render("YOU MADE THE TOP 10!", True, CLR["gold"])
    shad = F_LARGE.render("YOU MADE THE TOP 10!", True, (50, 30, 0))
    title_y = H // 2 - int(218 * S)
    screen.blit(shad, (W // 2 - trop.get_width() // 2 + int(3 * S), title_y + int(3 * S)))
    screen.blit(trop, (W // 2 - trop.get_width() // 2,              title_y))

    # Score / level
    sc = F_SMALL.render(f"Score: {score}   |   Level {level}", True, (200, 220, 200))
    screen.blit(sc, (W // 2 - sc.get_width() // 2, H // 2 - int(148 * S)))

    # Input prompt
    prompt = F_MED.render("Enter your name:", True, (190, 210, 190))
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
        bd_col = CLR["vine"] if filled else CLR["vine_dk"]
        screen.blit(cache.slot_filled if filled else cache.slot_empty, (sx, sy))
        pygame.draw.rect(screen, bd_col, (sx, sy, slot_w, slot_h), max(1, int(2 * S)), border_radius=int(6 * S))

        if filled:
            ch_surf = F_LARGE.render(name_input[i], True, CLR["gold"])
            screen.blit(ch_surf, (sx + slot_w // 2 - ch_surf.get_width() // 2,
                                  sy + slot_h // 2 - ch_surf.get_height() // 2))
        elif i == len(name_input):
            if cursor_on:
                pygame.draw.rect(screen, CLR["gold"],
                                 (sx + slot_w // 2 - int(3 * S), sy + int(16 * S),
                                  int(6 * S), int(48 * S)),
                                 border_radius=int(2 * S))

    # Hints
    h1 = F_SMALL.render("A-Z  /  0-9  to type     BACKSPACE to delete", True, (140, 170, 140))
    h2 = F_SMALL.render("ENTER to confirm     ESC to skip", True, (140, 170, 140))
    screen.blit(h1, (W // 2 - h1.get_width() // 2, sy + slot_h + int(18 * S)))
    screen.blit(h2, (W // 2 - h2.get_width() // 2, sy + slot_h + int(46 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Leaderboard table (shared by leaderboard & game-over screens)
# ─────────────────────────────────────────────────────────────────────────────
def draw_lb_table(screen, leaderboard, start_y, full=True):
    col_w  = int(620 * SX)
    row_h  = int(36 * S) if full else int(26 * S)
    font   = F_SMALL if full else F_TINY
    tx     = W // 2 - col_w // 2

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

    if not leaderboard:
        e = font.render("No scores yet \u2014 be the first!", True, (160, 190, 160))
        screen.blit(e, (W // 2 - e.get_width() // 2, start_y + row_h + int(8 * S)))
        return

    medal_bg = [(60, 45, 0), (35, 35, 45), (45, 25, 10)]
    medal_fc = [CLR["gold"], CLR["silver"], CLR["bronze"]]

    for i, entry in enumerate(leaderboard[:LEADERBOARD_SIZE]):
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


# ─────────────────────────────────────────────────────────────────────────────
#  Full Leaderboard screen
# ─────────────────────────────────────────────────────────────────────────────
def draw_leaderboard(screen, bg, cache, leaderboard, t):
    screen.blit(bg, (0, 0))
    screen.blit(cache.ov_lb, (0, 0))

    title  = F_LARGE.render("TOP 10 LEADERBOARD", True, CLR["gold"])
    shadow = F_LARGE.render("TOP 10 LEADERBOARD", True, (50, 35, 0))
    screen.blit(shadow, (W // 2 - title.get_width() // 2 + int(3 * S), int(28 * S)))
    screen.blit(title,  (W // 2 - title.get_width() // 2,              int(25 * S)))

    draw_lb_table(screen, leaderboard, int(95 * S), full=True)

    cta = F_MED.render("SPACE to play again  |  TAB / ESC to home", True,
                       pulse_color(CLR["gold"], t))
    screen.blit(cta, (W // 2 - cta.get_width() // 2, H - int(48 * S)))


# ─────────────────────────────────────────────────────────────────────────────
#  Game Over (not top 10)
# ─────────────────────────────────────────────────────────────────────────────
def draw_gameover(screen, bg, cache, leaderboard, score, level, t):
    screen.blit(bg, (0, 0))
    screen.blit(cache.ov_gameover, (0, 0))

    go   = F_HUGE.render("GAME OVER", True, CLR["red"])
    shad = F_HUGE.render("GAME OVER", True, (80, 0, 0))
    screen.blit(shad, (W // 2 - go.get_width() // 2 + int(4 * S), int(32 * S)))
    screen.blit(go,   (W // 2 - go.get_width() // 2,              int(28 * S)))

    sc = F_MED.render(f"Score: {score}   |   Level {level}", True, CLR["gold"])
    screen.blit(sc, (W // 2 - sc.get_width() // 2, int(128 * S)))

    if leaderboard:
        msg = F_MED.render("Not in the top 10 \u2014 keep trying!", True, CLR["red"])
    else:
        msg = F_MED.render("Score some points to get on the leaderboard!", True, CLR["red"])
    screen.blit(msg, (W // 2 - msg.get_width() // 2, int(170 * S)))

    lb_lbl = F_SMALL.render("Current Top 10:", True, (190, 210, 190))
    screen.blit(lb_lbl, (W // 2 - lb_lbl.get_width() // 2, int(208 * S)))

    draw_lb_table(screen, leaderboard, int(234 * S), full=False)

    cta = F_MED.render("SPACE to play again  |  ESC to home", True,
                       pulse_color(CLR["gold"], t))
    screen.blit(cta, (W // 2 - cta.get_width() // 2, H - int(48 * S)))


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


# ─────────────────────────────────────────────────────────────────────────────
#  Start screen
# ─────────────────────────────────────────────────────────────────────────────
def draw_start(screen, bg, cache, leaderboard, start_idle_t, t):
    screen.blit(bg, (0, 0))

    # Cinematic overlay
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 6, 0, 210))
    screen.blit(ov, (0, 0))

    draw_tree_silhouettes(screen)

    # Best score badge (top-right)
    if leaderboard:
        best      = leaderboard[0]
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

    # ? icon (top-left)
    icon_s = int(28 * S)
    icon_x = int(10 * SX)
    icon_y = int(10 * S)
    pygame.draw.rect(screen, (18, 32, 18), (icon_x, icon_y, icon_s, icon_s), border_radius=int(4 * S))
    pygame.draw.rect(screen, (55, 85, 55), (icon_x, icon_y, icon_s, icon_s), 1, border_radius=int(4 * S))
    qi = F_SMALL.render("?", True, (100, 140, 100))
    screen.blit(qi, (icon_x + icon_s // 2 - qi.get_width() // 2,
                     icon_y + icon_s // 2 - qi.get_height() // 2))

    if start_idle_t >= 5.0:
        screen.blit(cache.ctrl_panel, (icon_x + icon_s + int(6 * SX), icon_y - int(2 * S)))
        row_h = int(22 * S)
        for row, txt in enumerate([
            "Arrow keys / A-D  \u2014 move",
            "3 lives  |  45 s per level",
            "ESC \u2014 pause / home",
        ]):
            s = F_TINY.render(txt, True, (175, 210, 175))
            screen.blit(s, (icon_x + icon_s + int(12 * SX), icon_y + row * row_h))

    # Title
    title  = F_HUGE.render("JUNGLE DODGE", True, CLR["gold"])
    shadow = F_HUGE.render("JUNGLE DODGE", True, (28, 16, 0))
    cy_title = H // 2 - int(100 * S)
    screen.blit(shadow, (W // 2 - title.get_width() // 2 + int(4 * S), cy_title + int(4 * S)))
    screen.blit(title,  (W // 2 - title.get_width() // 2,              cy_title))

    # Tagline
    tag = F_SMALL.render("SURVIVE. DODGE. OUTLAST.", True, (185, 210, 185))
    screen.blit(tag, (W // 2 - tag.get_width() // 2, cy_title + int(106 * S)))

    # Bordered CTA
    cta_col = pulse_color(CLR["gold"], t)
    cta_txt = F_MED.render(">> PRESS SPACE TO START <<", True, cta_col)
    cta_w   = cta_txt.get_width() + int(44 * SX)
    cta_h   = cta_txt.get_height() + int(18 * S)
    cta_x   = W // 2 - cta_w // 2
    cta_y   = cy_title + int(148 * S)
    pygame.draw.rect(screen, (28, 22, 4),  (cta_x, cta_y, cta_w, cta_h), border_radius=int(6 * S))
    pygame.draw.rect(screen, cta_col,       (cta_x, cta_y, cta_w, cta_h), max(1, int(2 * S)), border_radius=int(6 * S))
    screen.blit(cta_txt, (cta_x + int(22 * SX), cta_y + int(9 * S)))

    # TAB + close hints
    lb_hint   = F_TINY.render("TAB \u2014 view leaderboard", True, (80, 110, 80))
    quit_hint = F_TINY.render("Close window to quit", True, (55, 75, 55))
    screen.blit(lb_hint,   (W // 2 - lb_hint.get_width()   // 2, cta_y + cta_h + int(10 * S)))
    screen.blit(quit_hint, (W // 2 - quit_hint.get_width() // 2, cta_y + cta_h + int(30 * S)))
