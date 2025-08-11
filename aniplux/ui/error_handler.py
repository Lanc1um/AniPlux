"""
Error Handler - Beautiful error displays with context and suggestions.

This module provides consistent error handling and display across
the application with helpful context and actionable suggestions.
"""

import traceback
from typing import Optional, Any, Dict, List

from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.tree import Tree

from aniplux.core.exceptions import (
    AniPluxError,
    ConfigurationError,
    PluginError,
    NetworkError,
    DownloadError,
    SearchError,
    ValidationError
)
from aniplux.ui.console import get_console
from aniplux.ui.themes import get_palette


class ErrorHandler:
    """Handles error display with consistent formatting and helpful context."""
    
    def __init__(self):
        """Initialize error handler with current theme."""
        self.console = get_console()
        self.palette = get_palette()
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """
        Handle and display an error with appropriate formatting.
        
        Args:
            error: Exception to handle
            context: Additional context about where the error occurred
            show_traceback: Whether to show the full traceback
        """
        if isinstance(error, AniPluxError):
            self._handle_aniplux_error(error, context, show_traceback)
        else:
            self._handle_generic_error(error, context, show_traceback)
    
    def _handle_aniplux_error(
        self,
        error: AniPluxError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Handle AniPlux-specific errors with specialized formatting."""
        if isinstance(error, ConfigurationError):
            self._display_configuration_error(error, context, show_traceback)
        elif isinstance(error, PluginError):
            self._display_plugin_error(error, context, show_traceback)
        elif isinstance(error, NetworkError):
            self._display_network_error(error, context, show_traceback)
        elif isinstance(error, DownloadError):
            self._display_download_error(error, context, show_traceback)
        elif isinstance(error, SearchError):
            self._display_search_error(error, context, show_traceback)
        elif isinstance(error, ValidationError):
            self._display_validation_error(error, context, show_traceback)
        else:
            self._display_generic_aniplux_error(error, context, show_traceback)
    
    def _display_configuration_error(
        self,
        error: ConfigurationError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Display configuration error with specific suggestions."""
        content_parts = []
        
        # Error message
        content_parts.append(f"[{self.palette.error}]{error.message}[/{self.palette.error}]")
        
        if error.config_path:
            content_parts.append(f"\n[dim]Configuration file:[/dim] [cyan]{error.config_path}[/cyan]")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        # Suggestions
        suggestions = [
            "Check configuration file syntax and format",
            "Verify all required settings are present",
            "Use [cyan]aniplux config[/cyan] to validate configuration",
            "Reset to defaults with [cyan]aniplux config reset[/cyan]"
        ]
        
        content_parts.append(f"\n\n[{self.palette.info}]💡 Suggestions:[/{self.palette.info}]")
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        if show_traceback and error.details:
            content_parts.append(f"\n\n[dim]Details:[/dim]\n{error.details}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="⚙️  Configuration Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _display_plugin_error(
        self,
        error: PluginError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Display plugin error with plugin-specific suggestions."""
        content_parts = []
        
        # Error message
        content_parts.append(f"[{self.palette.error}]{error.message}[/{self.palette.error}]")
        
        if error.plugin_name:
            content_parts.append(f"\n[dim]Plugin:[/dim] [cyan]{error.plugin_name}[/cyan]")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        # Plugin-specific suggestions
        suggestions = [
            "Check plugin configuration and settings",
            "Verify plugin is enabled in sources configuration",
            "Try reloading plugins with [cyan]aniplux sources reload[/cyan]",
            "Use alternative sources if available"
        ]
        
        content_parts.append(f"\n\n[{self.palette.info}]💡 Suggestions:[/{self.palette.info}]")
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        if show_traceback and error.details:
            content_parts.append(f"\n\n[dim]Details:[/dim]\n{error.details}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="🔌 Plugin Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _display_network_error(
        self,
        error: NetworkError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Display network error with connectivity suggestions."""
        content_parts = []
        
        # Error message
        content_parts.append(f"[{self.palette.error}]{error.message}[/{self.palette.error}]")
        
        if error.url:
            content_parts.append(f"\n[dim]URL:[/dim] [blue]{error.url}[/blue]")
        
        if error.status_code:
            content_parts.append(f"\n[dim]Status Code:[/dim] {error.status_code}")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        # Network-specific suggestions
        suggestions = [
            "Check your internet connection",
            "Verify the source website is accessible",
            "Try again in a few moments",
            "Check if a VPN or proxy is required"
        ]
        
        if error.status_code:
            if error.status_code == 403:
                suggestions.insert(0, "The source may be blocking requests - try different user agent")
            elif error.status_code == 404:
                suggestions.insert(0, "The requested content may no longer be available")
            elif error.status_code >= 500:
                suggestions.insert(0, "The source server is experiencing issues")
        
        content_parts.append(f"\n\n[{self.palette.info}]💡 Suggestions:[/{self.palette.info}]")
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        if show_traceback and error.details:
            content_parts.append(f"\n\n[dim]Details:[/dim]\n{error.details}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="🌐 Network Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _display_download_error(
        self,
        error: DownloadError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Display download error with download-specific suggestions."""
        content_parts = []
        
        # Error message
        content_parts.append(f"[{self.palette.error}]{error.message}[/{self.palette.error}]")
        
        if error.episode_title:
            content_parts.append(f"\n[dim]Episode:[/dim] [cyan]{error.episode_title}[/cyan]")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        # Download-specific suggestions
        suggestions = [
            "Check available disk space",
            "Verify download directory permissions",
            "Try a different video quality",
            "Retry the download",
            "Check if the episode is still available"
        ]
        
        content_parts.append(f"\n\n[{self.palette.info}]💡 Suggestions:[/{self.palette.info}]")
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        if show_traceback and error.details:
            content_parts.append(f"\n\n[dim]Details:[/dim]\n{error.details}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="⬇️  Download Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _display_search_error(
        self,
        error: SearchError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Display search error with search-specific suggestions."""
        content_parts = []
        
        # Error message
        content_parts.append(f"[{self.palette.error}]{error.message}[/{self.palette.error}]")
        
        if error.query:
            content_parts.append(f"\n[dim]Query:[/dim] [cyan]{error.query}[/cyan]")
        
        if error.source:
            content_parts.append(f"\n[dim]Source:[/dim] [cyan]{error.source}[/cyan]")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        # Search-specific suggestions
        suggestions = [
            "Try different search terms or keywords",
            "Check spelling and try alternative titles",
            "Use broader search terms",
            "Try searching other enabled sources"
        ]
        
        content_parts.append(f"\n\n[{self.palette.info}]💡 Suggestions:[/{self.palette.info}]")
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        if show_traceback and error.details:
            content_parts.append(f"\n\n[dim]Details:[/dim]\n{error.details}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="🔍 Search Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _display_validation_error(
        self,
        error: ValidationError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Display validation error with field-specific information."""
        content_parts = []
        
        # Error message
        content_parts.append(f"[{self.palette.error}]{error.message}[/{self.palette.error}]")
        
        if error.field_name:
            content_parts.append(f"\n[dim]Field:[/dim] [cyan]{error.field_name}[/cyan]")
        
        if error.invalid_value is not None:
            content_parts.append(f"\n[dim]Invalid Value:[/dim] [red]{error.invalid_value}[/red]")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        # Validation-specific suggestions
        suggestions = [
            "Check the data format and type",
            "Verify all required fields are provided",
            "Ensure values are within acceptable ranges",
            "Refer to documentation for valid formats"
        ]
        
        content_parts.append(f"\n\n[{self.palette.info}]💡 Suggestions:[/{self.palette.info}]")
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        if show_traceback and error.details:
            content_parts.append(f"\n\n[dim]Details:[/dim]\n{error.details}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="✅ Validation Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _display_generic_aniplux_error(
        self,
        error: AniPluxError,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Display generic AniPlux error."""
        content_parts = []
        
        # Error message
        content_parts.append(f"[{self.palette.error}]{error.message}[/{self.palette.error}]")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        if error.details:
            content_parts.append(f"\n[dim]Details:[/dim] {error.details}")
        
        if show_traceback:
            content_parts.append(f"\n\n[dim]Traceback:[/dim]\n{traceback.format_exc()}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="❌ Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _handle_generic_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """Handle generic Python exceptions."""
        content_parts = []
        
        # Error message
        error_type = error.__class__.__name__
        content_parts.append(f"[{self.palette.error}]{error_type}: {str(error)}[/{self.palette.error}]")
        
        if context:
            content_parts.append(f"\n[dim]Context:[/dim] {context}")
        
        # Generic suggestions
        suggestions = [
            "Check the command syntax and arguments",
            "Verify your configuration is correct",
            "Try running the command again",
            "Report this issue if it persists"
        ]
        
        content_parts.append(f"\n\n[{self.palette.info}]💡 Suggestions:[/{self.palette.info}]")
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        if show_traceback:
            content_parts.append(f"\n\n[dim]Traceback:[/dim]\n{traceback.format_exc()}")
        
        panel = Panel(
            "\n".join(content_parts),
            title="💥 Unexpected Error",
            border_style=self.palette.error,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def display_warning(self, message: str, title: str = "⚠️  Warning") -> None:
        """
        Display a warning message.
        
        Args:
            message: Warning message
            title: Warning title
        """
        panel = Panel(
            f"[{self.palette.warning}]{message}[/{self.palette.warning}]",
            title=f"[{self.palette.warning}]{title}[/{self.palette.warning}]",
            border_style=self.palette.warning,
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def display_info(self, message: str, title: str = "ℹ️  Information") -> None:
        """
        Display an information message.
        
        Args:
            message: Information message
            title: Information title
        """
        panel = Panel(
            f"[{self.palette.info}]{message}[/{self.palette.info}]",
            title=f"[{self.palette.info}]{title}[/{self.palette.info}]",
            border_style=self.palette.info,
            padding=(1, 2)
        )
        
        self.console.print(panel)


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


def handle_error(
    error: Exception,
    context: Optional[str] = None,
    show_traceback: bool = False
) -> None:
    """
    Handle and display an error using the global error handler.
    
    Args:
        error: Exception to handle
        context: Additional context
        show_traceback: Whether to show traceback
    """
    _error_handler.handle_error(error, context, show_traceback)


def display_warning(message: str, title: str = "⚠️  Warning") -> None:
    """Display a warning message using the global error handler."""
    _error_handler.display_warning(message, title)


def display_info(message: str, title: str = "ℹ️  Information") -> None:
    """Display an information message using the global error handler."""
    _error_handler.display_info(message, title)


# Export error handling functions
__all__ = [
    "ErrorHandler",
    "get_error_handler",
    "handle_error",
    "display_warning",
    "display_info",
]