"""Tests for audio.py — AudioManager singleton with no-op fallbacks."""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio import AudioManager, CHANNEL_MAP, NUM_CHANNELS


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
        # Should not raise even for a valid key or explicit channel
        mgr.play("SFX_HIT")
        mgr.play("SFX_HIT", channel="critical")
        mgr.play("NONEXISTENT", channel="player")
        assert mgr.muted is True

    # --- Test 3: play is no-op for unknown SFX -----------------------

    def test_play_does_nothing_for_unknown_sfx(self):
        mgr = AudioManager.get_instance()
        mgr.muted = False
        # Mixer not initialised → graceful no-op
        mgr.play("SFX_DOES_NOT_EXIST")
        mgr.play("SFX_DOES_NOT_EXIST", channel="critical")
        mgr.play("")
        # No exception means pass

    # --- Test 4: channel map is complete (12 channels) ----------------

    def test_channel_map_has_12_channels(self):
        assert NUM_CHANNELS == 12
        assert len(CHANNEL_MAP) == 12
        # Music stems occupy channels 0–3
        for i in range(4):
            assert CHANNEL_MAP[f"music_stem_{i}"] == i
        # All values are unique integers 0–11
        values = sorted(CHANNEL_MAP.values())
        assert values == list(range(12))

    # --- Test 5: play accepts channel parameter -----------------------

    def test_play_accepts_channel_parameter(self):
        mgr = AudioManager.get_instance()
        # Not initialised, so these are all no-ops — just verify no crash
        mgr.play("SFX_HIT", channel="critical")
        mgr.play("SFX_HIT", channel="player")
        mgr.play("SFX_HIT", channel="obstacle")
        mgr.play("SFX_HIT", channel="invalid_channel_name")

    # --- Test 6: set_stem_layers / set_volumes are no-ops when uninit -

    def test_stem_and_volume_noop_when_uninitialised(self):
        mgr = AudioManager.get_instance()
        # Should not raise even though mixer is not initialised
        mgr.set_stem_layers(0.5)
        mgr.set_volumes(master=0.8, music=0.6, sfx=0.9)
        mgr.update(0.016)
        assert mgr._volumes["master"] == 0.8
        assert mgr._volumes["music"] == 0.6
        assert mgr._volumes["sfx"] == 0.9

    # --- Test 7: toggle_mute flips state ----------------------------

    def test_toggle_mute(self):
        mgr = AudioManager.get_instance()
        assert mgr.muted is False
        result = mgr.toggle_mute()
        assert result is True
        assert mgr.muted is True
        result = mgr.toggle_mute()
        assert result is False
        assert mgr.muted is False

    # --- Test 8: set_volumes clamps to 0.0-1.0 ----------------------

    def test_set_volumes_clamps(self):
        mgr = AudioManager.get_instance()
        mgr.set_volumes(master=5.0, music=-1.0, sfx=0.5)
        assert mgr._volumes["master"] == 1.0
        assert mgr._volumes["music"] == 0.0
        assert mgr._volumes["sfx"] == 0.5

    # --- Test 9: direct construction raises RuntimeError -------------

    def test_direct_construction_raises(self):
        _ = AudioManager.get_instance()  # create singleton
        import pytest
        with pytest.raises(RuntimeError, match="get_instance"):
            AudioManager()

    # --- Test 10: load_all is no-op without mixer --------------------

    def test_load_all_noop_without_mixer(self):
        mgr = AudioManager.get_instance()
        # Even if mixer import failed, load_all should not raise
        mgr.load_all()
        # _initialized may or may not be True depending on environment,
        # but it should not crash

    # --- Test 11: load_stems is no-op when not initialized -----------

    def test_load_stems_noop_when_not_initialized(self):
        mgr = AudioManager.get_instance()
        mgr._initialized = False
        mgr.load_stems("space")  # should not raise
        assert all(s is None for s in mgr._stems)

    # --- Test 12: set_volumes with None leaves values unchanged ------

    def test_set_volumes_none_unchanged(self):
        mgr = AudioManager.get_instance()
        mgr.set_volumes(master=0.5)
        mgr.set_volumes(sfx=0.3)  # master and music unchanged
        assert mgr._volumes["master"] == 0.5
        assert mgr._volumes["music"] == 0.7  # default
        assert mgr._volumes["sfx"] == 0.3
