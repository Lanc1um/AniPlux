"""
HiAnime Plugin - Legacy wrapper for the modular HiAnime plugin.

This file provides backward compatibility by importing the new modular
HiAnime plugin implementation from the hianime package.
"""

# Import the new modular plugin implementation
from aniplux.plugins.hianime import HiAnimePlugin

# Re-export for backward compatibility
__all__ = ["HiAnimePlugin"]
