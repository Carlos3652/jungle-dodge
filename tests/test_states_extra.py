"""Extra tests for states.py — coverage for replace(), state transitions, helpers."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import types
import unittest
from unittest.mock import MagicMock

import pygame
pygame.init()

from states import (
    State, GameStateManager, GameContext,
    StartScreenState, PlayState, PauseState,
    LevelUpState, GameOverState, NameEntryState, LeaderboardState,
    _new_game, _reset_level, _spawn_rate,
)
from persistence import PersistenceManager


def _make_ctx():
    mock_persistence = MagicMock()
    mock_persistence.get_board.return_value = []
    mock_persistence.is_top_score.return_value = False
    mock_persistence.submit_score.return_value = None
    mock_persistence.load_settings.return_value = {
        "version": 1, "theme": "jungle", "difficulty": "normal",
        "volume_music": 0.7, "volume_sfx": 1.0, "volume_master": 1.0,
        "muted": False, "death_count": 0, "first_run": True,
        "show_tutorial": True, "fullscreen": True,
    }
    mock_persistence.save_settings.return_value = None
    screen = pygame.Surface((3840, 2160))
    display = pygame.Surface((3840, 2160))
    ctx = GameContext(
        screen=screen,
        display=display,
        clock=pygame.time.Clock(),
        persistence=mock_persistence,
    )
    ctx.bg = pygame.Surface((3840, 2160))
    return ctx


def _key_event(key, unicode=""):
    ev = types.SimpleNamespace(type=pygame.KEYDOWN, key=key, unicode=unicode)
    return ev


class TestReplace(unittest.TestCase):
    def test_replace_calls_exit_and_enter(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)

        class Spy(State):
            def __init__(self):
                self.entered = 0
                self.exited = 0
            def enter(self, ctx): self.entered += 1
            def exit(self, ctx): self.exited += 1

        old = Spy()
        new = Spy()
        mgr.push(old)
        mgr.replace(new)
        self.assertEqual(old.exited, 1)
        self.assertEqual(new.entered, 1)
        self.assertIs(mgr.current, new)

    def test_replace_on_empty_stack(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)

        class Spy(State):
            def __init__(self): self.entered = 0
            def enter(self, ctx): self.entered += 1

        s = Spy()
        mgr.replace(s)  # should not crash
        self.assertEqual(s.entered, 1)
        self.assertIs(mgr.current, s)


class TestSpaceFromStartGoesToPlay(unittest.TestCase):
    def test_space_starts_game(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        start = StartScreenState()
        mgr.push(start)
        start.handle_event(ctx, _key_event(pygame.K_SPACE))
        self.assertIsInstance(mgr.current, PlayState)
        self.assertIsNotNone(ctx.player)


class TestEscFromPlayGoesToPause(unittest.TestCase):
    def test_esc_pauses(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        play = PlayState()
        mgr.push(play)
        play.handle_event(ctx, _key_event(pygame.K_ESCAPE))
        self.assertIsInstance(mgr.current, PauseState)


class TestSpaceFromPauseResumes(unittest.TestCase):
    def test_space_resumes(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        play = PlayState()
        mgr.push(play)
        pause = PauseState()
        mgr.push(pause)
        pause.handle_event(ctx, _key_event(pygame.K_SPACE))
        # Should have popped pause, play is now on top
        self.assertIsInstance(mgr.current, PlayState)


class TestEscFromPauseGoesToStart(unittest.TestCase):
    def test_esc_goes_home(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        play = PlayState()
        mgr.push(play)
        pause = PauseState()
        mgr.push(pause)
        pause.handle_event(ctx, _key_event(pygame.K_ESCAPE))
        self.assertIsInstance(mgr.current, StartScreenState)


class TestGameOverSpaceRestarts(unittest.TestCase):
    def test_space_restarts(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        go = GameOverState()
        mgr.push(go)
        go.handle_event(ctx, _key_event(pygame.K_SPACE))
        self.assertIsInstance(mgr.current, PlayState)


class TestGameOverEscGoesHome(unittest.TestCase):
    def test_esc_goes_home(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        go = GameOverState()
        mgr.push(go)
        go.handle_event(ctx, _key_event(pygame.K_ESCAPE))
        self.assertIsInstance(mgr.current, StartScreenState)


class TestNameEntrySubmit(unittest.TestCase):
    def test_enter_submits_and_goes_to_leaderboard(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        ctx.score = 100
        ctx.name_input = "ACE"
        ne = NameEntryState()
        mgr.push(ne)
        ne.handle_event(ctx, _key_event(pygame.K_RETURN))
        self.assertIsInstance(mgr.current, LeaderboardState)
        ctx.persistence.submit_score.assert_called_once_with("ACE", 100, 1, difficulty="normal")

    def test_esc_submits_dashes(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        ctx.score = 50
        ne = NameEntryState()
        mgr.push(ne)
        ne.handle_event(ctx, _key_event(pygame.K_ESCAPE))
        ctx.persistence.submit_score.assert_called_once_with("-----", 50, 1, difficulty="normal")


class TestNameEntryTyping(unittest.TestCase):
    def test_typing_appends(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        ne = NameEntryState()
        mgr.push(ne)
        ctx.name_input = ""
        ne.handle_event(ctx, _key_event(0, unicode="a"))
        self.assertEqual(ctx.name_input, "A")

    def test_backspace_deletes(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        ne = NameEntryState()
        mgr.push(ne)
        ctx.name_input = "AB"
        ne.handle_event(ctx, _key_event(pygame.K_BACKSPACE))
        self.assertEqual(ctx.name_input, "A")


class TestNameEntryCursorBlink(unittest.TestCase):
    def test_cursor_toggles(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ne = NameEntryState()
        mgr.push(ne)
        ctx.cursor_on = True
        ctx.cursor_t = 0.0
        ne.update(ctx, 0.6)  # exceeds 0.5 threshold
        self.assertFalse(ctx.cursor_on)


class TestNewGame(unittest.TestCase):
    def test_resets_score_and_level(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ctx.score = 999
        ctx.level = 5
        _new_game(ctx)
        self.assertEqual(ctx.score, 0)
        self.assertEqual(ctx.level, 1)
        self.assertIsNotNone(ctx.player)


class TestSpawnRate(unittest.TestCase):
    def test_level_1(self):
        from constants import BASE_SPAWN
        self.assertAlmostEqual(_spawn_rate(1), BASE_SPAWN)

    def test_higher_level_spawns_faster(self):
        self.assertLess(_spawn_rate(5), _spawn_rate(1))

    def test_never_below_min(self):
        from constants import MIN_SPAWN
        self.assertGreaterEqual(_spawn_rate(100), MIN_SPAWN)


class TestLevelUpState(unittest.TestCase):
    def test_enter_sets_timer(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        lu = LevelUpState()
        mgr.push(lu)
        self.assertAlmostEqual(ctx.levelup_t, 2.8)

    def test_timer_expires_goes_to_play(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        _new_game(ctx)
        lu = LevelUpState()
        mgr.push(lu)
        lu.update(ctx, 3.0)  # exceed 2.8s
        self.assertIsInstance(mgr.current, PlayState)


class TestLeaderboardSpaceStartsGame(unittest.TestCase):
    def test_space_from_leaderboard(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        lb = LeaderboardState()
        mgr.push(lb)
        lb.handle_event(ctx, _key_event(pygame.K_SPACE))
        self.assertIsInstance(mgr.current, PlayState)


# ─────────────────────────────────────────────────────────────────────────────
#  Null-guard tests (CRIT-03): ctx.player is None must not crash
# ─────────────────────────────────────────────────────────────────────────────
class TestPauseStateNullPlayer(unittest.TestCase):
    """PauseState.draw must not crash when ctx.player is None."""

    def test_draw_with_none_player_does_not_crash(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ctx.player = None  # explicitly None
        pause = PauseState()
        mgr.push(pause)
        # Should return early without error
        pause.draw(ctx)

    def test_draw_with_none_player_skips_hud(self):
        """When player is None, hud.draw_hud should NOT be called."""
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ctx.player = None
        pause = PauseState()
        mgr.push(pause)
        import hud as _hud_mod
        from unittest.mock import patch as _patch
        with _patch.object(_hud_mod, "draw_hud") as mock_hud:
            pause.draw(ctx)
            mock_hud.assert_not_called()


class TestLevelUpStateNullPlayer(unittest.TestCase):
    """LevelUpState.update/draw must not crash when ctx.player is None."""

    def test_update_with_none_player_does_not_crash(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ctx.player = None
        lu = LevelUpState()
        mgr.push(lu)
        # Should not raise AttributeError
        lu.update(ctx, 0.1)

    def test_update_with_none_player_still_decrements_timer(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ctx.player = None
        lu = LevelUpState()
        mgr.push(lu)
        initial = ctx.levelup_t
        lu.update(ctx, 0.5)
        self.assertAlmostEqual(ctx.levelup_t, initial - 0.5)

    def test_draw_with_none_player_does_not_crash(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ctx.player = None
        lu = LevelUpState()
        mgr.push(lu)
        # Should return early without error
        lu.draw(ctx)

    def test_draw_with_none_player_skips_hud(self):
        ctx = _make_ctx()
        mgr = GameStateManager(ctx)
        ctx.player = None
        lu = LevelUpState()
        mgr.push(lu)
        import hud as _hud_mod
        from unittest.mock import patch as _patch
        with _patch.object(_hud_mod, "draw_hud") as mock_hud:
            lu.draw(ctx)
            mock_hud.assert_not_called()


class TestDrawSceneNullPlayer(unittest.TestCase):
    """_draw_scene must not crash when ctx.player is None."""

    def test_draw_scene_with_none_player(self):
        from states import _draw_scene
        ctx = _make_ctx()
        GameStateManager(ctx)
        ctx.player = None
        # Should not raise
        _draw_scene(ctx)


if __name__ == "__main__":
    unittest.main()
