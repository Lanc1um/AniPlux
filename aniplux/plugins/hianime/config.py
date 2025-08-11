"""
HiAnime Configuration - Plugin-specific configuration management.

This module handles configuration validation and management
specific to the HiAnime plugin.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field, validator

from aniplux.core.models import Quality


class HiAnimeConfig(BaseModel):
    """Configuration model for HiAnime plugin."""
    
    enabled: bool = Field(True, description="Whether the plugin is enabled")
    priority: int = Field(1, ge=1, le=10, description="Plugin priority (1-10)")
    timeout: int = Field(30, ge=5, le=120, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for requests"
    )
    search_limit: int = Field(50, ge=1, le=200, description="Maximum search results to return")
    quality_preference: str = Field("high", description="Preferred video quality")
    
    # Advanced settings
    rate_limit: float = Field(1.5, ge=0.1, le=10.0, description="Minimum seconds between requests")
    concurrent_requests: int = Field(3, ge=1, le=10, description="Maximum concurrent requests")
    cache_duration: int = Field(300, ge=0, le=3600, description="Cache duration in seconds")
    
    # Feature flags
    enable_ajax_extraction: bool = Field(True, description="Enable AJAX video source extraction")
    enable_iframe_extraction: bool = Field(True, description="Enable iframe video source extraction")
    enable_script_extraction: bool = Field(True, description="Enable script-based video source extraction")
    
    @validator('quality_preference')
    def validate_quality_preference(cls, v):
        """Validate quality preference value."""
        valid_qualities = ['low', 'medium', 'high', 'ultra', '4k']
        if v.lower() not in valid_qualities:
            raise ValueError(f"Quality preference must be one of: {', '.join(valid_qualities)}")
        return v.lower()
    
    @validator('user_agent')
    def validate_user_agent(cls, v):
        """Validate user agent string."""
        if not v or len(v.strip()) < 10:
            raise ValueError("User agent must be a valid browser string")
        return v.strip()
    
    def get_quality_enum(self) -> Quality:
        """Convert quality preference to Quality enum."""
        quality_map = {
            'low': Quality.LOW,
            'medium': Quality.MEDIUM,
            'high': Quality.HIGH,
            'ultra': Quality.ULTRA,
            '4k': Quality.FOUR_K
        }
        return quality_map.get(self.quality_preference, Quality.HIGH)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HiAnimeConfig':
        """Create configuration from dictionary."""
        return cls(**data)


def get_default_config() -> Dict[str, Any]:
    """Get default configuration for HiAnime plugin."""
    return HiAnimeConfig(
        enabled=True,
        priority=1,
        timeout=30,
        max_retries=3,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        search_limit=50,
        quality_preference="high",
        rate_limit=1.5,
        concurrent_requests=3,
        cache_duration=300,
        enable_ajax_extraction=True,
        enable_iframe_extraction=True,
        enable_script_extraction=True
    ).to_dict()


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize plugin configuration.
    
    Args:
        config: Raw configuration dictionary
        
    Returns:
        Validated and normalized configuration
        
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        validated_config = HiAnimeConfig.from_dict(config)
        return validated_config.to_dict()
    except Exception as e:
        raise ValueError(f"Invalid HiAnime plugin configuration: {e}")


# Export configuration utilities
__all__ = ["HiAnimeConfig", "get_default_config", "validate_config"]