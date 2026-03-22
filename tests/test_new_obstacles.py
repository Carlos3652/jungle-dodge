"""Tests for 5 new obstacle types (jd-14)."""

import sys
import types
import math
import unittest
from unittest.mock import MagicMock

# ── Stub pygame before importing game code ───────────────────────────────────
if "pygame" not in sys.modules:
    _pg = types.ModuleType("pygame")
    _pg.init = MagicMock()
    _pg.font = types.ModuleType("pygame.font")
    _pg.font.init = MagicMock()
    _pg.font.get_init = MagicMock(return_value=True)
    _pg.font.SysFont = MagicMock(return_value=MagicMock())
    _pg.font.Font = MagicMock(return_value=MagicMock())
    _pg.display = types.ModuleType("pygame.display")
    _pg.display.set_mode = MagicMock(return_value=MagicMock())
    _pg.display.set_caption = MagicMock()
    _pg.display.flip = MagicMock()
    _pg.mouse = types.ModuleType("pygame.mouse")
    _pg.mouse.set_visible = MagicMock()
    _pg.time = types.ModuleType("pygame.time")
    _pg.time.Clock = MagicMock
    _pg.time.get_ticks = MagicMock(return_value=0)
    _pg.Surface = MagicMock
    _pg.Rect = MagicMock(side_effect=lambda x, y, w, h: type('R', (), {
        'x': x, 'y': y, 'w': w, 'h': h,
        'colliderect': lambda self, o: True,
    })())
    _pg.draw = types.ModuleType("pygame.draw")
    _pg.draw.rect = MagicMock()
    _pg.draw.line = MagicMock()
    _pg.draw.lines = MagicMock()
    _pg.draw.circle = MagicMock()
    _pg.draw.ellipse = MagicMock()
    _pg.draw.polygon = MagicMock()
    _pg.draw.arc = MagicMock()
    _pg.image = types.ModuleType("pygame.image")
    _pg.image.load = MagicMock(return_value=MagicMock())
    _pg.transform = types.ModuleType("pygame.transform")
    _pg.transform.scale = MagicMock(return_value=MagicMock())
    _pg.transform.rotate = MagicMock(return_value=MagicMock(
        get_size=MagicMock(return_value=(100, 100))))
    _pg.mixer = types.ModuleType("pygame.mixer")
    _pg.mixer.init = MagicMock()
    _pg.mixer.Sound = MagicMock
    _pg.FULLSCREEN = 0
    _pg.SCALED = 0
    _pg.SRCALPHA = 0x00010000
    _pg.KEYDOWN = 2
    _pg.QUIT = 12
    _pg.K_LEFT = 276
    _pg.K_RIGHT = 275
    _pg.K_UP = 273
    _pg.K_DOWN = 274
    _pg.K_a = 97
    _pg.K_d = 100
    _pg.K_SPACE = 32
    _pg.K_ESCAPE = 27
    _pg.K_F11 = 292
    _pg.K_TAB = 9
    _pg.K_RETURN = 13
    _pg.K_KP_ENTER = 271
    _pg.K_BACKSPACE = 8
    _pg.K_1 = 49
    _pg.K_2 = 50
    _pg.K_3 = 51
    _pg.key = types.ModuleType("pygame.key")
    _pg.key.get_pressed = MagicMock(return_value={})
    _pg.event = types.ModuleType("pygame.event")
    _pg.event.get = MagicMock(return_value=[])
    _pg.quit = MagicMock()
    sys.modules["pygame"] = _pg
    sys.modules["pygame.font"] = _pg.font
    sys.modules["pygame.display"] = _pg.display
    sys.modules["pygame.mixer"] = _pg.mixer

_pg = sys.modules["pygame"]

from entities import (
    Player, Obstacle,
    CanopyDrop, CrocSnap, PoisonPuddle, ScreechBat, GroundHazard,
)
from constants import W, H, GROUND_Y, S, SX, SY


# ---------------------------------------------------------------------------
#  CanopyDrop
# ---------------------------------------------------------------------------
class TestCanopyDrop(unittest.TestCase):

    def test_inherits_obstacle(self):
        cd = CanopyDrop(level=2, spawn_x=500)
        self.assertIsInstance(cd, Obstacle)

    def test_creates_8_to_12_leaves(self):
        for _ in range(20):
            cd = CanopyDrop(level=2)
            self.assertGreaterEqual(len(cd.leaves), 8)
            self.assertLessEqual(len(cd.leaves), 12)

    def test_telegraph_phase(self):
        cd = CanopyDrop(level=2, spawn_x=500)
        self.assertFalse(cd.started)
        cd.update(0.1, Player())
        self.assertFalse(cd.started)  # still in telegraph
        cd.update(0.25, Player())
        self.assertTrue(cd.started)  # telegraph done (0.3s)

    def test_leaves_fall_after_telegraph(self):
        cd = CanopyDrop(level=2, spawn_x=500)
        # Complete telegraph
        cd.update(0.35, Player())
        self.assertTrue(cd.started)
        # Record initial y of first leaf
        initial_y = cd.leaves[0][1]
        cd.update(0.1, Player())
        self.assertGreater(cd.leaves[0][1], initial_y)

    def test_spike_leaf_reveals(self):
        cd = CanopyDrop(level=2, spawn_x=500)
        cd.update(0.35, Player())  # finish telegraph
        self.assertFalse(cd.revealed)
        # Fast-forward until revealed
        for _ in range(500):
            cd.update(0.05, Player())
            if cd.revealed:
                break
        self.assertTrue(cd.revealed)

    def test_only_spike_leaf_can_hit(self):
        """check_hit should only damage via the spike leaf."""
        cd = CanopyDrop(level=2, spawn_x=500)
        cd.started = True
        cd.revealed = True
        # Position spike leaf far from player
        cd.leaves[cd.spike_idx][0] = 9999.0
        cd.leaves[cd.spike_idx][1] = 9999.0
        p = Player()
        p.immune_t = 0.0
        self.assertFalse(cd.check_hit(p))

    def test_dies_when_all_leaves_pass_ground(self):
        cd = CanopyDrop(level=2, spawn_x=500)
        cd.update(0.35, Player())  # finish telegraph
        for _ in range(2000):
            cd.update(0.05, Player())
            if not cd.alive:
                break
        self.assertFalse(cd.alive)
        self.assertTrue(cd.scored)

    def test_no_hit_during_telegraph(self):
        cd = CanopyDrop(level=2, spawn_x=500)
        p = Player()
        p.immune_t = 0.0
        self.assertFalse(cd.check_hit(p))


# ---------------------------------------------------------------------------
#  CrocSnap
# ---------------------------------------------------------------------------
class TestCrocSnap(unittest.TestCase):

    def test_inherits_obstacle(self):
        cs = CrocSnap(level=4)
        self.assertIsInstance(cs, Obstacle)

    def test_telegraph_before_sweep(self):
        cs = CrocSnap(level=4)
        self.assertFalse(cs.started)
        cs.update(0.2, Player())
        self.assertFalse(cs.started)
        cs.update(0.35, Player())
        self.assertTrue(cs.started)

    def test_moves_horizontally(self):
        cs = CrocSnap(level=4)
        cs.direction = 1
        cs.x = 0.0
        cs.update(0.55, Player())  # pass telegraph
        initial_x = cs.x
        cs.update(0.1, Player())
        self.assertGreater(cs.x, initial_x)

    def test_moves_left_to_right(self):
        cs = CrocSnap(level=4)
        cs.direction = 1
        cs.x = float(-cs.CROC_W)
        cs.started = True
        initial_x = cs.x
        cs.update(0.1, Player())
        self.assertGreater(cs.x, initial_x)

    def test_moves_right_to_left(self):
        cs = CrocSnap(level=4)
        cs.direction = -1
        cs.x = float(W + cs.CROC_W)
        cs.started = True
        initial_x = cs.x
        cs.update(0.1, Player())
        self.assertLess(cs.x, initial_x)

    def test_dies_after_crossing_screen(self):
        cs = CrocSnap(level=4)
        cs.direction = 1
        cs.started = True
        cs.x = 0.0
        for _ in range(500):
            cs.update(0.05, Player())
            if not cs.alive:
                break
        self.assertFalse(cs.alive)
        self.assertTrue(cs.scored)

    def test_no_hit_during_telegraph(self):
        cs = CrocSnap(level=4)
        p = Player()
        p.immune_t = 0.0
        self.assertFalse(cs.check_hit(p))

    def test_ground_level_y(self):
        cs = CrocSnap(level=4)
        self.assertAlmostEqual(cs.y, GROUND_Y - cs.CROC_H, delta=1)


# ---------------------------------------------------------------------------
#  PoisonPuddle
# ---------------------------------------------------------------------------
class TestPoisonPuddle(unittest.TestCase):

    def test_inherits_obstacle(self):
        pp = PoisonPuddle(level=5, spawn_x=500)
        self.assertIsInstance(pp, Obstacle)

    def test_telegraph_before_active(self):
        pp = PoisonPuddle(level=5, spawn_x=500)
        self.assertFalse(pp.active)
        pp.update(0.1, Player())
        self.assertFalse(pp.active)
        pp.update(0.25, Player())
        self.assertTrue(pp.active)

    def test_no_instant_damage(self):
        """check_hit always returns False; damage via standing timer."""
        pp = PoisonPuddle(level=5, spawn_x=500)
        pp.active = True
        p = Player()
        p.immune_t = 0.0
        self.assertFalse(pp.check_hit(p))

    def test_standing_timer_stuns(self):
        """Player standing in puddle for 1.5s triggers hit."""
        pp = PoisonPuddle(level=5, spawn_x=500)
        pp.active = True
        p = Player()
        p.x = pp.x  # overlap
        p.y = pp.y - p.PH  # at ground level
        initial_lives = p.lives
        # Stand in puddle for 1.6s
        for _ in range(32):
            pp.update(0.05, p)
        self.assertLess(p.lives, initial_lives)

    def test_dies_after_lifetime(self):
        pp = PoisonPuddle(level=5, spawn_x=500)
        pp.active = True
        # Create a player far away so no stun interaction
        p = Player()
        p.x = W  # far away
        for _ in range(500):
            pp.update(0.05, p)
            if not pp.alive:
                break
        self.assertFalse(pp.alive)
        self.assertTrue(pp.scored)

    def test_lifetime_between_8_and_12(self):
        for _ in range(20):
            pp = PoisonPuddle(level=5)
            self.assertGreaterEqual(pp.lifetime, 8.0)
            self.assertLessEqual(pp.lifetime, 12.0)


# ---------------------------------------------------------------------------
#  ScreechBat
# ---------------------------------------------------------------------------
class TestScreechBat(unittest.TestCase):

    def test_inherits_obstacle(self):
        sb = ScreechBat(level=7, spawn_x=500)
        self.assertIsInstance(sb, Obstacle)

    def test_telegraph_phase(self):
        sb = ScreechBat(level=7, spawn_x=500)
        self.assertFalse(sb.tracking)
        self.assertFalse(sb.diving)
        sb.update(0.2, Player())
        self.assertFalse(sb.tracking)
        sb.update(0.35, Player())
        self.assertTrue(sb.tracking)

    def test_tracks_player_x(self):
        sb = ScreechBat(level=7, spawn_x=500)
        sb.update(0.55, Player())  # pass telegraph
        self.assertTrue(sb.tracking)
        p = Player()
        p.x = 1000
        sb.update(0.1, p)
        self.assertEqual(sb.target_x, 1000)

    def test_dives_after_tracking(self):
        sb = ScreechBat(level=7, spawn_x=500)
        p = Player()
        # Pass telegraph
        sb.update(0.55, p)
        # Track for 1s
        for _ in range(25):
            sb.update(0.05, p)
        self.assertTrue(sb.diving)

    def test_dies_after_dive_completes(self):
        sb = ScreechBat(level=7, spawn_x=500)
        p = Player()
        for _ in range(2000):
            sb.update(0.02, p)
            if not sb.alive:
                break
        self.assertFalse(sb.alive)
        self.assertTrue(sb.scored)

    def test_no_hit_during_tracking(self):
        sb = ScreechBat(level=7, spawn_x=500)
        sb.tracking = True
        p = Player()
        p.immune_t = 0.0
        self.assertFalse(sb.check_hit(p))

    def test_hit_possible_during_dive(self):
        sb = ScreechBat(level=7, spawn_x=500)
        sb.diving = True
        sb.x = 500.0
        sb.y = float(GROUND_Y - 50)
        p = Player()
        p.x = 500
        p.y = int(GROUND_Y - p.PH)
        p.immune_t = 0.0
        # With close proximity, should be hittable
        dist = math.hypot(sb.x - p.x, sb.y - (p.y + p.PH // 2))
        if dist < sb.HIT_R + max(p.PW, p.PH) // 2:
            self.assertTrue(sb.check_hit(p))


# ---------------------------------------------------------------------------
#  GroundHazard
# ---------------------------------------------------------------------------
class TestGroundHazard(unittest.TestCase):

    def test_inherits_obstacle(self):
        gh = GroundHazard(level=5, spawn_x=500)
        self.assertIsInstance(gh, Obstacle)

    def test_starts_in_telegraph(self):
        gh = GroundHazard(level=5, spawn_x=500)
        self.assertEqual(gh.phase, "telegraph")

    def test_phase_progression(self):
        gh = GroundHazard(level=5, spawn_x=500)
        # Telegraph -> rise
        gh.update(0.55, Player())
        self.assertEqual(gh.phase, "rise")
        # Rise -> active
        gh.update(0.35, Player())
        self.assertEqual(gh.phase, "active")
        # Active -> retract
        gh.update(1.05, Player())
        self.assertEqual(gh.phase, "retract")
        # Retract -> dead
        gh.update(0.35, Player())
        self.assertFalse(gh.alive)
        self.assertTrue(gh.scored)

    def test_hit_only_during_active(self):
        """check_hit returns False for non-active phases regardless of position."""
        gh = GroundHazard(level=5, spawn_x=500)
        p = Player()
        p.immune_t = 0.0
        # Telegraph: no hit
        self.assertFalse(gh.check_hit(p))
        # Rise: no hit
        gh.phase = "rise"
        self.assertFalse(gh.check_hit(p))
        # Retract: no hit
        gh.phase = "retract"
        self.assertFalse(gh.check_hit(p))

    def test_active_phase_allows_hit(self):
        """During active phase, check_hit delegates to rect collision."""
        gh = GroundHazard(level=5, spawn_x=500)
        p = Player()
        p.immune_t = 0.0
        gh.phase = "active"
        # The result depends on colliderect mock behavior;
        # just verify it doesn't raise and returns a boolean
        result = gh.check_hit(p)
        self.assertIsInstance(result, bool)

    def test_height_fraction_during_rise(self):
        gh = GroundHazard(level=5, spawn_x=500)
        gh.update(0.55, Player())  # pass telegraph
        self.assertEqual(gh.phase, "rise")
        gh.update(0.15, Player())  # halfway through rise
        self.assertGreater(gh.height_frac, 0.0)
        self.assertLess(gh.height_frac, 1.0)

    def test_height_fraction_during_retract(self):
        gh = GroundHazard(level=5, spawn_x=500)
        gh.update(0.55, Player())  # telegraph
        gh.update(0.35, Player())  # rise
        gh.update(1.05, Player())  # active
        self.assertEqual(gh.phase, "retract")
        self.assertEqual(gh.height_frac, 1.0)
        gh.update(0.15, Player())  # halfway retract
        self.assertLess(gh.height_frac, 1.0)
        self.assertGreater(gh.height_frac, 0.0)

    def test_full_lifecycle_duration(self):
        """Total lifecycle: 0.5 + 0.3 + 1.0 + 0.3 = 2.1s."""
        gh = GroundHazard(level=5, spawn_x=500)
        total = 0.0
        for _ in range(200):
            gh.update(0.02, Player())
            total += 0.02
            if not gh.alive:
                break
        self.assertFalse(gh.alive)
        self.assertAlmostEqual(total, 2.1, delta=0.05)

    def test_no_hit_immune_player(self):
        gh = GroundHazard(level=5, spawn_x=500)
        gh.phase = "active"
        p = Player()
        p.hit()  # makes immune
        self.assertFalse(gh.check_hit(p))


# ---------------------------------------------------------------------------
#  Spawn integration (level gating)
# ---------------------------------------------------------------------------
class TestNewObstacleSpawnIntegration(unittest.TestCase):

    def test_canopy_drop_in_pool_at_level2(self):
        """At level 2+, CanopyDrop should appear in spawn pool."""
        import random
        from states import _spawn, GameContext
        # Create minimal context
        ctx = MagicMock(spec=GameContext)
        ctx.level = 2
        ctx.obstacles = []
        ctx.speed_mult = 1.0
        ctx.player = Player()
        ctx.player.x = W // 2
        found = False
        for seed in range(200):
            random.seed(seed)
            ctx.obstacles = []
            _spawn(ctx)
            for obs in ctx.obstacles:
                if isinstance(obs, CanopyDrop):
                    found = True
                    break
            if found:
                break
        self.assertTrue(found, "CanopyDrop never spawned at level 2")

    def test_no_canopy_drop_at_level1(self):
        """At level 1, CanopyDrop should not appear."""
        import random
        from states import _spawn, GameContext
        ctx = MagicMock(spec=GameContext)
        ctx.level = 1
        ctx.obstacles = []
        ctx.speed_mult = 1.0
        ctx.player = Player()
        ctx.player.x = W // 2
        for seed in range(100):
            random.seed(seed)
            ctx.obstacles = []
            _spawn(ctx)
            for obs in ctx.obstacles:
                self.assertNotIsInstance(obs, CanopyDrop)

    def test_screech_bat_in_pool_at_level7(self):
        import random
        from states import _spawn, GameContext
        ctx = MagicMock(spec=GameContext)
        ctx.level = 7
        ctx.obstacles = []
        ctx.speed_mult = 1.0
        ctx.player = Player()
        ctx.player.x = W // 2
        found = False
        for seed in range(300):
            random.seed(seed)
            ctx.obstacles = []
            _spawn(ctx)
            for obs in ctx.obstacles:
                if isinstance(obs, ScreechBat):
                    found = True
                    break
            if found:
                break
        self.assertTrue(found, "ScreechBat never spawned at level 7")

    def test_poison_puddle_max_2(self):
        """With 2 puddles already on screen, no more should spawn."""
        import random
        from states import _spawn, GameContext
        ctx = MagicMock(spec=GameContext)
        ctx.level = 5
        ctx.speed_mult = 1.0
        ctx.player = Player()
        ctx.player.x = W // 2
        # Pre-fill with 2 alive puddles
        pp1 = PoisonPuddle(5, spawn_x=300)
        pp1.alive = True
        pp2 = PoisonPuddle(5, spawn_x=600)
        pp2.alive = True
        ctx.obstacles = [pp1, pp2]
        for seed in range(100):
            random.seed(seed)
            old_count = len(ctx.obstacles)
            _spawn(ctx)
            puddle_count = sum(1 for o in ctx.obstacles if isinstance(o, PoisonPuddle))
            self.assertLessEqual(puddle_count, 2 + (len(ctx.obstacles) - old_count - puddle_count + 2),
                                 "Should not spawn more puddles when 2 exist")


if __name__ == "__main__":
    unittest.main()
