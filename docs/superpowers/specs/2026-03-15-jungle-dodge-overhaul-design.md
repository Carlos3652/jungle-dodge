# Jungle Dodge — Full Overhaul Design Spec

**Date:** 2026-03-15
**Status:** Draft
**Author:** VECTOR (Game Designer) + Claude Code
**Project:** Jungle Dodge (`C:\Users\Rafa\jungle-dodge`)
**GitHub:** https://github.com/Carlos3652/jungle-dodge

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core Gameplay Enhancements](#2-core-gameplay-enhancements)
3. [Obstacle & Enemy Redesign](#3-obstacle--enemy-redesign)
4. [Progression & Scoring](#4-progression--scoring)
5. [Dual Theme System](#5-dual-theme-system)
6. [HUD & UI Overhaul](#6-hud--ui-overhaul)
7. [Audio Design](#7-audio-design)
8. [Juice & Feel](#8-juice--feel)
9. [Technical Architecture](#9-technical-architecture)

---

## 1. Overview

### 1.1 Current State

Jungle Dodge is a Pygame side-scroller dodge game. Single monolithic file (`jungle_dodge.py`, 1387 lines). 4K internal resolution (3840x2160), offscreen render surface scaled to display. Procedural drawing (no sprite sheets).

- **Gameplay:** Player moves left/right dodging 4 falling obstacle types. 3 lives, 45s per level, +10 pts per dodge.
- **Visuals:** Ancient temple + neon jungle theme, stone tablet HUD, explorer character.
- **Audio:** None — completely silent.
- **States:** START → PLAYING → PAUSED → LEVELUP → NAME_ENTRY → LEADERBOARD → GAMEOVER.

### 1.2 Goals

- **Full overhaul** — both gameplay depth AND visual/audio polish.
- **Audience:** Family-friendly but portfolio-quality. Leaderboard competition is core.
- **Dual themes:** Jungle (primary, refreshed) + Space (new alternative). Player picks on start screen.
- **"One more run" psychology** — every system supports replayability.

### 1.3 Design Principles

1. **One-button depth** — simple to learn, expressive to master (Crossy Road / Alto's Adventure model).
2. **The game roots for the player** — feedback escalates with skill, celebrating success.
3. **Earned complexity** — UI elements appear only after the player unlocks the system they represent.
4. **YAGNI** — no persistent unlocks, no loadouts, no network calls. Session-based, local, fair.

---

## 2. Core Gameplay Enhancements

### 2.1 Side Roll

- **Input:** SPACE triggers roll in held direction (or last facing).
- **Duration:** 0.4s.
- **Speed:** 2.5x normal movement speed during roll.
- **Invincibility:** Full hit immunity for first 0.25s (i-frames).
- **Cooldown:** 2.0s. Radial arc under player shows recharge.
- **Implementation:** `self.rolling = True`, `self.roll_t` timer, direction locked at roll-start. Feed `immune_t = 0.25` when roll begins. Cooldown: `self.roll_cd = 0.0`, counts down each update.

### 2.2 Combo Streak Multiplier

Consecutive dodges without getting hit build a score multiplier:

| Dodges | Multiplier | Visual |
|--------|-----------|--------|
| 0–4 | 1x | No indicator |
| 5–9 | 1.5x | Bronze streak counter above player |
| 10–19 | 2x | Silver, counter pulses, silver score pops |
| 20+ | 3x | Gold, counter pulses larger, particle trail on player |

- **Streak break:** "STREAK LOST" text in red fading upward. Only shows if streak was ≥5.
- **Near-roll near-miss bonus:** Roll dodge through an obstacle during streak awards double the base+bonus before multiplier: `(10 + 3 + 5) × 2 × streak_multiplier`. At 3x streak = 108 pts per obstacle.

### 2.3 Power-Up System

Three power-ups fall like obstacles but must be actively collected (no auto-collect). Creates risk/reward trade-offs.

**Shield (Jungle: leaf shield / Space: energy barrier)**
- Appears every 90–120s (reduced at high streaks).
- Absorbs next single hit. Life not lost, stun still plays. Shield shatters visually.
- Duration: Until hit (no timer).
- Visual: Rotating leaf/hex barrier aura around player.
- **Shield shatter on block:** Obstacle destroyed immediately on contact. 12 particles in obstacle's color, radial 500–900px/s, 0.3s lifetime. Distinct "deflected" SFX (metallic ping, 80–100ms).

**Slow-Mo (Jungle: time flower / Space: gravity well)**
- Appears every 120–180s.
- All falling obstacles at 40% speed for 5s. Player speed unchanged.
- Visual: Color desaturation on obstacles + golden pollen (jungle) / blue time-ripple (space).

**Magnet Score (Jungle: golden idol / Space: crystal shard)**
- Appears every 60s.
- For 8s, dodged obstacles worth 3x their current multiplied value (stacks on streak). Example: at 2x streak, a dodge = (10) × 2 × 3 = 60 pts.
- Additionally, small score orbs (worth 15 flat pts each, NOT multiplied) spawn near dodged obstacles during the magnet window, auto-collected within 120px of player. These are bonus pickups, not the main mechanic.
- Visual: Golden glow pulsing on HUD score counter + gold particle trail on score orbs.

**Spawn rules:** Never in first 15s of any level. Never cluster with obstacles. Minimum `W * 0.3` horizontal distance from recently spawned obstacle. Move at 60% of vine speed. Rotating glow ring in unique color.

### 2.4 Wave Rhythm

Replace linear spawn rate with push/breather cycles within each 45s level:

| Time | Phase | Behavior |
|------|-------|----------|
| 0–15s | Calm | Standard spawn rate |
| 15–23s | Push | Spawn interval -25% (more frequent), clustering ON |
| 23–27s | Breather | Spawn interval +40% (less frequent), clustering OFF |
| 27–35s | Push | Spawn interval -30% (more frequent) |
| 35–39s | Breather | Standard |
| 39–44s | Crescendo | Max spawn rate, 2 obstacles spawn simultaneously |
| 45s | Level complete | |

Crescendo dual-spawns require `W * 0.5` minimum separation.

### 2.5 Near-Miss Scoring

When obstacles pass within ~40px of player without hitting: +5 bonus points + "CLOSE!" particle. Rewards risky positioning.

### 2.6 Difficulty Selector

| Difficulty | Lives | Scaling | Leaderboard |
|-----------|-------|---------|-------------|
| Easy | 4 | Slower | Separate |
| Normal | 3 | Current | Separate |
| Hard | 2 | Faster | Separate |

First run forced to Easy with explanation.

### 2.7 Personal Best Indicator

HUD marker shows best score. "NEW BEST!" flash when surpassed. Only shows when current score > 80% of PB.

---

## 3. Obstacle & Enemy Redesign

### 3.1 Existing Obstacles — Modified

**Vine (spawn weight: 28% → 15% at L9+)**
- Snapping vine variant at L4: last 200px of descent, snaps sideways 120–180px. Telegraphed by green→yellow-green color shift on frame before snap.
- Ground linger scales: 0.8s at L1, up to 1.4s at L8+.
- Space variant: Tether Cable.

**Bomb (spawn weight: 20% → 14% at L9+)**
- Red ground circle (40% opacity) shows explosion radius on spawn.
- Delayed variant at L5: hits ground, fuse continues 0.8s, then explodes. Ground circle pulses during delay.
- Bomb size +15% at L7+, explosion radius scales to 88px.
- Space variant: Proximity Mine.

**Spike (spawn weight: 22% → 20% at L9+)**
- Cluster spike at L3: 3 spikes in triangle formation, staggered 0.15s.
- Bouncing spike at L6: hits ground, bounces up 60px, comes back down once. Squash frame on bounce.
- Space variant: Crystal Shard (shatters on ground with 6 small triangle particles).

**Boulder (spawn weight: 20% → 15% at L9+)**
- Split boulder at L5: 1.4x size, splits into two smaller boulders rolling opposite directions on ground hit.
- Rolling speed increases to 1.4–2.4s range at L8+.
- Space variant: Meteor Fragment.

### 3.2 New Obstacles

**Canopy Drop (L2, spawn weight: 10% → 10% at L9+)**
- 8–12 leaf/debris sprites falling in spread covering 25–40% screen width. One hidden spike, revealed at 80px from ground (darkens).
- Fall speed: 180px/s.
- L2: all visible. L3+: one hidden spike.
- Space variant: Debris Cloud.

**Croc Snap (L4, spawn weight: 8% → 10% at L9+)**
- Horizontal sweep at ground level only (always intersects player plane). Hitbox: 120px wide × 40px tall (base resolution), moves at 600px/s (base resolution, scaled by SX at 4K ≈ 2560px/s). All values are at base 900×600 reference.
- Warning: jaw icon at screen edge 0.5s before sweep + brief ground-shake line.
- **Counter:** Roll i-frames (0.25s window as the jaw passes player position). The sweep crosses any given X position in ~0.2s (120px / 600px/s at base res), so timing the roll is tight but learnable.
- Space variant: Laser Sweep (thin red beam, same hitbox).

**Poison Puddle (L5, spawn weight: 8% at L9+)**
- Ground-level persistent hazard, 80px radius, 3–4s duration.
- Damage model: Standing in puddle for 1.5s triggers a stun (same as hit, costs 1 life). A 1.0s progress bar appears above player when in puddle; leaving resets the timer. This is compatible with the integer-lives system — no fractional HP.
- Spawned by delayed bomb explosions AND as standalone drops.
- Max 2 puddles on screen. Third despawns oldest.
- Space variant: Radiation Pool.

**Screech Bat (L7, spawn weight: 8% at L9+)**
- Enters from one side, flies a diving arc: starts in top 30%, swoops down to ground level at the player's X position at time of spawn, then exits upward on the other side. Total crossing time: ~2.5s.
- Homing: Bat commits to a landing zone based on player X at spawn time + 15% correction per frame for the first 1.0s of flight (exponential decay: `correction = 0.15 * remaining_distance * (1.0 - t/1.0)` where t is time since spawn, capped at 1.0s). After 1.0s the bat locks its trajectory — no more tracking.
- **Counter:** Lateral dodge. Move away from the committed landing zone. The 1.0s tracking window gives the player ~1.5s of pure lateral escape time. Roll does NOT help — the bat's ground-level pass hitbox is 80px wide (base res) and its ground-level crossing speed is ~300px/s, meaning it occupies the player's position for ~0.27s, slightly longer than the 0.25s i-frame window.
- Space variant: Homing Drone.

**Ground Hazards (L5+)**
- Vines/steam vents rising from ground at random X positions.
- **Hitbox:** 60px wide × 120px tall column. Rises from ground to full height in 0.4s.
- **Telegraph:** 0.5s warning — ground cracks/glows at spawn X position before hazard rises.
- **Duration:** Active for 1.5–2.0s after reaching full height, then retracts in 0.3s.
- **Damage:** Contact deals standard hit (1 life + stun). Hitbox active only while fully extended.
- **Roll interaction:** Roll i-frames work — player can roll through the hazard column.
- **Spawn rules:** Max 2 active simultaneously. Minimum 200px horizontal separation. Never spawn within 100px of player position.
- **Spawn timing:** Ground hazards are on a separate timer from the obstacle spawn pool (like power-ups). Base interval: 12–18s at L5, decreasing to 8–12s at L10+. Not included in obstacle spawn weights.
- Space variant: Plasma Vents (cyan jet with steam particles).

### 3.3 Universal Telegraph Rule

Every obstacle gets visual warning proportional to danger:
- Common obstacles: 0.3s telegraph.
- Fast/dangerous obstacles: 0.5s telegraph.
- Single telegraph component for all obstacles.

### 3.4 L10+ Personality Upgrades (scoped to 3)

- **Paired vines** (area denial) — vines spawn in pairs.
- **Tracking bombs** (precision) — bombs bias slightly toward player during fall.
- **Wobble spikes** (timing) — spikes wobble unpredictably breaking muscle memory.

### 3.5 Obstacle Level Introduction Table

| Level | New Unlock | Behavior Change |
|-------|-----------|----------------|
| 1 | Vine, Bomb, Spike, Boulder (base) | Tutorial spacing, 1 obstacle at a time |
| 2 | Canopy Drop | 2 simultaneous obstacles |
| 3 | Cluster Spike, Vine Snap variant | Linger scaling starts |
| 4 | Croc Snap | Bomb delay variant |
| 5 | Poison Puddle, Delayed Bomb, Split Boulder, Ground Hazards | Post-bomb puddles |
| 6 | Bouncing Spike | 3 simultaneous obstacles |
| 7 | Screech Bat/Drone | Boulder speed increases |
| 8 | Large Boulder (split faster) | Bomb radius → 88px |
| 9 | Full combo patterns | All weights at final values |
| 10+ | Boss wave patterns | Personality upgrades activate |

Speed scaling: `FallSpeed = BaseFallSpeed * (1.0 + (level - 1) * 0.08)` — 8% faster per level.

### 3.6 Roll Interaction Table

| Obstacle | Roll Correct? | Notes |
|----------|--------------|-------|
| Vine | Marginal | Just step aside |
| Vine Snap | YES | Timing through snap is skill expression |
| Bomb explosion | YES | Roll through radius for near-miss points |
| Spike (base) | Marginal | Just sidestep |
| Bouncing Spike | YES | Roll during bounce is correct read |
| Cluster Spike | YES | Roll through gap between formation |
| Boulder (rolling) | NO | Read direction, move perpendicular |
| Split Boulder | NO | Lateral awareness |
| Canopy Drop | NO | Positional (stay near edge) |
| Croc Snap | YES | Roll showcase — ground-level sweep, time 0.25s i-frames as jaw passes |
| Poison Puddle | NO | Step off it |
| Screech Bat | NO | Diving arc commits to landing zone after 1s; move laterally to escape |
| Ground Hazard | YES | Roll i-frames work through the 60px column |

~40% reward rolling, ~60% want different response. Roll is precision tool, not panic button.

### 3.7 Boss Waves (every 5 levels)

**L5 "The Stampede" (20s scripted)**
1. (0–5s) 3-wide spike cluster gauntlet
2. (5–10s) Two regular boulders spawned simultaneously at opposite screen edges, rolling inward toward center (NOT split boulder — these are two independent boulders)
3. (10–15s) Bomb barrage — 4 bombs, overlapping radii, forces edges
4. (15–20s) Full-screen canopy drop + 2 hidden spikes
- Reward: 500 flat bonus + streak boost

**L10 "The Predator Run" (25s scripted)**
- Adds croc snap, screech bat. Alternating side snaps at 0.8s intervals.
- Reward: 750 bonus

**L15 "The Everything" (scripted)**
- Every obstacle type coordinated. Final 5s: 1.8x density.
- Reward: 1000 bonus + "Jungle Survivor" leaderboard badge.

**L16+:** Mini-boss every 5 levels (randomized from 3 boss types).

Boss waves stored as `(delay_ms, obstacle_class, x_pct)` tuple lists.

### 3.8 Named Combo Patterns (L4+)

5 scripted formations during push phases. 1 per push at L4+, 2 at L8+.

- **The Funnel:** 2 vines left+right → spike drops into forced center lane.
- **The Crossfire:** Boulder rolls + croc snap from opposite side simultaneously.
- **The Shell Game:** 3 canopy drops in sequence, hidden spike switches to drop 3.
- **The Rolling Wave:** Boulder passes → vine snaps from behind where player retreated.
- **The Triple Stack:** Bomb center → spike clusters at both sides of blast zone. Roll through spike or time around bomb.

Pattern clear bonus: +50 flat (not multiplied). "PATTERN CLEAR!" text.

---

## 4. Progression & Scoring

### 4.1 Point Values

| Source | Points | Multiplied? |
|--------|--------|------------|
| Dodge obstacle | 10 | Yes |
| Near-miss bonus | +5 | Yes |
| Roll dodge bonus | +3 | Yes |
| Pattern clear | +50 | No |
| Boss wave clear (L5/L10/L15) | +500/750/1000 | No |
| Level completion | 25 × level# | No |

**Multiplier math:** Applied to combined dodge value.
- Standard roll dodge + near-miss at 3x = (10 + 3 + 5) × 3 = **54 pts**.
- Near-roll near-miss bonus (roll THROUGH obstacle during streak) = (10 + 3 + 5) × 2 × 3 = **108 pts** (true skill ceiling per obstacle). The ×2 only applies when roll i-frames actively phase through the obstacle's hitbox.

Level completion bonus caps at L15 (375 flat post-L15).

### 4.2 Level Structure

**Infinite, tiered:**
- **Casual (L1–9):** Tutorial → complexity ramp. Speed 1.0–1.15x.
- **Serious (L10–15):** Personality upgrades, all obstacle types. Speed 1.3–1.6x.
- **Hardcore (L16+):** Speed caps at 1.75x after L17. Density continues increasing.
- Mini-boss every 5 levels post-L15.

### 4.3 Leaderboards

Single `leaderboard.json` file with per-difficulty boards inside a `boards` dict. Top 10 per board. See Section 9.4 for full schema.

**Entry schema:**
```json
{
  "name": "RAFA",
  "score": 14220,
  "level": 12,
  "max_streak": 47,
  "boss_clears": 2,
  "badges": ["UNTOUCHABLE", "BOSS_SLAYER"],
  "theme": "jungle",
  "date": "2026-03-15"
}
```

**Display columns:** Rank (medals 1–3), Name, Score (comma-formatted), Level, Max Streak, Date.

**"YOU BEAT [NAME]" callout** when displacing someone on the leaderboard.

### 4.4 Daily Challenge

- Fixed random seed per day: `seed = int(date.strftime("%Y%m%d"))`.
- One leaderboard (Normal difficulty only).
- Separate mode from main menu, clearly labeled.
- "DAILY PLAYED" greyed out if already attempted.

### 4.5 Session Badges (15 total)

**Skill:**

| Badge | Trigger |
|-------|---------|
| UNTOUCHABLE | Complete a level without getting hit |
| STREAKER | 25-dodge streak |
| LEGEND | 50-dodge streak |
| ROLL MASTER | 10 roll dodges in one level |
| CLOSE CALL | 5 near-misses in one level |
| PATTERN CLEAR | Clear any named combo pattern clean |

**Progression:**

| Badge | Trigger |
|-------|---------|
| SURVIVOR | Reach L5 |
| JUNGLE KING | Reach L10 |
| VOID WALKER | Reach L15 |
| ENDLESS | Reach L20 |

**Boss:**

| Badge | Trigger |
|-------|---------|
| STAMPEDE CLEAR | L5 boss no-hit |
| PREDATOR CLEAR | L10 boss no-hit |
| CHAOS CLEAR | L15 boss no-hit |

**Novelty:**

| Badge | Trigger |
|-------|---------|
| LUCKY | Survive a hit on last life |
| POWER HUNGRY | Collect all 3 power-up types in one run |

Badges travel with the score entry in JSON. Up to 2 shown on leaderboard (rarest first).

### 4.6 "One More Run" Hooks

1. **Visible gap:** Leaderboard shows score above player's best with delta: "BEAT CARLOS BY 340 PTS."
2. **Near-miss badges:** Game over shows 1–2 closest unearned badges grayed with shortfall: "STREAKER — missed by 8 dodges."
3. **"NEW DANGER AHEAD" tease** at new level thresholds.
4. **Anti-quit:** Show leaderboard delta 1.5s before "PLAY AGAIN" button fades in.
5. **Boss clear momentum:** 2s "BOSS DEFEATED" splash, auto-advance (no decision point).

### 4.7 Score Breakdown Animation

Game over tally: component by component (base dodges → streak → near-miss → power-up → boss/pattern → level → TOTAL). Slot-machine style counter, 2–3s total. Audio tick per component. Multiplied total flashes on final sum.

### 4.8 Game Over Stats

8-stat grid (2 rows × 4 columns):

```
LEVEL REACHED    MAX STREAK    ENEMIES DODGED    NEAR MISSES
POWER-UPS USED   ROLL USES     TIME SURVIVED     HITS TAKEN
```

**Flavor text** (one per run, priority-selected):
- Near-misses ≥10 and no hit: "LIVING DANGEROUSLY"
- Roll dodges >30% of total: "THE ROLLER"
- Died L1–L2: "BETTER LUCK NEXT TIME"
- Personal best level: "DEEPEST RUN YET"
- Max streak ≥50: "LEGENDARY RUN"

**Run stats tracked (ephemeral):**
```python
run_stats = {
    "score": 0, "level": 0, "max_streak": 0, "boss_clears": 0,
    "badges": [], "total_dodges": 0, "roll_dodges": 0,
    "near_misses": 0, "hits_taken": 0, "powerups_collected": 0,
    "pattern_clears": 0, "time_survived": 0.0
}
```

---

## 5. Dual Theme System

### 5.1 Theme Selection UX

Two large toggle panels on start screen between title and action buttons. LEFT/RIGHT or A/D cycles, click selects.

- Each panel: ~35% screen width, 220px tall.
- Selected: full brightness, 3px themed border, scale 1.03, animated mini-preview.
- Inactive: 60% brightness, scale 0.97, 1px dimmed border.
- Preview: miniature parallax background + one obstacle + character idle walk.
- 0.2s ease-out scale+brightness tween on switch.
- Theme persists to `settings.json`.

Title updates: "JUNGLE DODGE" / "SPACE DODGE".

### 5.2 Jungle Theme — Refreshed

**Sky (layered depth):**
- Far: `(8,20,12)` top → `(18,45,22)` horizon
- Mid: Silhouetted tree canopy `(12,35,16)`, parallax 0.1x
- Near: Foreground foliage `(6,18,8)`, parallax 0.3x

**Ground:** `(45,28,12)` dark soil, `(65,42,18)` edge line, procedural grass blades in `(52,110,38)` / `(72,155,50)`.

**Environmental FX:** Falling leaf particles (8–12 active), ground fog (35% alpha), bioluminescent spores at L5+.

**Character:** Explorer — leather brown jacket `(160,95,40)`, hat `(100,65,25)` with gold band `(200,160,80)`, warm skin `(200,155,110)`, dark pants `(75,55,35)`, boots `(55,35,15)`.

**Obstacles:** Vines `(45,140,55)` with `(85,200,90)` highlight. Bombs charcoal `(40,40,35)` with coiled rope fuse. Spikes bone-ivory `(210,195,170)`. Boulder warm stone `(95,82,65)`.

### 5.3 Space Theme

**Concept:** Deep space archaeological dig on alien moon.

**Sky (star field):** Base `(2,2,12)`. 200 procedural stars (3 size tiers, twinkle every 90 frames). Nebula ellipse `(60,20,90)` or `(20,40,80)` at 25% alpha. Distant planet upper-right `(80,55,120)`.

**Ground:** Regolith `(55,52,65)`, edge `(75,72,88)`, granular texture dots, 3–5 craters per section.

**Character:** Space archaeologist — light grey suit `(180,200,220)`, cyan visor `(60,160,220)` at 50% alpha, backpack `(70,85,100)` with indicator dots.

**Color palette:** Primary accent `(80,200,255)` cyan. Secondary `(200,80,255)` purple. Warning `(255,80,80)` red.

**HUD:** Holographic panel — `(20,30,50)` at 75% alpha, `(60,120,200)` 2px border. Cyan text. Shield-cell life indicators.

### 5.4 Obstacle Visual Mapping

| Obstacle | Jungle | Space |
|----------|--------|-------|
| Vine | Green cylindrical rope + leaf cluster | Tether cable + metal clamp |
| Bomb | Charcoal sphere + rope fuse | Grey hex prism + red blink light |
| Spike | Bone-ivory punji stakes | Red-orange drill shards |
| Boulder | Warm stone + cracks | Irregular polygon asteroid |
| Canopy Drop | Coconuts/branches cluster | Hull fragments + cyan edge glow |
| Croc Snap | Green jaw + teeth | Mechanical jaw trap + sparks |
| Poison Puddle | Green bubbling circle | Teal-green acid vent + steam |
| Screech Bat | Dark bat silhouette + red eyes | Hex drone + cyan emitter arms |
| Ground Hazard | Vine tendrils rising | Plasma vent jets |

### 5.5 Theme Data Architecture

Single `THEMES` dict. All draw code reads `T["key"]` — never hardcodes colors.

```python
THEMES = {
    "jungle": {
        "name": "JUNGLE",
        "accent_color": (80, 255, 80),
        "sky_top": (8, 20, 12),
        "sky_horizon": (18, 45, 22),
        "ground_base": (45, 28, 12),
        "char_jacket": (160, 95, 40),
        "hud_style": "stone_tablet",
        "transition_style": "vine_wipe",
        "audio_prefix": "jungle",
        # ... (100+ keys total per theme)
    },
    "space": {
        "name": "SPACE",
        "accent_color": (80, 200, 255),
        "sky_top": (2, 2, 12),
        "hud_style": "holographic",
        "transition_style": "star_jump",
        "audio_prefix": "space",
        # ...
    }
}
```

**Rules:**
- Zero theme-conditional branches in obstacle draw code. Only exceptions: `hud_style` switch in `draw_hud()` and `bg_extras_fn` for background rendering.
- Active theme accessed via `T = THEMES[selected_theme]`.
- Adding a 3rd theme: one dict entry + optional HUD style branch.
- Missing key fallback: magenta `(255, 0, 255)` — instantly visible during dev.

### 5.6 What Changes vs Stays the Same

**Does NOT change:** All hitboxes, timing values, scoring, game logic, input handling, state machine, badge conditions.

**Changes per theme:** All draw calls (environment, character, obstacles), HUD style, particle colors, SFX/music stems, transition style, floating text colors.

**Leaderboard:** One combined board per difficulty. Tiny color indicator per entry shows theme used.

---

## 6. HUD & UI Overhaul

> **Note on dimensions:** All pixel values in this section are at the **base 900×600 reference resolution** and should be scaled by `S = SY = 3.6` for the 4K internal render surface (3840×2160), unless explicitly noted as "at 4K."

### 6.1 In-Game HUD

**Dual-panel bottom bar with floating center element:**

```
[WAVE PHASE BAR — full width, 12px, above panels]
[SCORE PANEL — left 38%]  [TIMER — center]  [STATUS PANEL — right 38%]
```

**Wave Phase Bar:** Full width, 12px tall. Filled = progress through current phase. Push = warm amber, breather = cool green. Pulses in final 20% of push.

**Left Panel (Score + Streak):**
- "SCORE" label + comma-formatted value (52px)
- Streak badge pill (only at 2x+): bronze → silver → gold with pulse
- PB indicator (only at >80% of PB): "PB: X,XXX" → "NEW BEST!" when exceeded

**Center (Timer):**
- 64px diameter circle, arc depletes clockwise
- Normal color → red under 10s (pulses 4Hz) → bold under 5s

**Right Panel (Lives + Roll + Power-ups):**
- Lives: skull icons, cracking animation on loss
- Roll cooldown: 3 pip circles, drain/refill with cooldown
- Power-up status: pill above lives (only when active), icon + name + countdown

**Level indicator:** Top-center pill, "LEVEL 12". Turns red during boss waves.

### 6.2 Start Screen

```
[Title — updates per theme]
[Theme Selector — two toggle panels]
[Difficulty Row — Easy | Normal | Hard with PB shown]
[START RUN / DAILY CHALLENGE buttons]
[Tagline + ? hint]
[Best Player Badge — top-right]
```

- Difficulty selected via UP/DOWN or 1/2/3 keys.
- "START EASY RUN" / "START NORMAL RUN" / "START HARD RUN" — updates per selection.
- Daily Challenge: "NEW" badge first access of day, "PLAYED" if done.
- Jungle tagline: "SURVIVE. DODGE. OUTLAST."
- Space tagline: "SURVIVE. DODGE. TRANSCEND."

### 6.3 Pause Screen

Centered card (600×440px), themed border. Background: game world visible at 60% opacity.

- "PAUSED" with pause icon
- Score + streak badge (reminds player not to quit)
- Level + time remaining
- RESUME (primary) | QUIT (secondary) buttons
- Controls reminder (condensed 2-line)

### 6.4 Volume Overlay

Triggered by V key or gear icon on pause screen.

- 3 horizontal slider bars: Music, SFX, Master
- LEFT/RIGHT adjusts in 10% increments, UP/DOWN navigates
- Current % displayed next to each bar
- ESC closes. Settings persist to `settings.json`.
- M key: instant mute/unmute toggle (works anytime).

### 6.5 Level Up Transition

**Standard (2.0s):**
1. Screen flash white (0.2s)
2. Level number slams in from top (bounce settle)
3. Subtitle from pool (tier-appropriate: "Stay sharp." / "No room for error." / "You're still here. Interesting.")
4. Score + streak badge
5. "NEW THIS LEVEL" preview (only on levels introducing new obstacle)

**Boss Wave Intro (3.5s):**
1. Screen flashes DANGER RED
2. "BOSS WAVE" crashes in (120px)
3. Boss name + description
4. Dramatic 0.4s pause
5. Enemy preview drawing
6. Health warning if last life
7. Slam cut to gameplay (no fade — abrupt)

### 6.6 Name Entry

- Headline variants: "NEW PERSONAL BEST!" / "TOP 3 — LEGENDARY!" / "YOU MADE THE TOP 10!" / "YOU BEAT [NAME]!"
- 5-slot letter entry, 80×96px per slot, blinking cursor
- Real-time rank preview: "THIS WILL PLACE YOU: #3"
- Particle burst on confirm

### 6.7 Leaderboard

4 tabs: NORMAL | EASY | HARD | DAILY. LEFT/RIGHT or TAB cycles.

Columns: Rank (medals 1–3), Name, Score, Level, Max Streak, Date, Theme indicator.

- Player's just-entered entry: highlighted background for 3s.
- Cascade-slide animation: rows slide in from right, 50ms stagger.
- "YOU BEAT [NAME]!" floats up from beaten row.
- Up to 2 badge icons per entry (rarest first).
- Daily tab: "RESETS IN HH:MM:SS" countdown.

### 6.8 Game Over — 3-Phase Reveal

**Phase 1 (0–0.5s): Impact**
- Instant dark overlay (no fade). "GAME OVER" slams down from top.

**Phase 2 (0.5–2.5s): Score Breakdown**
- Slot-machine tally: BASE → STREAK → NEAR MISS → POWER-UP → TOTAL
- Each column counts up 0.8s (ease-in-out), staggered 0.15s
- Total slams in with flash after all complete
- Gap to best shown if not new PB

**Phase 3 (2.5–4.5s): Stats + Badges**
- 8-stat grid (cascade reveal, 100ms stagger)
- Earned badges with pop animation
- Near-miss badge teases (max 3, grayed with shortfall)
- Flavor text

**Anti-quit:** SPACE disabled for 2.5s. "PLAY AGAIN" fades in at 2.5s. Leaderboard insertion point shown.

### 6.9 Screen Transitions

| From → To | Transition |
|-----------|-----------|
| Start → Playing | Theme-burst: vine-wipe (jungle) / star-jump (space), 0.4s |
| Playing → Pause | Immediate overlay, 0.1s fade-in |
| Playing → Level Up | White flash + slight world zoom, 0.15s |
| Playing → Game Over | Red flash + 0.2s freeze-frame |
| Game Over → Name Entry | Slide-up, 0.4s |
| Name Entry → Leaderboard | Row cascade from right |
| Leaderboard → Start | Fade out/in, 0.5s total |
| Any → Any (ESC) | Fade to black 0.25s + fade in 0.25s |

**Death freeze-frame:** On last hit, game state freezes 0.2s (all movement stops, rendering continues). Player sees exactly what killed them. Then red flash hits.

### 6.10 Tutorial (First-Run)

Teach by doing, not reading. First 10 seconds:

1. **(0s)** Obstacles frozen 2s. Arrow indicators flanking player: "← MOVE  MOVE →"
2. **(2s)** Single slow obstacle (50% speed). Successful dodge → "+10" teaches scoring.
3. **(3s)** "PRESS SPACE TO ROLL" with pulsing arrow to roll pips. Stays 3s or until player rolls. After rolling: "NICE! ROLL HAS A COOLDOWN — WATCH THE PIPS"
4. **(6s)** Two obstacles, normal speed. No overlay.
5. **(10s)** If 3+ dodge streak: "STREAK ACTIVE — SCORE MULTIPLIED!" 2s then gone.

Controls card available via ? icon on start screen and pause screen. Max 12 lines, two-column layout.

---

## 7. Audio Design

### 7.1 Music Approach

Layered stems with intensity stacking per theme:

| Layer | Content | When Active |
|-------|---------|-------------|
| Stem 0 | Percussion/rhythm | Always during gameplay |
| Stem 1 | Melody/pad | After L2 or immediately |
| Stem 2 | Intensity | Crescendo + boss waves |
| Stem 3 | Thinned/muted variant | Breather phases |

All stems loop at same BPM, stay in sync. Volume crossfade between layers (never stop/swap).

- Jungle: 96 BPM, organic shuffle (marimba, steel drums, congas, pan flute).
- Space: 128 BPM, four-on-the-floor (synths, electronic percussion, arpeggiation).

### 7.2 SFX Catalog

**Tier 1 — Critical (7 sounds):**

| SFX ID | Event | Duration |
|--------|-------|----------|
| SFX_HIT | Player takes damage | 0.4s |
| SFX_STUN_LOOP | Loops during 3s stun | 3s loop |
| SFX_STREAK_UP (×3) | Multiplier increases (ascending pitch per tier) | 0.15/0.2/0.3s |
| SFX_STREAK_BREAK | Multiplier resets | 0.3s |
| SFX_DODGE_CLOSE | Near-miss "CLOSE!" | 0.35s |
| SFX_BOMB_EXPLODE | Bomb detonation (biggest sound) | 0.5s |
| SFX_LEVEL_UP | Level complete jingle (over music) | 1.2s |
| SFX_GAME_OVER | Death stinger (2-part: freeze + slam) | 0.9s |

**Tier 2 — High Value (8 sounds):**

SFX_VINE_LAND (0.4s), SFX_SPIKE_IMPACT (0.3s), SFX_BOULDER_ROLL (1.5s loop), SFX_BOULDER_SPLIT (0.5s), SFX_POWERUP_PICKUP ×3 variants (0.4s), SFX_POWERUP_ACTIVE (0.4s), SFX_POWERUP_EXPIRE (0.3s), SFX_SCORE_TICK (0.05s), SFX_BOSS_INTRO (1.0s), SFX_BOSS_CLEAR (1.5s).

**Tier 3 — Polish (13 sounds):**

SFX_WALK (0.1s cycle), SFX_ROLL (0.25s), SFX_BAT_SCREECH (0.3s), SFX_CROC_SNAP (0.4s), SFX_CANOPY_DROP (0.5s), SFX_GROUND_HAZARD_RISE (0.4s), SFX_UI_HOVER (0.07s), SFX_UI_SELECT (0.15s), SFX_NAME_LETTER (0.08s), SFX_NAME_CONFIRM (0.5s), SFX_TRANSITION_VINE_WIPE (0.5s), SFX_TRANSITION_STAR_JUMP (0.6s), SFX_DAILY_CHALLENGE (0.7s).

**Theme audio identity:**
- Jungle: woody, resonant, warm (marimba, steel drums, ambient birds).
- Space: digital, crisp, electronic (synths, processed tones, cosmic reverb).
- Same emotional shape per event across themes (ascending celebration, descending loss).

### 7.3 Channel Allocation (12 channels)

| Channel | Purpose | Priority |
|---------|---------|----------|
| 0–3 | Music stems 0–3 | Reserved |
| 4 | Critical (HIT, GAME_OVER, BOSS) | Highest |
| 5 | Player actions (ROLL, STREAK, POWERUP) | High |
| 6 | Obstacle SFX (BOMB, VINE, BOULDER) | Medium |
| 7 | Ambient/loops (STUN, BOULDER_ROLL, COMBO) | Medium |
| 8 | Score/UI (SCORE_TICK, UI_SELECT) | Low |
| 9 | Environment (footsteps, ambient) | Low |
| 10 | Jingles (LEVEL_UP, BOSS — ducks music) | High |
| 11 | Overflow/spare | — |

Max 4 non-music sounds simultaneously. Jingles duck stems 1+2 to 60% volume.

### 7.4 Adaptive Audio

- **Wave phases:** Breather → stem 2 fades out, stem 3 fades in (1.5s). Push → reverse. Crescendo → stem 2 hard fade-in (0.5s).
- **Streak influence:** 1.5x = score tick pitch +5%. 2x = tick tempo slight increase. 3x = combo ambient heartbeat pulse.
- **Boss wave:** All stems to 50% for intro stinger. Full intensity during boss.
- **Low health (1 life):** Anxious heartbeat ambient (low tom / electronic pulse). Stem 2 at 45%.

### 7.5 Volume Mix

| Category | Level |
|----------|-------|
| Music stems | 70% |
| Critical SFX | 90% |
| Gameplay SFX | 75% |
| Score tick | 60% |
| UI SFX | 55% |
| Footsteps | 30% |
| Ambient loops | 25% |
| Jingles | 85% |
| Background ambient | 15% |

Player-facing: 3 sliders (Music, SFX, Master). M key mute toggle.

### 7.6 Implementation

- `pygame.mixer.pre_init(44100, -16, 2, 512)` — 512 buffer for low-latency SFX.
- Music: .ogg (compression). SFX: .wav (latency).
- Sources: Bfxr (procedural SFX), freesound.org/Kenney (organic sounds), BeepBox (music stems).
- Total audio budget: under 20MB.
- AudioManager singleton: game code calls `AudioManager.play("SFX_HIT")`.
- Graceful degradation: missing sound keys do nothing (no crash).

### 7.7 Audio Implementation Order

1. SFX_HIT + SFX_STUN_LOOP + SFX_GAME_OVER (death feel)
2. SFX_STREAK_UP + SFX_STREAK_BREAK (core feedback)
3. SFX_LEVEL_UP (milestone)
4. SFX_BOMB_EXPLODE (biggest event)
5. SFX_POWERUP_PICKUP (reward)
6. Music (jungle stem 0 loop — game has a heartbeat)
7. SFX_SCORE_TICK (tally screen)
8. SFX_DODGE_CLOSE + SFX_ROLL (skill feedback)
9. Obstacle SFX (environmental texture)
10. Tier 3 (full polish)

---

## 8. Juice & Feel

### 8.1 Particle Systems

**Architecture:** Single `Particle` dataclass + `ParticleSystem` manager with object pooling. Budget cap: 400 simultaneous particles.

**Particle fields:** x, y, vx, vy, ax, ay, drag, size, size_end, color, alpha, alpha_end, lifetime, age, rotation, rot_speed, shape ('circle', 'rect', 'star', 'trail').

**11 particle types:**

| System | Trigger | Count | Lifetime | Key Behavior |
|--------|---------|-------|----------|-------------|
| Dodge | Movement | 4 | 0.18s | Speed-line rects trailing movement |
| Hit | Player damage | 18 | 0.25–0.7s | 12 chunks (gravity) + 6 star flashes |
| Near-miss | Close dodge | 6 | 0.22s | Horizontal sparks in obstacle direction |
| Roll trail | During roll | ~24 total | 0.3s | Ghost afterimages + speed lines |
| Power-up pickup | Collect | 20 | 0.35–0.9s | 10 burst + 10 rising sparkles |
| Power-up aura | While active | 2/frame | 0.4–0.6s | Themed orbit particles |
| Bomb explosion | Detonation | 45 | 0.3–0.8s | 3 waves: core flash → shrapnel → sparks |
| Streak milestone | 5/10/15/20 | 12–42 | 0.5–1.4s | Radial burst, confetti ring at 20+ |
| Boss clear | Boss defeated | 80 | 0.6–2.0s | 3 waves: burst → confetti rain → rising sparks |
| Death | Final death | 55 | 0.3–1.3s | 3 phases: flash → scatter → soul rise |
| Level up | Level complete | 24+8 | 0.4–0.9s | Upward fan + digit-center bursts |

All colors sourced from theme dict. Particle configs stored in `constants.py`, colors merged at emit time.

### 8.2 Screen Effects

**Screen Shake (trauma-based, Vlambeer model):**
- Add trauma (0.0–1.0) per event. `intensity = max_shake * trauma^2`. Decays at 4.0/sec.
- `offset_x = intensity * sin(time * frequency)`. Applied as single blit offset.
- Trauma per event: hit +0.25, bomb +0.45, vine +0.15, boss hit +0.50, death +0.65, boss clear +0.30, streak milestone 4 +0.20.
- Max shake: 22px horizontal, 12px vertical (4K).

**Screen Flash:** Full-screen colored surface with alpha curve `alpha = peak * (1 - (age/duration)^0.5)`.

| Event | Color | Alpha Peak | Duration |
|-------|-------|-----------|----------|
| Hit | (255,60,60) | 80 | 0.12s |
| Bomb | (255,180,80) | 140 | 0.18s |
| Power-up pickup | (255,255,200) | 60 | 0.10s |
| Boss clear | (255,255,140) | 100 | 0.25s |
| Death | (255,40,40) | 200 | 0.30s |
| Level up | (200,255,200) | 50 | 0.15s |

**Dynamic Vignette:** Pre-rendered radial gradient surface. Base 30% opacity. Ramps to 50% at 1 life, 65% during stun, 45% during boss wave.

**Pre-Death Bullet Time:** Final death only. `time_scale = 0.15` for 0.45s real-time. Player sees it happening. Snaps back to 1.0 for death explosion.

**Chromatic Aberration (Pygame approximation):** On big impact: blit frame 3× with red/blue channel offsets (±8px, 40% alpha). 1–3 frames only. Used on: boss entrance, final death, streak milestone 4, big power-up pickup.

### 8.3 Animation Polish

**Character micro-animations:**
- Idle bob: `y_offset = sin(time * 2.5) * 4px` when not moving for >0.3s.
- Lean on movement: 8 degrees in travel direction, lerp 12 deg/s.
- Landing squash after roll: 85%H × 115%W for 0.08s → spring back 108%H × 95%W for 0.06s.
- Breathing on start screen: `scale = 1.0 + sin(time * 1.2) * 0.025`.

**Obstacle entry:** Pop-in scale: 0.6x → 1.1x (0.06s) → 1.0x (0.12s). 3-keyframe spring.

**HUD animations:**
- Score: exponential approach counting `current + (target - current) * (1 - e^(-t*8))`. Pulses at every 100pt increment.
- Life loss: icon shakes ±8px for 0.3s → fades out 0.2s. Remaining icons pulse 105%.
- Streak badge: pop spring 0.0 → 1.25 → 1.0 over 0.3s on tier change.
- Power-up timer: smooth depletion, color change at 25%, pulse at 10%.

### 8.4 Death Sequence (2.5s total)

| Time | Event |
|------|-------|
| 0.00s | Pre-death bullet time begins (0.45s at 0.15x) |
| 0.00s | Screen flash + screen shake (+0.65 trauma) |
| 0.45s | Time snaps back. Death particles BURST (55) |
| 0.45–0.85s | Player sprite fades out, shrinks 1.0→0.7 |
| 0.85–1.45s | Ghost silhouette: 180% scale, alpha 60→0, floating up |
| 1.45–1.95s | Black overlay fades in, vignette spikes, music fades |
| 1.95s | GAME OVER text appears (3-phase reveal begins) |

### 8.5 Combo Feedback Escalation

| Tier | Score Pops | Character | Background | HUD |
|------|-----------|-----------|-----------|-----|
| 1x | Normal white | Normal | Normal | 1x neutral |
| 2x | Gold, +15% size | Faint golden shimmer (1 particle/0.2s) | Slight saturation boost | Badge glows |
| 3x | Hot gold, +25%, slight rotation | Visible energy aura (3 particles/0.2s), speed lines | 20% tint, sparse particle rain | Badge bounces |

**Break:** Character stumble (-10° lean, -15px drop, 0.3s). Aura particles drop (gravity flip). Badge collapses 0→1x.

### 8.6 Power-Up Activation

**Shield:** Expanding ring (0→140px, 0.25s) → shield dome appears (90px, alpha 40, pulses 1.2Hz). Shield persists until hit (no timer, no expiry). On hit absorption: dome flashes bright (alpha 200), obstacle shatters (12 particles), "deflected" SFX, then dome dissolves with 6 inward-implosion particles.

**Slow-Mo:** 3 concentric ripple rings (0→400px, 0.5s staggered) → blue-purple screen tint (alpha 20) → obstacles get trailing ghost blur → reverse ripple on expiry.

**Score Multiplier:** Gold star burst (10 stars) → HUD score scales 140%→100% → "×2 ACTIVE!" text → gold star particles on each score pop.

### 8.7 Boss Wave Atmosphere

**Pre-boss (3s):** Vignette 30%→60%. 3 red warning pulses. "BOSS WAVE INCOMING" vibrating text.

**Active:** Sky/background darkens 30%. Lightning/energy flashes every 4–7s. Boss continuous aura (4 particles/sec). Full intensity music.

**Boss death:** Boss sprite scales 1.0→1.8 (0.4s) → disappears → 0.6s silence → clear music sting → boss clear particle burst (Section 8.1, 80 particles).

### 8.8 Moments of Delight

1. **Idle animations (>3s no input):** Scratch head, look around, yawn (space), wave at camera (8s+).
2. **Perfect dodge whistle:** 3 dodges in 2s → brief SFX + music note particle.
3. **Bomb near-miss crown:** Survive within 80px of explosion → tiny crown particle.
4. **Streak celebration:** At 3x held 5s+ → fist pump, small jump between dodges.
5. **Theme easter eggs:** Every 15 levels — parrot silhouette (jungle) / shooting star (space).
6. **Name entry hop:** Each keystroke → character does tiny hop.
7. **Score pulse:** Final score on game over pulses every 3s — game is breathing, waiting.
8. **Death count milestones:** 10th="Getting the hang of it." 25th="Dedication." 50th="Respect."
9. **First successful roll:** "NICE ROLL!" once per session.
10. **The quiet moment:** 0.3s silence before Level 2 banner. Game being human.

### 8.9 Juice Implementation Priority

**Must-have:** Hit particles + screen shake, death sequence, streak escalation, roll trail.

**High value:** Screen flash table, score counting animation, power-up activation, bomb explosion particles.

**Polish:** Character micro-animations, boss atmosphere, dynamic vignette, near-miss particles.

**Delight:** All Section 8.8 moments, pre-death bullet time, chromatic aberration.

---

## 9. Technical Architecture

### 9.1 Module Structure

```
jungle_dodge/
├── main.py              # Entry point (~30 lines)
├── constants.py          # Magic numbers, screen dims, timing, particle configs
├── themes.py             # THEMES dict + accessor functions
├── entities.py           # Player, all Obstacle subclasses
├── particles.py          # Particle dataclass, ParticleSystem (pooling)
├── audio.py              # AudioManager singleton
├── hud.py                # All draw functions for HUD, overlays, transitions
├── states.py             # GameStateManager + all State subclasses
├── persistence.py        # Save/load for all JSON files
└── assets/
    ├── sounds/
    │   ├── CREDITS.txt
    │   ├── music/         # {theme}_stem_{0-3}.ogg
    │   └── sfx/           # {event}.wav
    └── (no images — procedural)
```

**Dependency graph (arrows = "imports from"):**
```
constants.py      ← (no deps, imported by all)
themes.py         ← constants
persistence.py    ← constants
particles.py      ← constants, themes
audio.py          ← constants
entities.py       ← constants, themes, particles, audio (plays SFX on hit/dodge)
hud.py            ← constants, themes, particles
states.py         ← all above (orchestrates everything)
main.py           ← states, audio, persistence
```
Key constraint: `entities.py` receives AudioManager via dependency injection (GameContext), never imports `hud.py` or `states.py`. `hud.py` never imports `entities.py` — it receives entity state through GameContext.

### 9.2 State Machine

Stack-based `GameStateManager`. Push overlays (pause, volume) on top of play state.

**13 states:**
StartScreenState, TransitionState, PlayState, LevelUpState, BossIntroState, PauseState, VolumeOverlayState, PreDeathState, DeathSequenceState, GameOverState, NameEntryState, LeaderboardState, DailyChallengeState.

**GameContext dataclass** shared across all states: screen, display, audio, persistence, particles, theme, fonts, settings, gameplay state (score, level, streak, lives, difficulty).

### 9.3 Performance Budget

- **Target:** 60fps locked. Logic+draw under 10ms.
- **Expensive ops:** (1) `pygame.transform.scale()` — unavoidable, do once per frame. (2) Particle draws — batch by type, alpha scratch surface. (3) Text rendering — digit cache, dirty-flag re-render only on value change.
- **Particle pool:** Pre-allocate 400 Particle objects to match budget cap. Reuse dead particles. Pool does not grow beyond 400.
- **Static surface caching:** HUD panels, borders, backgrounds cached at theme-load time.
- **F3 debug overlay** during dev: frame time, particle count, obstacle count, state, audio channels.

### 9.4 Save State

**settings.json:**
```json
{
  "version": 1,
  "theme": "jungle",
  "difficulty": "normal",
  "volume_music": 0.7,
  "volume_sfx": 1.0,
  "volume_master": 1.0,
  "muted": false,
  "death_count": 0,
  "first_run": false,
  "show_tutorial": true,
  "fullscreen": true
}
```

**leaderboard.json:**
```json
{
  "version": 1,
  "boards": {
    "normal": [{"name":"AAA","score":14200,"level":12,"max_streak":18,"badges":["UNTOUCHABLE"],"theme":"jungle","date":"2026-03-15"}],
    "easy": [], "hard": [], "daily": []
  },
  "personal_bests": {"normal":14200,"easy":0,"hard":0,"daily":0}
}
```

**daily_challenge.json:**
```json
{
  "version": 1,
  "current_date": "2026-03-15",
  "seed": 20260315,
  "completed": false,
  "best_score": 0,
  "attempts": 0
}
```

**PersistenceManager:** `_load_with_defaults()` handles corrupt/missing files gracefully (shallow merge with defaults). `_migrate()` fills missing keys from newer versions.

### 9.5 AudioManager

Singleton with 12 channels. Stem crossfading via manual lerp in `update(dt)`. Convention-based loading: filename stem = sfx_id. Graceful degradation on missing keys.

```python
class AudioManager:
    def play(self, sfx_id, channel="sfx_obstacle"): ...
    def set_stem_layers(self, intensity): ...  # 0=base, 1=+melody, 2=+intensity, 3=+ambient
    def set_volumes(self, music, sfx, master): ...
    def update(self, dt): ...  # drives fade animations
```

### 9.6 Implementation Order

Each step leaves a playable build:

1. **persistence.py** — no pygame deps, fully unit testable.
2. **constants.py + themes.py** — extract magic numbers and THEMES dict.
3. **particles.py** — pool + alpha scratch surface. Validate in monolith.
4. **audio.py** — AudioManager with no-op fallbacks. Wire SFX calls with placeholder WAVs.
5. **states.py** — extract states one at a time, starting with PlayState.
6. **hud.py** — extract draw functions.
7. **main.py** — shrink to 30 lines.

### 9.7 Testing

**Unit tests (20):** persistence (submit_score, cap, migration, corrupt file), particles (max cap, pool reuse), themes (required keys validation, magenta fallback), audio (mute, unknown SFX), state machine (push/pop/exit contracts, dt cap).

**Manual QA checklist:** Critical path (start→play→die→name→leaderboard→start), daily challenge persistence, all 8 obstacle types, roll i-frames, shield absorption, pause edge cases, audio layering, 60fps at L16+ crescendo, corrupt save handling, simultaneous hit prevention, name entry sanitization.

### 9.8 Asset Pipeline

1. **Bfxr** — generate all SFX. Export .wav.
2. **BeepBox** — compose music stems per theme. Export → convert to .ogg.
3. **freesound.org** — fill gaps (ambient, organic). CC0 only. Log in `CREDITS.txt`.
4. Target: each SFX under 100KB, each stem under 2MB, total under 20MB.

---

## Appendix: Theme Dict Required Keys

Full list of keys every theme must define (validated by unit test):

```
# Identity
name, accent_color, secondary_color, warning_color

# Sky/Background
sky_top, sky_horizon, parallax_mid, parallax_near

# Ground
ground_base, ground_edge, grass_main, grass_highlight

# Character
char_jacket, char_hat, char_hat_band, char_skin, char_pants, char_boots,
char_iframe_glow, char_hit_flash

# Obstacles
vine_base, vine_highlight, bomb_body, bomb_fuse, bomb_warning,
spike_base, spike_tip, boulder_base, boulder_crack,
canopy_drop_base, croc_base, croc_teeth, poison_puddle, bat_body, bat_wing

# HUD
hud_bg, hud_border, hud_text, hud_style, hud_label, hud_primary,
hud_pb_text, hud_pb_beating, hud_wave_push, hud_wave_breather,
timer_normal, timer_warning, streak_bronze, streak_silver, streak_gold,
lives_full, lives_lost, roll_ready, roll_charging,
powerup_shield, powerup_slowmo, powerup_magnet, level_pill_bg, boss_level_pill

# Start Screen
title_primary, title_shadow, selector_border,
diff_easy, diff_normal, diff_hard, diff_selected, daily_button

# Level Up / Boss
new_obstacle_preview, boss_wave_border

# Name Entry
name_entry_active, trophy_gold, beat_callout

# Leaderboard
tab_active, lb_player_row

# Game Over
gameover_headline, new_best_flash, stat_value, badge_bg, flavor_text

# Particles
particle_trail, particle_near_miss, particle_roll, particle_hit_chunk,
particle_hit_flash, near_miss, combo_text,
pu_shield_color, pu_slow_color, pu_score_color, pu_sparkle,
streak_particle, boss_clear_a, boss_clear_b, boss_clear_confetti, boss_clear_spark,
death_core, death_scatter, death_ghost, death_ghost_large,
level_up_particle, level_up_text_color,
delight_note, delight_crown

# Screen Effects
flash_hit, flash_bomb, flash_pu, flash_boss, flash_death, flash_level,
vignette_color, vignette_danger

# Transitions
transition_style, transition_color

# Audio
audio_prefix

# Tutorial
tutorial_arrow
```
