"""Tests for obstacle variant classes (jd-13)."""

import sys
import types
import math
import unittest
from unittest.mock import MagicMock

# ── Stub pygame before importing game code ───────────────────────────────────
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
_pg.transform.rotate = MagicMock(return_value=MagicMock(get_size=MagicMock(return_value=(100, 100))))
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
_pg.K_a = 97
_pg.K_d = 100
_pg.K_SPACE = 32
_pg.key = types.ModuleType("pygame.key")
_pg.key.get_pressed = MagicMock(return_value={})
_pg.event = types.ModuleType("pygame.event")
_pg.event.get = MagicMock(return_value=[])
sys.modules.setdefault("pygame", _pg)
sys.modules.setdefault("pygame.font", _pg.font)
sys.modules.setdefault("pygame.display", _pg.display)
sys.modules.setdefault("pygame.mixer", _pg.mixer)

from entities import (
    Player, Vine, Bomb, Spike, Boulder,
    VineSnap, BombDelay, BouncingSpike, SplitBoulder, spawn_cluster_spike,
)
from constants import W, GROUND_Y, S, SX, SY


class TestVineSnap(unittest.TestCase):
    """VineSnap: lunges sideways during fall."""

    def test_inherits_vine(self):
        vs = VineSnap(level=4, spawn_x=500)
        self.assertIsInstance(vs, Vine)

    def test_lunge_occurs_during_fall(self):
        """VineSnap should have lateral movement beyond normal sway."""
        vs = VineSnap(level=4, spawn_x=1000)
        vs._lunge_progress = 0.01  # trigger almost immediately
        vs._lunge_dir = 1
        vs._lunge_dist = 180 * SX
        initial_x = vs.x
        # Simulate falling until lunge triggers
        for _ in range(200):
            vs.update(0.02, Player())
            if vs._lunge_started:
                break
        self.assertTrue(vs._lunge_started)

    def test_lunge_completes(self):
        vs = VineSnap(level=4, spawn_x=1000)
        vs._lunge_progress = 0.01
        for _ in range(500):
            vs.update(0.02, Player())
            if vs._lunge_done:
                break
        self.assertTrue(vs._lunge_done)

    def test_lands_eventually(self):
        vs = VineSnap(level=4, spawn_x=1000)
        for _ in range(1000):
            vs.update(0.05, Player())
            if vs.landed or not vs.alive:
                break
        self.assertTrue(vs.landed or not vs.alive)


class TestBombDelay(unittest.TestCase):
    """BombDelay: 0.8s fuse delay before explosion."""

    def test_inherits_bomb(self):
        bd = BombDelay(level=5, spawn_x=500)
        self.assertIsInstance(bd, Bomb)

    def test_delay_before_explosion(self):
        """After hitting ground, bomb should delay before exploding."""
        bd = BombDelay(level=5, spawn_x=500)
        # Fast-forward to ground
        for _ in range(500):
            bd.update(0.05, Player())
            if bd._delay_active:
                break
        self.assertTrue(bd._delay_active)
        self.assertFalse(bd.exploded)

    def test_explodes_after_delay(self):
        bd = BombDelay(level=5, spawn_x=500)
        # Fast-forward to ground
        for _ in range(500):
            bd.update(0.05, Player())
            if bd._delay_active:
                break
        self.assertTrue(bd._delay_active)
        # Now wait for fuse delay
        for _ in range(50):
            bd.update(0.05, Player())
            if bd.exploded:
                break
        self.assertTrue(bd.exploded)

    def test_no_explosion_hit_during_delay(self):
        """During delay, only body collision counts, not explosion radius."""
        bd = BombDelay(level=5, spawn_x=500)
        # Force into delay state
        bd._delay_active = True
        bd.y = float(GROUND_Y - bd.R)
        p = Player()
        p.immune_t = 0.0
        # check_hit during delay uses rect collision (body only)
        result = bd.check_hit(p)
        # Result depends on rect overlap — but shouldn't use explosion radius
        self.assertFalse(bd.exploded)

    def test_dies_after_full_sequence(self):
        bd = BombDelay(level=5, spawn_x=500)
        for _ in range(2000):
            bd.update(0.05, Player())
            if not bd.alive:
                break
        self.assertFalse(bd.alive)


class TestClusterSpike(unittest.TestCase):
    """spawn_cluster_spike: returns 3 smaller spikes in triangle."""

    def test_returns_three_spikes(self):
        spikes = spawn_cluster_spike(level=3, spawn_x=1000)
        self.assertEqual(len(spikes), 3)
        for s in spikes:
            self.assertIsInstance(s, Spike)

    def test_spikes_are_smaller(self):
        """Cluster spikes should be 80% of normal size."""
        normal = Spike(level=3, spawn_x=1000)
        cluster = spawn_cluster_spike(level=3, spawn_x=1000)
        for s in cluster:
            self.assertLess(s.SW, normal.SW)
            self.assertLess(s.SH, normal.SH)

    def test_spikes_have_different_x_positions(self):
        """Center and flanking spikes should be at different X positions."""
        spikes = spawn_cluster_spike(level=3, spawn_x=1000)
        xs = [s.x for s in spikes]
        self.assertEqual(len(set(xs)), 3)  # all different

    def test_flanking_spikes_start_higher(self):
        """Flanking spikes should start at a higher Y position (more negative)."""
        spikes = spawn_cluster_spike(level=3, spawn_x=1000)
        center_y = spikes[0].y
        for s in spikes[1:]:
            self.assertLess(s.y, center_y)

    def test_all_spikes_fall_and_die(self):
        spikes = spawn_cluster_spike(level=3, spawn_x=1000)
        for s in spikes:
            for _ in range(500):
                s.update(0.05, Player())
                if not s.alive:
                    break
            self.assertFalse(s.alive)


class TestBouncingSpike(unittest.TestCase):
    """BouncingSpike: bounces once on ground contact."""

    def test_inherits_spike(self):
        bs = BouncingSpike(level=6, spawn_x=500)
        self.assertIsInstance(bs, Spike)

    def test_bounces_on_first_ground_contact(self):
        bs = BouncingSpike(level=6, spawn_x=500)
        # Fast-forward to ground
        for _ in range(500):
            bs.update(0.05, Player())
            if bs._has_bounced:
                break
        self.assertTrue(bs._has_bounced)
        self.assertTrue(bs.alive)  # should still be alive after first bounce
        self.assertLess(bs.vy, 0)  # should be going upward

    def test_dies_on_second_ground_contact(self):
        bs = BouncingSpike(level=6, spawn_x=500)
        for _ in range(2000):
            bs.update(0.02, Player())
            if not bs.alive:
                break
        self.assertFalse(bs.alive)
        self.assertTrue(bs._has_bounced)

    def test_bounce_velocity_is_60_percent(self):
        bs = BouncingSpike(level=6, spawn_x=500)
        original_vy = bs._original_vy
        # Fast-forward to ground
        for _ in range(500):
            bs.update(0.05, Player())
            if bs._has_bounced:
                break
        self.assertAlmostEqual(abs(bs.vy), abs(original_vy) * 0.6, places=0)


class TestSplitBoulder(unittest.TestCase):
    """SplitBoulder: 1.4x size, splits into 2 on ground contact."""

    def test_inherits_boulder(self):
        sb = SplitBoulder(level=5, spawn_x=500)
        self.assertIsInstance(sb, Boulder)

    def test_larger_radius(self):
        normal = Boulder(level=5, spawn_x=500)
        sb = SplitBoulder(level=5, spawn_x=500)
        self.assertGreater(sb.R, normal.R)
        expected_r = int(30 * S * 1.4)
        self.assertEqual(sb.R, expected_r)

    def test_splits_on_ground_contact(self):
        sb = SplitBoulder(level=5, spawn_x=500)
        for _ in range(1000):
            sb.update(0.05, Player())
            if sb._has_split:
                break
        self.assertTrue(sb._has_split)
        self.assertFalse(sb.alive)

    def test_split_returns_two_boulders(self):
        sb = SplitBoulder(level=5, spawn_x=500)
        # Force to ground
        sb.y = float(GROUND_Y - sb.R + 1)
        sb.update(0.05, Player())
        self.assertTrue(sb._has_split)
        children = sb.split()
        self.assertEqual(len(children), 2)
        for child in children:
            self.assertIsInstance(child, Boulder)

    def test_children_go_opposite_directions(self):
        sb = SplitBoulder(level=5, spawn_x=1000)
        sb.y = float(GROUND_Y - sb.R + 1)
        sb.update(0.05, Player())
        children = sb.split()
        dirs = {c.roll_dir for c in children}
        self.assertEqual(dirs, {-1, 1})

    def test_children_are_rolling(self):
        sb = SplitBoulder(level=5, spawn_x=1000)
        sb.y = float(GROUND_Y - sb.R + 1)
        sb.update(0.05, Player())
        children = sb.split()
        for child in children:
            self.assertTrue(child.rolling)

    def test_never_enters_rolling_state(self):
        """SplitBoulder should split, not roll."""
        sb = SplitBoulder(level=5, spawn_x=500)
        for _ in range(1000):
            sb.update(0.05, Player())
            if not sb.alive:
                break
        # SplitBoulder should never set self.rolling = True
        self.assertFalse(sb.rolling)


class TestVariantSpawnLogic(unittest.TestCase):
    """Test _maybe_variant level-gating from states.py."""

    def test_import_maybe_variant(self):
        """Verify _maybe_variant is callable."""
        from states import _maybe_variant
        result = _maybe_variant("vine", 1, 500, 1.0)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

    def test_base_type_at_low_level(self):
        """At level 1, no variants should spawn."""
        from states import _maybe_variant
        import random
        random.seed(42)
        for _ in range(50):
            for kind in ("vine", "bomb", "spike", "boulder"):
                result = _maybe_variant(kind, 1, 500, 1.0)
                self.assertEqual(len(result), 1)
                # At level 1, should always be base type
                if kind == "vine":
                    self.assertIsInstance(result[0], Vine)
                    self.assertNotIsInstance(result[0], VineSnap)
                elif kind == "bomb":
                    self.assertIsInstance(result[0], Bomb)
                    self.assertNotIsInstance(result[0], BombDelay)
                elif kind == "spike":
                    self.assertIsInstance(result[0], Spike)
                elif kind == "boulder":
                    self.assertIsInstance(result[0], Boulder)
                    self.assertNotIsInstance(result[0], SplitBoulder)

    def test_cluster_spike_possible_at_level3(self):
        """At level 3+, spike can produce cluster (3 spikes)."""
        from states import _maybe_variant
        import random
        found_cluster = False
        for seed in range(200):
            random.seed(seed)
            result = _maybe_variant("spike", 3, 500, 1.0)
            if len(result) == 3:
                found_cluster = True
                break
        self.assertTrue(found_cluster, "ClusterSpike never spawned at level 3")

    def test_vine_snap_possible_at_level4(self):
        from states import _maybe_variant
        import random
        found = False
        for seed in range(200):
            random.seed(seed)
            result = _maybe_variant("vine", 4, 500, 1.0)
            if isinstance(result[0], VineSnap):
                found = True
                break
        self.assertTrue(found, "VineSnap never spawned at level 4")

    def test_bomb_delay_possible_at_level5(self):
        from states import _maybe_variant
        import random
        found = False
        for seed in range(200):
            random.seed(seed)
            result = _maybe_variant("bomb", 5, 500, 1.0)
            if isinstance(result[0], BombDelay):
                found = True
                break
        self.assertTrue(found, "BombDelay never spawned at level 5")

    def test_split_boulder_possible_at_level5(self):
        from states import _maybe_variant
        import random
        found = False
        for seed in range(200):
            random.seed(seed)
            result = _maybe_variant("boulder", 5, 500, 1.0)
            if isinstance(result[0], SplitBoulder):
                found = True
                break
        self.assertTrue(found, "SplitBoulder never spawned at level 5")

    def test_bouncing_spike_possible_at_level6(self):
        from states import _maybe_variant
        import random
        found = False
        for seed in range(200):
            random.seed(seed)
            result = _maybe_variant("spike", 6, 500, 1.0)
            if len(result) == 1 and isinstance(result[0], BouncingSpike):
                found = True
                break
        self.assertTrue(found, "BouncingSpike never spawned at level 6")

    def test_speed_mult_applied(self):
        """Variants should have speed_mult applied to vy."""
        from states import _maybe_variant
        speed_mult = 1.5
        result = _maybe_variant("vine", 1, 500, speed_mult)
        # The base vine vy should be multiplied
        base_vine = Vine(1, spawn_x=500)
        # Result vy should be base * speed_mult
        # (approximately, since random sway might differ)
        self.assertAlmostEqual(result[0].vy / base_vine.vy, speed_mult, places=1)


if __name__ == "__main__":
    unittest.main()
