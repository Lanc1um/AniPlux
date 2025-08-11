"""
Core Utilities - Shared utility functions and helpers.

This module contains common utility functions used across the AniPlux
application, including validation helpers, formatting utilities, and
data processing functions.
"""

import re
from pathlib import Path
from typing import List, Optional, Union
from urllib.parse import urlparse

from aniplux.core.models import Quality, AnimeResult, Episode


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing invalid characters and limiting length.
    
    Args:
        filename: The original filename
        max_length: Maximum allowed filename length
        
    Returns:
        A sanitized filename safe for filesystem use
    """
    # Remove invalid characters for most filesystems
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # Trim whitespace and dots from ends
    sanitized = sanitized.strip(' .')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "untitled"
    
    # Limit length while preserving extension
    if len(sanitized) > max_length:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def generate_episode_filename(
    anime_title: str,
    episode: Episode,
    quality: Quality,
    extension: str = "mp4"
) -> str:
    """
    Generate a standardized filename for an episode download.
    
    Args:
        anime_title: The anime series title
        episode: The episode object
        quality: The selected quality
        extension: File extension (default: mp4)
        
    Returns:
        A formatted filename string
    """
    # Format: "Anime Title - S01E01 - Episode Title [1080p].mp4"
    episode_num = f"E{episode.number:02d}"
    
    # Clean episode title
    episode_title = episode.title.replace(':', ' -')
    
    filename = f"{anime_title} - {episode_num} - {episode_title} [{quality}].{extension}"
    
    return sanitize_filename(filename)


def validate_url(url: str) -> bool:
    """
    Validate if a string is a properly formatted URL.
    
    Args:
        url: The URL string to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable file size.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    
    for i, unit in enumerate(size_names):
        if size < 1024.0 or i == len(size_names) - 1:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    
    return f"{size:.1f} TB"


def format_duration(seconds: int) -> str:
    """
    Convert seconds to human-readable duration.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "1:23:45")
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def filter_anime_results(
    results: List[AnimeResult],
    min_rating: Optional[float] = None,
    genres: Optional[List[str]] = None,
    year_range: Optional[tuple[int, int]] = None,
    max_results: Optional[int] = None
) -> List[AnimeResult]:
    """
    Filter anime results based on various criteria.
    
    Args:
        results: List of anime results to filter
        min_rating: Minimum rating threshold
        genres: List of required genres (any match)
        year_range: Tuple of (min_year, max_year)
        max_results: Maximum number of results to return
        
    Returns:
        Filtered list of anime results
    """
    filtered = results.copy()
    
    # Filter by minimum rating
    if min_rating is not None:
        filtered = [r for r in filtered if r.rating and r.rating >= min_rating]
    
    # Filter by genres (any genre match)
    if genres:
        genre_set = {g.lower() for g in genres}
        filtered = [
            r for r in filtered 
            if any(g.lower() in genre_set for g in r.genres)
        ]
    
    # Filter by year range
    if year_range:
        min_year, max_year = year_range
        filtered = [
            r for r in filtered 
            if r.year and min_year <= r.year <= max_year
        ]
    
    # Limit results
    if max_results:
        filtered = filtered[:max_results]
    
    return filtered


def sort_episodes(episodes: List[Episode], reverse: bool = False) -> List[Episode]:
    """
    Sort episodes by episode number.
    
    Args:
        episodes: List of episodes to sort
        reverse: Sort in descending order if True
        
    Returns:
        Sorted list of episodes
    """
    return sorted(episodes, key=lambda ep: ep.number, reverse=reverse)


def get_best_quality_available(
    requested_quality: Quality,
    available_qualities: List[Quality]
) -> Quality:
    """
    Get the best available quality that doesn't exceed the requested quality.
    
    Args:
        requested_quality: The desired quality
        available_qualities: List of available qualities
        
    Returns:
        The best available quality
    """
    if not available_qualities:
        raise ValueError("No qualities available")
    
    # Sort qualities by resolution (highest first)
    sorted_qualities = sorted(available_qualities, key=lambda q: q.height, reverse=True)
    
    # If requested quality is available, return it
    if requested_quality in sorted_qualities:
        return requested_quality
    
    # Otherwise, find the best quality that doesn't exceed requested
    for quality in sorted_qualities:
        if quality.height <= requested_quality.height:
            return quality
    
    # If all available qualities exceed requested, return the lowest
    return min(sorted_qualities, key=lambda q: q.height)


def extract_anime_title_from_url(url: str) -> str:
    """
    Extract anime title from URL.
    
    Args:
        url: Anime URL to extract title from
        
    Returns:
        Extracted anime title or "Unknown Anime" if extraction fails
    """
    try:
        parsed_url = urlparse(url)
        
        # Handle Animetsu URLs
        if 'animetsu.to' in parsed_url.netloc:
            path_parts = parsed_url.path.split('/')
            
            # URL format: https://animetsu.to/watch/{anime_id}/{episode_number}
            if len(path_parts) >= 3 and path_parts[1] == 'watch':
                anime_id = path_parts[2]
                
                # For Animetsu, we need to make an API call to get the actual title
                # For now, return a placeholder that indicates we need to fetch it
                return f"Anime {anime_id}"
        
        # Handle HiAnime URLs
        elif 'hianime.to' in parsed_url.netloc:
            path_parts = parsed_url.path.split('/')
            
            if len(path_parts) >= 3 and path_parts[1] in ['watch', 'anime']:
                anime_slug = path_parts[2]
                
                # Remove ID suffix (e.g., -18056)
                anime_slug = re.sub(r'-\d+$', '', anime_slug)
                
                # Convert slug to title
                title = anime_slug.replace('-', ' ').title()
                
                # Fix common title formatting issues
                title = re.sub(r'\b(And|Of|The|To|No|Wa|Ni|Ga|Wo)\b', 
                              lambda m: m.group(1).lower(), title)
                title = re.sub(r'\bOva\b', 'OVA', title, flags=re.IGNORECASE)
                title = re.sub(r'\bTv\b', 'TV', title, flags=re.IGNORECASE)
                
                # Remove trailing numbers that might be IDs (like "18056")
                title = re.sub(r'\s+\d{4,}$', '', title)
                
                # Also remove common patterns like "Arc 18056"
                title = re.sub(r'\s+Arc\s+\d+$', ' Arc', title, flags=re.IGNORECASE)
                
                # Handle special cases
                title_fixes = {
                    'Kimetsu No Yaiba': 'Demon Slayer: Kimetsu no Yaiba',
                    'Shingeki No Kyojin': 'Attack on Titan',
                    'Boku No Hero Academia': 'My Hero Academia',
                }
                
                for old, new in title_fixes.items():
                    if old.lower() in title.lower():
                        title = new
                        break
                
                return title
        
        # Handle other anime sites (generic approach)
        path_parts = parsed_url.path.split('/')
        for part in path_parts:
            if part and len(part) > 3:  # Skip short path segments
                # Look for anime-like slugs
                if re.match(r'^[a-z0-9-]+$', part) and '-' in part:
                    title = part.replace('-', ' ').title()
                    # Remove common suffixes
                    title = re.sub(r'\s+(Episode|Ep|Season|S\d+).*$', '', title, flags=re.IGNORECASE)
                    return title
        
        return "Unknown Anime"
        
    except Exception:
        return "Unknown Anime"


# Export utility functions
__all__ = [
    "sanitize_filename",
    "generate_episode_filename", 
    "validate_url",
    "format_file_size",
    "format_duration",
    "filter_anime_results",
    "sort_episodes",
    "get_best_quality_available",
    "extract_anime_title_from_url",
]