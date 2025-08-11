"""
AniPlux - Modern anime episode downloader with beautiful CLI interface.

A command-line tool for searching, browsing, and downloading anime episodes
from various sources with a clean, interactive interface built on Typer and Rich.
"""

__version__ = "0.1.0"
__author__ = "AniPlux Team"
__email__ = "contact@aniplux.dev"

# Package metadata
__title__ = "aniplux"
__description__ = "Modern anime episode downloader with beautiful CLI interface"
__url__ = "https://github.com/Yui007/AniPlux"
__license__ = "MIT"

# Version info tuple for programmatic access
VERSION_INFO = tuple(map(int, __version__.split(".")))

# Export main components for easy importing
from aniplux.core.models import AnimeResult, Episode, DownloadTask, Quality
from aniplux.cli.main import cli_main

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "AnimeResult",
    "Episode", 
    "DownloadTask",
    "Quality",
    "cli_main",
]