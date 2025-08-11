"""
Info Command - Application and system information display.

This module implements the info command for showing application
status, configuration, and system information.
"""

import sys
import platform
from pathlib import Path
from typing import Dict, Any

from aniplux import __version__
from aniplux.core import ConfigManager
from aniplux.ui import get_console, UIComponents
from aniplux.ui.console import detect_terminal_capabilities


def show_application_info(config_manager: ConfigManager) -> None:
    """
    Display comprehensive application information.
    
    Args:
        config_manager: Configuration manager instance
    """
    console = get_console()
    ui = UIComponents()
    
    # Gather application information
    app_info = _gather_application_info(config_manager)
    system_info = _gather_system_info()
    config_info = _gather_configuration_info(config_manager)
    
    # Create information sections
    app_table = ui.create_status_grid(app_info)
    system_table = ui.create_status_grid(system_info)
    config_table = ui.create_status_grid(config_info)
    
    # Display sections
    console.print(ui.create_info_panel(
        app_table,
        title="📱 Application Information"
    ))
    
    console.print()
    
    console.print(ui.create_info_panel(
        system_table,
        title="💻 System Information"
    ))
    
    console.print()
    
    console.print(ui.create_info_panel(
        config_table,
        title="⚙️  Configuration Status"
    ))


def _gather_application_info(config_manager: ConfigManager) -> Dict[str, Any]:
    """Gather application-specific information."""
    # Count sources
    enabled_sources = len(config_manager.get_enabled_sources())
    total_sources = len(config_manager.sources.sources)
    
    # Get download directory info
    download_dir = Path(config_manager.settings.settings.download_directory)
    download_dir_status = "✅ Exists" if download_dir.exists() else "❌ Missing"
    
    return {
        "Version": __version__,
        "Installation Path": str(Path(__file__).parent.parent.parent),
        "Configuration Directory": str(config_manager.config_dir),
        "Download Directory": str(download_dir),
        "Download Directory Status": download_dir_status,
        "Enabled Sources": f"{enabled_sources}/{total_sources}",
        "Current Theme": config_manager.settings.ui.color_theme.title(),
    }


def _gather_system_info() -> Dict[str, Any]:
    """Gather system information."""
    # Get console information
    console_info = detect_terminal_capabilities()
    
    console = get_console()
    
    return {
        "Operating System": f"{platform.system()} {platform.release()}",
        "Architecture": platform.machine(),
        "Python Version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "Terminal Width": console.size.width,
        "Terminal Height": console.size.height,
        "Color System": console_info["colors"],
        "Unicode Support": "✅ Yes" if console_info.get("unicode", True) else "❌ No",
        "Terminal Type": "Interactive" if console.is_terminal else "Non-interactive",
    }


def _gather_configuration_info(config_manager: ConfigManager) -> Dict[str, Any]:
    """Gather configuration status information."""
    settings = config_manager.settings
    validation_report = config_manager.validate_configuration()
    
    # Configuration status
    config_status = "✅ Valid" if validation_report["valid"] else "⚠️  Issues"
    
    # Warnings count
    warnings_count = len(validation_report.get("warnings", []))
    warnings_text = f"{warnings_count} warnings" if warnings_count > 0 else "None"
    
    return {
        "Configuration Status": config_status,
        "Warnings": warnings_text,
        "Default Quality": settings.settings.default_quality,
        "Concurrent Downloads": settings.settings.concurrent_downloads,
        "Network Timeout": f"{settings.settings.timeout}s",
        "Show Banner": "✅ Yes" if settings.ui.show_banner else "❌ No",
        "Progress Style": settings.ui.progress_style.title(),
        "Max Results Per Source": settings.search.max_results_per_source,
        "Search Timeout": f"{settings.search.search_timeout}s",
    }


# Export info functions
__all__ = ["show_application_info"]