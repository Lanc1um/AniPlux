"""
HiAnime Plugin - Anime source plugin for hianime.to

This plugin provides access to anime content from hianime.to,
including search functionality, episode listing, and download URL extraction.
"""

from .plugin import HiAnimePlugin, plugin_metadata, default_config, SUPPORTED_QUALITIES
from .config import HiAnimeConfig, get_default_config, validate_config
from .downloader import HiAnimeSeleniumDownloader, HiAnimeDownloadManager
from .selenium_config import SeleniumConfigHelper

__all__ = [
    "HiAnimePlugin",
    "plugin_metadata", 
    "default_config",
    "SUPPORTED_QUALITIES",
    "HiAnimeConfig",
    "get_default_config",
    "validate_config",
    "HiAnimeSeleniumDownloader",
    "HiAnimeDownloadManager",
    "SeleniumConfigHelper"
]