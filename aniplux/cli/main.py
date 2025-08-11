"""
CLI Main Application - Typer app entry point with clean startup.

This module provides the main CLI application entry point with beautiful
startup sequence, theme management, and command registration.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.traceback import install as install_rich_traceback

from aniplux import __version__
from aniplux.core import ConfigManager, create_default_config_files
from aniplux.core.exceptions import AniPluxError, ConfigurationError
from aniplux.ui import (
    setup_console,
    get_console,
    ThemeName,
    set_theme,
    handle_error,
    display_info,
    status_spinner,
)
from aniplux.cli.startup import StartupManager
from aniplux.cli.context import (
    get_config_manager,
    set_config_manager,
    get_startup_manager,
    set_startup_manager
)


# Create main Typer application
app = typer.Typer(
    name="aniplux",
    help="🎌 Modern anime episode downloader with beautiful CLI interface",
    epilog="Visit https://github.com/aniplux/aniplux for documentation and support.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version information and exit",
        is_flag=True,
    ),
    config_dir: Optional[Path] = typer.Option(
        None,
        "--config-dir",
        help="Configuration directory path",
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    theme: Optional[ThemeName] = typer.Option(
        None,
        "--theme",
        help="UI color theme",
        case_sensitive=False,
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode with detailed logging",
        is_flag=True,
    ),
    no_banner: bool = typer.Option(
        False,
        "--no-banner",
        help="Disable startup banner",
        is_flag=True,
    ),
) -> None:
    """
    🎌 AniPlux - Modern anime episode downloader.
    
    A beautiful command-line tool for searching, browsing, and downloading
    anime episodes from various sources with a clean, interactive interface.
    """
    # Handle version flag
    if version:
        console = get_console()
        console.print(f"[bold blue]AniPlux[/bold blue] version [green]{__version__}[/green]")
        raise typer.Exit()
    
    # Initialize application
    try:
        _initialize_application(
            config_dir=config_dir,
            theme=theme,
            debug=debug,
            show_banner=not no_banner,
        )
        

        
    except Exception as e:
        # Handle initialization errors gracefully
        console = get_console()
        if isinstance(e, AniPluxError):
            handle_error(e, "During application initialization")
        else:
            handle_error(e, "Unexpected error during startup", show_traceback=debug)
        raise typer.Exit(1)


def _initialize_application(
    config_dir: Optional[Path] = None,
    theme: Optional[ThemeName] = None,
    debug: bool = False,
    show_banner: bool = True,
) -> None:
    """
    Initialize the application with configuration and UI setup.
    
    Args:
        config_dir: Configuration directory override
        theme: Theme override
        debug: Enable debug mode
        show_banner: Whether to show startup banner
    """
    # Set up logging
    _setup_logging(debug)
    
    # Install rich traceback handler
    install_rich_traceback(show_locals=debug)
    
    # Initialize startup manager
    startup_manager = StartupManager()
    set_startup_manager(startup_manager)
    
    # Determine configuration directory
    if config_dir is None:
        config_dir = Path("config")
    
    # Create default configuration if needed
    if not config_dir.exists():
        with status_spinner("Creating default configuration..."):
            create_default_config_files(config_dir)
    
    # Initialize configuration manager
    try:
        with status_spinner("Loading configuration..."):
            config_manager = ConfigManager(config_dir)
            set_config_manager(config_manager)
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}", str(config_dir))
    
    # Set up console and theme
    _setup_ui(theme, debug)
    
    # Show startup banner if enabled
    if show_banner and config_manager.settings.ui.show_banner:
        startup_manager.show_banner()
    
    # Validate configuration
    startup_manager.validate_startup_configuration(config_manager)


def _setup_logging(debug: bool = False) -> None:
    """
    Set up application logging.
    
    Args:
        debug: Enable debug logging
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
        ],
    )
    
    # Reduce noise from third-party libraries
    if not debug:
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def _setup_ui(theme_override: Optional[ThemeName] = None, debug: bool = False) -> None:
    """
    Set up UI console and theme.
    
    Args:
        theme_override: Theme to use (overrides configuration)
        debug: Enable debug mode
    """
    # Determine theme
    if theme_override:
        theme = theme_override
    else:
        try:
            config_manager = get_config_manager()
            theme_name = config_manager.settings.ui.color_theme
            try:
                theme = ThemeName(theme_name)
            except ValueError:
                theme = ThemeName.DEFAULT
        except RuntimeError:
            theme = ThemeName.DEFAULT
    
    # Set global theme
    set_theme(theme)
    
    # Set up console
    setup_console(
        theme_name=theme,
        force_terminal=None,  # Auto-detect
    )
    
    if debug:
        display_info(f"UI initialized with theme: {theme.value}")


def _register_commands() -> None:
    """Register command groups with the main app."""
    # Import commands here to avoid circular imports
    from aniplux.cli.commands import search, download, config, sources, episodes
    
    # Register command groups
    app.add_typer(search.app, name="search", help="🔍 Search for anime")
    app.add_typer(download.app, name="download", help="⬇️  Download episodes")
    app.add_typer(config.app, name="config", help="⚙️  Manage configuration")
    app.add_typer(sources.app, name="sources", help="🔌 Manage source plugins")
    app.add_typer(episodes.app, name="episodes", help="📺 Browse anime episodes")


# Register commands at module level to ensure they're available for help
_register_commands()


@app.command(name="info")
def show_info() -> None:
    """📋 Show application and system information."""
    from aniplux.cli.commands.info import show_application_info
    
    config_manager = get_config_manager()
    show_application_info(config_manager)


@app.command(name="doctor")
def run_diagnostics() -> None:
    """🔍 Run system diagnostics and health checks."""
    from aniplux.cli.commands.doctor import run_system_diagnostics
    
    config_manager = get_config_manager()
    run_system_diagnostics(config_manager)


def cli_main() -> None:
    """
    Main CLI entry point for the aniplux command.
    
    This function is called when the user runs 'aniplux' from the command line.
    """
    try:
        app()
    except KeyboardInterrupt:
        console = get_console()
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        console = get_console()
        handle_error(e, "Unexpected error in CLI")
        sys.exit(1)


# Export main components
__all__ = [
    "app",
    "cli_main",
    "get_config_manager",
    "get_startup_manager",
]