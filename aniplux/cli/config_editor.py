"""
Configuration Editor - Interactive configuration management with validation.

This module provides interactive configuration editing capabilities
with user-friendly prompts, validation, and rich display formatting.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from datetime import datetime

from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.panel import Panel
from rich.table import Table

from aniplux.core import ConfigManager
from aniplux.core.config_schemas import AppSettings, SourcesConfig
from aniplux.core.config_utils import find_config_issues, optimize_config_for_system
from aniplux.core.exceptions import ConfigurationError, ValidationError
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    handle_error,
    format_success,
    format_warning,
    format_error,
    ThemeName,
    set_theme,
    update_console_theme,
)


logger = logging.getLogger(__name__)


class ConfigurationEditor:
    """
    Interactive configuration editor with validation and rich display.
    
    Provides comprehensive configuration management including editing,
    validation, import/export, and system optimization suggestions.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize configuration editor.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.console = get_console()
        self.ui = UIComponents()
        
        # Configuration sections and their editable settings
        self.editable_settings = {
            "settings": {
                "download_directory": ("Download directory path", str, self._validate_path),
                "default_quality": ("Default video quality", str, self._validate_quality),
                "concurrent_downloads": ("Concurrent downloads", int, self._validate_concurrent),
                "timeout": ("Network timeout (seconds)", int, self._validate_timeout),
                "max_retries": ("Maximum retry attempts", int, self._validate_retries),
                "chunk_size": ("Download chunk size (bytes)", int, self._validate_chunk_size),
            },
            "ui": {
                "show_banner": ("Show startup banner", bool, None),
                "color_theme": ("Color theme", str, self._validate_theme),
                "progress_style": ("Progress bar style", str, self._validate_progress_style),
                "table_style": ("Table style", str, self._validate_table_style),
                "panel_style": ("Panel style", str, self._validate_panel_style),
                "animation_speed": ("Animation speed", str, self._validate_animation_speed),
            },
            "search": {
                "max_results_per_source": ("Max results per source", int, self._validate_max_results),
                "search_timeout": ("Search timeout (seconds)", int, self._validate_search_timeout),
                "enable_fuzzy_search": ("Enable fuzzy search", bool, None),
                "min_query_length": ("Minimum query length", int, self._validate_min_query),
            },
            "logging": {
                "level": ("Logging level", str, self._validate_log_level),
                "file": ("Log file name", str, None),
                "max_size": ("Max log file size", str, self._validate_log_size),
                "backup_count": ("Log backup count", int, self._validate_backup_count),
            }
        }
    
    def show_configuration(self, section: Optional[str] = None) -> None:
        """
        Display current configuration in a formatted view.
        
        Args:
            section: Specific section to show (None for all)
        """
        try:
            if section:
                if section not in self.editable_settings:
                    available_sections = list(self.editable_settings.keys())
                    display_warning(
                        f"Unknown section '{section}'.\n\n"
                        f"Available sections: {', '.join(available_sections)}",
                        "❓ Invalid Section"
                    )
                    return
                
                self._display_section(section)
            else:
                self._display_all_sections()
            
            # Show configuration status
            self._display_config_status()
            
        except Exception as e:
            handle_error(e, "Failed to display configuration")
    
    def _display_all_sections(self) -> None:
        """Display all configuration sections."""
        settings = self.config_manager.settings
        
        for section_name in self.editable_settings.keys():
            self._display_section(section_name)
            self.console.print()
    
    def _display_section(self, section_name: str) -> None:
        """Display a specific configuration section."""
        settings = self.config_manager.settings
        section_data = getattr(settings, section_name)
        
        # Create section table
        table = Table(
            title=f"⚙️  {section_name.title()} Configuration",
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Current Value", style="white", width=20)
        table.add_column("Description", style="dim", width=35)
        
        section_settings = self.editable_settings[section_name]
        
        for key, (description, _, _) in section_settings.items():
            current_value = getattr(section_data, key)
            
            # Format value for display
            if isinstance(current_value, bool):
                display_value = "✅ Yes" if current_value else "❌ No"
            elif isinstance(current_value, (int, float)):
                display_value = str(current_value)
            else:
                display_value = str(current_value)
            
            table.add_row(key, display_value, description)
        
        self.console.print(table)
    
    def _display_config_status(self) -> None:
        """Display configuration validation status."""
        validation_report = self.config_manager.validate_configuration()
        
        status_parts = []
        
        if validation_report["valid"]:
            status_parts.append("[green]✅ Valid[/green]")
        else:
            status_parts.append(f"[red]❌ {len(validation_report['issues'])} errors[/red]")
        
        if validation_report["warnings"]:
            status_parts.append(f"[yellow]⚠️  {len(validation_report['warnings'])} warnings[/yellow]")
        
        status_text = " • ".join(status_parts)
        
        self.console.print()
        self.console.print(f"[dim]Configuration Status: {status_text}[/dim]")
    
    def interactive_edit(self) -> bool:
        """
        Launch interactive configuration editor.
        
        Returns:
            True if configuration was modified, False otherwise
        """
        try:
            self.console.print("[bold blue]🔧 Interactive Configuration Editor[/bold blue]\n")
            
            # Show current configuration summary
            self._display_config_summary()
            
            # Main editing loop
            modified = False
            
            while True:
                self.console.print("\n[bold blue]Configuration Sections:[/bold blue]")
                
                sections = list(self.editable_settings.keys())
                for i, section in enumerate(sections, 1):
                    self.console.print(f"  {i}. {section.title()}")
                
                self.console.print(f"  {len(sections) + 1}. Validate configuration")
                self.console.print(f"  {len(sections) + 2}. Save and exit")
                self.console.print(f"  {len(sections) + 3}. Exit without saving")
                
                choice = Prompt.ask(
                    "\nSelect section to edit",
                    choices=[str(i) for i in range(1, len(sections) + 4)],
                    show_choices=False
                )
                
                choice_num = int(choice)
                
                if choice_num <= len(sections):
                    # Edit specific section
                    section_name = sections[choice_num - 1]
                    if self._edit_section(section_name):
                        modified = True
                elif choice_num == len(sections) + 1:
                    # Validate configuration
                    self._validate_configuration()
                elif choice_num == len(sections) + 2:
                    # Save and exit
                    if modified:
                        display_info("Configuration changes saved!", "✅ Saved")
                    else:
                        display_info("No changes made.", "ℹ️  No Changes")
                    return modified
                else:
                    # Exit without saving
                    if modified:
                        if not Confirm.ask("Exit without saving changes?", default=False):
                            continue
                        display_warning("Configuration changes discarded.", "⚠️  Changes Lost")
                    return False
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Configuration editing cancelled[/yellow]")
            return False
        except Exception as e:
            handle_error(e, "Configuration editing failed")
            return False
    
    def _display_config_summary(self) -> None:
        """Display configuration summary."""
        settings = self.config_manager.settings
        
        summary_items = {
            "Download Directory": settings.settings.download_directory,
            "Default Quality": settings.settings.default_quality,
            "Color Theme": settings.ui.color_theme,
            "Concurrent Downloads": settings.settings.concurrent_downloads,
            "Search Timeout": f"{settings.search.search_timeout}s",
        }
        
        summary_table = self.ui.create_status_grid(summary_items)
        
        panel = self.ui.create_info_panel(
            summary_table,
            title="📋 Configuration Summary"
        )
        
        self.console.print(panel)
    
    def _edit_section(self, section_name: str) -> bool:
        """
        Edit a specific configuration section.
        
        Args:
            section_name: Name of the section to edit
            
        Returns:
            True if section was modified, False otherwise
        """
        self.console.print(f"\n[bold blue]Editing {section_name.title()} Settings[/bold blue]\n")
        
        # Display current section
        self._display_section(section_name)
        
        section_settings = self.editable_settings[section_name]
        modified = False
        
        for key, (description, value_type, validator) in section_settings.items():
            if not Confirm.ask(f"\nEdit '{key}' ({description})?", default=False):
                continue
            
            current_value = self.config_manager.get_setting(f"{section_name}.{key}")
            
            try:
                new_value = self._prompt_for_value(key, description, value_type, current_value, validator)
                
                if new_value != current_value:
                    self.config_manager.update_setting(f"{section_name}.{key}", new_value)
                    
                    # Special handling for theme changes
                    if section_name == "ui" and key == "color_theme":
                        try:
                            theme = ThemeName(new_value)
                            set_theme(theme)
                            update_console_theme(theme)
                            display_info("Theme updated and applied!", "🎨 Theme Changed")
                        except ValueError:
                            display_warning(f"Invalid theme '{new_value}', but saved to configuration.")
                    
                    display_info(f"Updated {key}: {current_value} → {new_value}", "✅ Setting Updated")
                    modified = True
                else:
                    display_info("No change made.", "ℹ️  Unchanged")
                    
            except (ValueError, ConfigurationError) as e:
                display_warning(f"Failed to update {key}: {e}", "❌ Update Failed")
        
        return modified
    
    def _prompt_for_value(
        self,
        key: str,
        description: str,
        value_type: type,
        current_value: Any,
        validator: Optional[Callable[[Any], Optional[str]]]
    ) -> Any:
        """Prompt user for a configuration value."""
        self.console.print(f"\n[cyan]{description}[/cyan]")
        self.console.print(f"[dim]Current value: {current_value}[/dim]")
        
        if value_type == bool:
            return Confirm.ask("Enable this setting?", default=current_value)
        elif value_type == int:
            new_value = IntPrompt.ask("Enter new value", default=current_value)
        elif value_type == float:
            new_value = FloatPrompt.ask("Enter new value", default=current_value)
        else:  # str
            # Provide choices for specific settings
            choices = self._get_choices_for_setting(key)
            if choices:
                new_value = Prompt.ask(
                    "Select new value",
                    choices=choices,
                    default=str(current_value)
                )
            else:
                new_value = Prompt.ask("Enter new value", default=str(current_value))
        
        # Validate the new value
        if validator and callable(validator):
            error = validator(new_value)
            if error:
                raise ValueError(error)
        
        return new_value
    
    def _get_choices_for_setting(self, key: str) -> Optional[List[str]]:
        """Get valid choices for specific settings."""
        choices_map = {
            "default_quality": ["480p", "720p", "1080p", "1440p", "2160p"],
            "color_theme": ["default", "dark", "light", "colorful"],
            "progress_style": ["bar", "spinner", "dots"],
            "table_style": ["rounded", "simple", "grid", "minimal"],
            "panel_style": ["rounded", "square", "heavy", "double"],
            "animation_speed": ["slow", "normal", "fast"],
            "level": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        }
        
        return choices_map.get(key)
    
    def set_configuration_value(self, key: str, value: str) -> bool:
        """
        Set a specific configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'ui.color_theme')
            value: New value as string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse the key to determine type and validation
            parts = key.split('.')
            if len(parts) != 2:
                display_warning(
                    f"Invalid key format: {key}\n\n"
                    "Use dot notation like: ui.color_theme, settings.timeout",
                    "❓ Invalid Key Format"
                )
                return False
            
            section, setting = parts
            
            if section not in self.editable_settings:
                available_sections = list(self.editable_settings.keys())
                display_warning(
                    f"Unknown section '{section}'.\n\n"
                    f"Available sections: {', '.join(available_sections)}",
                    "❓ Invalid Section"
                )
                return False
            
            if setting not in self.editable_settings[section]:
                available_settings = list(self.editable_settings[section].keys())
                display_warning(
                    f"Unknown setting '{setting}' in section '{section}'.\n\n"
                    f"Available settings: {', '.join(available_settings)}",
                    "❓ Invalid Setting"
                )
                return False
            
            # Get setting metadata
            description, value_type, validator = self.editable_settings[section][setting]
            
            # Convert value to appropriate type
            try:
                if value_type == bool:
                    converted_value = value.lower() in ['true', '1', 'yes', 'on', 'enabled']
                elif value_type == int:
                    converted_value = int(value)
                elif value_type == float:
                    converted_value = float(value)
                else:
                    converted_value = value
            except ValueError as e:
                display_warning(
                    f"Invalid value '{value}' for {value_type.__name__} setting.\n\n"
                    f"Error: {e}",
                    "❓ Invalid Value Type"
                )
                return False
            
            # Validate the value
            if validator:
                error = validator(converted_value)
                if error:
                    display_warning(f"Validation failed: {error}", "❌ Validation Error")
                    return False
            
            # Get current value for comparison
            current_value = self.config_manager.get_setting(key)
            
            # Update the setting
            self.config_manager.update_setting(key, converted_value)
            
            # Special handling for theme changes
            if key == "ui.color_theme":
                try:
                    theme = ThemeName(converted_value)
                    set_theme(theme)
                    update_console_theme(theme)
                except ValueError:
                    pass  # Invalid theme, but still saved to config
            
            display_info(
                f"Configuration updated successfully!\n\n"
                f"Setting: {key}\n"
                f"Old value: {current_value}\n"
                f"New value: {converted_value}",
                "✅ Setting Updated"
            )
            
            return True
            
        except ConfigurationError as e:
            handle_error(e, f"Failed to set configuration value '{key}'")
            return False
        except Exception as e:
            handle_error(e, f"Unexpected error setting '{key}'")
            return False
    
    def _validate_configuration(self) -> None:
        """Validate current configuration and display results."""
        self.console.print("\n[bold blue]🔍 Configuration Validation[/bold blue]\n")
        
        # Run validation
        validation_report = self.config_manager.validate_configuration()
        
        if validation_report["valid"]:
            display_info("Configuration is valid!", "✅ Validation Passed")
        else:
            error_text = "Configuration validation failed:\n\n"
            for issue in validation_report["issues"]:
                error_text += f"• {issue}\n"
            
            display_warning(error_text.strip(), "❌ Validation Failed")
        
        # Show warnings
        if validation_report["warnings"]:
            warning_text = "Configuration warnings:\n\n"
            for warning in validation_report["warnings"]:
                warning_text += f"• {warning}\n"
            
            display_warning(warning_text.strip(), "⚠️  Configuration Warnings")
        
        # Show additional issues
        issues = find_config_issues(self.config_manager)
        if issues:
            self.console.print("\n[bold blue]Additional Issues Found:[/bold blue]")
            
            for issue in issues:
                severity = issue["severity"]
                message = issue["message"]
                suggestion = issue.get("suggestion", "")
                
                if severity == "error":
                    self.console.print(f"[red]❌ {message}[/red]")
                else:
                    self.console.print(f"[yellow]⚠️  {message}[/yellow]")
                
                if suggestion:
                    self.console.print(f"   [dim]💡 {suggestion}[/dim]")
        
        # Show optimization suggestions
        suggestions = optimize_config_for_system(self.config_manager)
        if suggestions:
            self.console.print("\n[bold blue]Optimization Suggestions:[/bold blue]")
            for suggestion in suggestions:
                self.console.print(f"[cyan]💡 {suggestion}[/cyan]")
    
    # Validation methods
    def _validate_path(self, value: str) -> Optional[str]:
        """Validate file path."""
        try:
            path = Path(value).expanduser().resolve()
            if not path.parent.exists():
                return f"Parent directory does not exist: {path.parent}"
            return None
        except Exception as e:
            return f"Invalid path: {e}"
    
    def _validate_quality(self, value: str) -> Optional[str]:
        """Validate video quality."""
        valid_qualities = ["480p", "720p", "1080p", "1440p", "2160p"]
        if value not in valid_qualities:
            return f"Invalid quality. Valid options: {', '.join(valid_qualities)}"
        return None
    
    def _validate_concurrent(self, value: int) -> Optional[str]:
        """Validate concurrent downloads."""
        if not (1 <= value <= 10):
            return "Concurrent downloads must be between 1 and 10"
        return None
    
    def _validate_timeout(self, value: int) -> Optional[str]:
        """Validate timeout value."""
        if not (5 <= value <= 300):
            return "Timeout must be between 5 and 300 seconds"
        return None
    
    def _validate_retries(self, value: int) -> Optional[str]:
        """Validate retry count."""
        if not (0 <= value <= 10):
            return "Max retries must be between 0 and 10"
        return None
    
    def _validate_chunk_size(self, value: int) -> Optional[str]:
        """Validate chunk size."""
        if not (1024 <= value <= 1048576):
            return "Chunk size must be between 1KB and 1MB"
        return None
    
    def _validate_theme(self, value: str) -> Optional[str]:
        """Validate theme name."""
        valid_themes = ["default", "dark", "light", "colorful"]
        if value not in valid_themes:
            return f"Invalid theme. Valid options: {', '.join(valid_themes)}"
        return None
    
    def _validate_progress_style(self, value: str) -> Optional[str]:
        """Validate progress style."""
        valid_styles = ["bar", "spinner", "dots"]
        if value not in valid_styles:
            return f"Invalid progress style. Valid options: {', '.join(valid_styles)}"
        return None
    
    def _validate_table_style(self, value: str) -> Optional[str]:
        """Validate table style."""
        valid_styles = ["rounded", "simple", "grid", "minimal"]
        if value not in valid_styles:
            return f"Invalid table style. Valid options: {', '.join(valid_styles)}"
        return None
    
    def _validate_panel_style(self, value: str) -> Optional[str]:
        """Validate panel style."""
        valid_styles = ["rounded", "square", "heavy", "double"]
        if value not in valid_styles:
            return f"Invalid panel style. Valid options: {', '.join(valid_styles)}"
        return None
    
    def _validate_animation_speed(self, value: str) -> Optional[str]:
        """Validate animation speed."""
        valid_speeds = ["slow", "normal", "fast"]
        if value not in valid_speeds:
            return f"Invalid animation speed. Valid options: {', '.join(valid_speeds)}"
        return None
    
    def _validate_max_results(self, value: int) -> Optional[str]:
        """Validate max results per source."""
        if not (1 <= value <= 200):
            return "Max results per source must be between 1 and 200"
        return None
    
    def _validate_search_timeout(self, value: int) -> Optional[str]:
        """Validate search timeout."""
        if not (1 <= value <= 60):
            return "Search timeout must be between 1 and 60 seconds"
        return None
    
    def _validate_min_query(self, value: int) -> Optional[str]:
        """Validate minimum query length."""
        if not (1 <= value <= 10):
            return "Minimum query length must be between 1 and 10"
        return None
    
    def _validate_log_level(self, value: str) -> Optional[str]:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value not in valid_levels:
            return f"Invalid log level. Valid options: {', '.join(valid_levels)}"
        return None
    
    def _validate_log_size(self, value: str) -> Optional[str]:
        """Validate log file size format."""
        import re
        if not re.match(r'^\d+[KMGT]?B$', value.upper()):
            return "Invalid size format. Use format like '10MB', '1GB'"
        return None
    
    def _validate_backup_count(self, value: int) -> Optional[str]:
        """Validate backup count."""
        if not (0 <= value <= 10):
            return "Backup count must be between 0 and 10"
        return None
# Export configuration editor
__all__ = ["ConfigurationEditor"]