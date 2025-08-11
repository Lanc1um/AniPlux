"""
Configuration Manager - JSON-based settings and plugin configuration management.

This module provides centralized configuration management for AniPlux,
handling user preferences, plugin settings, and application state with
validation, hot-reload capabilities, and default value management.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from threading import Lock

from pydantic import BaseModel, Field, ValidationError

from aniplux.core.config_schemas import AppSettings, SourcesConfig, SourceConfig
from aniplux.core.exceptions import ConfigurationError


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration with JSON persistence and validation.
    
    Provides thread-safe access to configuration data with automatic
    validation, default value management, and hot-reload capabilities.
    """
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files.
                       Defaults to './config' if not specified.
        """
        self.config_dir = Path(config_dir or "config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._settings_file = self.config_dir / "settings.json"
        self._sources_file = self.config_dir / "sources.json"
        
        # Thread-safe access to configuration data
        self._lock = Lock()
        self._settings: Optional[AppSettings] = None
        self._sources: Optional[SourcesConfig] = None
        
        # Load initial configuration
        self._load_configurations()
    
    def _load_configurations(self) -> None:
        """Load all configuration files with error handling."""
        try:
            self._settings = self._load_settings()
            self._sources = self._load_sources()
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def _load_settings(self) -> AppSettings:
        """Load and validate application settings."""
        if not self._settings_file.exists():
            logger.info("Settings file not found, creating default configuration")
            settings = AppSettings()
            self._save_settings(settings)
            return settings
        
        try:
            with open(self._settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppSettings.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Invalid settings file, using defaults: {e}")
            # Backup corrupted file
            backup_path = self._settings_file.with_suffix('.json.backup')
            self._settings_file.rename(backup_path)
            logger.info(f"Corrupted settings backed up to {backup_path}")
            
            # Create new default settings
            settings = AppSettings()
            self._save_settings(settings)
            return settings
    
    def _load_sources(self) -> SourcesConfig:
        """Load and validate sources configuration."""
        if not self._sources_file.exists():
            logger.info("Sources file not found, creating default configuration")
            sources = SourcesConfig()
            self._save_sources(sources)
            return sources
        
        try:
            with open(self._sources_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SourcesConfig.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Invalid sources file, using defaults: {e}")
            # Backup corrupted file
            backup_path = self._sources_file.with_suffix('.json.backup')
            self._sources_file.rename(backup_path)
            logger.info(f"Corrupted sources backed up to {backup_path}")
            
            # Create new default sources
            sources = SourcesConfig()
            self._save_sources(sources)
            return sources
    
    def _save_settings(self, settings: AppSettings) -> None:
        """Save settings to file with atomic write."""
        temp_file = self._settings_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(settings.model_dump() if settings else {}, f, indent=2, ensure_ascii=False)
            temp_file.replace(self._settings_file)
            logger.debug("Settings saved successfully")
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise ConfigurationError(f"Failed to save settings: {e}")
    
    def _save_sources(self, sources: SourcesConfig) -> None:
        """Save sources configuration to file with atomic write."""
        temp_file = self._sources_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(sources.model_dump() if sources else {}, f, indent=2, ensure_ascii=False)
            temp_file.replace(self._sources_file)
            logger.debug("Sources configuration saved successfully")
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise ConfigurationError(f"Failed to save sources: {e}")
    
    @property
    def settings(self) -> AppSettings:
        """Get current application settings (thread-safe)."""
        with self._lock:
            if self._settings is None:
                self._settings = self._load_settings()
            return self._settings
    
    @property
    def sources(self) -> SourcesConfig:
        """Get current sources configuration (thread-safe)."""
        with self._lock:
            if self._sources is None:
                self._sources = self._load_sources()
            return self._sources    

    def update_setting(self, key_path: str, value: Any) -> None:
        """
        Update a specific setting using dot notation.
        
        Args:
            key_path: Dot-separated path to the setting (e.g., 'ui.color_theme')
            value: New value for the setting
            
        Raises:
            ConfigurationError: If key path is invalid or value is invalid
        """
        with self._lock:
            if self._settings is None:
                raise ConfigurationError("Settings not loaded")
                
            settings_dict = self._settings.model_dump()
            
            # Navigate to the setting location
            keys = key_path.split('.')
            current = settings_dict
            
            for key in keys[:-1]:
                if key not in current:
                    raise ConfigurationError(f"Invalid setting path: {key_path}")
                current = current[key]
            
            final_key = keys[-1]
            if final_key not in current:
                raise ConfigurationError(f"Invalid setting key: {final_key}")
            
            # Update the value
            current[final_key] = value
            
            try:
                # Validate the updated configuration
                updated_settings = AppSettings.model_validate(settings_dict)
                self._settings = updated_settings
                self._save_settings(updated_settings)
                logger.info(f"Setting updated: {key_path} = {value}")
            except ValidationError as e:
                raise ConfigurationError(f"Invalid setting value: {e}")
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """
        Get a specific setting using dot notation.
        
        Args:
            key_path: Dot-separated path to the setting
            default: Default value if setting not found
            
        Returns:
            The setting value or default
        """
        with self._lock:
            if self._settings is None:
                return default
                
            settings_dict = self._settings.model_dump()
            
            keys = key_path.split('.')
            current = settings_dict
            
            try:
                for key in keys:
                    current = current[key]
                return current
            except (KeyError, TypeError):
                return default
    
    def update_source_config(self, source_name: str, config: Dict[str, Any]) -> None:
        """
        Update configuration for a specific source.
        
        Args:
            source_name: Name of the source plugin
            config: New configuration dictionary
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        with self._lock:
            if self._sources is None:
                raise ConfigurationError("Sources configuration not loaded")
                
            sources_dict = self._sources.model_dump()
            
            if source_name not in sources_dict['sources']:
                sources_dict['sources'][source_name] = {}
            
            sources_dict['sources'][source_name].update(config)
            
            try:
                updated_sources = SourcesConfig.model_validate(sources_dict)
                self._sources = updated_sources
                self._save_sources(updated_sources)
                logger.info(f"Source configuration updated: {source_name}")
            except ValidationError as e:
                raise ConfigurationError(f"Invalid source configuration: {e}")
    
    def enable_source(self, source_name: str) -> None:
        """Enable a source plugin."""
        self.update_source_config(source_name, {"enabled": True})
    
    def disable_source(self, source_name: str) -> None:
        """Disable a source plugin."""
        self.update_source_config(source_name, {"enabled": False})
    
    def get_enabled_sources(self) -> Dict[str, SourceConfig]:
        """Get all enabled source configurations."""
        with self._lock:
            if self._sources is None:
                return {}
            return {
                name: config for name, config in self._sources.sources.items()
                if config.enabled
            }
    
    def reload_configuration(self) -> None:
        """Reload configuration from files (hot-reload)."""
        with self._lock:
            logger.info("Reloading configuration from files")
            self._settings = None
            self._sources = None
            self._load_configurations()
    
    def reset_to_defaults(self) -> None:
        """Reset all configuration to default values."""
        with self._lock:
            logger.warning("Resetting configuration to defaults")
            self._settings = AppSettings()
            self._sources = SourcesConfig()
            self._save_settings(self._settings)
            self._save_sources(self._sources)
    
    def export_config(self, output_path: Path) -> None:
        """
        Export current configuration to a file.
        
        Args:
            output_path: Path to export the configuration
        """
        with self._lock:
            config_data = {
                "settings": self._settings.model_dump() if self._settings else {},
                "sources": self._sources.model_dump() if self._sources else {},
                "export_timestamp": json.dumps(
                    {"timestamp": "now"}, 
                    default=str
                )
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration exported to {output_path}")
    
    def import_config(self, import_path: Path) -> None:
        """
        Import configuration from a file.
        
        Args:
            import_path: Path to import the configuration from
            
        Raises:
            ConfigurationError: If import file is invalid
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate imported data
            settings = AppSettings.model_validate(config_data.get('settings', {}))
            sources = SourcesConfig.model_validate(config_data.get('sources', {}))
            
            with self._lock:
                self._settings = settings
                self._sources = sources
                self._save_settings(settings)
                self._save_sources(sources)
            
            logger.info(f"Configuration imported from {import_path}")
            
        except (json.JSONDecodeError, ValidationError, FileNotFoundError) as e:
            raise ConfigurationError(f"Failed to import configuration: {e}")
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate current configuration and return validation report.
        
        Returns:
            Dictionary containing validation results and any issues found
        """
        report = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        try:
            # Validate settings
            if self._settings:
                AppSettings.model_validate(self._settings.model_dump())
            else:
                report["issues"].append("Settings not loaded")
                report["valid"] = False
        except ValidationError as e:
            report["valid"] = False
            report["issues"].append(f"Settings validation failed: {e}")
        
        try:
            # Validate sources
            if self._sources:
                SourcesConfig.model_validate(self._sources.model_dump())
            else:
                report["issues"].append("Sources configuration not loaded")
                report["valid"] = False
        except ValidationError as e:
            report["valid"] = False
            report["issues"].append(f"Sources validation failed: {e}")
        
        # Check for common configuration issues
        if not self.get_enabled_sources():
            report["warnings"].append("No sources are enabled")
        
        download_dir = Path(self.settings.settings.download_directory)
        if not download_dir.parent.exists():
            report["warnings"].append(f"Download directory parent does not exist: {download_dir.parent}")
        
        return report