"""Tests for screen navigation via keyboard input in Jungle Dodge."""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ── Stub out pygame before importing game code ─────────────────────────────
# We only need enough of pygame to exercise Game.handle_event().

_pg = types.ModuleType("pygame")
_pg.init = MagicMock()
_pg.font = types.ModuleType("pygame.font")
_pg.font.init = MagicMock()
_pg.font.SysFont = MagicMock(return_value=MagicMock())
_pg.display = types.ModuleType("pygame.display")
_pg.display.set_mode = MagicMock(return_value=MagicMock())
_pg.display.set_caption = MagicMock()
_pg.mouse = types.ModuleType("pygame.mouse")
_pg.mouse.set_visible = MagicMock()
_pg.time = types.ModuleType("pygame.time")
_pg.time.Clock = MagicMock
_pg.Surface = MagicMock
_pg.Rect = MagicMock
_pg.draw = types.ModuleType("pygame.draw")
_pg.draw.rect = MagicMock()
_pg.image = types.ModuleType("pygame.image")
_pg.image.load = MagicMock(return_value=MagicMock())
_pg.transform = types.ModuleType("pygame.transform")
_pg.transform.scale = MagicMock(return_value=MagicMock())
_pg.mixer = types.ModuleType("pygame.mixer")
_pg.mixer.init = MagicMock()
_pg.mixer.Sound = MagicMock
_pg.FULLSCREEN = 0
_pg.SCALED = 0
_pg.KEYDOWN = 2
_pg.K_TAB = 9
_pg.K_ESCAPE = 27
_pg.K_SPACE = 32
_pg.K_RETURN = 13
_pg.K_KP_ENTER = 271
_pg.K_BACKSPACE = 8
_pg.K_F11 = 292
sys.modules["pygame"] = _pg

# Now we can safely reference the state constants and build a minimal Game stub.
ST_START = "start"
ST_PLAYING = "playing"
ST_PAUSED = "paused"
ST_LEVELUP = "levelup"
ST_GAMEOVER = "gameover"
ST_NAME_ENTRY = "name_entry"
ST_LEADERBOARD = "leaderboard"


def _make_event(key):
    """Create a minimal KEYDOWN-like event."""
    ev = types.SimpleNamespace()
    ev.type = _pg.KEYDOWN
    ev.key = key
    ev.unicode = ""
    return ev


# ---------------------------------------------------------------------------
# Rather than importing the entire game module (which has heavy side effects),
# we extract just the handle_event logic.  Read the real source to keep in sync.
# ---------------------------------------------------------------------------
import importlib.util, os

_spec = importlib.util.spec_from_file_location(
    "jungle_dodge",
    os.path.join(os.path.dirname(__file__), "_jungle_dodge_old.py"),
    submodule_search_locations=[],
)
# We don't exec the module (too many side effects).  Instead we test a
# lightweight reproduction of handle_event derived from reading the source.
# This is intentional: the authoritative test target is the event handler
# logic, which we replicate here and verify matches the source file.

class _FakeGame:
    """Minimal stand-in for Game with just the fields handle_event touches."""

    def __init__(self, state=ST_START):
        self.state = state
        self.name_input = ""
        self.start_idle_t = 0.0
        self.score = 0
        self.level = 1

    # stubs for methods called by handle_event
    def _new_game(self):
        self.score = 0
        self.level = 1

    def _submit_score(self, name):
        pass


def _read_handle_event():
    """Return the real handle_event source to compile it in isolation."""
    src_path = os.path.join(os.path.dirname(__file__), "_jungle_dodge_old.py")
    with open(src_path) as f:
        source = f.read()

    # Extract the handle_event method body
    import re
    m = re.search(
        r"(    def handle_event\(self, event\):.*?)(?=\n    # .+ Main loop)",
        source,
        re.DOTALL,
    )
    assert m, "Could not find handle_event in source"
    func_src = m.group(1)

    # Build a namespace with the constants / pygame refs the function needs
    ns = {
        "pygame": _pg,
        "ST_START": ST_START,
        "ST_PLAYING": ST_PLAYING,
        "ST_PAUSED": ST_PAUSED,
        "ST_LEVELUP": ST_LEVELUP,
        "ST_GAMEOVER": ST_GAMEOVER,
        "ST_NAME_ENTRY": ST_NAME_ENTRY,
        "ST_LEADERBOARD": ST_LEADERBOARD,
        "MAX_NAME_LEN": 5,
        "_toggle_fullscreen": lambda: None,
    }

    # Dedent to top-level so we can exec as a class body
    wrapper = (
        "class _H:\n"
        + func_src
        + "\n"
    )
    exec(compile(wrapper, "<handle_event>", "exec"), ns)
    return ns["_H"].handle_event


_handle_event = _read_handle_event()


def _apply(game, key):
    """Send a keydown event to the real handle_event logic."""
    _handle_event(game, _make_event(key))


# ===========================================================================
# Tests
# ===========================================================================

class TestTabNavigation(unittest.TestCase):
    """TAB should toggle between START and LEADERBOARD screens."""

    def test_tab_from_start_goes_to_leaderboard(self):
        g = _FakeGame(ST_START)
        _apply(g, _pg.K_TAB)
        self.assertEqual(g.state, ST_LEADERBOARD)

    def test_tab_from_leaderboard_goes_to_start(self):
        g = _FakeGame(ST_LEADERBOARD)
        _apply(g, _pg.K_TAB)
        self.assertEqual(g.state, ST_START)

    def test_tab_round_trip(self):
        g = _FakeGame(ST_START)
        _apply(g, _pg.K_TAB)
        self.assertEqual(g.state, ST_LEADERBOARD)
        _apply(g, _pg.K_TAB)
        self.assertEqual(g.state, ST_START)

    def test_tab_ignored_on_other_screens(self):
        for st in (ST_PLAYING, ST_PAUSED, ST_GAMEOVER, ST_LEVELUP):
            g = _FakeGame(st)
            _apply(g, _pg.K_TAB)
            self.assertEqual(g.state, st, f"TAB should be no-op on {st}")


class TestLeaderboardBackNav(unittest.TestCase):
    """ENTER and ESC should also navigate back from leaderboard."""

    def test_enter_from_leaderboard(self):
        g = _FakeGame(ST_LEADERBOARD)
        _apply(g, _pg.K_RETURN)
        self.assertEqual(g.state, ST_START)

    def test_kp_enter_from_leaderboard(self):
        g = _FakeGame(ST_LEADERBOARD)
        _apply(g, _pg.K_KP_ENTER)
        self.assertEqual(g.state, ST_START)

    def test_esc_from_leaderboard(self):
        g = _FakeGame(ST_LEADERBOARD)
        _apply(g, _pg.K_ESCAPE)
        self.assertEqual(g.state, ST_START)


class TestSpaceFromLeaderboard(unittest.TestCase):
    """SPACE from leaderboard should start playing (existing behaviour)."""

    def test_space_starts_game(self):
        g = _FakeGame(ST_LEADERBOARD)
        _apply(g, _pg.K_SPACE)
        self.assertEqual(g.state, ST_PLAYING)


if __name__ == "__main__":
    unittest.main()
