"""
HiAnime Plugin Registry - Plugin registration and metadata.

This module handles the registration of the HiAnime plugin
with the AniPlux plugin system.
"""

from typing import Dict, Any

from .plugin import HiAnimePlugin, plugin_metadata, default_config


def register_plugin() -> Dict[str, Any]:
    """
    Register the HiAnime plugin with the plugin system.
    
    Returns:
        Plugin registration information
    """
    return {
        "plugin_class": HiAnimePlugin,
        "metadata": plugin_metadata,
        "default_config": default_config,
        "module_name": "aniplux.plugins.hianime",
        "entry_point": "HiAnimePlugin"
    }


def get_plugin_info() -> Dict[str, Any]:
    """
    Get plugin information for display purposes.
    
    Returns:
        Plugin information dictionary
    """
    return {
        "name": plugin_metadata.name,
        "version": plugin_metadata.version,
        "author": plugin_metadata.author,
        "description": plugin_metadata.description,
        "website": plugin_metadata.website,
        "supported_qualities": [q.value for q in plugin_metadata.supported_qualities],
        "rate_limit": plugin_metadata.rate_limit,
        "requires_auth": plugin_metadata.requires_auth
    }


# Export registration functions
__all__ = ["register_plugin", "get_plugin_info"]