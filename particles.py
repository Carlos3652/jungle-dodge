"""
Particle system with object pooling (task jd-04).

Provides a Particle dataclass and ParticleSystem manager class.
Pre-allocated pool of 400 particles, alpha scratch surface for batched draws.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame

from constants import W, H, S, SY, F_MED

# ── Budget ───────────────────────────────────────────────────────────────────
MAX_PARTICLES = 400


# ── Particle dataclass ──────────────────────────────────────────────────────
@dataclass
class Particle:
    """Single particle with physics, visual, and lifetime state."""

    # Position / velocity / acceleration
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    drag: float = 0.0

    # Visual
    size: float = 4.0
    size_end: float = 0.0
    color: Tuple[int, int, int] = (255, 255, 255)
    alpha: float = 1.0
    alpha_end: float = 0.0
    rotation: float = 0.0
    rot_speed: float = 0.0
    shape: str = "circle"  # 'circle', 'rect', 'star', 'trail'

    # Text (for score pops / labels — optional)
    text: Optional[str] = None
    _text_surf: Optional[pygame.Surface] = None

    # Lifetime
    lifetime: float = 1.0
    age: float = 0.0

    # Pool management
    alive: bool = False

    def reset(
        self,
        x: float = 0.0,
        y: float = 0.0,
        vx: float = 0.0,
        vy: float = 0.0,
        ax: float = 0.0,
        ay: float = 0.0,
        drag: float = 0.0,
        size: float = 4.0,
        size_end: float = 0.0,
        color: Tuple[int, int, int] = (255, 255, 255),
        alpha: float = 1.0,
        alpha_end: float = 0.0,
        rotation: float = 0.0,
        rot_speed: float = 0.0,
        shape: str = "circle",
        text: Optional[str] = None,
        lifetime: float = 1.0,
    ) -> "Particle":
        """Re-initialise a pooled particle for reuse."""
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.ax = ax
        self.ay = ay
        self.drag = drag
        self.size = size
        self.size_end = size_end
        self.color = color
        self.alpha = alpha
        self.alpha_end = alpha_end
        self.rotation = rotation
        self.rot_speed = rot_speed
        self.shape = shape
        self.text = text
        self._text_surf = None
        self.lifetime = lifetime
        self.age = 0.0
        self.alive = True
        return self


# ── Particle configs for existing effects ────────────────────────────────────
# Each config is a dict describing how to emit a group of particles.
# Colors are placeholder keys resolved at emit-time from theme or passed directly.

PARTICLE_CONFIGS: Dict[str, dict] = {
    "hit": {
        "count": 18,
        "lifetime_range": (0.25, 0.7),
        "speed_range": (200, 600),
        "size": 6.0,
        "size_end": 1.0,
        "alpha": 1.0,
        "alpha_end": 0.0,
        "shape": "circle",
        "spread": 360,  # full radial
        "gravity": 800.0,
        "drag": 0.0,
    },
    "dodge_score_pop": {
        "count": 1,
        "lifetime": 1.1,
        "vy": -55 * SY,
        "size": 0,  # text particle, size unused
        "alpha": 1.0,
        "alpha_end": 0.0,
        "shape": "circle",
        "is_text": True,
    },
    "hit_text": {
        "count": 1,
        "lifetime": 1.1,
        "vy": -55 * SY,
        "size": 0,
        "alpha": 1.0,
        "alpha_end": 0.0,
        "shape": "circle",
        "is_text": True,
    },
}


# ── ParticleSystem ──────────────────────────────────────────────────────────
class ParticleSystem:
    """Manages a pre-allocated pool of particles with emit/update/draw."""

    def __init__(self, max_particles: int = MAX_PARTICLES) -> None:
        self.max_particles = max_particles
        # Pre-allocate pool
        self._pool: List[Particle] = [Particle() for _ in range(max_particles)]
        self._active: List[Particle] = []
        self._alpha_scratch: Optional[pygame.Surface] = None

    # ── Alpha scratch surface (per-instance) ─────────────────────────────

    def _get_scratch(self) -> pygame.Surface:
        """Lazy-init the scratch surface (needs pygame display to exist)."""
        if self._alpha_scratch is None:
            self._alpha_scratch = pygame.Surface((W, H), pygame.SRCALPHA)
        return self._alpha_scratch

    # ── Pool management ─────────────────────────────────────────────────────

    def _get_from_pool(self) -> Optional[Particle]:
        """Get a dead particle from the pool, or None if budget exhausted."""
        if self._pool:
            return self._pool.pop()
        return None

    def _return_to_pool(self, p: Particle) -> None:
        """Return a dead particle to the pool for reuse."""
        p.alive = False
        self._pool.append(p)

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def pool_count(self) -> int:
        return len(self._pool)

    # ── Emit ────────────────────────────────────────────────────────────────

    def emit(
        self,
        x: float,
        y: float,
        config_name: Optional[str] = None,
        *,
        text: Optional[str] = None,
        color: Tuple[int, int, int] = (255, 255, 255),
        count: Optional[int] = None,
        lifetime: Optional[float] = None,
        vx: float = 0.0,
        vy: float = 0.0,
        speed_range: Optional[Tuple[float, float]] = None,
        spread: float = 360.0,
        gravity: float = 0.0,
        drag: float = 0.0,
        size: float = 4.0,
        size_end: float = 0.0,
        alpha: float = 1.0,
        alpha_end: float = 0.0,
        shape: str = "circle",
    ) -> int:
        """Emit particles. Returns number actually emitted (may be < count if budget hit).

        If config_name is provided, loads defaults from PARTICLE_CONFIGS and
        overrides with any explicit keyword arguments.
        """
        cfg = {}
        if config_name and config_name in PARTICLE_CONFIGS:
            cfg = PARTICLE_CONFIGS[config_name].copy()

        n = count if count is not None else cfg.get("count", 1)
        is_text = cfg.get("is_text", False)

        emitted = 0
        for _ in range(n):
            p = self._get_from_pool()
            if p is None:
                break  # budget exhausted

            lt = lifetime
            if lt is None:
                lr = cfg.get("lifetime_range")
                if lr:
                    lt = random.uniform(lr[0], lr[1])
                else:
                    lt = cfg.get("lifetime", 1.0)

            p_vx = vx
            p_vy = vy if vy != 0.0 else cfg.get("vy", 0.0)
            p_ax = 0.0
            p_ay = gravity if gravity != 0.0 else cfg.get("gravity", 0.0)
            p_drag = drag if drag != 0.0 else cfg.get("drag", 0.0)
            p_size = size if size != 4.0 else cfg.get("size", 4.0)
            p_size_end = size_end if size_end != 0.0 else cfg.get("size_end", 0.0)
            p_alpha = alpha if alpha != 1.0 else cfg.get("alpha", 1.0)
            p_alpha_end = alpha_end if alpha_end != 0.0 else cfg.get("alpha_end", 0.0)
            p_shape = shape if shape != "circle" else cfg.get("shape", "circle")

            # For radial burst particles, compute random direction
            sr = speed_range or cfg.get("speed_range")
            if sr and not is_text:
                spd = random.uniform(sr[0], sr[1])
                angle = random.uniform(0, 2 * math.pi)
                p_vx = math.cos(angle) * spd
                p_vy = math.sin(angle) * spd

            p.reset(
                x=x,
                y=y,
                vx=p_vx,
                vy=p_vy,
                ax=p_ax,
                ay=p_ay,
                drag=p_drag,
                size=p_size,
                size_end=p_size_end,
                color=color,
                alpha=p_alpha,
                alpha_end=p_alpha_end,
                shape=p_shape,
                text=text if is_text else None,
                lifetime=lt,
            )
            self._active.append(p)
            emitted += 1

        return emitted

    # ── Convenience emitters matching old _pop() interface ──────────────────

    def pop_text(
        self,
        x: float,
        y: float,
        text: str,
        color: Tuple[int, int, int],
    ) -> None:
        """Emit a single floating text particle (backwards compat with old _pop)."""
        self.emit(
            x,
            y,
            text=text,
            color=color,
            count=1,
            lifetime=1.1,
            vy=float(int(-55 * SY)),
            shape="circle",
            alpha=1.0,
            alpha_end=0.0,
            size=0,
        )
        # Mark last emitted as text
        if self._active:
            self._active[-1].text = text

    # ── Update ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """Advance all active particles, return dead ones to pool."""
        still_alive: List[Particle] = []
        for p in self._active:
            p.age += dt
            if p.age >= p.lifetime:
                self._return_to_pool(p)
                continue

            # Physics
            p.vx += p.ax * dt
            p.vy += p.ay * dt
            if p.drag > 0:
                factor = max(0.0, 1.0 - p.drag * dt)
                p.vx *= factor
                p.vy *= factor
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rotation += p.rot_speed * dt

            still_alive.append(p)
        self._active = still_alive

    # ── Draw ────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        """Render all active particles onto *surface*."""
        for p in self._active:
            t = p.age / p.lifetime if p.lifetime > 0 else 1.0
            # Interpolate alpha
            a = p.alpha + (p.alpha_end - p.alpha) * t
            if a < 0.02:
                continue

            # Text particles (score pops, labels)
            if p.text is not None:
                if p._text_surf is None:
                    p._text_surf = F_MED.render(p.text, True, p.color)
                surf = p._text_surf
                surf.set_alpha(int(a * 255))
                surface.blit(
                    surf,
                    (int(p.x) - surf.get_width() // 2, int(p.y)),
                )
                continue

            # Shape particles
            cur_size = p.size + (p.size_end - p.size) * t
            if cur_size < 0.5:
                continue

            r, g, b = p.color
            alpha_int = int(a * 255)

            if p.shape == "circle":
                scratch = self._get_scratch()
                pygame.draw.circle(
                    scratch,
                    (r, g, b, alpha_int),
                    (int(p.x), int(p.y)),
                    max(1, int(cur_size)),
                )
            elif p.shape == "rect":
                scratch = self._get_scratch()
                half = max(1, int(cur_size))
                pygame.draw.rect(
                    scratch,
                    (r, g, b, alpha_int),
                    (int(p.x) - half, int(p.y) - half, half * 2, half * 2),
                )
            elif p.shape == "star":
                scratch = self._get_scratch()
                self._draw_star(scratch, p.x, p.y, cur_size, (r, g, b, alpha_int), p.rotation)
            elif p.shape == "trail":
                scratch = self._get_scratch()
                half = max(1, int(cur_size))
                pygame.draw.rect(
                    scratch,
                    (r, g, b, alpha_int),
                    (int(p.x) - half * 2, int(p.y) - half // 2, half * 4, half),
                )

        # Blit scratch and clear it
        if self._alpha_scratch is not None:
            surface.blit(self._alpha_scratch, (0, 0))
            self._alpha_scratch.fill((0, 0, 0, 0))

    @staticmethod
    def _draw_star(
        surface: pygame.Surface,
        cx: float,
        cy: float,
        size: float,
        color: Tuple[int, int, int, int],
        rotation: float,
    ) -> None:
        """Draw a simple 4-point star."""
        pts = []
        for i in range(8):
            angle = rotation + i * math.pi / 4
            r = size if i % 2 == 0 else size * 0.4
            pts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
        if len(pts) >= 3:
            pygame.draw.polygon(surface, color, [(int(x), int(y)) for x, y in pts])

    # ── Cleanup ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Return all active particles to pool (e.g. on level reset)."""
        for p in self._active:
            p.alive = False
            self._pool.append(p)
        self._active.clear()
