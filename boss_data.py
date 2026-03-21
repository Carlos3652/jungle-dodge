"""
Boss wave data for Jungle Dodge (jd-15).

Each boss wave is a dict with:
  name      - display name for the intro card
  duration  - total wave duration in seconds
  reward    - bonus points awarded on clear
  script    - list of (delay_s, obstacle_class_name, x_pct) tuples

x_pct is a 0.0-1.0 fraction of screen width for spawn position.
obstacle_class_name must match a class name in entities.py.

Mini-boss waves (L16+) are generated dynamically via get_mini_boss().
"""

BOSS_WAVES = {
    5: {
        "name": "STAMPEDE",
        "duration": 20,
        "reward": 500,
        "script": [
            (0.0,  "Vine",    0.2),
            (0.5,  "Vine",    0.8),
            (1.0,  "Vine",    0.5),
            (2.0,  "Boulder", 0.3),
            (2.5,  "Boulder", 0.7),
            (3.5,  "Vine",    0.15),
            (4.0,  "Vine",    0.85),
            (5.0,  "Spike",   0.4),
            (5.3,  "Spike",   0.6),
            (6.5,  "Boulder", 0.5),
            (7.5,  "Vine",    0.3),
            (8.0,  "Vine",    0.7),
            (9.0,  "Spike",   0.2),
            (9.5,  "Spike",   0.8),
            (10.5, "Boulder", 0.4),
            (11.5, "Vine",    0.1),
            (12.0, "Vine",    0.5),
            (12.5, "Vine",    0.9),
            (14.0, "Boulder", 0.3),
            (14.5, "Boulder", 0.7),
            (15.5, "Spike",   0.5),
            (16.5, "Vine",    0.25),
            (17.0, "Vine",    0.75),
            (18.0, "Boulder", 0.5),
            (19.0, "Spike",   0.4),
        ],
    },
    10: {
        "name": "PREDATOR RUN",
        "duration": 25,
        "reward": 750,
        "script": [
            (0.0,  "Bomb",    0.3),
            (0.5,  "Bomb",    0.7),
            (1.5,  "Spike",   0.5),
            (2.0,  "Spike",   0.2),
            (2.5,  "Spike",   0.8),
            (3.5,  "Vine",    0.4),
            (4.0,  "Vine",    0.6),
            (5.0,  "Boulder", 0.5),
            (5.5,  "Bomb",    0.2),
            (6.5,  "Spike",   0.3),
            (7.0,  "Spike",   0.7),
            (8.0,  "Bomb",    0.5),
            (9.0,  "Vine",    0.15),
            (9.5,  "Vine",    0.85),
            (10.5, "Boulder", 0.3),
            (11.0, "Boulder", 0.7),
            (12.0, "Spike",   0.5),
            (13.0, "Bomb",    0.4),
            (13.5, "Bomb",    0.6),
            (14.5, "Vine",    0.2),
            (15.0, "Vine",    0.8),
            (16.0, "Spike",   0.3),
            (16.5, "Spike",   0.7),
            (17.5, "Boulder", 0.5),
            (18.5, "Bomb",    0.3),
            (19.0, "Bomb",    0.7),
            (20.0, "Spike",   0.5),
            (21.0, "Vine",    0.4),
            (21.5, "Vine",    0.6),
            (23.0, "Boulder", 0.5),
        ],
    },
    15: {
        "name": "EVERYTHING",
        "duration": 30,
        "reward": 1000,
        "script": [
            (0.0,  "Bomb",    0.5),
            (0.5,  "Vine",    0.2),
            (0.5,  "Vine",    0.8),
            (1.5,  "Spike",   0.3),
            (1.5,  "Spike",   0.7),
            (2.5,  "Boulder", 0.4),
            (3.0,  "Boulder", 0.6),
            (4.0,  "Bomb",    0.2),
            (4.5,  "Bomb",    0.8),
            (5.5,  "Spike",   0.5),
            (6.0,  "Vine",    0.15),
            (6.0,  "Vine",    0.85),
            (7.0,  "Spike",   0.4),
            (7.5,  "Spike",   0.6),
            (8.5,  "Boulder", 0.3),
            (9.0,  "Boulder", 0.7),
            (10.0, "Bomb",    0.5),
            (11.0, "Vine",    0.3),
            (11.0, "Vine",    0.7),
            (12.0, "Spike",   0.2),
            (12.5, "Spike",   0.8),
            (13.5, "Boulder", 0.5),
            (14.5, "Bomb",    0.3),
            (15.0, "Bomb",    0.7),
            (16.0, "Vine",    0.5),
            (17.0, "Spike",   0.4),
            (17.0, "Spike",   0.6),
            (18.0, "Boulder", 0.2),
            (18.5, "Boulder", 0.8),
            (19.5, "Bomb",    0.5),
            (20.5, "Vine",    0.1),
            (20.5, "Vine",    0.9),
            (21.5, "Spike",   0.3),
            (22.0, "Spike",   0.7),
            (23.0, "Boulder", 0.5),
            (24.0, "Bomb",    0.4),
            (24.5, "Bomb",    0.6),
            (25.5, "Vine",    0.25),
            (25.5, "Vine",    0.75),
            (27.0, "Spike",   0.5),
            (28.0, "Boulder", 0.3),
            (28.5, "Boulder", 0.7),
        ],
    },
}

# Mini-boss template (L16+, every 5 levels)
MINI_BOSS_DURATION = 15
MINI_BOSS_REWARD = 300
MINI_BOSS_OBSTACLES = ["Vine", "Bomb", "Spike", "Boulder"]

def get_mini_boss(level):
    """Generate a mini-boss script for L16+ (every 5 levels).

    Returns a boss dict with a procedurally generated 15-entry script
    using the standard obstacle types.
    """
    import random
    rng = random.Random(level * 7919)  # deterministic per level
    script = []
    t = 0.0
    for _ in range(15):
        cls_name = rng.choice(MINI_BOSS_OBSTACLES)
        x_pct = rng.uniform(0.1, 0.9)
        script.append((round(t, 1), cls_name, round(x_pct, 2)))
        t += rng.uniform(0.8, 1.2)
    return {
        "name": f"MINI-BOSS L{level}",
        "duration": MINI_BOSS_DURATION,
        "reward": MINI_BOSS_REWARD,
        "script": script,
    }


def get_boss_wave(level):
    """Return boss wave data for the given level, or None if not a boss level.

    Boss levels: 5, 10, 15 (scripted), then every 5 levels from 16+ (mini-boss).
    """
    if level in BOSS_WAVES:
        return BOSS_WAVES[level]
    if level >= 16 and level % 5 == 0:
        return get_mini_boss(level)
    return None


def is_boss_level(level):
    """Return True if this level triggers a boss wave."""
    return get_boss_wave(level) is not None
