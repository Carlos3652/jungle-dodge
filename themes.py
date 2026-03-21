"""
Theme data for Jungle Dodge.

Single THEMES dict drives ALL visual theming — zero theme-conditional branches
in obstacle draw code.  All draw code reads T["key"] from the active theme.

Missing-key fallback: magenta (255, 0, 255) — instantly visible during dev.

Spec reference: docs/superpowers/specs/2026-03-15-jungle-dodge-overhaul-design.md
                Section 5.5 + Appendix
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Union

# Magenta fallback — unmistakable "you forgot a key" colour
FALLBACK_COLOR: Tuple[int, int, int] = (255, 0, 255)

# ---------------------------------------------------------------------------
# Required keys every theme MUST define  (95 keys from spec Appendix)
# ---------------------------------------------------------------------------
REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        # Identity (4)
        "name",
        "accent_color",
        "secondary_color",
        "warning_color",
        # Sky / Background (4)
        "sky_top",
        "sky_horizon",
        "parallax_mid",
        "parallax_near",
        # Ground (4)
        "ground_base",
        "ground_edge",
        "grass_main",
        "grass_highlight",
        # Character (8)
        "char_jacket",
        "char_hat",
        "char_hat_band",
        "char_skin",
        "char_pants",
        "char_boots",
        "char_iframe_glow",
        "char_hit_flash",
        # Obstacles (15)
        "vine_base",
        "vine_highlight",
        "bomb_body",
        "bomb_fuse",
        "bomb_warning",
        "spike_base",
        "spike_tip",
        "boulder_base",
        "boulder_crack",
        "canopy_drop_base",
        "croc_base",
        "croc_teeth",
        "poison_puddle",
        "bat_body",
        "bat_wing",
        # HUD (22)
        "hud_bg",
        "hud_border",
        "hud_text",
        "hud_style",
        "hud_label",
        "hud_primary",
        "hud_pb_text",
        "hud_pb_beating",
        "hud_wave_push",
        "hud_wave_breather",
        "timer_normal",
        "timer_warning",
        "streak_bronze",
        "streak_silver",
        "streak_gold",
        "lives_full",
        "lives_lost",
        "roll_ready",
        "roll_charging",
        "powerup_shield",
        "powerup_slowmo",
        "powerup_magnet",
        "level_pill_bg",
        "boss_level_pill",
        # Start screen (6)
        "title_primary",
        "title_shadow",
        "selector_border",
        "diff_easy",
        "diff_normal",
        "diff_hard",
        "diff_selected",
        "daily_button",
        # Level-up / boss (2)
        "new_obstacle_preview",
        "boss_wave_border",
        # Name entry (3)
        "name_entry_active",
        "trophy_gold",
        "beat_callout",
        # Leaderboard (2)
        "tab_active",
        "lb_player_row",
        # Game over (5)
        "gameover_headline",
        "new_best_flash",
        "stat_value",
        "badge_bg",
        "flavor_text",
        # Particles (16)
        "particle_trail",
        "particle_near_miss",
        "particle_roll",
        "particle_hit_chunk",
        "particle_hit_flash",
        "near_miss",
        "combo_text",
        "pu_shield_color",
        "pu_slow_color",
        "pu_score_color",
        "pu_sparkle",
        "streak_particle",
        "boss_clear_a",
        "boss_clear_b",
        "boss_clear_confetti",
        "boss_clear_spark",
        "death_core",
        "death_scatter",
        "death_ghost",
        "death_ghost_large",
        "level_up_particle",
        "level_up_text_color",
        "delight_note",
        "delight_crown",
        # Screen effects (6)
        "flash_hit",
        "flash_bomb",
        "flash_pu",
        "flash_boss",
        "flash_death",
        "flash_level",
        "vignette_color",
        "vignette_danger",
        # Transitions (2)
        "transition_style",
        "transition_color",
        # Audio (1)
        "audio_prefix",
        # Tutorial (1)
        "tutorial_arrow",
    }
)

# ---------------------------------------------------------------------------
# THEMES — one entry per visual theme.  Jungle is the launch default.
# ---------------------------------------------------------------------------
THEMES: Dict[str, Dict[str, Union[str, Tuple[int, int, int]]]] = {
    "jungle": {
        # ---- Identity ----
        "name": "Jungle",
        "accent_color": (38, 212, 72),       # neon green (vine)
        "secondary_color": (200, 70, 255),    # electric purple (spike)
        "warning_color": (220, 50, 50),       # red

        # ---- Sky / Background ----
        "sky_top": (4, 10, 6),
        "sky_horizon": (10, 25, 10),
        "parallax_mid": (10, 22, 10),
        "parallax_near": (18, 38, 16),

        # ---- Ground ----
        "ground_base": (55, 35, 18),
        "ground_edge": (75, 50, 25),
        "grass_main": (38, 85, 28),
        "grass_highlight": (55, 115, 35),

        # ---- Character ----
        "char_jacket": (185, 155, 90),        # leather jacket warm tone
        "char_hat": (130, 90, 45),
        "char_hat_band": (190, 145, 45),      # gold hat band
        "char_skin": (220, 180, 130),
        "char_pants": (80, 60, 40),
        "char_boots": (50, 35, 20),
        "char_iframe_glow": (255, 255, 255),  # white flash
        "char_hit_flash": (220, 50, 50),      # red

        # ---- Obstacles ----
        "vine_base": (32, 195, 65),           # natural green vine
        "vine_highlight": (15, 110, 35),
        "bomb_body": (25, 25, 25),
        "bomb_fuse": (255, 90, 20),           # coiled fuse neon orange
        "bomb_warning": (255, 50, 50),
        "spike_base": (190, 65, 240),         # bone-ivory spike with purple tint
        "spike_tip": (130, 35, 180),
        "boulder_base": (130, 108, 80),       # earth-tone boulder
        "boulder_crack": (100, 80, 60),
        "canopy_drop_base": (34, 140, 50),
        "croc_base": (50, 100, 40),
        "croc_teeth": (240, 240, 220),
        "poison_puddle": (80, 200, 40),
        "bat_body": (60, 50, 70),
        "bat_wing": (90, 70, 110),

        # ---- HUD ----
        "hud_bg": (42, 46, 38),              # stone
        "hud_border": (62, 68, 56),           # stone_hi
        "hud_text": (255, 255, 255),          # white
        "hud_style": "stone",
        "hud_label": (120, 130, 90),          # olive
        "hud_primary": (38, 212, 72),         # vine green
        "hud_pb_text": (255, 210, 30),        # yellow
        "hud_pb_beating": (220, 50, 50),      # red
        "hud_wave_push": (255, 140, 0),       # orange
        "hud_wave_breather": (0, 200, 160),   # teal
        "timer_normal": (255, 255, 255),
        "timer_warning": (220, 50, 50),
        "streak_bronze": (205, 127, 50),
        "streak_silver": (192, 192, 192),
        "streak_gold": (212, 160, 32),
        "lives_full": (140, 26, 26),          # heart
        "lives_lost": (40, 10, 10),           # heart_empty
        "roll_ready": (0, 200, 160),          # teal
        "roll_charging": (80, 80, 80),
        "powerup_shield": (0, 200, 160),      # teal
        "powerup_slowmo": (200, 70, 255),     # purple
        "powerup_magnet": (255, 210, 30),     # yellow
        "level_pill_bg": (18, 45, 18),
        "boss_level_pill": (140, 26, 26),

        # ---- Start screen ----
        "title_primary": (38, 212, 72),       # vine green
        "title_shadow": (6, 14, 8),           # sky_top
        "selector_border": (38, 212, 72),
        "diff_easy": (38, 212, 72),           # green
        "diff_normal": (255, 210, 30),        # yellow
        "diff_hard": (220, 50, 50),           # red
        "diff_selected": (255, 255, 255),
        "daily_button": (255, 140, 0),        # orange

        # ---- Level-up / Boss ----
        "new_obstacle_preview": (255, 255, 255),
        "boss_wave_border": (220, 50, 50),

        # ---- Name entry ----
        "name_entry_active": (38, 212, 72),
        "trophy_gold": (212, 160, 32),
        "beat_callout": (255, 210, 30),

        # ---- Leaderboard ----
        "tab_active": (38, 212, 72),
        "lb_player_row": (18, 45, 18),

        # ---- Game over ----
        "gameover_headline": (220, 50, 50),
        "new_best_flash": (255, 210, 30),
        "stat_value": (255, 255, 255),
        "badge_bg": (42, 46, 38),
        "flavor_text": (120, 130, 90),

        # ---- Particles ----
        "particle_trail": (38, 212, 72),
        "particle_near_miss": (255, 200, 50),   # spark
        "particle_roll": (0, 200, 160),          # teal
        "particle_hit_chunk": (220, 50, 50),
        "particle_hit_flash": (255, 255, 255),
        "near_miss": (255, 210, 30),
        "combo_text": (255, 210, 30),
        "pu_shield_color": (0, 200, 160),
        "pu_slow_color": (200, 70, 255),
        "pu_score_color": (255, 210, 30),
        "pu_sparkle": (255, 255, 255),
        "streak_particle": (212, 160, 32),
        "boss_clear_a": (38, 212, 72),
        "boss_clear_b": (200, 70, 255),
        "boss_clear_confetti": (255, 210, 30),
        "boss_clear_spark": (255, 200, 50),
        "death_core": (220, 50, 50),
        "death_scatter": (140, 26, 26),
        "death_ghost": (255, 255, 255),
        "death_ghost_large": (200, 200, 200),
        "level_up_particle": (38, 212, 72),
        "level_up_text_color": (255, 210, 30),
        "delight_note": (255, 200, 50),
        "delight_crown": (212, 160, 32),

        # ---- Screen effects ----
        "flash_hit": (220, 50, 50),
        "flash_bomb": (255, 140, 0),
        "flash_pu": (0, 200, 160),
        "flash_boss": (200, 70, 255),
        "flash_death": (220, 50, 50),
        "flash_level": (38, 212, 72),
        "vignette_color": (0, 0, 0),
        "vignette_danger": (100, 10, 10),

        # ---- Transitions ----
        "transition_style": "vine_sweep",
        "transition_color": (6, 14, 8),

        # ---- Audio ----
        "audio_prefix": "jungle",

        # ---- Tutorial ----
        "tutorial_arrow": (38, 212, 72),
    },
}

# Default theme name
DEFAULT_THEME = "jungle"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_theme(name: str | None = None) -> Dict[str, Union[str, Tuple[int, int, int]]]:
    """Return a theme dict by name.  Defaults to *jungle* if *name* is None."""
    if name is None:
        name = DEFAULT_THEME
    return THEMES[name]


def get_color(
    key: str,
    theme: Dict[str, Union[str, Tuple[int, int, int]]] | None = None,
) -> Tuple[int, int, int]:
    """Look up a colour from *theme* (default: jungle).

    Returns magenta ``(255, 0, 255)`` for any missing key so artists
    can instantly spot holes during development.
    """
    if theme is None:
        theme = get_theme()
    value = theme.get(key, FALLBACK_COLOR)
    # Some keys are strings (hud_style, transition_style, audio_prefix, name).
    # Callers that ask for a colour should only pass colour keys, but guard
    # against accidents by returning fallback for non-tuple values.
    if not isinstance(value, tuple):
        return FALLBACK_COLOR
    return value  # type: ignore[return-value]


def list_themes() -> List[str]:
    """Return sorted list of available theme names."""
    return sorted(THEMES.keys())
