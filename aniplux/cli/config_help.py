"""
Configuration Help - Help and documentation for configuration options.

This module provides comprehensive help and documentation for all
configuration options, including examples and best practices.
"""

import logging
from typing import Dict, List, Optional

from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from aniplux.ui import get_console, UIComponents


logger = logging.getLogger(__name__)


class ConfigurationHelp:
    """
    Provides help and documentation for configuration options.
    
    Offers detailed explanations, examples, and best practices
    for all configuration settings and commands.
    """
    
    def __init__(self):
        """Initialize configuration help."""
        self.console = get_console()
        self.ui = UIComponents()
        
        # Configuration documentation
        self.setting_docs = {
            "settings": {
                "download_directory": {
                    "description": "Directory where downloaded anime episodes will be saved",
                    "type": "string (path)",
                    "default": "./downloads",
                    "examples": [
                        "~/Downloads/AniPlux",
                        "/media/storage/anime",
                        "D:\\Anime"
                    ],
                    "tips": [
                        "Use absolute paths for reliability",
                        "Ensure sufficient disk space",
                        "Choose a location with fast write speeds"
                    ]
                },
                "default_quality": {
                    "description": "Default video quality for downloads when multiple options are available",
                    "type": "string",
                    "default": "720p",
                    "examples": ["480p", "720p", "1080p", "1440p", "2160p"],
                    "tips": [
                        "Higher quality = larger file sizes",
                        "Consider your internet speed",
                        "720p is a good balance for most users"
                    ]
                },
                "concurrent_downloads": {
                    "description": "Maximum number of simultaneous downloads",
                    "type": "integer",
                    "default": "3",
                    "examples": ["1", "3", "5"],
                    "tips": [
                        "More concurrent downloads = higher bandwidth usage",
                        "Don't exceed your CPU core count * 2",
                        "Some sources may limit concurrent connections"
                    ]
                },
                "timeout": {
                    "description": "Network timeout for requests in seconds",
                    "type": "integer",
                    "default": "30",
                    "examples": ["15", "30", "60"],
                    "tips": [
                        "Increase for slow connections",
                        "Decrease for faster failure detection",
                        "Balance between reliability and speed"
                    ]
                },
                "max_retries": {
                    "description": "Maximum retry attempts for failed operations",
                    "type": "integer", 
                    "default": "3",
                    "examples": ["1", "3", "5"],
                    "tips": [
                        "Higher values = more resilience to temporary failures",
                        "Lower values = faster failure detection",
                        "Consider source reliability"
                    ]
                },
                "chunk_size": {
                    "description": "Download chunk size in bytes",
                    "type": "integer",
                    "default": "8192",
                    "examples": ["4096", "8192", "16384"],
                    "tips": [
                        "Larger chunks = fewer network requests",
                        "Smaller chunks = more responsive progress updates",
                        "8KB is optimal for most connections"
                    ]
                }
            },
            "ui": {
                "show_banner": {
                    "description": "Display ASCII art banner on startup",
                    "type": "boolean",
                    "default": "true",
                    "examples": ["true", "false"],
                    "tips": [
                        "Disable for cleaner output in scripts",
                        "Enable for better visual experience"
                    ]
                },
                "color_theme": {
                    "description": "Color theme for the user interface",
                    "type": "string",
                    "default": "default",
                    "examples": ["default", "dark", "light", "colorful"],
                    "tips": [
                        "Dark theme for low-light environments",
                        "Light theme for bright environments",
                        "Colorful theme for enhanced visual experience"
                    ]
                },
                "progress_style": {
                    "description": "Style of progress indicators",
                    "type": "string",
                    "default": "bar",
                    "examples": ["bar", "spinner", "dots"],
                    "tips": [
                        "Bar shows precise progress percentage",
                        "Spinner for indeterminate operations",
                        "Dots for minimal visual impact"
                    ]
                },
                "table_style": {
                    "description": "Style of data tables",
                    "type": "string",
                    "default": "rounded",
                    "examples": ["rounded", "simple", "grid", "minimal"],
                    "tips": [
                        "Rounded for modern appearance",
                        "Simple for compatibility",
                        "Grid for data-heavy displays"
                    ]
                },
                "panel_style": {
                    "description": "Style of information panels",
                    "type": "string",
                    "default": "rounded",
                    "examples": ["rounded", "square", "heavy", "double"],
                    "tips": [
                        "Match with table_style for consistency",
                        "Heavy for emphasis",
                        "Double for formal appearance"
                    ]
                },
                "animation_speed": {
                    "description": "Speed of UI animations",
                    "type": "string",
                    "default": "normal",
                    "examples": ["slow", "normal", "fast"],
                    "tips": [
                        "Slow for accessibility",
                        "Fast for power users",
                        "Normal for most users"
                    ]
                }
            },
            "search": {
                "max_results_per_source": {
                    "description": "Maximum search results to return per source",
                    "type": "integer",
                    "default": "50",
                    "examples": ["20", "50", "100"],
                    "tips": [
                        "Higher values = more comprehensive results",
                        "Lower values = faster search responses",
                        "Consider terminal screen size"
                    ]
                },
                "search_timeout": {
                    "description": "Timeout for search operations in seconds",
                    "type": "integer",
                    "default": "10",
                    "examples": ["5", "10", "20"],
                    "tips": [
                        "Increase for slow sources",
                        "Decrease for faster user experience",
                        "Balance between completeness and speed"
                    ]
                },
                "enable_fuzzy_search": {
                    "description": "Enable fuzzy matching for search queries",
                    "type": "boolean",
                    "default": "true",
                    "examples": ["true", "false"],
                    "tips": [
                        "Helps find results with typos",
                        "May return less precise matches",
                        "Useful for discovering similar titles"
                    ]
                },
                "min_query_length": {
                    "description": "Minimum length for search queries",
                    "type": "integer",
                    "default": "2",
                    "examples": ["1", "2", "3"],
                    "tips": [
                        "Prevents overly broad searches",
                        "Reduces server load",
                        "Improves result relevance"
                    ]
                }
            },
            "logging": {
                "level": {
                    "description": "Logging verbosity level",
                    "type": "string",
                    "default": "INFO",
                    "examples": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "tips": [
                        "DEBUG for troubleshooting",
                        "INFO for normal operation",
                        "WARNING to reduce log noise"
                    ]
                },
                "file": {
                    "description": "Log file name or path",
                    "type": "string",
                    "default": "aniplux.log",
                    "examples": ["aniplux.log", "logs/app.log", "/var/log/aniplux.log"],
                    "tips": [
                        "Use absolute paths for system-wide logging",
                        "Relative paths are relative to working directory",
                        "Ensure directory exists and is writable"
                    ]
                },
                "max_size": {
                    "description": "Maximum log file size before rotation",
                    "type": "string",
                    "default": "10MB",
                    "examples": ["5MB", "10MB", "50MB", "1GB"],
                    "tips": [
                        "Larger sizes = fewer rotations",
                        "Smaller sizes = more manageable files",
                        "Consider available disk space"
                    ]
                },
                "backup_count": {
                    "description": "Number of backup log files to keep",
                    "type": "integer",
                    "default": "3",
                    "examples": ["1", "3", "5", "10"],
                    "tips": [
                        "More backups = longer history",
                        "Fewer backups = less disk usage",
                        "Balance between history and storage"
                    ]
                }
            }
        }
    
    def show_setting_help(self, setting_path: str) -> None:
        """
        Show detailed help for a specific setting.
        
        Args:
            setting_path: Dot notation path to the setting
        """
        parts = setting_path.split('.')
        if len(parts) != 2:
            self.console.print(f"[red]❌ Invalid setting path: {setting_path}[/red]")
            return
        
        section, setting = parts
        
        if section not in self.setting_docs:
            self.console.print(f"[red]❌ Unknown section: {section}[/red]")
            return
        
        if setting not in self.setting_docs[section]:
            self.console.print(f"[red]❌ Unknown setting: {setting}[/red]")
            return
        
        doc = self.setting_docs[section][setting]
        
        # Create help panel
        help_content = f"[bold]{doc['description']}[/bold]\n\n"
        help_content += f"[cyan]Type:[/cyan] {doc['type']}\n"
        help_content += f"[cyan]Default:[/cyan] {doc['default']}\n\n"
        
        if doc['examples']:
            help_content += "[cyan]Examples:[/cyan]\n"
            for example in doc['examples']:
                help_content += f"  • {example}\n"
            help_content += "\n"
        
        if doc['tips']:
            help_content += "[yellow]💡 Tips:[/yellow]\n"
            for tip in doc['tips']:
                help_content += f"  • {tip}\n"
        
        panel = Panel(
            help_content.strip(),
            title=f"📖 Help: {setting_path}",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def show_section_help(self, section: str) -> None:
        """
        Show help for all settings in a section.
        
        Args:
            section: Section name (settings, ui, search, logging)
        """
        if section not in self.setting_docs:
            self.console.print(f"[red]❌ Unknown section: {section}[/red]")
            return
        
        self.console.print(f"[bold blue]📖 {section.title()} Configuration Help[/bold blue]\n")
        
        # Create table of settings
        table = Table(
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Description", style="white", width=40)
        table.add_column("Type", style="green", width=15)
        table.add_column("Default", style="yellow", width=15)
        
        for setting_name, doc in self.setting_docs[section].items():
            table.add_row(
                setting_name,
                doc['description'][:40] + "..." if len(doc['description']) > 40 else doc['description'],
                doc['type'],
                str(doc['default'])
            )
        
        self.console.print(table)
        
        self.console.print(f"\n[dim]Use 'aniplux config help {section}.setting_name' for detailed help on specific settings.[/dim]")
    
    def show_all_help(self) -> None:
        """Show overview of all configuration sections."""
        self.console.print("[bold blue]📖 AniPlux Configuration Help[/bold blue]\n")
        
        # Section overview
        sections = [
            ("settings", "Core application settings", "Download directory, quality, performance"),
            ("ui", "User interface preferences", "Themes, styles, visual options"),
            ("search", "Search behavior settings", "Results, timeouts, fuzzy matching"),
            ("logging", "Logging configuration", "Log levels, files, rotation")
        ]
        
        # Create sections table
        table = Table(
            title="Configuration Sections",
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Section", style="cyan", width=15)
        table.add_column("Purpose", style="white", width=30)
        table.add_column("Key Settings", style="dim", width=40)
        
        for section, purpose, key_settings in sections:
            table.add_row(section, purpose, key_settings)
        
        self.console.print(table)
        
        # Usage examples
        examples_panel = Panel(
            "[bold]Common Commands:[/bold]\n\n"
            "• [cyan]aniplux config help settings[/cyan] - Help for settings section\n"
            "• [cyan]aniplux config help ui.color_theme[/cyan] - Help for specific setting\n"
            "• [cyan]aniplux config show[/cyan] - Show current configuration\n"
            "• [cyan]aniplux config edit[/cyan] - Interactive configuration editor\n"
            "• [cyan]aniplux config set ui.color_theme dark[/cyan] - Set specific value\n"
            "• [cyan]aniplux config wizard[/cyan] - Run setup wizard",
            title="💡 Usage Examples",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(f"\n{examples_panel}")
    
    def show_command_help(self) -> None:
        """Show help for configuration commands."""
        self.console.print("[bold blue]📖 Configuration Commands Help[/bold blue]\n")
        
        commands = [
            ("show [section]", "Display current configuration", "aniplux config show ui"),
            ("edit", "Interactive configuration editor", "aniplux config edit"),
            ("set <key> <value>", "Set a configuration value", "aniplux config set ui.color_theme dark"),
            ("reset", "Reset to default values", "aniplux config reset --yes"),
            ("validate", "Validate configuration", "aniplux config validate"),
            ("export <file>", "Export configuration", "aniplux config export backup.json"),
            ("import <file>", "Import configuration", "aniplux config import backup.json"),
            ("backup", "Create configuration backup", "aniplux config backup -d 'Before update'"),
            ("restore [backup]", "Restore from backup", "aniplux config restore config_backup_20240101.json"),
            ("backups", "List available backups", "aniplux config backups"),
            ("cleanup", "Clean up old backups", "aniplux config cleanup --keep 5"),
            ("preview", "Preview configuration changes", "aniplux config preview --theme dark"),
            ("wizard", "Run setup wizard", "aniplux config wizard"),
            ("help [setting]", "Show configuration help", "aniplux config help ui.color_theme")
        ]
        
        # Create commands table
        table = Table(
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Command", style="cyan", width=25)
        table.add_column("Description", style="white", width=35)
        table.add_column("Example", style="dim", width=35)
        
        for command, description, example in commands:
            table.add_row(command, description, example)
        
        self.console.print(table)


# Export help functionality
__all__ = ["ConfigurationHelp"]