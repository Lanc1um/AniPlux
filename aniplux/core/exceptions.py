"""
Core Exceptions - Custom exception classes for AniPlux.

This module defines custom exception classes used throughout the
AniPlux application for better error handling and user feedback.
"""

from typing import Optional, Any


class AniPluxError(Exception):
    """Base exception class for all AniPlux-specific errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        """
        Initialize AniPlux error.
        
        Args:
            message: Human-readable error message
            details: Additional error details for debugging
        """
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        return self.message


class ConfigurationError(AniPluxError):
    """Raised when configuration-related errors occur."""
    
    def __init__(self, message: str, config_path: Optional[str] = None, details: Optional[Any] = None):
        """
        Initialize configuration error.
        
        Args:
            message: Error description
            config_path: Path to the problematic configuration file
            details: Additional error context
        """
        super().__init__(message, details)
        self.config_path = config_path


class PluginError(AniPluxError):
    """Raised when plugin-related errors occur."""
    
    def __init__(self, message: str, plugin_name: Optional[str] = None, details: Optional[Any] = None):
        """
        Initialize plugin error.
        
        Args:
            message: Error description
            plugin_name: Name of the problematic plugin
            details: Additional error context
        """
        super().__init__(message, details)
        self.plugin_name = plugin_name


class NetworkError(AniPluxError):
    """Raised when network-related errors occur."""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, details: Optional[Any] = None):
        """
        Initialize network error.
        
        Args:
            message: Error description
            url: URL that caused the error
            status_code: HTTP status code if applicable
            details: Additional error context
        """
        super().__init__(message, details)
        self.url = url
        self.status_code = status_code


class DownloadError(AniPluxError):
    """Raised when download-related errors occur."""
    
    def __init__(self, message: str, episode_title: Optional[str] = None, details: Optional[Any] = None):
        """
        Initialize download error.
        
        Args:
            message: Error description
            episode_title: Title of the episode that failed to download
            details: Additional error context
        """
        super().__init__(message, details)
        self.episode_title = episode_title


class ValidationError(AniPluxError):
    """Raised when data validation errors occur."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, invalid_value: Optional[Any] = None, details: Optional[Any] = None):
        """
        Initialize validation error.
        
        Args:
            message: Error description
            field_name: Name of the field that failed validation
            invalid_value: The invalid value that caused the error
            details: Additional error context
        """
        super().__init__(message, details)
        self.field_name = field_name
        self.invalid_value = invalid_value


class SearchError(AniPluxError):
    """Raised when search-related errors occur."""
    
    def __init__(self, message: str, query: Optional[str] = None, source: Optional[str] = None, details: Optional[Any] = None):
        """
        Initialize search error.
        
        Args:
            message: Error description
            query: Search query that caused the error
            source: Source plugin that failed
            details: Additional error context
        """
        super().__init__(message, details)
        self.query = query
        self.source = source


# Export all exception classes
__all__ = [
    "AniPluxError",
    "ConfigurationError",
    "PluginError", 
    "NetworkError",
    "DownloadError",
    "ValidationError",
    "SearchError",
]