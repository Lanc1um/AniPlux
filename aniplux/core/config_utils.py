"""
Configuration Utilities - Helper functions for configuration management.

This module provides utility functions for working with configuration data,
including validation helpers, migration utilities, and configuration analysis.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aniplux.core.config_defaults import get_default_settings, get_default_sources
from aniplux.core.config_schemas import AppSettings, SourcesConfig
from aniplux.core.exceptions import ConfigurationError


logger = logging.getLogger(__name__)


def migrate_config_format(config_data: Dict[str, Any], config_type: str) -> Dict[str, Any]:
    """
    Migrate configuration data from older formats to current schema.
    
    Args:
        config_data: Raw configuration data
        config_type: Type of configuration ('settings' or 'sources')
        
    Returns:
        Migrated configuration data
        
    Raises:
        ConfigurationError: If migration fails
    """
    try:
        if config_type == "settings":
            # Handle legacy format migrations
            if "download_settings" in config_data:
                # Migrate from v0.0.x format
                legacy_data = config_data.copy()
                config_data = {
                    "settings": legacy_data.pop("download_settings", {}),
                    "ui": legacy_data.pop("ui_settings", {}),
                    "search": legacy_data.pop("search_settings", {}),
                    "logging": legacy_data.pop("logging_settings", {})
                }
            
            # Ensure all required sections exist
            defaults = get_default_settings().model_dump()
            for section in defaults:
                if section not in config_data:
                    config_data[section] = defaults[section]
                else:
                    # Merge with defaults to add missing keys
                    for key, value in defaults[section].items():
                        if key not in config_data[section]:
                            config_data[section][key] = value
        
        elif config_type == "sources":
            # Handle legacy sources format
            if "plugins" in config_data:
                # Migrate from plugin-based format
                config_data["sources"] = config_data.pop("plugins", {})
            
            # Ensure global_config exists
            if "global_config" not in config_data:
                config_data["global_config"] = get_default_sources().global_config.model_dump()
        
        return config_data
        
    except Exception as e:
        raise ConfigurationError(f"Failed to migrate {config_type} configuration: {e}")


def compare_configs(config1: Dict[str, Any], config2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two configuration dictionaries and return differences.
    
    Args:
        config1: First configuration
        config2: Second configuration
        
    Returns:
        Dictionary containing differences and analysis
    """
    def _deep_diff(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
        """Recursively find differences between dictionaries."""
        differences = []
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            
            if key not in dict1:
                differences.append({
                    "type": "added",
                    "path": current_path,
                    "value": dict2[key]
                })
            elif key not in dict2:
                differences.append({
                    "type": "removed", 
                    "path": current_path,
                    "value": dict1[key]
                })
            elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                differences.extend(_deep_diff(dict1[key], dict2[key], current_path))
            elif dict1[key] != dict2[key]:
                differences.append({
                    "type": "changed",
                    "path": current_path,
                    "old_value": dict1[key],
                    "new_value": dict2[key]
                })
        
        return differences
    
    differences = _deep_diff(config1, config2)
    
    return {
        "identical": len(differences) == 0,
        "differences": differences,
        "summary": {
            "added": len([d for d in differences if d["type"] == "added"]),
            "removed": len([d for d in differences if d["type"] == "removed"]),
            "changed": len([d for d in differences if d["type"] == "changed"])
        }
    }


def backup_config_file(file_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """
    Create a backup of a configuration file.
    
    Args:
        file_path: Path to the configuration file
        backup_dir: Directory to store backup (defaults to same directory)
        
    Returns:
        Path to the backup file
        
    Raises:
        ConfigurationError: If backup creation fails
    """
    if not file_path.exists():
        raise ConfigurationError(f"Configuration file does not exist: {file_path}")
    
    if backup_dir is None:
        backup_dir = file_path.parent
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}.backup{file_path.suffix}"
    backup_path = backup_dir / backup_name
    
    try:
        import shutil
        shutil.copy2(file_path, backup_path)
        logger.info(f"Configuration backed up to {backup_path}")
        return backup_path
    except Exception as e:
        raise ConfigurationError(f"Failed to create backup: {e}")


def restore_config_from_backup(backup_path: Path, target_path: Path) -> None:
    """
    Restore configuration from a backup file.
    
    Args:
        backup_path: Path to the backup file
        target_path: Path where to restore the configuration
        
    Raises:
        ConfigurationError: If restoration fails
    """
    if not backup_path.exists():
        raise ConfigurationError(f"Backup file does not exist: {backup_path}")
    
    try:
        import shutil
        shutil.copy2(backup_path, target_path)
        logger.info(f"Configuration restored from {backup_path} to {target_path}")
    except Exception as e:
        raise ConfigurationError(f"Failed to restore from backup: {e}")


def find_config_issues(config_manager) -> List[Dict[str, Any]]:
    """
    Analyze configuration for common issues and inconsistencies.
    
    Args:
        config_manager: ConfigManager instance
        
    Returns:
        List of issues found with severity levels
    """
    issues = []
    
    try:
        settings = config_manager.settings
        sources = config_manager.sources
        
        # Check download directory
        download_dir = Path(settings.settings.download_directory)
        if not download_dir.exists():
            issues.append({
                "severity": "warning",
                "category": "filesystem",
                "message": f"Download directory does not exist: {download_dir}",
                "suggestion": "Create the directory or update the path in settings"
            })
        elif not download_dir.is_dir():
            issues.append({
                "severity": "error",
                "category": "filesystem", 
                "message": f"Download path is not a directory: {download_dir}",
                "suggestion": "Update download_directory to point to a valid directory"
            })
        
        # Check for write permissions
        try:
            test_file = download_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError):
            issues.append({
                "severity": "error",
                "category": "permissions",
                "message": f"No write permission for download directory: {download_dir}",
                "suggestion": "Check directory permissions or choose a different location"
            })
        
        # Check enabled sources
        enabled_sources = sources.get_enabled_sources()
        if not enabled_sources:
            issues.append({
                "severity": "warning",
                "category": "sources",
                "message": "No sources are enabled",
                "suggestion": "Enable at least one source plugin to search for anime"
            })
        
        # Check for conflicting settings
        if settings.settings.concurrent_downloads > 10:
            issues.append({
                "severity": "warning",
                "category": "performance",
                "message": f"High concurrent downloads setting: {settings.settings.concurrent_downloads}",
                "suggestion": "Consider reducing concurrent downloads to avoid overwhelming sources"
            })
        
        if settings.settings.timeout < 10:
            issues.append({
                "severity": "warning",
                "category": "network",
                "message": f"Low timeout setting: {settings.settings.timeout}s",
                "suggestion": "Consider increasing timeout for better reliability"
            })
        
        # Check log file location
        log_file = Path(settings.logging.file)
        if log_file.is_absolute() and not log_file.parent.exists():
            issues.append({
                "severity": "warning",
                "category": "logging",
                "message": f"Log file directory does not exist: {log_file.parent}",
                "suggestion": "Create the directory or use a relative path"
            })
        
    except Exception as e:
        issues.append({
            "severity": "error",
            "category": "validation",
            "message": f"Failed to analyze configuration: {e}",
            "suggestion": "Check configuration file format and content"
        })
    
    return issues


def optimize_config_for_system(config_manager) -> List[str]:
    """
    Suggest configuration optimizations based on system capabilities.
    
    Args:
        config_manager: ConfigManager instance
        
    Returns:
        List of optimization suggestions
    """
    suggestions = []
    
    try:
        import psutil
        import os
        
        # Check available memory
        memory = psutil.virtual_memory()
        if memory.available < 1024 * 1024 * 1024:  # Less than 1GB
            suggestions.append(
                "Consider reducing concurrent_downloads due to low available memory"
            )
        
        # Check CPU cores
        cpu_count = os.cpu_count() or 1
        current_concurrent = config_manager.settings.settings.concurrent_downloads
        
        if current_concurrent > cpu_count * 2:
            suggestions.append(
                f"Consider reducing concurrent_downloads to {cpu_count * 2} "
                f"(2x CPU cores) for better performance"
            )
        
        # Check disk space
        download_dir = Path(config_manager.settings.settings.download_directory)
        if download_dir.exists():
            disk_usage = psutil.disk_usage(str(download_dir))
            free_gb = disk_usage.free / (1024**3)
            
            if free_gb < 5:
                suggestions.append(
                    f"Low disk space in download directory: {free_gb:.1f}GB free"
                )
        
    except ImportError:
        suggestions.append("Install psutil for system-specific optimizations")
    except Exception as e:
        logger.debug(f"Failed to analyze system for optimizations: {e}")
    
    return suggestions


# Export utility functions
__all__ = [
    "migrate_config_format",
    "compare_configs",
    "backup_config_file",
    "restore_config_from_backup", 
    "find_config_issues",
    "optimize_config_for_system",
]