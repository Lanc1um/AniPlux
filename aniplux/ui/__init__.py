"""
UI Layer - Visual design system and Rich components.

This module contains the visual design system, theme management, and Rich UI
components that provide a consistent and beautiful interface across all CLI commands.
"""

from aniplux.ui.components import UIComponents
from aniplux.ui.themes import ThemeManager, ThemeName, get_theme, set_theme
from aniplux.ui.error_handler import ErrorHandler, handle_error, display_warning, display_info
from aniplux.ui.progress import (
    SimpleProgressManager, 
    get_progress_manager, 
    download_progress_context,
    update_download_progress,
    finish_download_progress,
    status_spinner,
    search_progress
)
from aniplux.ui.console import get_console, setup_console, update_console_theme
from aniplux.ui.styling import (
    StyleFormatter,
    format_title,
    format_success,
    format_warning,
    format_error,
    format_info,
    format_muted,
    format_quality,
    format_file_size,
)

__all__ = [
    # Core UI Components
    "UIComponents",
    # Theme System
    "ThemeManager",
    "ThemeName",
    "get_theme",
    "set_theme",
    # Error Handling
    "ErrorHandler",
    "handle_error",
    "display_warning",
    "display_info",
    # Progress Management
    "SimpleProgressManager",
    "get_progress_manager",
    "download_progress_context",
    "update_download_progress",
    "finish_download_progress",
    "status_spinner",
    "search_progress",
    # Console Management
    "get_console",
    "setup_console",
    "update_console_theme",
    # Styling Utilities
    "StyleFormatter",
    "format_title",
    "format_success",
    "format_warning",
    "format_error",
    "format_info",
    "format_muted",
    "format_quality",
    "format_file_size",
]