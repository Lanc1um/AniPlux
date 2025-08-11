"""
Configuration Defaults - Default configuration templates and utilities.

This module provides default configuration templates and utilities
for creating and managing configuration files with sensible defaults.
"""

from pathlib import Path
from typing import Dict, Any

from aniplux.core.config_schemas import AppSettings, SourcesConfig, SourceConfig


def get_default_settings() -> AppSettings:
    """
    Get default application settings.
    
    Returns:
        AppSettings instance with sensible defaults
    """
    return AppSettings()


def get_default_sources() -> SourcesConfig:
    """
    Get default sources configuration with sample plugin.
    
    Returns:
        SourcesConfig instance with sample configuration
    """
    sources_config = SourcesConfig()
    
    # Add sample source for development/testing
    sample_source = SourceConfig(
        enabled=False,  # Disabled by default
        priority=99,    # Low priority
        name="Sample Source",
        description="Sample plugin for testing and development",
        config={
            "base_url": "https://example.com",
            "rate_limit": 1.0,
            "user_agent": "AniPlux/0.1.0",
            "timeout": 30
        }
    )
    
    sources_config.add_source("sample", sample_source)
    return sources_config


def create_default_config_files(config_dir: Path) -> None:
    """
    Create default configuration files in the specified directory.
    
    Args:
        config_dir: Directory to create configuration files in
    """
    import json
    
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create settings.json
    settings_file = config_dir / "settings.json"
    if not settings_file.exists():
        settings = get_default_settings()
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings.model_dump(), f, indent=2, ensure_ascii=False)
    
    # Create sources.json
    sources_file = config_dir / "sources.json"
    if not sources_file.exists():
        sources = get_default_sources()
        with open(sources_file, 'w', encoding='utf-8') as f:
            json.dump(sources.model_dump(), f, indent=2, ensure_ascii=False)


def get_config_template(config_type: str) -> Dict[str, Any]:
    """
    Get a configuration template for documentation or initialization.
    
    Args:
        config_type: Type of configuration ('settings' or 'sources')
        
    Returns:
        Dictionary containing the configuration template
        
    Raises:
        ValueError: If config_type is not recognized
    """
    if config_type == "settings":
        return get_default_settings().model_dump()
    elif config_type == "sources":
        return get_default_sources().model_dump()
    else:
        raise ValueError(f"Unknown config type: {config_type}")


def validate_config_directory(config_dir: Path) -> Dict[str, Any]:
    """
    Validate a configuration directory and return status report.
    
    Args:
        config_dir: Path to configuration directory
        
    Returns:
        Dictionary containing validation results
    """
    report = {
        "valid": True,
        "exists": config_dir.exists(),
        "writable": False,
        "files": {
            "settings.json": {"exists": False, "valid": False},
            "sources.json": {"exists": False, "valid": False}
        },
        "issues": []
    }
    
    if not report["exists"]:
        report["issues"].append(f"Configuration directory does not exist: {config_dir}")
        return report
    
    # Check if directory is writable
    try:
        test_file = config_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        report["writable"] = True
    except (PermissionError, OSError):
        report["valid"] = False
        report["issues"].append("Configuration directory is not writable")
    
    # Check configuration files
    for filename in ["settings.json", "sources.json"]:
        file_path = config_dir / filename
        file_info = report["files"][filename]
        
        file_info["exists"] = file_path.exists()
        
        if file_info["exists"]:
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate against schema
                if filename == "settings.json":
                    AppSettings.model_validate(data)
                else:  # sources.json
                    SourcesConfig.model_validate(data)
                
                file_info["valid"] = True
            except Exception as e:
                report["valid"] = False
                file_info["valid"] = False
                report["issues"].append(f"Invalid {filename}: {e}")
    
    return report


# Export utility functions
__all__ = [
    "get_default_settings",
    "get_default_sources",
    "create_default_config_files",
    "get_config_template",
    "validate_config_directory",
]