"""
Animetsu Plugin Configuration

This module handles configuration validation and defaults for the Animetsu plugin.
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator

from aniplux.core.models import Quality


logger = logging.getLogger(__name__)


class AnimetsuConfig(BaseModel):
    """Configuration model for Animetsu plugin."""
    
    enabled: bool = Field(default=True, description="Enable/disable the plugin")
    priority: int = Field(default=2, description="Plugin priority (lower = higher priority)")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of request retries")
    rate_limit: float = Field(default=1.0, description="Minimum seconds between requests")
    
    # Base URL configuration - supports both animetsu.to and animetsu.cc
    base_url: str = Field(default="https://animetsu.to", description="Primary base URL for Animetsu")
    api_base_url: str = Field(default="https://backend.animetsu.to/api", description="API base URL")
    
    # Search configuration
    search_limit: int = Field(default=200, description="Maximum search results to return")
    
    # Quality preferences
    quality_preference: str = Field(default="1080p", description="Preferred video quality")
    
    # User agent
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        description="User agent string for requests"
    )
    
    # Download configuration
    use_aria2c: bool = Field(default=True, description="Use aria2c for downloads when available")
    use_yt_dlp: bool = Field(default=True, description="Use yt-dlp for downloads when available")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v < 1:
            raise ValueError("Priority must be at least 1")
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v < 5:
            raise ValueError("Timeout must be at least 5 seconds")
        return v
    
    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        if v < 0.1:
            raise ValueError("Rate limit must be at least 0.1 seconds")
        return v
    
    @validator('quality_preference')
    def validate_quality_preference(cls, v):
        valid_qualities = ["480p", "720p", "1080p"]
        if v not in valid_qualities:
            logger.warning(f"Invalid quality preference '{v}', using '1080p'")
            return "1080p"
        return v


def get_default_config() -> Dict[str, Any]:
    """Get default configuration for Animetsu plugin."""
    return {
        "enabled": True,
        "priority": 2,
        "timeout": 30,
        "max_retries": 3,
        "rate_limit": 1.0,
        "base_url": "https://animetsu.to",
        "api_base_url": "https://backend.animetsu.to/api",
        "search_limit": 200,
        "quality_preference": "1080p",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "use_aria2c": True,
        "use_yt_dlp": True
    }


def validate_config(config: Dict[str, Any]) -> AnimetsuConfig:
    """
    Validate and create AnimetsuConfig from dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Validated AnimetsuConfig instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        return AnimetsuConfig(**config)
    except Exception as e:
        logger.error(f"Invalid Animetsu configuration: {e}")
        raise ValueError(f"Invalid Animetsu configuration: {e}")


def merge_with_defaults(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Merge provided config with defaults.
    
    Args:
        config: User configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    default_config = get_default_config()
    
    if config:
        # Deep merge configuration
        merged = default_config.copy()
        merged.update(config)
        return merged
    
    return default_config


# Quality mapping for Animetsu
QUALITY_MAP = {
    "480p": Quality.LOW,
    "720p": Quality.MEDIUM, 
    "1080p": Quality.HIGH
}


def get_quality_from_string(quality_str: str) -> Quality:
    """
    Convert quality string to Quality enum.
    
    Args:
        quality_str: Quality string (e.g., "1080p")
        
    Returns:
        Quality enum value
    """
    return QUALITY_MAP.get(quality_str, Quality.HIGH)


def get_string_from_quality(quality: Quality) -> str:
    """
    Convert Quality enum to string.
    
    Args:
        quality: Quality enum value
        
    Returns:
        Quality string (e.g., "1080p")
    """
    reverse_map = {v: k for k, v in QUALITY_MAP.items()}
    return reverse_map.get(quality, "1080p")