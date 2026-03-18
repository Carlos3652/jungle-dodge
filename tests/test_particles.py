"""
Tests for particles.py (task jd-04).

Four tests per spec:
  1. test_particles_respect_max_cap
  2. test_dead_particles_return_to_pool
  3. test_pool_reuse_resets_state
  4. test_emit_respects_budget
"""

import pygame
import pytest

# pygame must be initialised before importing particles (needs font/display)
pygame.init()
pygame.display.set_mode((1, 1))

from particles import Particle, ParticleSystem, MAX_PARTICLES


class TestParticleSystem:
    """ParticleSystem pool and budget behaviour."""

    def test_particles_respect_max_cap(self):
        """Emitting beyond MAX_PARTICLES never exceeds the cap."""
        ps = ParticleSystem(max_particles=20)
        # Try to emit 30 particles — should cap at 20
        emitted = ps.emit(100, 100, count=30, lifetime=5.0, speed_range=(10, 20))
        assert emitted == 20
        assert ps.active_count == 20
        # Another emit should return 0 (budget exhausted)
        emitted2 = ps.emit(100, 100, count=5, lifetime=5.0)
        assert emitted2 == 0
        assert ps.active_count == 20

    def test_dead_particles_return_to_pool(self):
        """After lifetime expires, particles go back to the pool."""
        ps = ParticleSystem(max_particles=10)
        ps.emit(0, 0, count=5, lifetime=0.1)
        assert ps.active_count == 5
        assert ps.pool_count == 5

        # Advance past lifetime
        ps.update(0.2)

        assert ps.active_count == 0
        assert ps.pool_count == 10  # all returned

    def test_pool_reuse_resets_state(self):
        """Reused particles have fresh state (age=0, alive=True, cleared velocity)."""
        ps = ParticleSystem(max_particles=5)

        # Emit with specific velocity, let them die
        ps.emit(50, 50, count=3, lifetime=0.05, vy=-100.0, color=(255, 0, 0))
        ps.update(0.1)  # all dead
        assert ps.pool_count == 5

        # Re-emit — particles should have fresh state
        ps.emit(200, 200, count=2, lifetime=1.0, vy=0.0, color=(0, 255, 0))
        assert ps.active_count == 2

        for p in ps._active:
            assert p.age == 0.0
            assert p.alive is True
            assert p.x == 200.0
            assert p.y == 200.0
            assert p.color == (0, 255, 0)
            assert p.lifetime == 1.0

    def test_emit_respects_budget(self):
        """When pool is partially depleted, emit returns only what's available."""
        ps = ParticleSystem(max_particles=8)

        # Use 6 of 8
        first = ps.emit(0, 0, count=6, lifetime=10.0)
        assert first == 6
        assert ps.pool_count == 2

        # Try to emit 5 more — only 2 available
        second = ps.emit(0, 0, count=5, lifetime=10.0)
        assert second == 2
        assert ps.active_count == 8
        assert ps.pool_count == 0

    def test_emitted_particles_alpha_normalised(self):
        """All emitted particles must have alpha in [0.0, 1.0]."""
        ps = ParticleSystem(max_particles=20)
        ps.emit(
            100, 100,
            count=10,
            lifetime=1.0,
            speed_range=(10, 50),
            alpha=1.0,
            alpha_end=0.0,
        )
        for p in ps._active:
            assert 0.0 <= p.alpha <= 1.0, (
                f"Particle alpha {p.alpha} outside normalised range [0.0, 1.0]"
            )

