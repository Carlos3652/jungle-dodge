# Jungle Dodge

A side-scrolling dodge game built with Pygame at 4K internal resolution (3840x2160).

## Overview

Jungle Dodge is a fast-paced side-scroller where players dodge obstacles, collect power-ups, and chase high scores across multiple themed environments. The game features a streak multiplier system, boss waves, difficulty selection, dual themes (Jungle and Space), and a modular state-machine architecture.

## Tech Stack

- **Language:** Python 3
- **Framework:** Pygame
- **Resolution:** 4K internal (3840x2160), scaled to display via offscreen surface
- **Architecture:** State machine pattern with modular entity/particle/HUD systems
- **Tests:** pytest (496+ tests across 20+ test files)

## Prerequisites

- Python 3.10+
- Pygame

## Installation and Running

```bash
pip install pygame

# Run the game
python main.py
```

The game launches in fullscreen mode at your display resolution, with internal rendering at 3840x2160 scaled to fit.

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / A-D | Move left/right |
| SPACE | Side roll (with i-frames) / Start / Restart |
| ESC | Pause / Quit |

## Current Status

**Overhaul in progress** via Subagent-Driven Development (SDD). Waves 1-3a complete (10 tasks done), approximately 40 remaining in backlog.

## Completed Features

### Core Gameplay
- Side roll dodge mechanic (SPACE key) with invincibility frames
- Streak multiplier system (1x to 3x)
- Near-miss scoring (+5 bonus with "CLOSE!" particle)
- Wave rhythm system for obstacle pacing

### Obstacles
- 9 base obstacle types (VineSnap, BombDelay, ClusterSpike, BouncingSpike, SplitBoulder, CanopyDrop, CrocSnap, PoisonPuddle, ScreechBat, GroundHazard)
- 5 obstacle variants with unique behaviors
- Boss waves every 5 levels (L5, L10, L15 + mini-bosses)
- Level 10+ personality upgrades for increased difficulty

### Power-ups
- Shield, Slow-Mo, and Magnet power-ups
- HUD pill indicator for active power-ups

### Themes
- **Jungle** (default) -- Refreshed parallax layers, warmer palette, ground fog
- **Space** -- Full 95-key implementation with distinct visuals

### Settings and Progression
- Difficulty selector (Easy, Normal, Hard) with persistence
- Per-difficulty leaderboards
- Audio system wired (asset integration pending)

## What's Next

- **Wave 3b-3c:** Combo patterns (jd-16), theme selection UX (jd-20)
- **Wave 4:** HUD redesign (jd-21), start screen (jd-22), game over reveal (jd-23)
- **Waves 5-10:** Progression, audio assets, juice/polish, transitions, style fixes

## Project Structure

```
jungle-dodge/
  main.py              -- Entry point (~50 lines)
  constants.py         -- Shared constants (resolution, scale factors, colors)
  entities.py          -- Player, obstacles, and game entity classes
  states.py            -- Game state machine (StartScreen, Playing, Paused, GameOver)
  hud.py               -- HUD rendering and caching
  particles.py         -- Particle system
  themes.py            -- Theme definitions (Jungle, Space) with get_color() API
  audio.py             -- Audio manager (singleton)
  persistence.py       -- Save/load (leaderboards, settings)
  boss_data.py         -- Boss wave definitions
  combo_patterns.py    -- Combo pattern system
  assets/              -- Game assets (sprites, etc.)
  tests/               -- 20+ test modules (496+ tests)
    test_entities.py
    test_states.py
    test_boss_waves.py
    test_powerups.py
    test_obstacle_variants.py
    test_new_obstacles.py
    test_near_miss.py
    test_difficulty.py
    test_space_theme.py
    test_jungle_theme_refresh.py
    test_theme_migration.py
    ...
  docs/superpowers/    -- Design specs and implementation plans
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Render Architecture

The game renders to an offscreen surface at 3840x2160, then scales to the display:

- `screen = pygame.Surface((W, H))` -- offscreen render target
- `_present()` scales to display surface
- Scale factors: `SX = W/900`, `SY = H/600`, `S = SY`

## License

All rights reserved.
