"""
CLI Context - Global application context and state management.

This module provides global application context including configuration
manager and startup manager instances to avoid circular imports.
"""

from typing import Optional

from aniplux.core import ConfigManager
from aniplux.cli.startup import StartupManager


# Global application state
_config_manager: Optional[ConfigManager] = None
_startup_manager: Optional[StartupManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        raise RuntimeError("Configuration manager not initialized")
    return _config_manager


def set_config_manager(config_manager: ConfigManager) -> None:
    """Set the global configuration manager instance."""
    global _config_manager
    _config_manager = config_manager


def get_startup_manager() -> StartupManager:
    """Get the global startup manager instance."""
    global _startup_manager
    if _startup_manager is None:
        raise RuntimeError("Startup manager not initialized")
    return _startup_manager


def set_startup_manager(startup_manager: StartupManager) -> None:
    """Set the global startup manager instance."""
    global _startup_manager
    _startup_manager = startup_manager


# Export context functions
__all__ = [
    "get_config_manager",
    "set_config_manager", 
    "get_startup_manager",
    "set_startup_manager"
]