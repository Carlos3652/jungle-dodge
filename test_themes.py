"""Tests for themes.py — Task jd-02."""

import pytest

from themes import (
    DEFAULT_THEME,
    FALLBACK_COLOR,
    REQUIRED_KEYS,
    THEMES,
    get_color,
    get_theme,
    list_themes,
)


# ---------------------------------------------------------------------------
# Required-keys coverage
# ---------------------------------------------------------------------------

class TestAllThemesHaveRequiredKeys:
    """Every registered theme must define every key from the spec Appendix."""

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_all_themes_have_required_keys(self, theme_name: str) -> None:
        theme = THEMES[theme_name]
        missing = REQUIRED_KEYS - theme.keys()
        assert not missing, (
            f"Theme '{theme_name}' is missing {len(missing)} required key(s): "
            f"{sorted(missing)}"
        )

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_no_extra_keys(self, theme_name: str) -> None:
        """Warn about typos — every key should be in REQUIRED_KEYS."""
        theme = THEMES[theme_name]
        extra = theme.keys() - REQUIRED_KEYS
        assert not extra, (
            f"Theme '{theme_name}' has {len(extra)} unexpected key(s): "
            f"{sorted(extra)}"
        )


# ---------------------------------------------------------------------------
# Magenta fallback
# ---------------------------------------------------------------------------

class TestGetColorMagentaFallback:
    """get_color() returns magenta (255,0,255) for missing keys."""

    def test_missing_key_returns_magenta(self) -> None:
        color = get_color("this_key_does_not_exist")
        assert color == FALLBACK_COLOR

    def test_valid_key_returns_tuple(self) -> None:
        color = get_color("sky_top")
        assert isinstance(color, tuple)
        assert len(color) == 3
        assert color != FALLBACK_COLOR

    def test_string_key_returns_magenta(self) -> None:
        """String-valued keys (e.g. hud_style) should fallback to magenta."""
        color = get_color("hud_style")
        assert color == FALLBACK_COLOR

    def test_explicit_theme_param(self) -> None:
        theme = get_theme("jungle")
        color = get_color("sky_top", theme=theme)
        assert color == theme["sky_top"]


# ---------------------------------------------------------------------------
# get_theme defaults
# ---------------------------------------------------------------------------

class TestGetThemeReturnsJungleDefault:
    """get_theme() with no args returns the jungle theme."""

    def test_default_returns_jungle(self) -> None:
        theme = get_theme()
        assert theme is THEMES["jungle"]
        assert theme["name"] == "Jungle"

    def test_explicit_jungle(self) -> None:
        theme = get_theme("jungle")
        assert theme["name"] == "Jungle"

    def test_unknown_theme_raises(self) -> None:
        with pytest.raises(KeyError):
            get_theme("atlantis")

    def test_none_returns_default(self) -> None:
        theme = get_theme(None)
        assert theme is THEMES[DEFAULT_THEME]


# ---------------------------------------------------------------------------
# list_themes
# ---------------------------------------------------------------------------

class TestListThemes:
    def test_returns_list(self) -> None:
        result = list_themes()
        assert isinstance(result, list)

    def test_contains_jungle(self) -> None:
        assert "jungle" in list_themes()

    def test_sorted(self) -> None:
        result = list_themes()
        assert result == sorted(result)
