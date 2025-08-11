"""
Animetsu Plugin - Anime source plugin for animetsu.to

This plugin provides access to anime content from animetsu.to,
including search functionality, episode listing, and download URL extraction.
"""

from .plugin import AnimetsuPlugin, plugin_metadata, default_config, SUPPORTED_QUALITIES
from .config import AnimetsuConfig, get_default_config, validate_config
from .downloader import AnimetsuDownloadManager

__all__ = [
    "AnimetsuPlugin",
    "plugin_metadata", 
    "default_config",
    "SUPPORTED_QUALITIES",
    "AnimetsuConfig",
    "get_default_config",
    "validate_config",
    "AnimetsuDownloadManager"
]