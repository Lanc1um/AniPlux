"""
Sources Command - Plugin management functionality.

This module implements source plugin management commands for enabling,
disabling, and configuring anime source plugins.
"""

import asyncio
import typer
from typing import Optional, Any
from rich.prompt import Prompt, Confirm

from aniplux.cli.context import get_config_manager
from aniplux.cli.source_manager import SourceManager
from aniplux.core.config_cli import interactive_source_management
from aniplux.core.exceptions import PluginError, ConfigurationError
from aniplux.ui import (
    get_console,
    handle_error,
    display_info,
    display_warning,
)

# Create sources command group
app = typer.Typer(
    name="sources",
    help="🔌 Manage anime source plugins",
    no_args_is_help=True,
)

console = get_console()


@app.command(name="list")
def list_sources(
    enabled_only: bool = typer.Option(
        False,
        "--enabled",
        "-e",
        help="Show only enabled sources"
    ),
    details: bool = typer.Option(
        False,
        "--details",
        "-d",
        help="Show detailed plugin information"
    ),
) -> None:
    """
    📋 List available source plugins.
    
    Display all discovered source plugins with their status,
    priority, and configuration information.
    
    Examples:
    
        aniplux sources list
        
        aniplux sources list --enabled
        
        aniplux sources list --details
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_list_sources(
            enabled_only=enabled_only,
            show_details=details,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Source listing cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "Failed to list sources")
        raise typer.Exit(1)


async def _list_sources(
    enabled_only: bool,
    show_details: bool,
    config_manager: Any
) -> None:
    """
    List source plugins.
    
    Args:
        enabled_only: Show only enabled sources
        show_details: Show detailed information
        config_manager: Configuration manager instance
    """
    source_manager = SourceManager(config_manager)
    
    await source_manager.list_sources(
        enabled_only=enabled_only,
        show_details=show_details
    )


@app.command(name="enable")
def enable_source(
    source_name: str = typer.Argument(..., help="Source plugin name to enable"),
) -> None:
    """
    ✅ Enable a source plugin.
    
    Enable a specific source plugin for use in searches and downloads.
    The command will also test the source connectivity after enabling.
    
    Examples:
    
        aniplux sources enable sample
        
        aniplux sources enable gogoanime
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_enable_source(
            source_name=source_name,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Source enable cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, f"Failed to enable source '{source_name}'")
        raise typer.Exit(1)


async def _enable_source(source_name: str, config_manager: Any) -> None:
    """
    Enable a source plugin.
    
    Args:
        source_name: Name of the source to enable
        config_manager: Configuration manager instance
    """
    source_manager = SourceManager(config_manager)
    
    success = await source_manager.enable_source(source_name)
    
    if not success:
        raise typer.Exit(1)


@app.command(name="disable")
def disable_source(
    source_name: str = typer.Argument(..., help="Source plugin name to disable"),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt"
    ),
) -> None:
    """
    ❌ Disable a source plugin.
    
    Disable a specific source plugin to exclude it from operations.
    This will prevent the source from being used in searches and downloads.
    
    Examples:
    
        aniplux sources disable sample
        
        aniplux sources disable gogoanime --yes
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_disable_source(
            source_name=source_name,
            skip_confirm=confirm,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Source disable cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, f"Failed to disable source '{source_name}'")
        raise typer.Exit(1)


async def _disable_source(
    source_name: str,
    skip_confirm: bool,
    config_manager: Any
) -> None:
    """
    Disable a source plugin.
    
    Args:
        source_name: Name of the source to disable
        skip_confirm: Skip confirmation prompt
        config_manager: Configuration manager instance
    """
    # Confirm disable action
    if not skip_confirm:
        if not Confirm.ask(f"Disable source '{source_name}'?", default=False):
            display_info("Source disable cancelled.", "ℹ️  Cancelled")
            return
    
    source_manager = SourceManager(config_manager)
    
    success = await source_manager.disable_source(source_name)
    
    if not success:
        raise typer.Exit(1)


@app.command(name="test")
def test_source(
    source_name: Optional[str] = typer.Argument(
        None,
        help="Source plugin name to test (tests all enabled if not specified)"
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        "-t",
        help="Connection timeout in seconds",
        min=5,
        max=120
    ),
) -> None:
    """
    🧪 Test source plugin connectivity.
    
    Test connection and basic functionality of source plugins.
    This helps verify that sources are working correctly.
    
    Examples:
    
        aniplux sources test
        
        aniplux sources test sample
        
        aniplux sources test gogoanime --timeout 60
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_test_sources(
            source_name=source_name,
            timeout=timeout,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Source testing cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "Failed to test sources")
        raise typer.Exit(1)


async def _test_sources(
    source_name: Optional[str],
    timeout: int,
    config_manager: Any
) -> None:
    """
    Test source connectivity.
    
    Args:
        source_name: Specific source to test
        timeout: Connection timeout
        config_manager: Configuration manager instance
    """
    source_manager = SourceManager(config_manager)
    
    # Update timeout in plugin manager if needed
    # This would require extending the plugin manager to support timeout configuration
    
    results = await source_manager.test_sources(source_name)
    
    # Check if any tests failed
    if results:
        failed_tests = [name for name, result in results.items() if not result["success"]]
        if failed_tests:
            raise typer.Exit(1)


@app.command(name="reload")
def reload_sources() -> None:
    """
    🔄 Reload source plugins.
    
    Reload all source plugins from the plugins directory.
    This is useful for development and after plugin updates.
    
    Examples:
    
        aniplux sources reload
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_reload_sources(config_manager))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Source reload cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "Failed to reload sources")
        raise typer.Exit(1)


async def _reload_sources(config_manager: Any) -> None:
    """
    Reload source plugins.
    
    Args:
        config_manager: Configuration manager instance
    """
    source_manager = SourceManager(config_manager)
    
    success = await source_manager.reload_sources()
    
    if not success:
        raise typer.Exit(1)


@app.command(name="info")
def source_info(
    source_name: str = typer.Argument(..., help="Source plugin name"),
) -> None:
    """
    ℹ️  Show detailed source information.
    
    Display detailed information about a specific source plugin
    including metadata, configuration, and capabilities.
    
    Examples:
    
        aniplux sources info sample
        
        aniplux sources info gogoanime
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_show_source_info(
            source_name=source_name,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Source info cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, f"Failed to get source info for '{source_name}'")
        raise typer.Exit(1)


async def _show_source_info(source_name: str, config_manager: Any) -> None:
    """
    Show detailed source information.
    
    Args:
        source_name: Name of the source
        config_manager: Configuration manager instance
    """
    source_manager = SourceManager(config_manager)
    
    success = await source_manager.show_source_info(source_name)
    
    if not success:
        raise typer.Exit(1)


@app.command(name="configure")
def configure_source(
    source_name: str = typer.Argument(..., help="Source plugin name to configure"),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Use interactive configuration editor"
    ),
) -> None:
    """
    ⚙️  Configure source plugin settings.
    
    Interactive configuration editor for source-specific settings.
    This allows you to customize plugin behavior and connection parameters.
    
    Examples:
    
        aniplux sources configure sample
        
        aniplux sources configure gogoanime --no-interactive
    """
    try:
        config_manager = get_config_manager()
        
        if interactive:
            # Use the interactive source management from config_cli
            interactive_source_management(config_manager)
        else:
            display_info(
                "Non-interactive source configuration is not yet implemented.\n"
                "Use the interactive mode or edit the configuration files directly.",
                "⚙️  Configuration"
            )
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Source configuration cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, f"Failed to configure source '{source_name}'")
        raise typer.Exit(1)


@app.command(name="priority")
def set_source_priority(
    source_name: str = typer.Argument(..., help="Source plugin name"),
    priority: int = typer.Argument(..., help="Priority value (lower = higher priority)", min=1, max=100),
) -> None:
    """
    🔢 Set source priority.
    
    Set the priority for a source plugin. Lower numbers indicate higher priority.
    Sources with higher priority are searched first and preferred for downloads.
    
    Examples:
    
        aniplux sources priority sample 1
        
        aniplux sources priority gogoanime 5
    """
    try:
        config_manager = get_config_manager()
        
        # Get current source config
        source_config = config_manager.sources.get_source(source_name)
        
        if not source_config:
            display_warning(
                f"Source '{source_name}' not found in configuration.\n\n"
                "Available sources can be seen with: aniplux sources list",
                "🔌 Source Not Found"
            )
            raise typer.Exit(1)
        
        # Update priority
        config_manager.update_source_config(source_name, {"priority": priority})
        
        display_info(
            f"Priority for source '{source_name}' set to {priority}.\n\n"
            "Lower numbers indicate higher priority in search and download operations.",
            "🔢 Priority Updated"
        )
        
    except ConfigurationError as e:
        handle_error(e, f"Failed to set priority for source '{source_name}'")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e, f"Unexpected error setting priority for source '{source_name}'")
        raise typer.Exit(1)


@app.command(name="status")
def sources_status() -> None:
    """
    📊 Show sources status summary.
    
    Display a quick overview of all sources with their current status,
    including enabled/disabled state and any error conditions.
    
    Examples:
    
        aniplux sources status
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_show_sources_status(config_manager))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Sources status cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "Failed to get sources status")
        raise typer.Exit(1)


async def _show_sources_status(config_manager: Any) -> None:
    """
    Show sources status summary.
    
    Args:
        config_manager: Configuration manager instance
    """
    source_manager = SourceManager(config_manager)
    
    # This is essentially the same as list but with a focus on status
    await source_manager.list_sources(enabled_only=False, show_details=False)


# Export the command app
__all__ = ["app"]