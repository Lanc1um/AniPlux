"""
Configuration Command - Settings management functionality.

This module implements configuration commands for managing application
settings with interactive editing and validation.
"""

import typer
from typing import Optional
from pathlib import Path

from aniplux.core import ConfigManager
from aniplux.cli.config_editor import ConfigurationEditor
from aniplux.ui import (
    get_console, 
    display_info, 
    display_warning, 
    handle_error,
    format_success
)

# Create config command group
app = typer.Typer(
    name="config",
    help="⚙️  Manage application configuration and settings",
    no_args_is_help=True,
)

console = get_console()

# Initialize configuration manager and editor
config_manager = ConfigManager()
config_editor = ConfigurationEditor(config_manager)


@app.command(name="show")
def show_config(
    section: Optional[str] = typer.Argument(
        None,
        help="Configuration section to display (settings, sources, ui, etc.)"
    ),
) -> None:
    """
    📋 Display current configuration.
    
    Show the current application configuration in a formatted display.
    Optionally specify a section to show only that part of the config.
    """
    try:
        config_editor.show_configuration(section)
    except Exception as e:
        handle_error(e, "Failed to display configuration")


@app.command(name="edit")
def edit_config() -> None:
    """
    ✏️  Interactive configuration editor.
    
    Launch an interactive configuration editor with prompts
    for updating settings with validation.
    """
    try:
        modified = config_editor.interactive_edit()
        if modified:
            display_info("Configuration changes have been saved.", "✅ Configuration Updated")
        else:
            display_info("No configuration changes were made.", "ℹ️  No Changes")
    except KeyboardInterrupt:
        display_warning("Configuration editing cancelled by user.", "⚠️  Cancelled")
    except Exception as e:
        handle_error(e, "Configuration editing failed")


@app.command(name="set")
def set_config(
    key: str = typer.Argument(..., help="Configuration key (dot notation)"),
    value: str = typer.Argument(..., help="New value for the setting"),
) -> None:
    """
    🔧 Set a configuration value.
    
    Set a specific configuration value using dot notation.
    Example: aniplux config set ui.color_theme dark
    """
    try:
        success = config_editor.set_configuration_value(key, value)
        if not success:
            raise typer.Exit(1)
    except Exception as e:
        handle_error(e, f"Failed to set configuration value '{key}'")
        raise typer.Exit(1)


@app.command(name="reset")
def reset_config(
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt"
    ),
) -> None:
    """
    🔄 Reset configuration to defaults.
    
    Reset all configuration settings to their default values.
    This action requires confirmation unless --yes is used.
    """
    try:
        if not confirm:
            from rich.prompt import Confirm
            if not Confirm.ask(
                "[bold red]⚠️  This will reset ALL configuration to defaults. Continue?[/bold red]",
                default=False
            ):
                display_info("Configuration reset cancelled.", "ℹ️  Cancelled")
                return
        
        config_manager.reset_to_defaults()
        display_info(
            "Configuration has been reset to default values.\n\n"
            "All custom settings have been restored to their original state.",
            "✅ Configuration Reset"
        )
        
    except Exception as e:
        handle_error(e, "Failed to reset configuration")
        raise typer.Exit(1)


@app.command(name="validate")
def validate_config() -> None:
    """
    ✅ Validate current configuration.
    
    Check the current configuration for errors and inconsistencies.
    Provides detailed validation report with suggestions.
    """
    try:
        config_editor._validate_configuration()
    except Exception as e:
        handle_error(e, "Configuration validation failed")


@app.command(name="export")
def export_config(
    output: Path = typer.Argument(..., help="Output file path"),
) -> None:
    """📤 Export configuration to file."""
    try:
        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists and confirm overwrite
        if output.exists():
            from rich.prompt import Confirm
            if not Confirm.ask(f"File {output} already exists. Overwrite?", default=False):
                display_info("Export cancelled.", "ℹ️  Cancelled")
                return
        
        config_manager.export_config(output)
        display_info(
            f"Configuration exported successfully!\n\n"
            f"Export file: {output}\n"
            f"File size: {output.stat().st_size} bytes",
            "✅ Export Complete"
        )
        
    except Exception as e:
        handle_error(e, f"Failed to export configuration to '{output}'")
        raise typer.Exit(1)


@app.command(name="import")
def import_config(
    input_file: Path = typer.Argument(..., help="Configuration file to import"),
) -> None:
    """📥 Import configuration from file."""
    try:
        # Check if input file exists
        if not input_file.exists():
            display_warning(
                f"Configuration file not found: {input_file}",
                "❌ File Not Found"
            )
            raise typer.Exit(1)
        
        # Confirm import action
        from rich.prompt import Confirm
        if not Confirm.ask(
            f"[bold yellow]⚠️  This will replace current configuration with settings from {input_file}. Continue?[/bold yellow]",
            default=False
        ):
            display_info("Configuration import cancelled.", "ℹ️  Cancelled")
            return
        
        config_manager.import_config(input_file)
        display_info(
            f"Configuration imported successfully!\n\n"
            f"Import file: {input_file}\n"
            f"Settings have been updated and saved.",
            "✅ Import Complete"
        )
        
    except Exception as e:
        handle_error(e, f"Failed to import configuration from '{input_file}'")
        raise typer.Exit(1)


@app.command(name="backup")
def backup_config(
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Description for the backup"
    ),
) -> None:
    """💾 Create a backup of current configuration."""
    try:
        from aniplux.cli.config_backup import ConfigurationBackupManager
        
        backup_manager = ConfigurationBackupManager(config_manager)
        backup_path = backup_manager.create_backup(description)
        
        display_info(
            f"Configuration backup created successfully!\n\n"
            f"Backup file: {backup_path.name}\n"
            f"Location: {backup_path.parent}\n"
            f"Description: {description or 'Manual backup'}",
            "💾 Backup Created"
        )
        
    except Exception as e:
        handle_error(e, "Failed to create configuration backup")
        raise typer.Exit(1)


@app.command(name="restore")
def restore_config(
    backup_name: Optional[str] = typer.Argument(
        None,
        help="Name of backup file to restore (without path)"
    ),
    list_backups: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List available backups"
    ),
) -> None:
    """🔄 Restore configuration from backup."""
    try:
        from aniplux.cli.config_backup import ConfigurationBackupManager
        
        backup_manager = ConfigurationBackupManager(config_manager)
        
        if list_backups or not backup_name:
            backup_manager.display_backups()
            
            if not backup_name:
                from rich.prompt import Prompt
                backup_name = Prompt.ask(
                    "\nEnter backup name to restore (or press Enter to cancel)",
                    default=""
                )
                
                if not backup_name:
                    display_info("Restore cancelled.", "ℹ️  Cancelled")
                    return
        
        # Find backup file
        backup_path = backup_manager.backup_dir / backup_name
        if not backup_path.exists():
            display_warning(
                f"Backup file not found: {backup_name}",
                "❌ Backup Not Found"
            )
            raise typer.Exit(1)
        
        # Confirm restore
        from rich.prompt import Confirm
        if not Confirm.ask(
            f"[bold yellow]⚠️  This will replace current configuration with backup '{backup_name}'. Continue?[/bold yellow]",
            default=False
        ):
            display_info("Restore cancelled.", "ℹ️  Cancelled")
            return
        
        success = backup_manager.restore_backup(backup_path)
        if not success:
            raise typer.Exit(1)
        
    except Exception as e:
        handle_error(e, f"Failed to restore configuration from backup")
        raise typer.Exit(1)


@app.command(name="backups")
def list_backups() -> None:
    """📋 List all configuration backups."""
    try:
        from aniplux.cli.config_backup import ConfigurationBackupManager
        
        backup_manager = ConfigurationBackupManager(config_manager)
        backup_manager.display_backups()
        
    except Exception as e:
        handle_error(e, "Failed to list configuration backups")


@app.command(name="cleanup")
def cleanup_backups(
    keep: int = typer.Option(
        10,
        "--keep",
        "-k",
        help="Number of backups to keep (default: 10)"
    ),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt"
    ),
) -> None:
    """🧹 Clean up old configuration backups."""
    try:
        from aniplux.cli.config_backup import ConfigurationBackupManager
        
        backup_manager = ConfigurationBackupManager(config_manager)
        backups = backup_manager.list_backups()
        
        if len(backups) <= keep:
            display_info(
                f"No cleanup needed. Found {len(backups)} backups, keeping {keep}.",
                "ℹ️  No Action Required"
            )
            return
        
        to_delete = len(backups) - keep
        
        if not confirm:
            from rich.prompt import Confirm
            if not Confirm.ask(
                f"[bold yellow]Delete {to_delete} old backup(s), keeping {keep} most recent?[/bold yellow]",
                default=False
            ):
                display_info("Cleanup cancelled.", "ℹ️  Cancelled")
                return
        
        deleted_count = backup_manager.cleanup_old_backups(keep)
        
        if deleted_count > 0:
            display_info(
                f"Cleanup completed! Deleted {deleted_count} old backup(s).",
                "🧹 Cleanup Complete"
            )
        else:
            display_info("No backups were deleted.", "ℹ️  No Changes")
        
    except Exception as e:
        handle_error(e, "Failed to cleanup configuration backups")
        raise typer.Exit(1)


@app.command(name="preview")
def preview_config(
    setting: Optional[str] = typer.Argument(
        None,
        help="Setting to preview (e.g., 'ui.color_theme dark')"
    ),
    theme: Optional[str] = typer.Option(
        None,
        "--theme",
        "-t",
        help="Preview a specific theme"
    ),
    all_themes: bool = typer.Option(
        False,
        "--all-themes",
        help="Preview all available themes"
    ),
) -> None:
    """🎨 Preview configuration changes before applying them."""
    try:
        from aniplux.cli.config_preview import ConfigurationPreview
        
        preview = ConfigurationPreview()
        
        if all_themes:
            preview.preview_all_themes()
        elif theme:
            preview.preview_theme(theme)
        elif setting:
            # Parse setting argument (e.g., "ui.color_theme dark")
            parts = setting.split()
            if len(parts) != 2:
                display_warning(
                    "Invalid setting format. Use: setting_path new_value\n"
                    "Example: ui.color_theme dark",
                    "❓ Invalid Format"
                )
                return
            
            setting_path, new_value = parts
            current_value = config_manager.get_setting(setting_path)
            
            if current_value is None:
                display_warning(
                    f"Setting '{setting_path}' not found.",
                    "❓ Invalid Setting"
                )
                return
            
            preview.preview_setting_change(setting_path, current_value, new_value)
        else:
            # Show preview help
            display_info(
                "Configuration Preview Options:\n\n"
                "• aniplux config preview --all-themes\n"
                "• aniplux config preview --theme dark\n"
                "• aniplux config preview 'ui.color_theme light'\n"
                "• aniplux config preview 'ui.table_style grid'",
                "🎨 Preview Help"
            )
        
    except Exception as e:
        handle_error(e, "Failed to preview configuration")


@app.command(name="wizard")
def config_wizard() -> None:
    """🧙 Run the configuration setup wizard."""
    try:
        from aniplux.cli.config_wizard import ConfigurationWizard
        
        wizard = ConfigurationWizard(config_manager)
        success = wizard.run_wizard()
        
        if success:
            display_info(
                "Configuration wizard completed successfully!\n"
                "Your settings have been saved and applied.",
                "🎉 Wizard Complete"
            )
        else:
            display_info(
                "Configuration wizard was cancelled.\n"
                "Your existing settings remain unchanged.",
                "ℹ️  Wizard Cancelled"
            )
        
    except Exception as e:
        handle_error(e, "Configuration wizard failed")
        raise typer.Exit(1)


@app.command(name="help")
def config_help(
    setting: Optional[str] = typer.Argument(
        None,
        help="Specific setting to get help for (e.g., 'ui.color_theme')"
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Show help for entire section"
    ),
    commands: bool = typer.Option(
        False,
        "--commands",
        "-c",
        help="Show help for configuration commands"
    ),
) -> None:
    """📖 Show configuration help and documentation."""
    try:
        from aniplux.cli.config_help import ConfigurationHelp
        
        help_system = ConfigurationHelp()
        
        if commands:
            help_system.show_command_help()
        elif section:
            help_system.show_section_help(section)
        elif setting:
            help_system.show_setting_help(setting)
        else:
            help_system.show_all_help()
        
    except Exception as e:
        handle_error(e, "Failed to show configuration help")


# Export the command app
__all__ = ["app"]