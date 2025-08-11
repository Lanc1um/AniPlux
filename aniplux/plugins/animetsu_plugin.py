"""
Animetsu Plugin Entry Point

This module serves as the entry point for the Animetsu plugin,
importing the main plugin class from the animetsu subdirectory.
"""

from aniplux.plugins.animetsu.plugin import AnimetsuPlugin

# Export the plugin class for discovery
__all__ = ["AnimetsuPlugin"]