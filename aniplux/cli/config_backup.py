"""
Configuration Backup Manager - Backup and restore functionality for configurations.

This module provides comprehensive backup and restore capabilities for
configuration files with versioning, validation, and recovery options.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aniplux.core import ConfigManager
from aniplux.core.config_utils import backup_config_file, restore_config_from_backup
from aniplux.core.exceptions import ConfigurationError
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    handle_error,
)


logger = logging.getLogger(__name__)


class ConfigurationBackupManager:
    """
    Manages configuration backups with versioning and recovery options.
    
    Provides automatic and manual backup creation, listing, and restoration
    with validation and rollback capabilities.
    """
    
    def __init__(self, config_manager: ConfigManager, backup_dir: Optional[Path] = None):
        """
        Initialize backup manager.
        
        Args:
            config_manager: Configuration manager instance
            backup_dir: Directory for storing backups (defaults to config/.backups)
        """
        self.config_manager = config_manager
        self.backup_dir = backup_dir or (config_manager.config_dir / ".backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.console = get_console()
        self.ui = UIComponents()
    
    def create_backup(self, description: Optional[str] = None) -> Path:
        """
        Create a backup of current configuration.
        
        Args:
            description: Optional description for the backup
            
        Returns:
            Path to the created backup file
            
        Raises:
            ConfigurationError: If backup creation fails
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"config_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_name
            
            # Create backup data
            backup_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "description": description or "Manual backup",
                    "version": "1.0",
                    "created_by": "aniplux_cli"
                },
                "settings": self.config_manager.settings.model_dump(),
                "sources": self.config_manager.sources.model_dump()
            }
            
            # Write backup file
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create backup: {e}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available configuration backups.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("config_backup_*.json"):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                    
                    metadata = backup_data.get("metadata", {})
                    
                    backups.append({
                        "file": backup_file,
                        "name": backup_file.name,
                        "timestamp": metadata.get("timestamp", "Unknown"),
                        "description": metadata.get("description", "No description"),
                        "size": backup_file.stat().st_size,
                        "valid": self._validate_backup(backup_data)
                    })
                    
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Invalid backup file {backup_file}: {e}")
                    backups.append({
                        "file": backup_file,
                        "name": backup_file.name,
                        "timestamp": "Invalid",
                        "description": f"Corrupted backup: {e}",
                        "size": backup_file.stat().st_size if backup_file.exists() else 0,
                        "valid": False
                    })
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x["timestamp"] if x["timestamp"] != "Invalid" else "", reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    def restore_backup(self, backup_path: Path, create_backup_before: bool = True) -> bool:
        """
        Restore configuration from a backup file.
        
        Args:
            backup_path: Path to the backup file
            create_backup_before: Whether to create a backup before restoring
            
        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            if not backup_path.exists():
                display_warning(f"Backup file not found: {backup_path}", "❌ File Not Found")
                return False
            
            # Load and validate backup
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            if not self._validate_backup(backup_data):
                display_warning("Backup file is invalid or corrupted", "❌ Invalid Backup")
                return False
            
            # Create backup of current configuration if requested
            if create_backup_before:
                current_backup = self.create_backup("Pre-restore backup")
                display_info(f"Current configuration backed up to: {current_backup.name}")
            
            # Restore settings
            from aniplux.core.config_schemas import AppSettings, SourcesConfig
            
            settings = AppSettings.model_validate(backup_data["settings"])
            sources = SourcesConfig.model_validate(backup_data["sources"])
            
            # Update configuration manager
            self.config_manager._settings = settings
            self.config_manager._sources = sources
            
            # Save to files
            self.config_manager._save_settings(settings)
            self.config_manager._save_sources(sources)
            
            metadata = backup_data.get("metadata", {})
            display_info(
                f"Configuration restored successfully!\n\n"
                f"Backup: {backup_path.name}\n"
                f"Created: {metadata.get('timestamp', 'Unknown')}\n"
                f"Description: {metadata.get('description', 'No description')}",
                "✅ Restore Complete"
            )
            
            return True
            
        except Exception as e:
            handle_error(e, f"Failed to restore backup from '{backup_path}'")
            return False
    
    def delete_backup(self, backup_path: Path) -> bool:
        """
        Delete a backup file.
        
        Args:
            backup_path: Path to the backup file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            if not backup_path.exists():
                display_warning(f"Backup file not found: {backup_path}", "❌ File Not Found")
                return False
            
            backup_path.unlink()
            display_info(f"Backup deleted: {backup_path.name}", "🗑️  Backup Deleted")
            return True
            
        except Exception as e:
            handle_error(e, f"Failed to delete backup '{backup_path}'")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backup files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Number of backups deleted
        """
        try:
            backups = self.list_backups()
            valid_backups = [b for b in backups if b["valid"]]
            
            if len(valid_backups) <= keep_count:
                return 0
            
            # Delete oldest backups
            to_delete = valid_backups[keep_count:]
            deleted_count = 0
            
            for backup in to_delete:
                try:
                    backup["file"].unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete backup {backup['name']}: {e}")
            
            if deleted_count > 0:
                display_info(
                    f"Cleaned up {deleted_count} old backup(s), keeping {keep_count} most recent",
                    "🧹 Cleanup Complete"
                )
            
            return deleted_count
            
        except Exception as e:
            handle_error(e, "Failed to cleanup old backups")
            return 0
    
    def display_backups(self) -> None:
        """Display list of available backups in a formatted table."""
        backups = self.list_backups()
        
        if not backups:
            display_info("No configuration backups found.", "📁 No Backups")
            return
        
        # Create backups table
        from rich.table import Table
        
        table = Table(
            title="📁 Configuration Backups",
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Name", style="cyan", width=25)
        table.add_column("Created", style="white", width=20)
        table.add_column("Description", style="dim", width=30)
        table.add_column("Size", style="green", width=10)
        table.add_column("Status", style="white", width=10)
        
        for backup in backups:
            # Format timestamp
            try:
                if backup["timestamp"] != "Invalid":
                    timestamp = datetime.fromisoformat(backup["timestamp"])
                    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
                else:
                    formatted_time = "Invalid"
            except:
                formatted_time = "Unknown"
            
            # Format size
            size_bytes = backup["size"]
            if size_bytes < 1024:
                size_str = f"{size_bytes}B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f}KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f}MB"
            
            # Status indicator
            status = "✅ Valid" if backup["valid"] else "❌ Invalid"
            
            table.add_row(
                backup["name"],
                formatted_time,
                backup["description"][:30] + "..." if len(backup["description"]) > 30 else backup["description"],
                size_str,
                status
            )
        
        self.console.print(table)
        
        # Show summary
        valid_count = sum(1 for b in backups if b["valid"])
        invalid_count = len(backups) - valid_count
        
        summary_text = f"Total: {len(backups)} backups"
        if invalid_count > 0:
            summary_text += f" ({valid_count} valid, {invalid_count} invalid)"
        
        self.console.print(f"\n[dim]{summary_text}[/dim]")
    
    def _validate_backup(self, backup_data: Dict) -> bool:
        """
        Validate backup data structure and content.
        
        Args:
            backup_data: Backup data dictionary
            
        Returns:
            True if backup is valid, False otherwise
        """
        try:
            # Check required sections
            required_sections = ["metadata", "settings", "sources"]
            for section in required_sections:
                if section not in backup_data:
                    return False
            
            # Validate settings and sources schemas
            from aniplux.core.config_schemas import AppSettings, SourcesConfig
            
            AppSettings.model_validate(backup_data["settings"])
            SourcesConfig.model_validate(backup_data["sources"])
            
            return True
            
        except Exception as e:
            logger.debug(f"Backup validation failed: {e}")
            return False


# Export backup manager
__all__ = ["ConfigurationBackupManager"]