"""
Startup Manager - Clean application startup and initialization.

This module handles the application startup sequence including banner display,
configuration validation, and system checks.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from aniplux import __version__
from aniplux.core import ConfigManager
from aniplux.core.exceptions import ConfigurationError
from aniplux.ui import (
    get_console,
    UIComponents,
    display_warning,
    display_info,
    format_title,
    format_success,
    format_warning,
    format_error,
)


logger = logging.getLogger(__name__)


class StartupManager:
    """Manages application startup sequence and initialization."""
    
    def __init__(self):
        """Initialize startup manager."""
        self.console = get_console()
        self.ui = UIComponents()
    
    def show_banner(self) -> None:
        """Display the application banner with ASCII art."""
        try:
            # Try to load banner from assets
            banner_path = Path(__file__).parent.parent.parent / "assets" / "banner.txt"
            
            if banner_path.exists():
                with open(banner_path, 'r', encoding='utf-8') as f:
                    banner_content = f.read()
                
                # Add version information
                banner_with_version = banner_content.replace(
                    "v0.1.0",
                    f"v{__version__}"
                )
                
                self.console.print(banner_with_version, style="bold blue")
            else:
                # Fallback banner
                self._show_fallback_banner()
                
        except Exception as e:
            logger.warning(f"Failed to load banner: {e}")
            self._show_fallback_banner()
    
    def _show_fallback_banner(self) -> None:
        """Show a simple fallback banner if ASCII art fails."""
        banner_text = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    🎌 AniPlux v{__version__:<10}                    ║
║                                                              ║
║           Modern Anime Episode Downloader                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        self.console.print(banner_text, style="bold blue")
    
    def validate_startup_configuration(self, config_manager: ConfigManager) -> None:
        """
        Validate configuration and show startup warnings if needed.
        
        Args:
            config_manager: Configuration manager instance
        """
        logger.info("Validating startup configuration")
        
        # Run configuration validation
        validation_report = config_manager.validate_configuration()
        
        # Show critical issues
        if not validation_report["valid"]:
            display_warning(
                "Configuration validation failed. Some features may not work correctly.",
                "⚠️  Configuration Issues"
            )
            
            for issue in validation_report["issues"]:
                self.console.print(f"  • {format_error(issue)}")
        
        # Show warnings
        if validation_report["warnings"]:
            for warning in validation_report["warnings"]:
                self.console.print(f"  • {format_warning(warning)}")
        
        # Check for enabled sources
        enabled_sources = config_manager.get_enabled_sources()
        if not enabled_sources:
            display_warning(
                "No anime sources are enabled. Use 'aniplux sources' to enable sources.",
                "🔌 No Sources Enabled"
            )
        else:
            logger.info(f"Found {len(enabled_sources)} enabled sources")
    
    def show_startup_info(self, config_manager: ConfigManager) -> None:
        """
        Show startup information and system status.
        
        Args:
            config_manager: Configuration manager instance
        """
        # Create startup info panel
        info_items = self._gather_startup_info(config_manager)
        
        status_table = self.ui.create_status_grid(info_items)
        
        info_panel = self.ui.create_info_panel(
            status_table,
            title="🚀 Startup Information"
        )
        
        self.console.print(info_panel)
    
    def _gather_startup_info(self, config_manager: ConfigManager) -> Dict[str, Any]:
        """
        Gather startup information for display.
        
        Args:
            config_manager: Configuration manager instance
            
        Returns:
            Dictionary of startup information
        """
        settings = config_manager.settings
        sources = config_manager.sources
        
        # Count enabled sources
        enabled_sources = len(config_manager.get_enabled_sources())
        total_sources = len(sources.sources)
        
        # Get download directory status
        download_dir = Path(settings.settings.download_directory)
        download_dir_status = "✅ Ready" if download_dir.exists() else "❌ Missing"
        
        return {
            "Version": __version__,
            "Theme": settings.ui.color_theme.title(),
            "Download Directory": str(download_dir),
            "Directory Status": download_dir_status,
            "Enabled Sources": f"{enabled_sources}/{total_sources}",
            "Default Quality": settings.settings.default_quality,
            "Concurrent Downloads": settings.settings.concurrent_downloads,
            "Configuration": "✅ Valid" if config_manager.validate_configuration()["valid"] else "⚠️  Issues",
        }
    
    def check_system_requirements(self) -> Dict[str, bool]:
        """
        Check system requirements and capabilities.
        
        Returns:
            Dictionary of requirement check results
        """
        requirements = {}
        
        # Check Python version
        import sys
        python_version = sys.version_info
        requirements["python_version"] = python_version >= (3, 8)
        
        # Check required modules
        required_modules = [
            "typer",
            "rich", 
            "aiohttp",
            "pydantic",
            "beautifulsoup4",
        ]
        
        for module in required_modules:
            try:
                __import__(module)
                requirements[f"module_{module}"] = True
            except ImportError:
                requirements[f"module_{module}"] = False
        
        # Check terminal capabilities
        from aniplux.ui.console import detect_terminal_capabilities
        capabilities = detect_terminal_capabilities()
        
        requirements.update({
            "color_support": capabilities["colors"] != "none",
            "unicode_support": capabilities["unicode"],
        })
        
        return requirements
    
    def show_system_requirements(self) -> None:
        """Display system requirements check results."""
        requirements = self.check_system_requirements()
        
        # Create requirements table
        headers = ["Requirement", "Status", "Details"]
        rows = []
        
        # Python version
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        python_status = "✅ OK" if requirements["python_version"] else "❌ Failed"
        rows.append(["Python 3.8+", python_status, f"Current: {python_version}"])
        
        # Required modules
        module_names = {
            "module_typer": "Typer CLI Framework",
            "module_rich": "Rich Terminal Library",
            "module_aiohttp": "Async HTTP Client",
            "module_pydantic": "Data Validation",
            "module_beautifulsoup4": "HTML Parsing",
        }
        
        for key, name in module_names.items():
            status = "✅ OK" if requirements.get(key, False) else "❌ Missing"
            rows.append([name, status, "Required for operation"])
        
        # Terminal capabilities
        color_status = "✅ Supported" if requirements["color_support"] else "⚠️  Limited"
        unicode_status = "✅ Supported" if requirements["unicode_support"] else "⚠️  Limited"
        
        rows.append(["Color Support", color_status, "For beautiful interface"])
        rows.append(["Unicode Support", unicode_status, "For icons and symbols"])
        
        # Create and display table
        requirements_table = self.ui.create_data_table(
            headers=headers,
            rows=rows,
            title="System Requirements"
        )
        
        panel = self.ui.create_info_panel(
            requirements_table,
            title="🔍 System Requirements Check"
        )
        
        self.console.print(panel)
        
        # Show warnings for failed requirements
        failed_requirements = [k for k, v in requirements.items() if not v]
        if failed_requirements:
            warning_messages = []
            
            if not requirements["python_version"]:
                warning_messages.append("Python 3.8 or higher is required")
            
            for key in failed_requirements:
                if key.startswith("module_"):
                    module = key.replace("module_", "")
                    warning_messages.append(f"Missing required module: {module}")
            
            if warning_messages:
                display_warning(
                    "\n".join(f"• {msg}" for msg in warning_messages),
                    "⚠️  System Issues Detected"
                )
    
    def perform_startup_checks(self, config_manager: ConfigManager) -> bool:
        """
        Perform comprehensive startup checks.
        
        Args:
            config_manager: Configuration manager instance
            
        Returns:
            True if all critical checks pass, False otherwise
        """
        logger.info("Performing startup checks")
        
        checks_passed = True
        
        # Check system requirements
        requirements = self.check_system_requirements()
        critical_requirements = ["python_version"] + [
            k for k in requirements.keys() if k.startswith("module_")
        ]
        
        for req in critical_requirements:
            if not requirements.get(req, False):
                logger.error(f"Critical requirement failed: {req}")
                checks_passed = False
        
        # Check configuration
        validation_report = config_manager.validate_configuration()
        if not validation_report["valid"]:
            logger.warning("Configuration validation failed")
            # Don't fail startup for configuration issues
        
        # Check download directory
        download_dir = Path(config_manager.settings.settings.download_directory)
        try:
            download_dir.mkdir(parents=True, exist_ok=True)
            # Test write permissions
            test_file = download_dir / ".aniplux_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            logger.error(f"Download directory check failed: {e}")
            display_warning(
                f"Cannot write to download directory: {download_dir}",
                "📁 Directory Access Issue"
            )
            # Don't fail startup for directory issues
        
        return checks_passed
    
    def show_quick_help(self) -> None:
        """Show quick help information for new users."""
        help_text = """
[bold blue]Quick Start Guide:[/bold blue]

• [cyan]aniplux search "anime name"[/cyan] - Search for anime
• [cyan]aniplux sources[/cyan] - Manage anime sources  
• [cyan]aniplux config[/cyan] - Configure settings
• [cyan]aniplux --help[/cyan] - Show detailed help

[dim]Visit https://github.com/Yui007/AniPlux for documentation[/dim]
"""
        
        panel = self.ui.create_info_panel(
            help_text.strip(),
            title="🚀 Getting Started"
        )
        
        self.console.print(panel)


# Export startup manager
__all__ = ["StartupManager"]