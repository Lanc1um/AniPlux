"""
Configuration CLI Helpers - Interactive configuration management utilities.

This module provides helper functions for CLI-based configuration management,
including interactive prompts, validation, and user-friendly configuration editing.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from aniplux.core.config_manager import ConfigManager
from aniplux.core.config_schemas import AppSettings, SourcesConfig
from aniplux.core.config_utils import find_config_issues, optimize_config_for_system
from aniplux.core.exceptions import ConfigurationError


console = Console()


def display_current_config(config_manager: ConfigManager, section: Optional[str] = None) -> None:
    """
    Display current configuration in a formatted panel.
    
    Args:
        config_manager: ConfigManager instance
        section: Specific section to display (optional)
    """
    if section:
        # Display specific section
        if section == "settings":
            config_data = config_manager.settings.model_dump()
        elif section == "sources":
            config_data = config_manager.sources.model_dump()
        else:
            console.print(f"[red]Unknown configuration section: {section}[/red]")
            return
        
        title = f"📋 {section.title()} Configuration"
    else:
        # Display all configuration
        config_data = {
            "settings": config_manager.settings.model_dump(),
            "sources": config_manager.sources.model_dump()
        }
        title = "📋 Current Configuration"
    
    # Format configuration as JSON with syntax highlighting
    config_json = json.dumps(config_data, indent=2, ensure_ascii=False)
    
    panel = Panel(
        config_json,
        title=title,
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(panel)


def display_config_summary(config_manager: ConfigManager) -> None:
    """
    Display a summary of key configuration settings.
    
    Args:
        config_manager: ConfigManager instance
    """
    settings = config_manager.settings
    sources = config_manager.sources
    
    # Create summary table
    table = Table(title="⚙️  Configuration Summary", show_header=True, header_style="bold blue")
    table.add_column("Setting", style="cyan", width=25)
    table.add_column("Value", style="white", width=30)
    table.add_column("Description", style="dim", width=40)
    
    # Add key settings
    table.add_row(
        "Download Directory",
        str(settings.settings.download_directory),
        "Where downloaded files are saved"
    )
    table.add_row(
        "Default Quality",
        settings.settings.default_quality,
        "Default video quality for downloads"
    )
    table.add_row(
        "Concurrent Downloads",
        str(settings.settings.concurrent_downloads),
        "Maximum simultaneous downloads"
    )
    table.add_row(
        "Color Theme",
        settings.ui.color_theme,
        "CLI interface color scheme"
    )
    
    # Add sources summary
    enabled_sources = sources.get_enabled_sources()
    table.add_row(
        "Enabled Sources",
        str(len(enabled_sources)),
        f"Active plugins: {', '.join(enabled_sources.keys()) if enabled_sources else 'None'}"
    )
    
    console.print(table)


def display_sources_status(config_manager: ConfigManager) -> None:
    """
    Display status of all configured sources.
    
    Args:
        config_manager: ConfigManager instance
    """
    sources = config_manager.sources
    
    if not sources.sources:
        console.print("[yellow]No sources configured[/yellow]")
        return
    
    # Create sources table
    table = Table(title="🔌 Source Plugins Status", show_header=True, header_style="bold blue")
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Status", width=10)
    table.add_column("Priority", style="magenta", width=8)
    table.add_column("Description", style="dim", width=40)
    
    for name, config in sources.sources.items():
        # Status with emoji
        if config.enabled:
            status = "[green]✅ Enabled[/green]"
        else:
            status = "[red]❌ Disabled[/red]"
        
        table.add_row(
            config.name or name,
            status,
            str(config.priority),
            config.description or "No description"
        )
    
    console.print(table)


def interactive_setting_update(config_manager: ConfigManager) -> None:
    """
    Interactive setting update with prompts and validation.
    
    Args:
        config_manager: ConfigManager instance
    """
    console.print("[bold blue]🔧 Interactive Configuration Editor[/bold blue]\n")
    
    # Define available settings with metadata
    available_settings = {
        "settings.download_directory": {
            "description": "Directory where downloaded files are saved",
            "type": "path",
            "current": config_manager.settings.settings.download_directory
        },
        "settings.default_quality": {
            "description": "Default video quality for downloads",
            "type": "choice",
            "choices": ["480p", "720p", "1080p", "1440p", "2160p"],
            "current": config_manager.settings.settings.default_quality
        },
        "settings.concurrent_downloads": {
            "description": "Maximum number of concurrent downloads",
            "type": "int",
            "range": (1, 10),
            "current": config_manager.settings.settings.concurrent_downloads
        },
        "ui.color_theme": {
            "description": "CLI interface color theme",
            "type": "choice", 
            "choices": ["default", "dark", "light", "colorful"],
            "current": config_manager.settings.ui.color_theme
        },
        "ui.show_banner": {
            "description": "Show ASCII banner on startup",
            "type": "bool",
            "current": config_manager.settings.ui.show_banner
        }
    }
    
    # Display available settings
    table = Table(title="Available Settings", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Current Value", style="white")
    table.add_column("Description", style="dim")
    
    for key, meta in available_settings.items():
        table.add_row(key, str(meta["current"]), meta["description"])
    
    console.print(table)
    console.print()
    
    # Prompt for setting to update
    setting_key = Prompt.ask(
        "Enter setting key to update (or 'quit' to exit)",
        choices=list(available_settings.keys()) + ["quit"]
    )
    
    if setting_key == "quit":
        return
    
    meta = available_settings[setting_key]
    current_value = meta["current"]
    
    console.print(f"\n[cyan]Updating:[/cyan] {setting_key}")
    console.print(f"[dim]Description:[/dim] {meta['description']}")
    console.print(f"[dim]Current value:[/dim] {current_value}")
    
    # Get new value based on type
    try:
        if meta["type"] == "choice":
            new_value = Prompt.ask(
                "Select new value",
                choices=meta["choices"],
                default=str(current_value)
            )
        elif meta["type"] == "bool":
            new_value = Confirm.ask(
                "Enable this setting?",
                default=current_value
            )
        elif meta["type"] == "int":
            min_val, max_val = meta["range"]
            new_value = int(Prompt.ask(
                f"Enter new value ({min_val}-{max_val})",
                default=str(current_value)
            ))
            if not (min_val <= new_value <= max_val):
                console.print(f"[red]Value must be between {min_val} and {max_val}[/red]")
                return
        elif meta["type"] == "path":
            new_value = Prompt.ask(
                "Enter new path",
                default=str(current_value)
            )
            # Validate path
            path = Path(new_value).expanduser()
            if not path.parent.exists():
                if not Confirm.ask(f"Parent directory {path.parent} doesn't exist. Create it?"):
                    return
                path.parent.mkdir(parents=True, exist_ok=True)
        else:
            new_value = Prompt.ask(
                "Enter new value",
                default=str(current_value)
            )
        
        # Confirm change
        if new_value != current_value:
            console.print(f"\n[yellow]Change:[/yellow] {current_value} → {new_value}")
            if Confirm.ask("Apply this change?"):
                config_manager.update_setting(setting_key, new_value)
                console.print("[green]✅ Setting updated successfully![/green]")
            else:
                console.print("[yellow]Change cancelled[/yellow]")
        else:
            console.print("[dim]No change made[/dim]")
            
    except (ValueError, ConfigurationError) as e:
        console.print(f"[red]Error updating setting: {e}[/red]")


def interactive_source_management(config_manager: ConfigManager) -> None:
    """
    Interactive source plugin management.
    
    Args:
        config_manager: ConfigManager instance
    """
    console.print("[bold blue]🔌 Source Plugin Management[/bold blue]\n")
    
    while True:
        display_sources_status(config_manager)
        console.print()
        
        action = Prompt.ask(
            "Choose action",
            choices=["enable", "disable", "configure", "list", "quit"],
            default="list"
        )
        
        if action == "quit":
            break
        elif action == "list":
            continue
        elif action in ["enable", "disable"]:
            sources = config_manager.sources.sources
            if not sources:
                console.print("[yellow]No sources configured[/yellow]")
                continue
            
            source_name = Prompt.ask(
                f"Select source to {action}",
                choices=list(sources.keys())
            )
            
            if action == "enable":
                config_manager.enable_source(source_name)
                console.print(f"[green]✅ Enabled source: {source_name}[/green]")
            else:
                config_manager.disable_source(source_name)
                console.print(f"[red]❌ Disabled source: {source_name}[/red]")
        
        elif action == "configure":
            console.print("[yellow]Source configuration editing not yet implemented[/yellow]")
        
        console.print()


def run_config_diagnostics(config_manager: ConfigManager) -> None:
    """
    Run configuration diagnostics and display results.
    
    Args:
        config_manager: ConfigManager instance
    """
    console.print("[bold blue]🔍 Configuration Diagnostics[/bold blue]\n")
    
    # Run validation
    validation_report = config_manager.validate_configuration()
    
    if validation_report["valid"]:
        console.print("[green]✅ Configuration is valid[/green]")
    else:
        console.print("[red]❌ Configuration has issues:[/red]")
        for issue in validation_report["issues"]:
            console.print(f"  • {issue}")
    
    # Show warnings
    if validation_report["warnings"]:
        console.print("\n[yellow]⚠️  Warnings:[/yellow]")
        for warning in validation_report["warnings"]:
            console.print(f"  • {warning}")
    
    # Find additional issues
    console.print("\n[blue]🔍 Analyzing configuration...[/blue]")
    issues = find_config_issues(config_manager)
    
    if issues:
        # Group issues by severity
        errors = [i for i in issues if i["severity"] == "error"]
        warnings = [i for i in issues if i["severity"] == "warning"]
        
        if errors:
            console.print("\n[red]❌ Errors found:[/red]")
            for issue in errors:
                console.print(f"  • {issue['message']}")
                if issue.get("suggestion"):
                    console.print(f"    💡 {issue['suggestion']}")
        
        if warnings:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for issue in warnings:
                console.print(f"  • {issue['message']}")
                if issue.get("suggestion"):
                    console.print(f"    💡 {issue['suggestion']}")
    else:
        console.print("[green]✅ No additional issues found[/green]")
    
    # Show optimization suggestions
    console.print("\n[blue]🚀 Checking for optimizations...[/blue]")
    suggestions = optimize_config_for_system(config_manager)
    
    if suggestions:
        console.print("\n[cyan]💡 Optimization suggestions:[/cyan]")
        for suggestion in suggestions:
            console.print(f"  • {suggestion}")
    else:
        console.print("[green]✅ Configuration appears optimized for your system[/green]")


# Export CLI helper functions
__all__ = [
    "display_current_config",
    "display_config_summary",
    "display_sources_status",
    "interactive_setting_update",
    "interactive_source_management",
    "run_config_diagnostics",
]