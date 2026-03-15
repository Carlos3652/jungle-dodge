"""
Tests for Player side-roll mechanic (task jd-07).

Covers i-frames, cooldown, and speed multiplier during roll.
"""

import os
import sys
import math

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Pygame must be initialised before importing game modules
import pygame
pygame.init()
# Tiny hidden display so Surface / font calls work in CI
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.display.set_mode((1, 1))

from entities import Player
from constants import (
    PLAYER_SPD, ROLL_DURATION, ROLL_SPEED_MULT,
    ROLL_IFRAME, ROLL_COOLDOWN, W,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

class _FakeKeys:
    """Minimal fake key-state that supports index access like pygame.key.get_pressed()."""
    def __init__(self, pressed=None):
        self._pressed = pressed or {}

    def __getitem__(self, key):
        return self._pressed.get(key, False)

def _make_keys(**overrides):
    pressed = {}
    for k, v in overrides.items():
        pressed[getattr(pygame, k)] = v
    return _FakeKeys(pressed)

NEUTRAL_KEYS = _make_keys()
RIGHT_KEYS   = _make_keys(K_RIGHT=True, K_d=True)
LEFT_KEYS    = _make_keys(K_LEFT=True, K_a=True)


# ── I-Frames ────────────────────────────────────────────────────────────────

class TestRollIFrames:

    def test_roll_grants_iframes(self):
        """Starting a roll should set immune_t >= ROLL_IFRAME."""
        p = Player()
        p.facing = 1
        p.start_roll()
        assert p.rolling is True
        assert p.immune_t >= ROLL_IFRAME

    def test_iframes_prevent_damage(self):
        """Player cannot lose a life during i-frames from roll."""
        p = Player()
        initial_lives = p.lives
        p.start_roll()
        # Immediately try to hit — should be immune
        p.hit()
        assert p.lives == initial_lives

    def test_iframes_expire_after_duration(self):
        """After ROLL_IFRAME seconds the immunity from the roll wears off."""
        p = Player()
        p.start_roll()
        # Advance past i-frame window but still within roll
        dt = ROLL_IFRAME + 0.01
        p.update(dt, NEUTRAL_KEYS)
        assert p.immune_t <= 0
        # Now a hit should connect
        initial_lives = p.lives
        p.hit()
        assert p.lives == initial_lives - 1

    def test_roll_does_not_override_longer_immunity(self):
        """If player already has longer immunity (e.g. stun), roll keeps the max."""
        p = Player()
        p.immune_t = 5.0  # e.g. stun immunity
        p.start_roll()
        assert p.immune_t == 5.0  # should keep the longer one


# ── Cooldown ─────────────────────────────────────────────────────────────────

class TestRollCooldown:

    def test_cooldown_prevents_spam(self):
        """Cannot roll again while cooldown is active."""
        p = Player()
        p.start_roll()
        # Finish the roll
        p.update(ROLL_DURATION + 0.01, NEUTRAL_KEYS)
        assert p.rolling is False
        assert p.roll_cd > 0
        # Try to roll again — should fail
        p.start_roll()
        assert p.rolling is False

    def test_cooldown_allows_roll_after_expiry(self):
        """After cooldown expires, player can roll again."""
        p = Player()
        p.start_roll()
        # Finish roll + full cooldown
        p.update(ROLL_DURATION + 0.01, NEUTRAL_KEYS)
        p.update(ROLL_COOLDOWN + 0.01, NEUTRAL_KEYS)
        assert p.roll_cd <= 0
        p.start_roll()
        assert p.rolling is True

    def test_cooldown_value_is_correct(self):
        """After roll ends, roll_cd should be set to ROLL_COOLDOWN (minus any leftover dt)."""
        p = Player()
        p.start_roll()
        overshoot = 0.01
        p.update(ROLL_DURATION + overshoot, NEUTRAL_KEYS)
        # Cooldown starts at ROLL_COOLDOWN but the leftover dt is ticked off
        assert p.roll_cd > 0
        assert p.roll_cd <= ROLL_COOLDOWN

    def test_cannot_roll_while_stunned(self):
        """Player cannot start a roll while stunned."""
        p = Player()
        p.stun_t = 2.0  # simulate being stunned
        p.start_roll()
        assert p.rolling is False


# ── Speed ────────────────────────────────────────────────────────────────────

class TestRollSpeed:

    def test_roll_speed_multiplied(self):
        """During roll the player moves at ROLL_SPEED_MULT * normal speed."""
        p = Player()
        start_x = float(p.x)
        p.facing = 1
        p.start_roll()

        dt = 0.1  # 100 ms
        p.update(dt, NEUTRAL_KEYS)

        expected_dx = PLAYER_SPD * ROLL_SPEED_MULT * dt
        actual_dx = p.x - start_x
        # Allow small floating-point tolerance and clamping tolerance
        assert abs(actual_dx - expected_dx) < 2.0, (
            f"Expected ~{expected_dx:.1f}px movement, got {actual_dx:.1f}px"
        )

    def test_roll_direction_locked(self):
        """Roll direction is locked at start — holding opposite key has no effect."""
        p = Player()
        p.facing = -1  # face left
        p.start_roll()
        assert p.roll_dir == -1

        start_x = float(p.x)
        # Hold RIGHT during roll — should still move left
        p.update(0.1, RIGHT_KEYS)
        assert p.x < start_x

    def test_roll_respects_boundaries(self):
        """Player cannot roll off-screen."""
        p = Player()
        p.x = p.PW // 2 + 5  # near left edge
        p.facing = -1
        p.start_roll()
        p.update(ROLL_DURATION, NEUTRAL_KEYS)
        assert p.x >= p.PW // 2

    def test_roll_ends_after_duration(self):
        """Roll state resets after ROLL_DURATION seconds."""
        p = Player()
        p.start_roll()
        assert p.rolling is True
        p.update(ROLL_DURATION + 0.01, NEUTRAL_KEYS)
        assert p.rolling is False
        assert p.roll_t == 0.0
