"""
Console Management - Centralized Rich console configuration.

This module provides console setup and management with theme integration
and consistent configuration across the application.
"""

import os
import sys
from typing import Optional

from rich.console import Console
from rich.terminal_theme import TerminalTheme

from aniplux.ui.themes import get_theme, ThemeName


# Global console instance
_console: Optional[Console] = None


def setup_console(
    theme_name: Optional[ThemeName] = None,
    force_terminal: Optional[bool] = None,
    width: Optional[int] = None,
    height: Optional[int] = None
) -> Console:
    """
    Set up and configure the global Rich console.
    
    Args:
        theme_name: Theme to apply to the console
        force_terminal: Force terminal mode detection
        width: Console width override
        height: Console height override
        
    Returns:
        Configured Rich Console instance
    """
    global _console
    
    # Get theme
    theme = get_theme(theme_name)
    
    # Configure console options
    console_kwargs = {
        "theme": theme,
        "stderr": False,  # Use stdout for all output
        "force_terminal": force_terminal,
        "color_system": "auto",  # Auto-detect color support
        "legacy_windows": False,  # Use modern Windows terminal features
    }
    
    # Add size overrides if specified
    if width is not None:
        console_kwargs["width"] = width
    if height is not None:
        console_kwargs["height"] = height
    
    # Create new console instance
    _console = Console(**console_kwargs)
    
    return _console


def get_console() -> Console:
    """
    Get the global Rich console instance.
    
    Creates a default console if none exists.
    
    Returns:
        Rich Console instance
    """
    global _console
    
    if _console is None:
        _console = setup_console()
    
    return _console


def update_console_theme(theme_name: ThemeName) -> None:
    """
    Update the console theme.
    
    Args:
        theme_name: New theme to apply
    """
    global _console
    
    if _console is not None:
        # Create a new console with the updated theme since _theme is not directly assignable
        _console = setup_console(theme_name)


def get_console_info() -> dict:
    """
    Get information about the current console configuration.
    
    Returns:
        Dictionary containing console information
    """
    console = get_console()
    
    return {
        "width": console.width,
        "height": console.height,
        "color_system": console.color_system,
        "is_terminal": console.is_terminal,
        "is_dumb_terminal": console.is_dumb_terminal,
        "is_jupyter": console.is_jupyter,
        "encoding": console.encoding,
        "legacy_windows": console.legacy_windows,
    }


def detect_terminal_capabilities() -> dict:
    """
    Detect terminal capabilities and features.
    
    Returns:
        Dictionary containing capability information
    """
    console = get_console()
    
    capabilities = {
        "colors": "none",
        "unicode": False,
        "hyperlinks": False,
        "images": False,
        "mouse": False,
    }
    
    # Detect color support
    if console.color_system == "truecolor":
        capabilities["colors"] = "truecolor"
    elif console.color_system == "256":
        capabilities["colors"] = "256"
    elif console.color_system == "standard":
        capabilities["colors"] = "16"
    elif console.color_system == "windows":
        capabilities["colors"] = "windows"
    
    # Detect Unicode support
    try:
        # Test Unicode rendering
        console.print("", end="")  # Empty print to test encoding
        capabilities["unicode"] = True
    except UnicodeEncodeError:
        capabilities["unicode"] = False
    
    # Detect hyperlink support (basic heuristic)
    if console.is_terminal and not console.is_dumb_terminal:
        # Most modern terminals support hyperlinks
        term = sys.platform
        if term != "win32" or "WT_SESSION" in os.environ:
            capabilities["hyperlinks"] = True
    
    return capabilities


def create_fallback_console() -> Console:
    """
    Create a fallback console for limited terminals.
    
    Returns:
        Console configured for basic terminal compatibility
    """
    return Console(
        color_system="standard",
        force_terminal=True,
        width=80,
        legacy_windows=True,
        theme=get_theme(ThemeName.DEFAULT)
    )


def is_color_supported() -> bool:
    """
    Check if the terminal supports colors.
    
    Returns:
        True if colors are supported
    """
    console = get_console()
    return console.color_system is not None and console.color_system != "none"


def is_unicode_supported() -> bool:
    """
    Check if the terminal supports Unicode characters.
    
    Returns:
        True if Unicode is supported
    """
    try:
        console = get_console()
        # Test with a common Unicode character
        test_output = console.render_str("✓")
        return len(test_output) > 0
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


# Export console management functions
__all__ = [
    "setup_console",
    "get_console",
    "update_console_theme",
    "get_console_info",
    "detect_terminal_capabilities",
    "create_fallback_console",
    "is_color_supported",
    "is_unicode_supported",
]