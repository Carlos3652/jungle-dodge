"""AudioManager singleton — graceful no-op stub.

All methods silently do nothing when sound files are missing,
so the game runs without audio assets during early development.
"""

import os

try:
    import pygame.mixer as _mixer
    _HAS_MIXER = True
except Exception:
    _HAS_MIXER = False

# ---------------------------------------------------------------------------
# Channel allocation (12 channels) — spec Section 7.3
# ---------------------------------------------------------------------------
CHANNEL_MAP = {
    "music_stem_0": 0,
    "music_stem_1": 1,
    "music_stem_2": 2,
    "music_stem_3": 3,
    "critical":     4,   # HIT, GAME_OVER, BOSS
    "player":       5,   # ROLL, STREAK, POWERUP
    "obstacle":     6,   # BOMB, VINE, BOULDER
    "ambient":      7,   # STUN, BOULDER_ROLL, COMBO
    "score_ui":     8,   # SCORE_TICK, UI_SELECT
    "environment":  9,   # footsteps, ambient
    "jingles":      10,  # LEVEL_UP, BOSS — ducks music
    "overflow":     11,  # spare
}

NUM_CHANNELS = 12

# Base paths (relative to this file's directory)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SFX_DIR = os.path.join(_BASE_DIR, "assets", "sounds", "sfx")
MUSIC_DIR = os.path.join(_BASE_DIR, "assets", "sounds", "music")


class AudioManager:
    """Singleton audio manager with graceful no-op fallbacks.

    Usage::

        audio = AudioManager.get_instance()
        audio.load_all()
        audio.play("SFX_HIT")          # no-op if file missing
        audio.set_stem_layers(0.7)     # no-op if stems not loaded
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Return the singleton AudioManager, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if AudioManager._instance is not None:
            raise RuntimeError(
                "Use AudioManager.get_instance() instead of direct construction."
            )
        self._initialized = False
        self._muted = False
        self._sounds: dict[str, object] = {}      # name -> pygame.mixer.Sound
        self._stems: list[object | None] = [None] * 4
        self._volumes = {
            "master": 1.0,
            "music": 0.7,
            "sfx": 0.75,
        }
        self._stem_intensity = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_all(self, theme: str = "jungle"):
        """Load every .wav in sfx/ and every stem .ogg in music/.

        *theme* is passed to :meth:`load_stems` to select which music stems
        are loaded (e.g. ``"jungle"`` or ``"space"``).
        Silently skips missing directories or files.
        """
        if not _HAS_MIXER:
            return
        try:
            _mixer.init(44100, -16, 2, 512)
            _mixer.set_num_channels(NUM_CHANNELS)
            self._initialized = True
        except Exception:
            return

        # SFX
        if os.path.isdir(SFX_DIR):
            for fname in os.listdir(SFX_DIR):
                if fname.lower().endswith(".wav"):
                    key = os.path.splitext(fname)[0].upper()
                    path = os.path.join(SFX_DIR, fname)
                    try:
                        self._sounds[key] = _mixer.Sound(path)
                    except Exception:
                        pass

        # Music stems
        self.load_stems(theme)

    def load_stems(self, theme_prefix: str = "jungle"):
        """Load music stems for *theme_prefix* (e.g. ``jungle_stem_0.ogg``).

        Missing stems are silently ignored.
        """
        if not self._initialized:
            return
        for i in range(4):
            path = os.path.join(MUSIC_DIR, f"{theme_prefix}_stem_{i}.ogg")
            if os.path.isfile(path):
                try:
                    self._stems[i] = _mixer.Sound(path)
                except Exception:
                    self._stems[i] = None
            else:
                self._stems[i] = None

    def play(self, name: str, volume: float | None = None,
             channel: str | None = None):
        """Play the SFX identified by *name* (e.g. ``"SFX_HIT"``).

        If *channel* is a key in :data:`CHANNEL_MAP` and the mixer is
        initialised, the sound is played on that specific channel.
        Otherwise falls back to ``sound.play()``.

        No-op when muted, when the mixer is uninitialised, or when
        *name* is not in the loaded sound catalogue.
        """
        if self._muted or not self._initialized:
            return
        sound = self._sounds.get(name.upper())
        if sound is None:
            return
        effective_vol = (volume if volume is not None else 1.0)
        effective_vol *= self._volumes["sfx"] * self._volumes["master"]
        sound.set_volume(max(0.0, min(1.0, effective_vol)))
        try:
            idx = CHANNEL_MAP.get(channel) if channel is not None else None
            if idx is not None:
                _mixer.Channel(idx).play(sound)
            else:
                sound.play()
        except Exception:
            pass

    def set_stem_layers(self, intensity: float):
        """Crossfade music stems based on *intensity* (0.0 – 1.0).

        No-op when stems are not loaded.
        """
        self._stem_intensity = max(0.0, min(1.0, intensity))
        if not self._initialized:
            return
        music_vol = self._volumes["music"] * self._volumes["master"]
        for i, stem in enumerate(self._stems):
            if stem is None:
                continue
            # Simple layering: stem 0 always on, higher stems fade in
            layer_vol = 1.0 if i == 0 else self._stem_intensity
            stem.set_volume(max(0.0, min(1.0, layer_vol * music_vol)))

    def set_volumes(self, master: float | None = None,
                    music: float | None = None,
                    sfx: float | None = None):
        """Update volume levels.  ``None`` values are left unchanged."""
        if master is not None:
            self._volumes["master"] = max(0.0, min(1.0, master))
        if music is not None:
            self._volumes["music"] = max(0.0, min(1.0, music))
        if sfx is not None:
            self._volumes["sfx"] = max(0.0, min(1.0, sfx))
        # Re-apply stem volumes
        self.set_stem_layers(self._stem_intensity)

    def update(self, dt: float = 0.0):
        """Per-frame tick (reserved for future crossfade / ducking logic).

        Currently a no-op; safe to call every frame.
        """
        pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool):
        self._muted = value

    def toggle_mute(self):
        """Toggle mute state.  Returns the new muted flag."""
        self._muted = not self._muted
        return self._muted

    @classmethod
    def _reset(cls):
        """Reset the singleton (for testing only)."""
        cls._instance = None
