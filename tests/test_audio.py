"""Tests for audio.py — AudioManager singleton with no-op fallbacks."""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio import AudioManager


class TestAudioManager:
    """AudioManager tests — all run without real sound files."""

    def setup_method(self):
        """Reset singleton before each test."""
        AudioManager._reset()

    def teardown_method(self):
        AudioManager._reset()

    # --- Test 1: singleton returns same instance ----------------------

    def test_singleton_returns_same_instance(self):
        a = AudioManager.get_instance()
        b = AudioManager.get_instance()
        assert a is b

    # --- Test 2: play is no-op when muted -----------------------------

    def test_play_does_nothing_when_muted(self):
        mgr = AudioManager.get_instance()
        mgr.muted = True
        # Should not raise even for a valid key
        mgr.play("SFX_HIT")
        mgr.play("NONEXISTENT")
        assert mgr.muted is True

    # --- Test 3: play is no-op for unknown SFX -----------------------

    def test_play_does_nothing_for_unknown_sfx(self):
        mgr = AudioManager.get_instance()
        mgr.muted = False
        # Mixer not initialised → graceful no-op
        mgr.play("SFX_DOES_NOT_EXIST")
        mgr.play("")
        # No exception means pass
