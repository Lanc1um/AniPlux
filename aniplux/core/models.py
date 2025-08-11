"""
Core Data Models - Pydantic models for type safety and validation.

This module defines the core data structures used throughout AniPlux,
including anime results, episodes, download tasks, and quality options.
All models use Pydantic for validation, serialization, and type safety.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class Quality(str, Enum):
    """Video quality options for anime episodes."""
    
    LOW = "480p"
    MEDIUM = "720p" 
    HIGH = "1080p"
    ULTRA = "1440p"
    FOUR_K = "2160p"
    
    @classmethod
    def from_resolution(cls, width: int, height: int) -> "Quality":
        """Convert resolution dimensions to Quality enum."""
        if height <= 480:
            return cls.LOW
        elif height <= 720:
            return cls.MEDIUM
        elif height <= 1080:
            return cls.HIGH
        elif height <= 1440:
            return cls.ULTRA
        else:
            return cls.FOUR_K
    
    @property
    def height(self) -> int:
        """Get the height in pixels for this quality."""
        return int(self.value.replace('p', ''))
    
    def __str__(self) -> str:
        return self.value


class DownloadStatus(str, Enum):
    """Status options for download tasks."""
    
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnimeResult(BaseModel):
    """
    Represents an anime search result from a plugin source.
    
    Contains basic information about an anime series including
    metadata, source information, and optional thumbnail.
    """
    
    title: str = Field(..., min_length=1, description="Anime title")
    url: HttpUrl = Field(..., description="URL to the anime page")
    source: str = Field(..., min_length=1, description="Source plugin name")
    episode_count: Optional[int] = Field(None, ge=1, description="Total episodes")
    description: Optional[str] = Field(None, description="Anime description")
    thumbnail: Optional[HttpUrl] = Field(None, description="Thumbnail image URL")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="Release year")
    genres: List[str] = Field(default_factory=list, description="Genre tags")
    rating: Optional[float] = Field(None, ge=0.0, le=10.0, description="User rating")
    status: Optional[str] = Field(None, description="Airing status")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is properly formatted."""
        return v.strip()
    
    @field_validator('genres')
    @classmethod
    def validate_genres(cls, v: List[str]) -> List[str]:
        """Clean and validate genre list."""
        return [genre.strip().title() for genre in v if genre.strip()]
    
    def __str__(self) -> str:
        return f"{self.title} ({self.source})"
    
    def __repr__(self) -> str:
        return f"AnimeResult(title='{self.title}', source='{self.source}')"


class Episode(BaseModel):
    """
    Represents an individual anime episode with download options.
    
    Contains episode metadata, quality options, and download URLs
    for a specific episode of an anime series.
    """
    
    number: int = Field(..., ge=1, description="Episode number")
    title: str = Field(..., min_length=1, description="Episode title")
    url: HttpUrl = Field(..., description="URL to the episode page")
    source: str = Field(..., min_length=1, description="Source plugin name")
    quality_options: List[Quality] = Field(..., description="Available qualities")
    duration: Optional[str] = Field(None, description="Episode duration (HH:MM format)")
    description: Optional[str] = Field(None, description="Episode description")
    thumbnail: Optional[HttpUrl] = Field(None, description="Episode thumbnail URL")
    air_date: Optional[datetime] = Field(None, description="Original air date")
    filler: bool = Field(False, description="Whether episode is filler")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is properly formatted."""
        return v.strip()
    
    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v: Optional[str]) -> Optional[str]:
        """Validate duration format (MM:SS or HH:MM:SS)."""
        if v is None:
            return v
        
        parts = v.split(':')
        if len(parts) not in [2, 3]:
            raise ValueError("Duration must be in MM:SS or HH:MM:SS format")
        
        try:
            # Validate all parts are integers
            [int(part) for part in parts]
        except ValueError:
            raise ValueError("Duration parts must be integers")
        
        return v
    
    @field_validator('quality_options')
    @classmethod
    def validate_quality_options(cls, v: List[Quality]) -> List[Quality]:
        """Ensure quality options are unique and sorted."""
        unique_qualities = list(dict.fromkeys(v))  # Remove duplicates while preserving order
        return sorted(unique_qualities, key=lambda q: q.height, reverse=True)
    
    @property
    def best_quality(self) -> Quality:
        """Get the highest available quality."""
        return max(self.quality_options, key=lambda q: q.height)
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Convert duration to total seconds."""
        if not self.duration:
            return None
        
        parts = [int(p) for p in self.duration.split(':')]
        if len(parts) == 2:  # MM:SS
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:  # HH:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return None
    
    def __str__(self) -> str:
        return f"Episode {self.number}: {self.title}"
    
    def __repr__(self) -> str:
        return f"Episode(number={self.number}, title='{self.title}')"

class DownloadTask(BaseModel):
    """
    Represents a download task with progress tracking and metadata.
    
    Manages the state and progress of downloading an anime episode,
    including file information, download statistics, and error handling.
    """
    
    episode: Episode = Field(..., description="Episode being downloaded")
    quality: Quality = Field(..., description="Selected quality for download")
    output_path: Path = Field(..., description="Output file path")
    download_url: Optional[HttpUrl] = Field(None, description="Direct download URL")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers for download")
    
    # Progress tracking
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Download progress percentage")
    status: DownloadStatus = Field(DownloadStatus.PENDING, description="Current download status")
    
    # File information
    file_size: Optional[int] = Field(None, ge=0, description="Total file size in bytes")
    downloaded_bytes: int = Field(0, ge=0, description="Bytes downloaded so far")
    
    # Download statistics
    download_speed: float = Field(0.0, ge=0.0, description="Current download speed (bytes/sec)")
    eta_seconds: Optional[int] = Field(None, ge=0, description="Estimated time remaining")
    start_time: Optional[datetime] = Field(None, description="Download start timestamp")
    end_time: Optional[datetime] = Field(None, description="Download completion timestamp")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, ge=0, description="Number of retry attempts")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    
    @field_validator('output_path')
    @classmethod
    def validate_output_path(cls, v: Path) -> Path:
        """Ensure output path is valid and create parent directories."""
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    @field_validator('quality')
    @classmethod
    def validate_quality_available(cls, v: Quality, info) -> Quality:
        """Ensure selected quality is available for the episode."""
        if 'episode' in info.data:
            episode = info.data['episode']
            if v not in episode.quality_options:
                raise ValueError(f"Quality {v} not available for this episode")
        return v
    
    @model_validator(mode='after')
    def validate_progress_consistency(self) -> 'DownloadTask':
        """Ensure progress values are consistent."""
        if self.file_size and self.downloaded_bytes > self.file_size:
            raise ValueError("Downloaded bytes cannot exceed file size")
        
        if self.file_size and self.file_size > 0:
            calculated_progress = (self.downloaded_bytes / self.file_size) * 100
            # Allow small discrepancy due to floating point precision
            if abs(self.progress - calculated_progress) > 0.1:
                self.progress = calculated_progress
        
        return self
    
    @property
    def is_active(self) -> bool:
        """Check if download is currently active."""
        return self.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PENDING]
    
    @property
    def is_complete(self) -> bool:
        """Check if download is completed successfully."""
        return self.status == DownloadStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if download has failed."""
        return self.status == DownloadStatus.FAILED
    
    @property
    def can_retry(self) -> bool:
        """Check if download can be retried."""
        return self.is_failed and self.retry_count < self.max_retries  
  
    @property
    def formatted_file_size(self) -> str:
        """Get human-readable file size."""
        if not self.file_size:
            return "Unknown"
        
        size = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    @property
    def formatted_speed(self) -> str:
        """Get human-readable download speed."""
        if self.download_speed == 0:
            return "0 B/s"
        
        speed = self.download_speed
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} TB/s"
    
    @property
    def formatted_eta(self) -> str:
        """Get human-readable ETA."""
        if not self.eta_seconds:
            return "Unknown"
        
        hours, remainder = divmod(self.eta_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get total download duration in seconds."""
        if not self.start_time:
            return None
        
        end = self.end_time or datetime.now()
        return int((end - self.start_time).total_seconds())
    
    def update_progress(self, downloaded_bytes: int, total_bytes: Optional[int] = None) -> None:
        """Update download progress with new byte counts."""
        import logging
        logger = logging.getLogger(__name__)
        
        self.downloaded_bytes = downloaded_bytes
        
        if total_bytes:
            self.file_size = total_bytes
        
        if self.file_size and self.file_size > 0:
            self.progress = (self.downloaded_bytes / self.file_size) * 100
        else:
            # For streams without known total size, show as indeterminate
            self.progress = 0.0
        
        # Calculate download speed if we have timing information
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                self.download_speed = self.downloaded_bytes / elapsed
                
                # Calculate ETA
                if self.file_size and self.download_speed > 0:
                    remaining_bytes = self.file_size - self.downloaded_bytes
                    self.eta_seconds = int(remaining_bytes / self.download_speed)
    
    def mark_started(self) -> None:
        """Mark download as started."""
        self.status = DownloadStatus.DOWNLOADING
        self.start_time = datetime.now()
    
    def mark_completed(self) -> None:
        """Mark download as completed."""
        self.status = DownloadStatus.COMPLETED
        self.progress = 100.0
        self.end_time = datetime.now()
        self.eta_seconds = 0
    
    def mark_failed(self, error_message: str) -> None:
        """Mark download as failed with error message."""
        self.status = DownloadStatus.FAILED
        self.error_message = error_message
        self.end_time = datetime.now()
    
    def __str__(self) -> str:
        return f"Download: {self.episode.title} ({self.quality}) - {self.progress:.1f}%"
    
    def __repr__(self) -> str:
        return f"DownloadTask(episode={self.episode.number}, quality='{self.quality}', status='{self.status}')"


# Type aliases for better code readability
AnimeList = List[AnimeResult]
EpisodeList = List[Episode]
DownloadQueue = List[DownloadTask]

# Export all models and types
__all__ = [
    "Quality",
    "DownloadStatus", 
    "AnimeResult",
    "Episode",
    "DownloadTask",
    "AnimeList",
    "EpisodeList", 
    "DownloadQueue",
]