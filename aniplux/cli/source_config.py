"""
Source Configuration - Interactive source plugin configuration utilities.

This module provides utilities for configuring source plugins with
interactive prompts and validation.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.panel import Panel

from aniplux.core import ConfigManager
from aniplux.core.config_schemas import SourceConfig
from aniplux.core.exceptions import ConfigurationError, ValidationError
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    handle_error,
    format_success,
    format_warning,
)


logger = logging.getLogger(__name__)


class SourceConfigManager:
    """
    Interactive source configuration manager.
    
    Provides utilities for configuring source plugins with
    user-friendly prompts and validation.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize source config manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.console = get_console()
        self.ui = UIComponents()
    
    def configure_source_interactive(self, source_name: str) -> bool:
        """
        Interactive configuration for a source plugin.
        
        Args:
            source_name: Name of the source to configure
            
        Returns:
            True if configuration was updated, False otherwise
        """
        try:
            # Get current source configuration
            current_config = self.config_manager.sources.get_source(source_name)
            
            if not current_config:
                # Create new source configuration
                if not Confirm.ask(f"Source '{source_name}' not found. Create new configuration?"):
                    return False
                
                current_config = SourceConfig()
            
            self.console.print(f"\n[bold blue]🔧 Configuring Source: {source_name}[/bold blue]\n")
            
            # Display current configuration
            self._display_current_config(source_name, current_config)
            
            # Interactive configuration
            updated_config = self._interactive_config_edit(current_config)
            
            if updated_config != current_config:
                # Save updated configuration
                self.config_manager.sources.add_source(source_name, updated_config)
                
                display_info(
                    f"Configuration for '{source_name}' updated successfully!",
                    "✅ Configuration Saved"
                )
                return True
            else:
                display_info("No changes made to configuration.", "ℹ️  No Changes")
                return False
                
        except Exception as e:
            handle_error(e, f"Failed to configure source '{source_name}'")
            return False
    
    def _display_current_config(self, source_name: str, config: SourceConfig) -> None:
        """Display current source configuration."""
        config_lines = []
        
        # Basic settings
        config_lines.append(f"[bold]Enabled:[/bold] {'Yes' if config.enabled else 'No'}")
        config_lines.append(f"[bold]Priority:[/bold] {config.priority}")
        
        if config.name:
            config_lines.append(f"[bold]Display Name:[/bold] {config.name}")
        
        if config.description:
            config_lines.append(f"[bold]Description:[/bold] {config.description}")
        
        # Plugin-specific configuration
        if config.config:
            config_lines.append(f"\n[bold]Plugin Configuration:[/bold]")
            for key, value in config.config.items():
                config_lines.append(f"  [dim]{key}:[/dim] {value}")
        
        content = "\n".join(config_lines)
        
        panel = self.ui.create_info_panel(
            content,
            title=f"📋 Current Configuration - {source_name}"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def _interactive_config_edit(self, current_config: SourceConfig) -> SourceConfig:
        """Interactive configuration editing."""
        # Create a copy to modify
        new_config = SourceConfig(
            enabled=current_config.enabled,
            priority=current_config.priority,
            name=current_config.name,
            description=current_config.description,
            config=current_config.config.copy()
        )
        
        # Basic settings
        self.console.print("[bold blue]Basic Settings[/bold blue]")
        
        # Enabled status
        new_config.enabled = Confirm.ask(
            "Enable this source?",
            default=current_config.enabled
        )
        
        # Priority
        new_config.priority = IntPrompt.ask(
            "Priority (1-100, lower = higher priority)",
            default=current_config.priority,
            show_default=True
        )
        
        if not (1 <= new_config.priority <= 100):
            display_warning("Priority must be between 1 and 100. Using default value.")
            new_config.priority = current_config.priority
        
        # Display name
        new_name = Prompt.ask(
            "Display name (optional)",
            default=current_config.name or "",
            show_default=True
        ).strip()
        
        new_config.name = new_name if new_name else None
        
        # Description
        new_description = Prompt.ask(
            "Description (optional)",
            default=current_config.description or "",
            show_default=True
        ).strip()
        
        new_config.description = new_description if new_description else None
        
        # Plugin-specific configuration
        self.console.print(f"\n[bold blue]Plugin Configuration[/bold blue]")
        
        if current_config.config:
            self.console.print("Current plugin settings:")
            for key, value in current_config.config.items():
                self.console.print(f"  [cyan]{key}[/cyan]: {value}")
            self.console.print()
        
        if Confirm.ask("Configure plugin-specific settings?", default=bool(current_config.config)):
            new_config.config = self._configure_plugin_settings(current_config.config)
        
        return new_config
    
    def _configure_plugin_settings(self, current_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Configure plugin-specific settings."""
        settings = current_settings.copy()
        
        # Common plugin settings
        common_settings = {
            "base_url": ("Base URL", str, "https://example.com"),
            "rate_limit": ("Rate limit (seconds)", float, 1.0),
            "timeout": ("Request timeout (seconds)", int, 30),
            "user_agent": ("User agent string", str, "AniPlux/0.1.0"),
            "max_retries": ("Maximum retries", int, 3),
        }
        
        self.console.print("Configure common plugin settings:")
        self.console.print("[dim]Press Enter to keep current value or skip if not applicable[/dim]\n")
        
        for key, (description, value_type, default_value) in common_settings.items():
            current_value = settings.get(key, default_value)
            
            try:
                if value_type == str:
                    new_value = Prompt.ask(
                        f"{description}",
                        default=str(current_value),
                        show_default=True
                    ).strip()
                    
                    if new_value:
                        settings[key] = new_value
                    elif key in settings:
                        # Remove if empty and was previously set
                        if not Confirm.ask(f"Remove {key} setting?", default=False):
                            settings[key] = current_value
                        else:
                            settings.pop(key, None)
                
                elif value_type == int:
                    new_value = IntPrompt.ask(
                        f"{description}",
                        default=int(current_value) if current_value else default_value,
                        show_default=True
                    )
                    settings[key] = new_value
                
                elif value_type == float:
                    new_value = FloatPrompt.ask(
                        f"{description}",
                        default=float(current_value) if current_value else default_value,
                        show_default=True
                    )
                    settings[key] = new_value
                    
            except (ValueError, TypeError) as e:
                display_warning(f"Invalid value for {key}: {e}")
                continue
        
        # Custom settings
        if Confirm.ask("\nAdd custom plugin settings?", default=False):
            settings.update(self._configure_custom_settings(settings))
        
        return settings
    
    def _configure_custom_settings(self, current_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Configure custom plugin settings."""
        custom_settings = {}
        
        self.console.print("\n[bold blue]Custom Settings[/bold blue]")
        self.console.print("[dim]Add custom key-value pairs for plugin-specific configuration[/dim]\n")
        
        while True:
            key = Prompt.ask("Setting name (or press Enter to finish)", default="").strip()
            
            if not key:
                break
            
            if key in current_settings:
                current_value = current_settings[key]
                self.console.print(f"[dim]Current value: {current_value}[/dim]")
            
            value = Prompt.ask(f"Value for '{key}'", default="").strip()
            
            if value:
                # Try to convert to appropriate type
                try:
                    # Try integer
                    if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                        custom_settings[key] = int(value)
                    # Try float
                    elif '.' in value:
                        custom_settings[key] = float(value)
                    # Try boolean
                    elif value.lower() in ['true', 'false']:
                        custom_settings[key] = value.lower() == 'true'
                    # Keep as string
                    else:
                        custom_settings[key] = value
                        
                except ValueError:
                    custom_settings[key] = value  # Keep as string if conversion fails
            
            if not Confirm.ask("Add another setting?", default=False):
                break
        
        return custom_settings
    
    def validate_source_config(self, source_name: str, config: SourceConfig) -> List[str]:
        """
        Validate source configuration.
        
        Args:
            source_name: Name of the source
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Validate priority range
            if not (1 <= config.priority <= 100):
                errors.append(f"Priority must be between 1 and 100, got {config.priority}")
            
            # Validate plugin configuration
            if config.config:
                # Check for required URL if base_url is specified
                if "base_url" in config.config:
                    base_url = config.config["base_url"]
                    if not isinstance(base_url, str) or not base_url.startswith(('http://', 'https://')):
                        errors.append("base_url must be a valid HTTP/HTTPS URL")
                
                # Check numeric values
                numeric_fields = ["rate_limit", "timeout", "max_retries"]
                for field in numeric_fields:
                    if field in config.config:
                        value = config.config[field]
                        if not isinstance(value, (int, float)) or value < 0:
                            errors.append(f"{field} must be a non-negative number")
            
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
        
        return errors
    
    def export_source_config(self, source_name: str, output_file: str) -> bool:
        """
        Export source configuration to file.
        
        Args:
            source_name: Name of the source
            output_file: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            from pathlib import Path
            
            source_config = self.config_manager.sources.get_source(source_name)
            
            if not source_config:
                display_warning(f"Source '{source_name}' not found.")
                return False
            
            # Export configuration
            config_data = {
                "source_name": source_name,
                "configuration": source_config.model_dump(),
                "exported_at": datetime.now().isoformat()
            }
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            display_info(
                f"Configuration for '{source_name}' exported to {output_path}",
                "📤 Export Complete"
            )
            
            return True
            
        except Exception as e:
            handle_error(e, f"Failed to export configuration for '{source_name}'")
            return False
    
    def import_source_config(self, source_name: str, input_file: str) -> bool:
        """
        Import source configuration from file.
        
        Args:
            source_name: Name of the source
            input_file: Input file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            from pathlib import Path
            
            input_path = Path(input_file)
            
            if not input_path.exists():
                display_warning(f"Configuration file not found: {input_path}")
                return False
            
            with open(input_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate imported data
            if "configuration" not in config_data:
                display_warning("Invalid configuration file format.")
                return False
            
            # Create source config
            source_config = SourceConfig.model_validate(config_data["configuration"])
            
            # Validate configuration
            errors = self.validate_source_config(source_name, source_config)
            if errors:
                display_warning(
                    f"Configuration validation failed:\n" + "\n".join(f"• {error}" for error in errors)
                )
                return False
            
            # Save configuration
            self.config_manager.sources.add_source(source_name, source_config)
            
            display_info(
                f"Configuration for '{source_name}' imported from {input_path}",
                "📥 Import Complete"
            )
            
            return True
            
        except Exception as e:
            handle_error(e, f"Failed to import configuration for '{source_name}'")
            return False


# Export source config manager
__all__ = ["SourceConfigManager"]