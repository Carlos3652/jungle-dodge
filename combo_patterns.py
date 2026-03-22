"""
Named combo pattern definitions for Jungle Dodge (jd-16).

Each pattern is a scripted multi-obstacle spawn that creates a specific
tactical challenge. Patterns trigger during "push" wave phases.

Format:
  name      - display name for "PATTERN CLEAR!" pop text
  min_level - minimum level to appear
  clear_bonus - points awarded when all obstacles dodged
  spawns    - list of (delay_s, class_name, x_pct) tuples
              x_pct is 0.0-1.0 fraction of screen width (None = class picks own)
              class_name "ClusterSpike" gets special handling via spawn_cluster_spike()
"""

COMBO_PATTERNS = {
    "funnel": {
        "name": "The Funnel",
        "min_level": 4,
        "clear_bonus": 50,
        "spawns": [
            (0.0, "Vine", 0.1),       # left vine
            (0.0, "Vine", 0.9),       # right vine
            (0.6, "Spike", 0.5),      # center spike
        ],
    },
    "crossfire": {
        "name": "The Crossfire",
        "min_level": 5,
        "clear_bonus": 50,
        "spawns": [
            (0.0, "Boulder", 0.2),
            (0.3, "CrocSnap", None),   # CrocSnap picks its own side
        ],
    },
    "shell_game": {
        "name": "The Shell Game",
        "min_level": 4,
        "clear_bonus": 50,
        "spawns": [
            (0.0, "CanopyDrop", 0.25),
            (0.0, "CanopyDrop", 0.5),
            (0.0, "CanopyDrop", 0.75),
        ],
    },
    "rolling_wave": {
        "name": "The Rolling Wave",
        "min_level": 5,
        "clear_bonus": 50,
        "spawns": [
            (0.0, "Boulder", 0.5),
            (0.8, "VineSnap", 0.5),
        ],
    },
    "triple_stack": {
        "name": "The Triple Stack",
        "min_level": 6,
        "clear_bonus": 50,
        "spawns": [
            (0.0, "Bomb", 0.5),
            (0.3, "ClusterSpike", 0.2),
            (0.3, "ClusterSpike", 0.8),
        ],
    },
}

COMBO_CLEAR_BONUS = 50
