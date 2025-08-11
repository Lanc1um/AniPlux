"""
Configuration Schemas - Pydantic models for configuration validation.

This module defines the data structures and validation rules for
application settings and plugin configurations using Pydantic models.
"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DownloadSettings(BaseModel):
    """Download-related configuration settings."""
    
    download_directory: str = Field(
        default="./downloads",
        description="Directory where downloaded files are saved"
    )
    default_quality: Literal["480p", "720p", "1080p", "1440p", "2160p"] = Field(
        default="720p",
        description="Default video quality for downloads"
    )
    concurrent_downloads: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of concurrent downloads"
    )
    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Network timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts"
    )
    chunk_size: int = Field(
        default=8192,
        ge=1024,
        le=1048576,
        description="Download chunk size in bytes"
    )
    use_aria2c: bool = Field(
        default=True,
        description="Use aria2c for faster downloads when available"
    )
    aria2c_path: Optional[str] = Field(
        default=None,
        description="Path to aria2c executable (auto-detected if None)"
    )
    aria2c_connections: int = Field(
        default=16,
        ge=1,
        le=32,
        description="Number of connections per download for aria2c"
    )
    aria2c_split: int = Field(
        default=16,
        ge=1,
        le=32,
        description="Number of pieces to split downloads into for aria2c"
    )
    aria2c_min_split_size: str = Field(
        default="1M",
        description="Minimum size to split downloads (e.g., '1M', '5M')"
    )
    
    @field_validator('download_directory')
    @classmethod
    def validate_download_directory(cls, v: str) -> str:
        """Ensure download directory path is valid."""
        path = Path(v).expanduser().resolve()
        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)
        return str(path)


class UISettings(BaseModel):
    """User interface configuration settings."""
    
    show_banner: bool = Field(
        default=True,
        description="Whether to show ASCII banner on startup"
    )
    color_theme: Literal["default", "dark", "light", "colorful"] = Field(
        default="default",
        description="Color theme for the CLI interface"
    )
    progress_style: Literal["bar", "spinner", "dots"] = Field(
        default="bar",
        description="Style for progress indicators"
    )
    table_style: Literal["rounded", "simple", "grid", "minimal"] = Field(
        default="rounded",
        description="Style for data tables"
    )
    panel_style: Literal["rounded", "square", "heavy", "double"] = Field(
        default="rounded",
        description="Style for information panels"
    )
    animation_speed: Literal["slow", "normal", "fast"] = Field(
        default="normal",
        description="Speed of UI animations"
    )


class SearchSettings(BaseModel):
    """Search-related configuration settings."""
    
    max_results_per_source: int = Field(
        default=200,
        ge=1,
        le=200,
        description="Maximum results to fetch per source"
    )
    search_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Timeout for search operations in seconds"
    )
    enable_fuzzy_search: bool = Field(
        default=True,
        description="Enable fuzzy matching for search queries"
    )
    min_query_length: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Minimum search query length"
    )


class LoggingSettings(BaseModel):
    """Logging configuration settings."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    file: str = Field(
        default="aniplux.log",
        description="Log file name"
    )
    max_size: str = Field(
        default="10MB",
        description="Maximum log file size"
    )
    backup_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of backup log files to keep"
    )
    
    @field_validator('max_size')
    @classmethod
    def validate_max_size(cls, v: str) -> str:
        """Validate log file size format."""
        import re
        if not re.match(r'^\d+[KMGT]?B$', v.upper()):
            raise ValueError("Invalid size format. Use format like '10MB', '1GB'")
        return v.upper()


class AppSettings(BaseModel):
    """Main application settings container."""
    
    settings: DownloadSettings = Field(default_factory=DownloadSettings)
    ui: UISettings = Field(default_factory=UISettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    @model_validator(mode='after')
    def validate_settings_consistency(self) -> 'AppSettings':
        """Validate that settings are internally consistent."""
        # Ensure concurrent downloads doesn't exceed reasonable limits
        if self.settings.concurrent_downloads > 5 and self.settings.timeout < 30:
            # Increase timeout for high concurrency
            self.settings.timeout = max(30, self.settings.timeout)
        
        return self

class SourceConfig(BaseModel):
    """Configuration for an individual source plugin."""
    
    enabled: bool = Field(
        default=False,
        description="Whether the source is enabled"
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Source priority (lower numbers = higher priority)"
    )
    name: Optional[str] = Field(
        default=None,
        description="Display name for the source"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the source"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific configuration"
    )
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate source-specific configuration."""
        # Ensure common configuration keys have reasonable defaults
        if 'rate_limit' in v and not isinstance(v['rate_limit'], (int, float)):
            raise ValueError("rate_limit must be a number")
        
        if 'timeout' in v and (not isinstance(v['timeout'], int) or v['timeout'] < 1):
            raise ValueError("timeout must be a positive integer")
        
        return v


class GlobalSourceConfig(BaseModel):
    """Global configuration for source management."""
    
    enable_all_by_default: bool = Field(
        default=False,
        description="Whether to enable new sources by default"
    )
    auto_discover: bool = Field(
        default=True,
        description="Whether to automatically discover new plugins"
    )
    plugin_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Default timeout for plugin operations"
    )
    max_concurrent_plugins: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of plugins to query concurrently"
    )


class SourcesConfig(BaseModel):
    """Sources configuration container."""
    
    sources: Dict[str, SourceConfig] = Field(
        default_factory=dict,
        description="Individual source configurations"
    )
    global_config: GlobalSourceConfig = Field(
        default_factory=GlobalSourceConfig,
        description="Global source management settings"
    )
    
    @model_validator(mode='after')
    def validate_source_priorities(self) -> 'SourcesConfig':
        """Ensure source priorities are unique where possible."""
        priorities = {}
        for name, config in self.sources.items():
            if config.priority in priorities:
                # Log warning but don't fail validation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Duplicate priority {config.priority} for sources "
                    f"{name} and {priorities[config.priority]}"
                )
            priorities[config.priority] = name
        
        return self
    
    def get_enabled_sources(self) -> Dict[str, SourceConfig]:
        """Get all enabled sources sorted by priority."""
        enabled = {
            name: config for name, config in self.sources.items()
            if config.enabled
        }
        
        # Sort by priority (lower numbers first)
        return dict(sorted(
            enabled.items(),
            key=lambda item: item[1].priority
        ))
    
    def add_source(self, name: str, config: SourceConfig) -> None:
        """Add a new source configuration."""
        self.sources[name] = config
    
    def remove_source(self, name: str) -> bool:
        """Remove a source configuration. Returns True if removed."""
        return self.sources.pop(name, None) is not None
    
    def get_source(self, name: str) -> Optional[SourceConfig]:
        """Get configuration for a specific source."""
        return self.sources.get(name)


# Export all configuration models
__all__ = [
    "DownloadSettings",
    "UISettings", 
    "SearchSettings",
    "LoggingSettings",
    "AppSettings",
    "SourceConfig",
    "GlobalSourceConfig",
    "SourcesConfig",
]