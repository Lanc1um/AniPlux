"""
Styling Utilities - Consistent styling helpers and formatters.

This module provides utility functions for consistent text formatting,
color application, and style management across the application.
"""

from typing import Optional, Union, Any
from datetime import datetime, timedelta

from rich.text import Text
from rich.markup import escape

from aniplux.core.models import Quality, DownloadStatus
from aniplux.ui.themes import get_palette


class StyleFormatter:
    """Utility class for consistent text styling and formatting."""
    
    def __init__(self):
        """Initialize formatter with current theme palette."""
        self.palette = get_palette()
    
    def format_title(self, text: str, style: Optional[str] = None) -> str:
        """
        Format text as a title with consistent styling.
        
        Args:
            text: Text to format
            style: Optional style override
            
        Returns:
            Formatted title string
        """
        style = style or f"bold {self.palette.primary}"
        return f"[{style}]{escape(text)}[/{style}]"
    
    def format_subtitle(self, text: str, style: Optional[str] = None) -> str:
        """
        Format text as a subtitle.
        
        Args:
            text: Text to format
            style: Optional style override
            
        Returns:
            Formatted subtitle string
        """
        style = style or self.palette.secondary
        return f"[{style}]{escape(text)}[/{style}]"
    
    def format_muted(self, text: str) -> str:
        """
        Format text as muted/secondary text.
        
        Args:
            text: Text to format
            
        Returns:
            Formatted muted text
        """
        return f"[{self.palette.text_muted}]{escape(text)}[/{self.palette.text_muted}]"
    
    def format_highlight(self, text: str, style: Optional[str] = None) -> str:
        """
        Format text as highlighted/emphasized.
        
        Args:
            text: Text to format
            style: Optional style override
            
        Returns:
            Formatted highlighted text
        """
        style = style or f"bold {self.palette.accent}"
        return f"[{style}]{escape(text)}[/{style}]"
    
    def format_success(self, text: str) -> str:
        """Format text with success styling."""
        return f"[{self.palette.success}]{escape(text)}[/{self.palette.success}]"
    
    def format_warning(self, text: str) -> str:
        """Format text with warning styling."""
        return f"[{self.palette.warning}]{escape(text)}[/{self.palette.warning}]"
    
    def format_error(self, text: str) -> str:
        """Format text with error styling."""
        return f"[{self.palette.error}]{escape(text)}[/{self.palette.error}]"
    
    def format_info(self, text: str) -> str:
        """Format text with info styling."""
        return f"[{self.palette.info}]{escape(text)}[/{self.palette.info}]"
    
    def format_quality(self, quality: Quality) -> str:
        """
        Format video quality with appropriate color coding.
        
        Args:
            quality: Quality enum value
            
        Returns:
            Formatted quality string
        """
        if quality.height >= 1080:
            color = self.palette.success
        elif quality.height >= 720:
            color = self.palette.warning
        else:
            color = self.palette.error
        
        return f"[{color}]{quality.value}[/{color}]"
    
    def format_download_status(self, status: DownloadStatus) -> str:
        """
        Format download status with appropriate styling.
        
        Args:
            status: Download status enum value
            
        Returns:
            Formatted status string
        """
        status_styles = {
            DownloadStatus.PENDING: (self.palette.text_muted, "⏳"),
            DownloadStatus.DOWNLOADING: (self.palette.info, "⬇️"),
            DownloadStatus.COMPLETED: (self.palette.success, "✅"),
            DownloadStatus.FAILED: (self.palette.error, "❌"),
            DownloadStatus.PAUSED: (self.palette.warning, "⏸️"),
            DownloadStatus.CANCELLED: (self.palette.text_muted, "🚫")
        }
        
        color, emoji = status_styles.get(status, (self.palette.text_secondary, "📁"))
        status_text = status.value.title()
        
        return f"[{color}]{emoji} {status_text}[/{color}]"
    
    def format_file_size(self, size_bytes: Optional[int]) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes is None:
            return self.format_muted("Unknown")
        
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    def format_duration(self, duration: Optional[str]) -> str:
        """
        Format duration string with consistent styling.
        
        Args:
            duration: Duration string (MM:SS or HH:MM:SS)
            
        Returns:
            Formatted duration string
        """
        if not duration:
            return self.format_muted("Unknown")
        
        return f"[{self.palette.text_secondary}]{duration}[/{self.palette.text_secondary}]"
    
    def format_percentage(self, percentage: float, show_color: bool = True) -> str:
        """
        Format percentage with optional color coding.
        
        Args:
            percentage: Percentage value (0-100)
            show_color: Whether to apply color coding
            
        Returns:
            Formatted percentage string
        """
        if not show_color:
            return f"{percentage:.1f}%"
        
        if percentage >= 100:
            color = self.palette.success
        elif percentage >= 75:
            color = self.palette.info
        elif percentage >= 50:
            color = self.palette.warning
        else:
            color = self.palette.error
        
        return f"[{color}]{percentage:.1f}%[/{color}]"
    
    def format_rating(self, rating: Optional[float]) -> str:
        """
        Format anime rating with color coding.
        
        Args:
            rating: Rating value (0-10)
            
        Returns:
            Formatted rating string
        """
        if rating is None:
            return self.format_muted("N/A")
        
        if rating >= 8.0:
            color = self.palette.success
        elif rating >= 7.0:
            color = self.palette.warning
        elif rating >= 6.0:
            color = self.palette.info
        else:
            color = self.palette.error
        
        return f"[{color}]{rating:.1f}[/{color}]"
    
    def format_episode_count(self, count: Optional[int]) -> str:
        """
        Format episode count with appropriate styling.
        
        Args:
            count: Number of episodes
            
        Returns:
            Formatted episode count string
        """
        if count is None:
            return self.format_muted("?")
        
        if count > 100:
            return self.format_highlight(str(count))
        else:
            return str(count)
    
    def format_timestamp(self, timestamp: Optional[datetime]) -> str:
        """
        Format timestamp in human-readable format.
        
        Args:
            timestamp: Datetime object
            
        Returns:
            Formatted timestamp string
        """
        if timestamp is None:
            return self.format_muted("Unknown")
        
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    
    def format_speed(self, bytes_per_second: float) -> str:
        """
        Format download speed in human-readable format.
        
        Args:
            bytes_per_second: Speed in bytes per second
            
        Returns:
            Formatted speed string
        """
        if bytes_per_second == 0:
            return "0 B/s"
        
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        speed = float(bytes_per_second)
        unit_index = 0
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
        
        return f"{speed:.1f} {units[unit_index]}"
    
    def format_eta(self, seconds: Optional[int]) -> str:
        """
        Format estimated time remaining.
        
        Args:
            seconds: Seconds remaining
            
        Returns:
            Formatted ETA string
        """
        if seconds is None or seconds <= 0:
            return self.format_muted("Unknown")
        
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def create_status_indicator(self, enabled: bool, text: str = "") -> str:
        """
        Create a status indicator with color coding.
        
        Args:
            enabled: Whether the status is enabled/active
            text: Optional text to include
            
        Returns:
            Formatted status indicator
        """
        if enabled:
            indicator = f"[{self.palette.success}]●[/{self.palette.success}]"
            if text:
                return f"{indicator} [{self.palette.success}]{escape(text)}[/{self.palette.success}]"
        else:
            indicator = f"[{self.palette.text_muted}]○[/{self.palette.text_muted}]"
            if text:
                return f"{indicator} [{self.palette.text_muted}]{escape(text)}[/{self.palette.text_muted}]"
        
        return indicator


# Global formatter instance
_formatter = StyleFormatter()


def get_formatter() -> StyleFormatter:
    """Get the global style formatter instance."""
    return _formatter


# Convenience functions for common formatting operations
def format_title(text: str, style: Optional[str] = None) -> str:
    """Format text as a title."""
    return _formatter.format_title(text, style)


def format_success(text: str) -> str:
    """Format text with success styling."""
    return _formatter.format_success(text)


def format_warning(text: str) -> str:
    """Format text with warning styling."""
    return _formatter.format_warning(text)


def format_error(text: str) -> str:
    """Format text with error styling."""
    return _formatter.format_error(text)


def format_info(text: str) -> str:
    """Format text with info styling."""
    return _formatter.format_info(text)


def format_muted(text: str) -> str:
    """Format text as muted."""
    return _formatter.format_muted(text)


def format_quality(quality: Quality) -> str:
    """Format video quality with color coding."""
    return _formatter.format_quality(quality)


def format_file_size(size_bytes: Optional[int]) -> str:
    """Format file size in human-readable format."""
    return _formatter.format_file_size(size_bytes)


# Export styling utilities
__all__ = [
    "StyleFormatter",
    "get_formatter",
    "format_title",
    "format_success",
    "format_warning",
    "format_error",
    "format_info",
    "format_muted",
    "format_quality",
    "format_file_size",
]