"""
Theme System - Color palettes and styling configuration.

This module provides theme management with multiple color schemes
and consistent styling across all UI components.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

from rich.style import Style
from rich.theme import Theme


class ThemeName(str, Enum):
    """Available theme names."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    COLORFUL = "colorful"


@dataclass
class ColorPalette:
    """Color palette definition for a theme."""
    
    # Primary colors
    primary: str
    secondary: str
    accent: str
    
    # Status colors
    success: str
    warning: str
    error: str
    info: str
    
    # Text colors
    text_primary: str
    text_secondary: str
    text_muted: str
    
    # Background colors
    background: str
    surface: str
    
    # Border colors
    border_primary: str
    border_secondary: str


class ThemeManager:
    """Manages theme selection and color palette configuration."""
    
    def __init__(self):
        """Initialize theme manager with predefined palettes."""
        self._palettes = self._create_palettes()
        self._current_theme = ThemeName.DEFAULT
    
    def _create_palettes(self) -> Dict[ThemeName, ColorPalette]:
        """Create predefined color palettes."""
        return {
            ThemeName.DEFAULT: ColorPalette(
                primary="blue",
                secondary="cyan",
                accent="magenta",
                success="green",
                warning="yellow",
                error="red",
                info="blue",
                text_primary="white",
                text_secondary="bright_white",
                text_muted="dim white",
                background="black",
                surface="bright_black",
                border_primary="blue",
                border_secondary="dim blue"
            ),
            
            ThemeName.DARK: ColorPalette(
                primary="bright_blue",
                secondary="bright_cyan",
                accent="bright_magenta",
                success="bright_green",
                warning="bright_yellow",
                error="bright_red",
                info="bright_blue",
                text_primary="bright_white",
                text_secondary="white",
                text_muted="bright_black",
                background="black",
                surface="grey23",
                border_primary="bright_blue",
                border_secondary="grey37"
            ),
            
            ThemeName.LIGHT: ColorPalette(
                primary="blue",
                secondary="dark_cyan",
                accent="dark_magenta",
                success="dark_green",
                warning="dark_orange",
                error="dark_red",
                info="blue",
                text_primary="black",
                text_secondary="grey19",
                text_muted="grey37",
                background="white",
                surface="grey93",
                border_primary="blue",
                border_secondary="grey70"
            ),
            
            ThemeName.COLORFUL: ColorPalette(
                primary="dodger_blue1",
                secondary="deep_sky_blue1",
                accent="hot_pink",
                success="spring_green1",
                warning="gold1",
                error="red1",
                info="cornflower_blue",
                text_primary="white",
                text_secondary="light_cyan1",
                text_muted="grey62",
                background="black",
                surface="grey15",
                border_primary="dodger_blue1",
                border_secondary="deep_sky_blue3"
            )
        }
    
    def get_palette(self, theme_name: Optional[ThemeName] = None) -> ColorPalette:
        """
        Get color palette for a theme.
        
        Args:
            theme_name: Theme to get palette for (defaults to current theme)
            
        Returns:
            ColorPalette for the specified theme
        """
        if theme_name is None:
            theme_name = self._current_theme
        
        return self._palettes.get(theme_name, self._palettes[ThemeName.DEFAULT])
    
    def set_theme(self, theme_name: ThemeName) -> None:
        """
        Set the current theme.
        
        Args:
            theme_name: Theme to activate
        """
        if theme_name in self._palettes:
            self._current_theme = theme_name
        else:
            raise ValueError(f"Unknown theme: {theme_name}")
    
    def get_current_theme(self) -> ThemeName:
        """Get the currently active theme name."""
        return self._current_theme
    
    def create_rich_theme(self, theme_name: Optional[ThemeName] = None) -> Theme:
        """
        Create a Rich Theme object from a color palette.
        
        Args:
            theme_name: Theme to create Rich theme for
            
        Returns:
            Rich Theme object
        """
        palette = self.get_palette(theme_name)
        
        # Define style mappings
        styles = {
            # Component styles
            "panel.border": palette.border_primary,
            "panel.title": f"bold {palette.primary}",
            "table.header": f"bold {palette.secondary}",
            "table.border": palette.border_secondary,
            "progress.bar": palette.primary,
            "progress.complete": palette.success,
            "progress.remaining": palette.text_muted,
            
            # Status styles
            "success": palette.success,
            "warning": palette.warning,
            "error": palette.error,
            "info": palette.info,
            
            # Text styles
            "primary": palette.primary,
            "secondary": palette.secondary,
            "accent": palette.accent,
            "muted": palette.text_muted,
            
            # Semantic styles
            "title": f"bold {palette.primary}",
            "subtitle": palette.secondary,
            "highlight": f"bold {palette.accent}",
            "link": f"underline {palette.primary}",
            "code": f"bold {palette.accent}",
            
            # Status indicators
            "status.enabled": palette.success,
            "status.disabled": palette.text_muted,
            "status.error": palette.error,
            "status.loading": palette.warning,
            
            # Quality indicators
            "quality.high": palette.success,
            "quality.medium": palette.warning,
            "quality.low": palette.error,
        }
        
        return Theme(styles)
    
    def get_available_themes(self) -> list[ThemeName]:
        """Get list of available theme names."""
        return list(self._palettes.keys())


# Global theme manager instance
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return _theme_manager


def get_theme(theme_name: Optional[ThemeName] = None) -> Theme:
    """
    Get a Rich Theme object.
    
    Args:
        theme_name: Theme to get (defaults to current theme)
        
    Returns:
        Rich Theme object
    """
    return _theme_manager.create_rich_theme(theme_name)


def get_palette(theme_name: Optional[ThemeName] = None) -> ColorPalette:
    """
    Get color palette for a theme.
    
    Args:
        theme_name: Theme to get palette for (defaults to current theme)
        
    Returns:
        ColorPalette for the specified theme
    """
    return _theme_manager.get_palette(theme_name)


def set_theme(theme_name: ThemeName) -> None:
    """
    Set the global theme.
    
    Args:
        theme_name: Theme to activate
    """
    _theme_manager.set_theme(theme_name)


# Export theme system components
__all__ = [
    "ThemeName",
    "ColorPalette",
    "ThemeManager",
    "get_theme_manager",
    "get_theme",
    "get_palette",
    "set_theme",
]