"""
Plugin Layer - Extensible anime source implementations.

This module contains the plugin architecture and individual source implementations
that provide anime search and download capabilities from various websites.
"""

from aniplux.plugins.base import BasePlugin, PluginMetadata
from aniplux.plugins.common import (
    HTMLParser,
    QualityExtractor,
    URLHelper,
    TextCleaner,
    create_anime_result,
    create_episode,
)

__all__ = [
    # Base Plugin Architecture
    "BasePlugin",
    "PluginMetadata",
    # Plugin Development Utilities
    "HTMLParser",
    "QualityExtractor", 
    "URLHelper",
    "TextCleaner",
    "create_anime_result",
    "create_episode",
]