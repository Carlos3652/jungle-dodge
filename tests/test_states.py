"""Tests for the state machine (task jd-06).

4 required tests:
- test_push_calls_enter
- test_pop_calls_exit
- test_stack_empty_exits_run
- test_dt_capped_at_50ms
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# ── Stub out pygame before importing game code ───────────────────────────────
_pg = types.ModuleType("pygame")
_pg.init = MagicMock()
_pg.font = types.ModuleType("pygame.font")
_pg.font.init = MagicMock()
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
_pg.Rect = MagicMock
_pg.draw = types.ModuleType("pygame.draw")
_pg.draw.rect = MagicMock()
_pg.draw.line = MagicMock()
_pg.draw.lines = MagicMock()
_pg.draw.circle = MagicMock()
_pg.draw.ellipse = MagicMock()
_pg.draw.polygon = MagicMock()
_pg.image = types.ModuleType("pygame.image")
_pg.image.load = MagicMock(return_value=MagicMock())
_pg.transform = types.ModuleType("pygame.transform")
_pg.transform.scale = MagicMock(return_value=MagicMock())
_pg.mixer = types.ModuleType("pygame.mixer")
_pg.mixer.init = MagicMock()
_pg.mixer.Sound = MagicMock
_pg.FULLSCREEN = 0
_pg.SCALED = 0
_pg.SRCALPHA = 0x00010000
_pg.KEYDOWN = 2
_pg.QUIT = 12
_pg.K_TAB = 9
_pg.K_ESCAPE = 27
_pg.K_SPACE = 32
_pg.K_RETURN = 13
_pg.K_KP_ENTER = 271
_pg.K_BACKSPACE = 8
_pg.K_F11 = 292
_pg.K_LEFT = 276
_pg.K_RIGHT = 275
_pg.K_a = 97
_pg.K_d = 100
_pg.key = types.ModuleType("pygame.key")
_pg.key.get_pressed = MagicMock(return_value={})
_pg.event = types.ModuleType("pygame.event")
_pg.event.get = MagicMock(return_value=[])
_pg.event.Event = MagicMock
_pg.quit = MagicMock()
sys.modules["pygame"] = _pg
sys.modules["pygame.font"] = _pg.font
sys.modules["pygame.display"] = _pg.display
sys.modules["pygame.mixer"] = _pg.mixer

from states import State, GameStateManager, GameContext
from persistence import PersistenceManager


def _make_ctx():
    """Create a minimal GameContext for testing."""
    ctx = GameContext(
        screen=MagicMock(),
        display=MagicMock(),
        clock=MagicMock(),
        persistence=PersistenceManager.__new__(PersistenceManager),
    )
    # Stub persistence methods used by states
    ctx.persistence.get_board = MagicMock(return_value=[])
    ctx.persistence.is_top_score = MagicMock(return_value=False)
    return ctx


class _SpyState(State):
    """State subclass that records enter/exit calls."""

    def __init__(self):
        self.entered = False
        self.exited = False

    def enter(self, ctx):
        self.entered = True

    def exit(self, ctx):
        self.exited = True


class TestPushCallsEnter(unittest.TestCase):
    def test_push_calls_enter(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        s = _SpyState()
        self.assertFalse(s.entered)
        mgr.push(s)
        self.assertTrue(s.entered)


class TestPopCallsExit(unittest.TestCase):
    def test_pop_calls_exit(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        s = _SpyState()
        mgr.push(s)
        self.assertFalse(s.exited)
        mgr.pop()
        self.assertTrue(s.exited)


class TestStackEmptyExitsRun(unittest.TestCase):
    def test_stack_empty_exits_run(self):
        """run() should return immediately when the stack is empty."""
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        # With no states pushed, run() should return immediately (not block)
        mgr.run()  # should not hang


class TestDtCappedAt50ms(unittest.TestCase):
    def test_dt_capped_at_50ms(self):
        """dt passed to State.update() must never exceed 0.05 s."""
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)

        # Make clock.tick return 200 ms (way over cap)
        ctx.clock.tick = MagicMock(return_value=200)

        recorded_dts = []

        class _RecordingState(State):
            def update(self, ctx, dt):
                recorded_dts.append(dt)
                # Pop self to end the run loop after one frame
                ctx.manager.pop()

            def draw(self, ctx):
                pass

        s = _RecordingState()
        ctx.manager = mgr
        mgr.push(s)
        _pg.event.get = MagicMock(return_value=[])
        mgr.run()

        self.assertEqual(len(recorded_dts), 1)
        self.assertLessEqual(recorded_dts[0], 0.05)


if __name__ == "__main__":
    unittest.main()
