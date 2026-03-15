# Jungle Dodge Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Jungle Dodge from a 1387-line monolith into a modular, polished, dual-themed dodge game with deep gameplay, audio, and portfolio-quality juice.

**Architecture:** Refactor monolithic `jungle_dodge.py` into 9 modules (constants, themes, persistence, particles, audio, entities, hud, states, main). Stack-based state machine. THEMES dict drives all visual theming. AudioManager singleton for layered music + SFX.

**Tech Stack:** Python 3, Pygame 2, JSON persistence, Bfxr/BeepBox for audio asset creation.

**Spec:** `docs/superpowers/specs/2026-03-15-jungle-dodge-overhaul-design.md`

---

## Phase Overview

| Phase | Name | Tasks | Priority | Dependency |
|-------|------|-------|----------|------------|
| 1 | Foundation Refactor | jd-01 to jd-06 | P0 | None |
| 2 | Core Gameplay | jd-07 to jd-12 | P0 | Phase 1 |
| 3 | Obstacles & Bosses | jd-13 to jd-17 | P1 | Phase 2 |
| 4 | Dual Themes | jd-18 to jd-20 | P1 | Phase 1 |
| 5 | UI Overhaul | jd-21 to jd-27 | P1 | Phases 2, 4 |
| 6 | Progression & Scoring | jd-28 to jd-30 | P2 | Phases 2, 5 |
| 7 | Audio | jd-31 to jd-33 | P2 | Phase 1 |
| 8 | Juice & Feel | jd-34 to jd-39 | P2 | Phases 2, 4 |
| 9 | Polish & Delight | jd-40 to jd-42 | P3 | All above |

---

## File Structure

```
jungle_dodge/
├── main.py              # Entry point (~30 lines)
├── constants.py          # W, H, SX, SY, S, FPS, GROUND_Y, all timing/speed constants
├── themes.py             # THEMES dict, get_theme(), get_color()
├── persistence.py        # PersistenceManager: settings, leaderboard, daily challenge
├── particles.py          # Particle dataclass, ParticleSystem (400 pool), emitter configs
├── audio.py              # AudioManager singleton, 12 channels, stem crossfading
├── entities.py           # Player (roll, streak, shield), Obstacle base + 8 subclasses
├── hud.py                # All draw_* functions for HUD, overlays, screen effects
├── states.py             # GameStateManager, GameContext, 13 State subclasses
├── tests/
│   ├── test_persistence.py
│   ├── test_particles.py
│   ├── test_themes.py
│   ├── test_entities.py
│   └── test_states.py
└── assets/
    └── sounds/
        ├── CREDITS.txt
        ├── music/         # {theme}_stem_{0-3}.ogg
        └── sfx/           # {event}.wav
```

---

## Phase 1: Foundation Refactor

The monolith must be split before any new features. Each task extracts one module. The game must remain playable after every task.

### Task jd-01: Extract constants.py

**Files:**
- Create: `jungle_dodge/constants.py`
- Modify: `jungle_dodge/jungle_dodge.py`

- [ ] Extract all module-level constants from `jungle_dodge.py` into `constants.py`: W, H, SX, SY, S, FPS, GROUND_Y, PLAYER_FLOOR, DODGE_PTS, font definitions, color dict CLR, timing values (STUN_DUR, GRACE_DUR, LEVEL_DUR, etc.), obstacle speed/weight constants.
- [ ] Replace all references in `jungle_dodge.py` with imports from `constants`.
- [ ] Verify game runs: `python jungle_dodge.py` — start, play L1, die, leaderboard all work.
- [ ] Commit: `git commit -m "refactor: extract constants.py from monolith"`

### Task jd-02: Extract themes.py + migrate CLR dict

**Files:**
- Create: `jungle_dodge/themes.py`
- Create: `jungle_dodge/tests/test_themes.py`
- Modify: `jungle_dodge/constants.py`

- [ ] Create `themes.py` with full THEMES dict (jungle theme only initially). Populate all ~95 keys from spec Section 5.5 + Appendix, using current CLR values as the jungle theme colors.
- [ ] Add `get_theme()`, `get_color()` with magenta fallback, `list_themes()`.
- [ ] Write `test_themes.py`: `test_all_themes_have_required_keys()`, `test_get_color_magenta_fallback()`, `test_get_theme_returns_jungle_default()`.
- [ ] Run tests: `pytest tests/test_themes.py -v` — all pass.
- [ ] For now, keep CLR dict in constants.py as backward compat — will remove when draw functions migrate to theme dict.
- [ ] Verify game still runs.
- [ ] Commit: `git commit -m "refactor: add themes.py with jungle theme dict + tests"`

### Task jd-03: Extract persistence.py

**Files:**
- Create: `jungle_dodge/persistence.py`
- Create: `jungle_dodge/tests/test_persistence.py`
- Modify: `jungle_dodge/jungle_dodge.py`

- [ ] Create `PersistenceManager` class with: `load_settings()`, `save_settings()`, `load_leaderboard()`, `submit_score()`, `load_daily_challenge()`, `save_daily_challenge()`.
- [ ] Implement `_load_with_defaults()` and `_migrate()` for corrupt file handling.
- [ ] Define `DEFAULT_SETTINGS` and `DEFAULT_LEADERBOARD` schemas per spec Section 9.4.
- [ ] Write `test_persistence.py`: `test_submit_score_returns_correct_rank()`, `test_submit_score_caps_at_10()`, `test_load_missing_file_returns_defaults()`, `test_migrate_adds_missing_keys()`, `test_daily_challenge_regenerates_on_new_date()`, `test_personal_best_survives_leaderboard_reset()`.
- [ ] Run tests: `pytest tests/test_persistence.py -v` — all pass.
- [ ] Replace existing leaderboard load/save in monolith with PersistenceManager calls.
- [ ] Migrate existing `leaderboard.json` data into new schema (map to "normal" difficulty board).
- [ ] Verify game runs: leaderboard loads old scores, new scores save correctly.
- [ ] Commit: `git commit -m "refactor: extract persistence.py with leaderboard migration + tests"`

### Task jd-04: Extract particles.py

**Files:**
- Create: `jungle_dodge/particles.py`
- Create: `jungle_dodge/tests/test_particles.py`
- Modify: `jungle_dodge/jungle_dodge.py`

- [ ] Create `Particle` dataclass with fields per spec Section 8.1.
- [ ] Create `ParticleSystem` class: `emit()`, `update()`, `draw()`, `_get_from_pool()`. 400 cap, pre-allocated pool.
- [ ] Create `_ALPHA_SCRATCH` surface for batched alpha-blended draws.
- [ ] Define `PARTICLE_CONFIGS` dict for existing effects (hit, dodge score pop) — will expand later.
- [ ] Write `test_particles.py`: `test_particles_respect_max_cap()`, `test_dead_particles_return_to_pool()`, `test_pool_reuse_resets_state()`, `test_emit_respects_budget()`.
- [ ] Run tests — all pass.
- [ ] Replace existing particle dict system in monolith with ParticleSystem.
- [ ] Verify game runs: +10 score pops and OUCH! text still appear.
- [ ] Commit: `git commit -m "refactor: extract particles.py with object pooling + tests"`

### Task jd-05: Extract audio.py (stub)

**Files:**
- Create: `jungle_dodge/audio.py`
- Create: `jungle_dodge/tests/test_audio.py`
- Create: `jungle_dodge/assets/sounds/sfx/` (empty dir)
- Create: `jungle_dodge/assets/sounds/music/` (empty dir)

- [ ] Create `AudioManager` singleton with: `play()`, `set_stem_layers()`, `set_volumes()`, `update()`, `load_all()`, `load_stems()`.
- [ ] All methods are graceful no-ops when sound files don't exist (game runs silently).
- [ ] Define `CHANNEL_MAP` dict (12 channels per spec Section 7.3).
- [ ] Write `test_audio.py`: `test_play_does_nothing_when_muted()`, `test_play_does_nothing_for_unknown_sfx()`, `test_singleton_returns_same_instance()`.
- [ ] Run tests — all pass.
- [ ] Commit: `git commit -m "refactor: add audio.py stub with graceful no-op fallbacks + tests"`

### Task jd-06: Extract states.py + entities.py + hud.py + main.py

**Files:**
- Create: `jungle_dodge/states.py`
- Create: `jungle_dodge/entities.py`
- Create: `jungle_dodge/hud.py`
- Create: `jungle_dodge/main.py`
- Create: `jungle_dodge/tests/test_states.py`
- Delete (after verification): `jungle_dodge/jungle_dodge.py` (or rename to `_old.py`)

This is the big extraction. Do it in sub-steps:

- [ ] **6a: entities.py** — Extract `Player`, `Obstacle`, `Vine`, `Bomb`, `Spike`, `Boulder` classes. Keep existing behavior unchanged. Import constants, themes. Add `context` parameter to constructors for theme/audio access.
- [ ] **6b: hud.py** — Extract all `draw_*` functions: `draw_hud()`, `draw_start_screen()`, `draw_pause()`, `draw_levelup()`, `draw_name_entry()`, `draw_leaderboard()`, `draw_gameover()`, `draw_background()`. Each receives `surface`, `theme`, and relevant state data as arguments.
- [ ] **6c: states.py** — Create `State` base class, `GameStateManager` (stack-based), `GameContext` dataclass. Create initial states: `StartScreenState`, `PlayState`, `PauseState`, `LevelUpState`, `GameOverState`, `NameEntryState`, `LeaderboardState`. Each state has `enter()`, `exit()`, `handle_event()`, `update()`, `draw()`.
- [ ] **6d: main.py** — ~30 line entry point: init pygame, create AudioManager, PersistenceManager, GameStateManager, push StartScreenState, run loop.
- [ ] Write `test_states.py`: `test_push_calls_enter()`, `test_pop_calls_exit()`, `test_stack_empty_exits_run()`, `test_dt_capped_at_50ms()`.
- [ ] Run tests — all pass.
- [ ] Run game via `python main.py` — full game loop works: start → play → die → leaderboard → restart.
- [ ] Delete or rename `jungle_dodge.py`.
- [ ] Commit: `git commit -m "refactor: complete modular extraction — 9 files, state machine, game runs"`

---

## Phase 2: Core Gameplay

### Task jd-07: Side roll mechanic

**Files:**
- Modify: `jungle_dodge/entities.py` (Player class)
- Modify: `jungle_dodge/constants.py` (ROLL_DURATION, ROLL_SPEED_MULT, ROLL_IFRAME, ROLL_COOLDOWN)
- Create: `jungle_dodge/tests/test_entities.py`

- [ ] Add to Player: `rolling`, `roll_t`, `roll_cd`, `roll_dir` fields.
- [ ] Implement `start_roll()`: sets rolling=True, roll_t=0.4, roll_dir from last input, grants immune_t=0.25.
- [ ] Implement roll update: 2.5x speed during roll, cooldown tracking, radial cooldown arc drawing.
- [ ] Roll animation: 45-degree tilt, Y-scale 0.85, trail particles from ParticleSystem.
- [ ] Handle SPACE input in PlayState.handle_event() — trigger roll if cooldown ready.
- [ ] Write tests: `test_roll_grants_iframes()`, `test_roll_cooldown_prevents_spam()`, `test_roll_speed_multiplied()`.
- [ ] Verify in-game: SPACE rolls, i-frames work, cooldown shows, animation plays.
- [ ] Commit: `git commit -m "feat: add side roll mechanic with i-frames and cooldown"`

### Task jd-08: Streak combo multiplier

**Files:**
- Modify: `jungle_dodge/entities.py` or `jungle_dodge/states.py` (PlayState)
- Modify: `jungle_dodge/constants.py`

- [ ] Add streak tracking: `self.streak = 0` on PlayState or GameContext.
- [ ] On dodge (existing scored path): increment streak, calculate multiplier tier (1x/1.5x/2x/3x).
- [ ] Apply multiplier to dodge points: `pts = int(DODGE_PTS * multiplier)`.
- [ ] On hit: if streak ≥ 5, emit "STREAK LOST" particle. Reset streak to 0.
- [ ] Add streak badge to HUD (right of score): bronze/silver/gold pill, pulse at 3x.
- [ ] Write tests: `test_streak_increments_on_dodge()`, `test_multiplier_tiers()`, `test_streak_resets_on_hit()`.
- [ ] Verify in-game: dodge 5+ in a row, see badge, get hit, see reset.
- [ ] Commit: `git commit -m "feat: add streak combo multiplier (1x→3x)"`

### Task jd-09: Wave rhythm system

**Files:**
- Modify: `jungle_dodge/states.py` (PlayState)
- Modify: `jungle_dodge/constants.py`

- [ ] Add `_get_spawn_interval_modifier(level_t)` that returns float multiplier based on wave phase per spec Section 2.4.
- [ ] Apply modifier to existing spawn timer in PlayState.update().
- [ ] Crescendo (39–44s): spawn 2 obstacles simultaneously with W*0.5 separation.
- [ ] Add wave phase bar to HUD (full width, 12px above panels). Color from theme dict.
- [ ] Verify in-game: feel push/breather rhythm, see crescendo dual-spawns.
- [ ] Commit: `git commit -m "feat: add wave rhythm system (push/breather/crescendo)"`

### Task jd-10: Near-miss scoring

**Files:**
- Modify: `jungle_dodge/entities.py` (Obstacle base)
- Modify: `jungle_dodge/states.py` (PlayState)

- [ ] In obstacle update/scoring path: check distance to player when obstacle passes GROUND_Y.
- [ ] If distance < 40px (base res) and obstacle didn't hit: award +5 near-miss bonus, emit "CLOSE!" particle.
- [ ] Track `near_misses` counter in run stats.
- [ ] Write test: `test_near_miss_awards_bonus_within_threshold()`.
- [ ] Verify in-game: stand close to falling obstacle, see CLOSE! and +15 (10+5).
- [ ] Commit: `git commit -m "feat: add near-miss scoring (+5 bonus + CLOSE! particle)"`

### Task jd-11: Difficulty selector

**Files:**
- Modify: `jungle_dodge/states.py` (StartScreenState)
- Modify: `jungle_dodge/persistence.py`
- Modify: `jungle_dodge/constants.py`

- [ ] Add difficulty row to start screen: Easy (4 lives, 0.85x scaling) | Normal (3, 1.0x) | Hard (2, 1.15x).
- [ ] UP/DOWN or 1/2/3 keys to select. Selection persists to settings.json.
- [ ] PlayState reads difficulty from context, applies lives + scaling modifier.
- [ ] PersistenceManager: leaderboard loads correct difficulty board.
- [ ] Show per-difficulty PB on start screen below difficulty row.
- [ ] First run: force Easy, show "We'll start you here."
- [ ] Verify: select Hard, play with 2 lives, score saves to hard board.
- [ ] Commit: `git commit -m "feat: add difficulty selector (Easy/Normal/Hard) with per-difficulty leaderboards"`

### Task jd-12: Power-up system (shield, slow-mo, magnet)

**Files:**
- Create: `jungle_dodge/powerups.py` (or add to entities.py)
- Modify: `jungle_dodge/states.py` (PlayState)
- Modify: `jungle_dodge/constants.py`

- [ ] Create `PowerUp` class inheriting from Obstacle: `kind` field ("shield"/"slowmo"/"magnet"), slower fall speed (60% vine), rotating glow ring.
- [ ] Add spawn timers per power-up type in PlayState. Enforce spawn rules (no first 15s, W*0.3 separation).
- [ ] **Shield:** `player.shield_active = True`. On hit: skip life loss, shatter obstacle (12 particles), play SFX, set shield_active=False.
- [ ] **Slow-Mo:** `slowmo_factor = 0.4` applied to all obstacle vy for 5s. Player speed unchanged.
- [ ] **Magnet Score:** `magnet_active = True` for 8s. Dodge pts × 3 during window. Spawn 15pt orbs near dodged obstacles.
- [ ] Add power-up status pill to HUD right panel (only when active).
- [ ] Verify each power-up in-game.
- [ ] Commit: `git commit -m "feat: add 3 power-ups (shield, slow-mo, magnet score)"`

---

## Phase 3: Obstacles & Bosses

### Task jd-13: Existing obstacle variants

**Files:**
- Modify: `jungle_dodge/entities.py`
- Modify: `jungle_dodge/constants.py`

- [ ] **Vine snap variant (L4):** Last 200px, snap sideways 120–180px. Green→yellow telegraph.
- [ ] **Bomb delay variant (L5):** Lands, fuse 0.8s, then explodes. Ground circle pulses.
- [ ] **Bomb ground circle:** Red circle (40% alpha) at spawn showing blast radius.
- [ ] **Cluster spike (L3):** 3 spikes in triangle, 0.15s stagger.
- [ ] **Bouncing spike (L6):** Bounce 60px after ground hit.
- [ ] **Split boulder (L5):** 1.4x size, splits into 2 on ground hit.
- [ ] Add level-gated unlock logic: variants only spawn at or above their introduction level.
- [ ] Verify each variant in-game by forcing high levels.
- [ ] Commit: `git commit -m "feat: add obstacle variants (vine snap, bomb delay, cluster/bouncing spike, split boulder)"`

### Task jd-14: New obstacle types

**Files:**
- Modify: `jungle_dodge/entities.py`
- Modify: `jungle_dodge/constants.py`

- [ ] **Canopy Drop (L2):** 8–12 leaf sprites, one hidden spike revealed at 80px from ground.
- [ ] **Croc Snap (L4):** Horizontal ground sweep, 120×40px hitbox, 600px/s. 0.5s edge warning.
- [ ] **Poison Puddle (L5):** 80px radius ground hazard, 1.5s standing timer → stun. Max 2 active.
- [ ] **Screech Bat (L7):** Diving arc, 1s tracking window, lateral dodge counter.
- [ ] **Ground Hazards (L5+):** 60×120px columns rising from ground. 0.5s telegraph, 1.5–2s active.
- [ ] Add all to spawn weight tables with level-gated unlocks.
- [ ] Universal telegraph: 0.3s common, 0.5s dangerous.
- [ ] Verify each obstacle spawns at correct level, deals damage, has telegraph.
- [ ] Commit: `git commit -m "feat: add 5 new obstacle types (canopy drop, croc snap, puddle, bat, ground hazards)"`

### Task jd-15: L10+ personality upgrades

**Files:**
- Modify: `jungle_dodge/entities.py`

- [ ] Paired vines: when level ≥ 10, vine spawns trigger a second vine at offset position.
- [ ] Tracking bombs: when level ≥ 10, bomb fall has slight X bias toward player (15% per frame).
- [ ] Wobble spikes: when level ≥ 10, spike X oscillates with random-frequency sine wave during fall.
- [ ] Commit: `git commit -m "feat: add L10+ obstacle personality upgrades"`

### Task jd-16: Boss waves

**Files:**
- Modify: `jungle_dodge/states.py` (PlayState, BossIntroState)
- Modify: `jungle_dodge/constants.py`

- [ ] Define boss wave scripts as `BOSS_WAVES` dict: keyed by level (5, 10, 15). Each is list of `(delay_ms, obstacle_class, x_pct)` tuples.
- [ ] At end of L5/L10/L15: push BossIntroState (3.5s card), then switch PlayState to scripted spawn mode.
- [ ] During boss wave: read from script queue instead of random spawns.
- [ ] Boss clear: 500/750/1000 bonus pts, "BOSS DEFEATED" 2s splash, particle burst.
- [ ] L16+: mini-boss every 5 levels (random from 3 types).
- [ ] Commit: `git commit -m "feat: add boss waves at L5/L10/L15 with scripted obstacle sequences"`

### Task jd-17: Combo patterns

**Files:**
- Modify: `jungle_dodge/states.py` (PlayState)
- Modify: `jungle_dodge/constants.py`

- [ ] Define 5 named patterns: Funnel, Crossfire, Shell Game, Rolling Wave, Triple Stack.
- [ ] Each pattern: list of `(delay_ms, obstacle_class, x_pct)` tuples with specific positions.
- [ ] Insert 1 pattern per push phase at L4+, 2 at L8+.
- [ ] Track `pattern_hit` flag — if player survives full sequence without hit, award +50 "PATTERN CLEAR!" bonus.
- [ ] Commit: `git commit -m "feat: add 5 named combo patterns with pattern clear bonus"`

---

## Phase 4: Dual Themes

### Task jd-18: Jungle theme refresh

**Files:**
- Modify: `jungle_dodge/themes.py`
- Modify: `jungle_dodge/hud.py`
- Modify: `jungle_dodge/entities.py`

- [ ] Update jungle theme colors in THEMES dict per spec Section 5.2: refreshed sky gradient, richer ground, warmer character palette, updated obstacle colors.
- [ ] Update background drawing: layered parallax (far canopy, mid silhouettes, near foliage).
- [ ] Add environmental FX: falling leaf particles (8–12), ground fog surface.
- [ ] Update character drawing: warmer leather jacket, gold hat band.
- [ ] Update obstacle drawing: vines natural green, spikes bone-ivory, bombs coiled fuse.
- [ ] Verify game looks cohesive with new palette.
- [ ] Commit: `git commit -m "feat: refresh jungle theme with layered parallax and updated palette"`

### Task jd-19: Space theme

**Files:**
- Modify: `jungle_dodge/themes.py`
- Modify: `jungle_dodge/hud.py`
- Modify: `jungle_dodge/entities.py`

- [ ] Add complete "space" entry to THEMES dict with all ~95 keys per spec Section 5.3.
- [ ] Implement star field background: 200 stars, 3 size tiers, twinkle. Nebula ellipse. Distant planet. Cache to static surface.
- [ ] Implement space character draw: grey suit, cyan visor, backpack with indicator dots.
- [ ] Implement holographic HUD style: dark blue panel, cyan border.
- [ ] Map all obstacles to space variants (tether cable, proximity mine, drill shard, asteroid, etc.) using theme colors.
- [ ] Add craters to ground, regolith texture.
- [ ] Run `test_all_themes_have_required_keys()` — passes for both themes.
- [ ] Commit: `git commit -m "feat: add complete space theme with star field, astronaut character, holographic HUD"`

### Task jd-20: Theme selection UX

**Files:**
- Modify: `jungle_dodge/states.py` (StartScreenState)
- Modify: `jungle_dodge/persistence.py`

- [ ] Add two toggle panels to start screen: jungle | space. LEFT/RIGHT cycles.
- [ ] Selected: full brightness, border glow, scale 1.03, mini-preview (parallax + character + obstacle).
- [ ] Inactive: 60% brightness, scale 0.97.
- [ ] Title updates: "JUNGLE DODGE" / "SPACE DODGE".
- [ ] Space tagline: "SURVIVE. DODGE. TRANSCEND."
- [ ] Theme persists to settings.json.
- [ ] All game systems read from `context.theme` — verify full game loop in space theme.
- [ ] Leaderboard: tiny color indicator per entry (green=jungle, cyan=space).
- [ ] Commit: `git commit -m "feat: add theme selection on start screen with persistence"`

---

## Phase 5: UI Overhaul

### Task jd-21: New HUD (dual-panel)

**Files:**
- Modify: `jungle_dodge/hud.py`

- [ ] Replace stone tablet with dual-panel layout: Score+Streak (left 38%), Timer circle (center floating), Lives+Roll+Power-ups (right 38%).
- [ ] Level pill at top-center (red during boss waves).
- [ ] Score: comma-formatted, exponential approach counting animation.
- [ ] Timer: circular arc depleting clockwise. Red + pulse under 10s.
- [ ] Lives: skull icons with crack animation on loss.
- [ ] Roll pips: 3 circles, drain/refill with cooldown.
- [ ] Streak badge: bronze→silver→gold pill with pulse.
- [ ] Theme-driven: stone tablet border (jungle) vs holographic panel (space).
- [ ] Commit: `git commit -m "feat: redesign HUD with dual-panel layout, timer circle, roll pips"`

### Task jd-22: Start screen redesign

**Files:**
- Modify: `jungle_dodge/states.py` (StartScreenState)
- Modify: `jungle_dodge/hud.py`

- [ ] Layout: Title → Theme selector → Difficulty row → START/DAILY buttons → Tagline.
- [ ] Best player badge (top-right), themed frame.
- [ ] ? icon → controls overlay on press.
- [ ] Daily challenge button: "NEW"/"PLAYED" badge, greyed if done today.
- [ ] "START EASY/NORMAL/HARD RUN" updates per selection.
- [ ] Pulse animation on CTA.
- [ ] Commit: `git commit -m "feat: redesign start screen with theme picker, difficulty, daily challenge"`

### Task jd-23: Game over 3-phase reveal

**Files:**
- Modify: `jungle_dodge/states.py` (GameOverState)
- Modify: `jungle_dodge/hud.py`

- [ ] Phase 1 (0–0.5s): "GAME OVER" slam-in from top.
- [ ] Phase 2 (0.5–2.5s): Score breakdown tally (base→streak→near-miss→power-up→TOTAL). Slot-machine counter with SFX_SCORE_TICK.
- [ ] Phase 3 (2.5–4.5s): 8-stat grid + badges + near-miss badge teases + flavor text.
- [ ] Anti-quit: SPACE disabled 2.5s, "PLAY AGAIN" fades in, shows leaderboard insertion point.
- [ ] "YOU BEAT [NAME]" callout if displaced someone.
- [ ] Commit: `git commit -m "feat: add 3-phase game over reveal with score breakdown animation"`

### Task jd-24: Leaderboard overhaul

**Files:**
- Modify: `jungle_dodge/states.py` (LeaderboardState)
- Modify: `jungle_dodge/hud.py`

- [ ] 4 tabs: NORMAL | EASY | HARD | DAILY. LEFT/RIGHT or TAB cycles.
- [ ] Columns: Rank (medals 1–3), Name, Score, Level, Max Streak, Date, Theme indicator.
- [ ] Row cascade-slide animation (50ms stagger).
- [ ] Player's entry highlighted for 3s.
- [ ] Badge icons (up to 2) per entry.
- [ ] Daily tab: "RESETS IN HH:MM:SS" countdown.
- [ ] Commit: `git commit -m "feat: redesign leaderboard with 4 tabs, badges, cascade animation"`

### Task jd-25: Name entry modernize

**Files:**
- Modify: `jungle_dodge/states.py` (NameEntryState)
- Modify: `jungle_dodge/hud.py`

- [ ] Headline variants: "NEW PERSONAL BEST!" / "TOP 3 — LEGENDARY!" / "YOU MADE THE TOP 10!" / "YOU BEAT [NAME]!"
- [ ] 80×96px slots with active highlight and blinking cursor.
- [ ] Real-time rank preview: "THIS WILL PLACE YOU: #3".
- [ ] Particle burst on confirm.
- [ ] Commit: `git commit -m "feat: modernize name entry with rank preview and dynamic headlines"`

### Task jd-26: Pause + volume overlay

**Files:**
- Modify: `jungle_dodge/states.py` (PauseState, VolumeOverlayState)
- Modify: `jungle_dodge/hud.py`

- [ ] Pause: centered card, score/streak/level visible, RESUME/QUIT buttons, game visible behind at 60%.
- [ ] Volume overlay (V key): 3 sliders (Music, SFX, Master), LEFT/RIGHT adjusts 10%, UP/DOWN navigates, ESC closes.
- [ ] M key: instant mute/unmute toggle (works anytime).
- [ ] Settings persist via PersistenceManager.
- [ ] Commit: `git commit -m "feat: redesign pause screen + add volume overlay with persistence"`

### Task jd-27: Screen transitions + tutorial

**Files:**
- Modify: `jungle_dodge/states.py` (TransitionState, PlayState)
- Modify: `jungle_dodge/hud.py`

- [ ] Start→Play: vine-wipe (jungle) / star-jump (space), 0.4s.
- [ ] Play→GameOver: 0.2s freeze-frame + red flash.
- [ ] Level up: 2.0s white flash + bounce-in number + tier-appropriate subtitle.
- [ ] Boss intro: 3.5s danger-red flash + slam cut.
- [ ] All ESC transitions: fade black 0.25s + fade in 0.25s.
- [ ] Tutorial (first run): 4-step overlay in first 10s (move arrows → dodge → roll prompt → streak explanation).
- [ ] Commit: `git commit -m "feat: add themed screen transitions + first-run tutorial"`

---

## Phase 6: Progression & Scoring

### Task jd-28: Badge system

**Files:**
- Modify: `jungle_dodge/states.py` (PlayState, GameOverState)
- Modify: `jungle_dodge/persistence.py`

- [ ] Track badge conditions during run: untouchable, streaker, legend, roll master, close call, pattern clear, survivor/king/walker/endless, boss clears, lucky, power hungry.
- [ ] Evaluate badges at game over before screen renders.
- [ ] Store as string array in leaderboard entry.
- [ ] Display earned badges on game over (pop animation, max 4s).
- [ ] Display up to 2 badge icons on leaderboard (rarest first).
- [ ] Commit: `git commit -m "feat: add 15 session badges with leaderboard display"`

### Task jd-29: Personal best + one-more-run hooks

**Files:**
- Modify: `jungle_dodge/hud.py`
- Modify: `jungle_dodge/states.py` (PlayState, GameOverState)

- [ ] PB indicator in HUD (only at >80% of PB). "NEW BEST!" flash when exceeded.
- [ ] Visible gap on game over: "BEAT [NAME] BY X PTS" (delta to next leaderboard slot).
- [ ] Near-miss badge teases: show 1–2 closest unearned badges grayed with shortfall.
- [ ] "NEW DANGER AHEAD" tease at new level thresholds.
- [ ] Commit: `git commit -m "feat: add personal best indicator + one-more-run hooks"`

### Task jd-30: Daily challenge mode

**Files:**
- Modify: `jungle_dodge/states.py` (DailyChallengeState)
- Modify: `jungle_dodge/persistence.py`

- [ ] Daily seed: `int(date.strftime("%Y%m%d"))`. Seed `random.seed()` at challenge start.
- [ ] Normal difficulty only, separate leaderboard board.
- [ ] Start from main menu "DAILY CHALLENGE" button.
- [ ] "DAILY PLAYED" grey-out after completion.
- [ ] Track attempts and best_score in daily_challenge.json.
- [ ] Regenerate on new date.
- [ ] Commit: `git commit -m "feat: add daily challenge mode with seeded obstacle sequence"`

---

## Phase 7: Audio

### Task jd-31: Source + integrate Tier 1 SFX

**Files:**
- Modify: `jungle_dodge/audio.py`
- Create: `jungle_dodge/assets/sounds/sfx/*.wav` (7 files)
- Modify: `jungle_dodge/states.py`, `jungle_dodge/entities.py`

- [ ] Generate with Bfxr: player_hit, player_death, streak_x1/x2/x3, streak_break, bomb_explode, level_up, near_miss.
- [ ] Wire AudioManager.play() calls at: hit detection, streak change, bomb explode, level complete, near-miss, game over.
- [ ] `pygame.mixer.pre_init(44100, -16, 2, 512)` for low latency.
- [ ] Verify: each SFX plays at correct moment, no crashes on missing files.
- [ ] Commit: `git commit -m "feat: add Tier 1 SFX (hit, death, streak, bomb, level up, near-miss)"`

### Task jd-32: Music stems

**Files:**
- Create: `jungle_dodge/assets/sounds/music/*.ogg` (4 stems per theme)
- Modify: `jungle_dodge/audio.py`

- [ ] Compose in BeepBox: 4 stems per theme at matching BPM (jungle 96, space 128).
- [ ] Implement stem layer crossfading in AudioManager.update(): `set_stem_layers(intensity)`.
- [ ] Wire to wave phases: breather → stem 3 fades in, push → stems 1+2 full, crescendo → stem 2 hard.
- [ ] Boss wave: duck to 50% for intro stinger, full intensity during boss.
- [ ] Low health: heartbeat ambient on channel 7.
- [ ] Commit: `git commit -m "feat: add layered music stems with adaptive intensity"`

### Task jd-33: Tier 2+3 SFX

**Files:**
- Create: `jungle_dodge/assets/sounds/sfx/*.wav` (20 files)
- Modify: `jungle_dodge/audio.py`, various state/entity files

- [ ] Source/generate remaining SFX: obstacle impacts, power-up pickup/active/expire, roll, walk, UI hover/select, name entry, transitions, boss intro/clear, score tick, daily challenge.
- [ ] Wire all AudioManager.play() calls throughout codebase.
- [ ] Rate-limit SFX_SCORE_TICK to max 20/sec.
- [ ] Footsteps at 30% volume, silenced during stun/roll.
- [ ] Commit: `git commit -m "feat: add Tier 2+3 SFX (obstacles, power-ups, UI, transitions)"`

---

## Phase 8: Juice & Feel

### Task jd-34: Screen shake + flash + vignette

**Files:**
- Modify: `jungle_dodge/hud.py`
- Modify: `jungle_dodge/states.py`

- [ ] Trauma-based screen shake: `intensity = max_shake * trauma^2`, decay 4.0/sec. Apply as blit offset on final composite.
- [ ] Trauma per event: hit +0.25, bomb +0.45, death +0.65, boss clear +0.30.
- [ ] Screen flash table: pre-rendered surface, alpha curve `peak * (1 - (age/duration)^0.5)`.
- [ ] Dynamic vignette: pre-rendered radial gradient. Base 30%, 50% at 1 life, 65% during stun.
- [ ] Commit: `git commit -m "feat: add trauma-based screen shake, flash table, dynamic vignette"`

### Task jd-35: Full particle systems

**Files:**
- Modify: `jungle_dodge/particles.py`
- Modify: `jungle_dodge/constants.py`

- [ ] Add all 11 particle configs to PARTICLE_CONFIGS: dodge, hit, near-miss, roll trail, power-up pickup, power-up aura, bomb explosion (45 particles, 3 waves), streak milestone, boss clear (80 particles), death (55 particles), level up.
- [ ] Wire emitters at all trigger points throughout codebase.
- [ ] Score pop cap at 4 with fade-replace.
- [ ] Commit: `git commit -m "feat: implement all 11 particle systems with themed colors"`

### Task jd-36: Death sequence

**Files:**
- Modify: `jungle_dodge/states.py` (PreDeathState, DeathSequenceState)

- [ ] Pre-death bullet time: time_scale=0.15 for 0.45s real-time on final death.
- [ ] Death freeze-frame: `is_frozen` flag, 0.2s pause.
- [ ] Death particles: 55 particles in 3 phases (flash → scatter → soul rise).
- [ ] Ghost silhouette: 180% scale, alpha 60→0, floating up for 0.6s.
- [ ] Screen darkens, music fades, transitions to GameOverState.
- [ ] Total: 2.5s from hit to game over screen.
- [ ] Commit: `git commit -m "feat: add cinematic death sequence with bullet time and ghost silhouette"`

### Task jd-37: Combo feedback escalation

**Files:**
- Modify: `jungle_dodge/hud.py`
- Modify: `jungle_dodge/entities.py`

- [ ] 1x: clean, no effects.
- [ ] 2x: gold score pops (+15% size), faint golden shimmer (1 particle/0.2s), HUD badge glows.
- [ ] 3x: hot gold pops (+25%), visible aura (3 particles/0.2s), speed lines, background tint, badge bounces.
- [ ] Break: character stumble (-10° lean, -15px drop, 0.3s), aura particles fall, badge collapses.
- [ ] Commit: `git commit -m "feat: add combo feedback escalation (1x quiet → 3x explosive)"`

### Task jd-38: Power-up activation visuals

**Files:**
- Modify: `jungle_dodge/hud.py`
- Modify: `jungle_dodge/entities.py`

- [ ] Shield: expanding ring → dome (pulses 1.2Hz) → shatter on hit with 12 particles.
- [ ] Slow-Mo: 3 concentric ripple rings → blue tint → obstacles get ghost trail blur → reverse ripple on expiry.
- [ ] Magnet: gold star burst → HUD score scales 140%→100% → "×2 ACTIVE!" text.
- [ ] Commit: `git commit -m "feat: add power-up activation visual sequences"`

### Task jd-39: Character micro-animations + obstacle entry

**Files:**
- Modify: `jungle_dodge/entities.py`

- [ ] Idle bob: sine wave 4px at 2.5Hz when not moving >0.3s.
- [ ] Lean on movement: 8 degrees, lerp 12 deg/s.
- [ ] Landing squash after roll: 85%H×115%W → spring back.
- [ ] Breathing on start screen: 2.5% scale pulse at 1.2Hz.
- [ ] Obstacle entry pop-in: 0.6x → 1.1x → 1.0x over 0.12s.
- [ ] Commit: `git commit -m "feat: add character micro-animations and obstacle entry pop-in"`

---

## Phase 9: Polish & Delight

### Task jd-40: Moments of delight

**Files:**
- Modify: various files

- [ ] Idle character animations (>3s): scratch head, look around, wave.
- [ ] Perfect dodge whistle: 3 dodges in 2s → SFX + music note particle.
- [ ] Bomb near-miss crown particle.
- [ ] First successful roll: "NICE ROLL!" once per session.
- [ ] Theme easter eggs: parrot (jungle) / shooting star (space) every 15 levels.
- [ ] Death count milestones: 10th/25th/50th.
- [ ] The quiet moment: 0.3s silence before L2 banner.
- [ ] Commit: `git commit -m "feat: add moments of delight (idle anims, easter eggs, milestones)"`

### Task jd-41: Chromatic aberration + pre-death bullet time polish

**Files:**
- Modify: `jungle_dodge/hud.py`

- [ ] CA effect: triple-blit with RGB offset (±8px, 40% alpha). 1–3 frames only on: boss entrance, final death, streak milestone 4, big power-up pickup.
- [ ] Profile performance at 4K — if framerate drops, use region-based (player vicinity only).
- [ ] Commit: `git commit -m "feat: add chromatic aberration effect on high-impact moments"`

### Task jd-42: Colorblind accessibility audit

**Files:**
- Modify: `jungle_dodge/themes.py`
- Modify: `jungle_dodge/hud.py`

- [ ] Audit all HUD indicators for colorblind-safe contrast: streak tiers, roll pips, power-up readiness, timer warning, wave phase bar.
- [ ] Add iconography where color alone communicates state (e.g., streak badge shows number not just color).
- [ ] Verify obstacle silhouettes are distinct without color.
- [ ] Commit: `git commit -m "feat: colorblind accessibility audit and iconography fixes"`

---

## Dependency Graph

```
Phase 1 (Foundation) ──┬── Phase 2 (Gameplay) ──┬── Phase 3 (Obstacles)
                       │                        │
                       ├── Phase 4 (Themes) ────┼── Phase 5 (UI) ──── Phase 6 (Progression)
                       │                        │
                       └── Phase 7 (Audio)      └── Phase 8 (Juice)
                                                         │
                                                    Phase 9 (Polish)
```

Phases 2, 4, and 7 can run in parallel after Phase 1. Phase 5 needs both 2 and 4. Phase 8 needs 2 and 4. Phase 9 is last.
