"""
Core Layer - Business logic and application services.

This module contains the core business logic, plugin management, configuration
handling, and data models that power the AniPlux application.
"""

from aniplux.core.config_manager import ConfigManager
from aniplux.core.config_schemas import AppSettings, SourcesConfig, SourceConfig
from aniplux.core.config_defaults import (
    create_default_config_files,
    get_default_settings,
    get_default_sources,
)
from aniplux.core.exceptions import (
    AniPluxError,
    ConfigurationError,
    DownloadError,
    NetworkError,
    PluginError,
    SearchError,
    ValidationError,
)
from aniplux.core.models import AnimeResult, DownloadTask, Episode, Quality
from aniplux.core.plugin_manager import PluginManager
from aniplux.core.downloader import Downloader

__all__ = [
    # Data Models
    "AnimeResult",
    "Episode", 
    "DownloadTask",
    "Quality",
    # Configuration Management
    "ConfigManager",
    "AppSettings",
    "SourcesConfig",
    "SourceConfig",
    # Configuration Utilities
    "create_default_config_files",
    "get_default_settings",
    "get_default_sources",
    # Plugin Management
    "PluginManager",
    # Download Management
    "Downloader",
    # Exceptions
    "AniPluxError",
    "ConfigurationError",
    "DownloadError",
    "NetworkError", 
    "PluginError",
    "SearchError",
    "ValidationError",
]