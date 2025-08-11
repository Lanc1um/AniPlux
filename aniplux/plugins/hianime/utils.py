"""
HiAnime Utilities - Helper functions specific to hianime.to

This module provides utility functions and constants
specific to the HiAnime plugin implementation.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

from aniplux.core.models import Quality


logger = logging.getLogger(__name__)


# HiAnime-specific constants
HIANIME_DOMAINS = [
    "hianime.to",
    "aniwatch.to",  # Previous domain
    "9anime.to"     # Alternative domain
]

HIANIME_SEARCH_FILTERS = {
    "type": {
        "all": "",
        "tv": "1",
        "movie": "2",
        "ova": "3",
        "ona": "4",
        "special": "5"
    },
    "status": {
        "all": "",
        "completed": "1",
        "ongoing": "2",
        "upcoming": "3"
    },
    "season": {
        "all": "",
        "spring": "1",
        "summer": "2",
        "fall": "3",
        "winter": "4"
    },
    "language": {
        "all": "",
        "sub": "1",
        "dub": "2",
        "chinese": "3"
    },
    "sort": {
        "default": "",
        "recently_added": "recently_added",
        "recently_updated": "recently_updated",
        "score": "score",
        "name_az": "name_az",
        "released_date": "released_date",
        "most_watched": "most_watched"
    }
}

# Common video server patterns for HiAnime
VIDEO_SERVER_PATTERNS = [
    r'vidstreaming\.io',
    r'gogo-stream\.com',
    r'streamani\.net',
    r'gogoplay\d*\.io',
    r'anime789\.com'
]

# Quality mapping for HiAnime
HIANIME_QUALITY_MAP = {
    "360": Quality.LOW,
    "480": Quality.LOW,
    "720": Quality.MEDIUM,
    "1080": Quality.HIGH,
    "1440": Quality.ULTRA,
    "2160": Quality.FOUR_K
}


def is_hianime_url(url: str) -> bool:
    """
    Check if URL belongs to HiAnime domains.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is from HiAnime, False otherwise
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain in HIANIME_DOMAINS
    except Exception:
        return False


def extract_anime_id(url: str) -> Optional[str]:
    """
    Extract anime ID from HiAnime URL.
    
    Args:
        url: HiAnime anime URL
        
    Returns:
        Anime ID if found, None otherwise
    """
    if not url:
        return None
    
    # Common patterns for anime IDs in HiAnime URLs
    patterns = [
        r'/watch/([^/?]+)',
        r'/anime/([^/?]+)',
        r'/detail/([^/?]+)',
        r'-(\d+)/?$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def extract_episode_id(url: str) -> Optional[str]:
    """
    Extract episode ID from HiAnime episode URL.
    
    Args:
        url: HiAnime episode URL
        
    Returns:
        Episode ID if found, None otherwise
    """
    if not url:
        return None
    
    # Look for episode ID in URL path or query parameters
    try:
        parsed = urlparse(url)
        
        # Check query parameters first
        params = parse_qs(parsed.query)
        if 'ep' in params:
            return params['ep'][0]
        
        # Check URL path
        path_patterns = [
            r'/watch/[^/]+-episode-(\d+)',
            r'/episode/([^/?]+)',
            r'ep-(\d+)',
            r'episode-(\d+)'
        ]
        
        for pattern in path_patterns:
            match = re.search(pattern, parsed.path)
            if match:
                return match.group(1)
        
    except Exception as e:
        logger.debug(f"Failed to extract episode ID from {url}: {e}")
    
    return None


def normalize_anime_title(title: str) -> str:
    """
    Normalize anime title for HiAnime.
    
    Args:
        title: Raw anime title
        
    Returns:
        Normalized title
    """
    if not title:
        return ""
    
    # Remove common HiAnime-specific prefixes/suffixes
    title = re.sub(r'^(Watch\s+)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+(English\s+)?(Sub|Dub)bed?$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+Online\s*$', '', title, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    title = re.sub(r'\s+', ' ', title.strip())
    
    return title


def parse_episode_range(episode_text: str) -> Optional[Dict[str, int]]:
    """
    Parse episode range from text (e.g., "1-12", "Episode 5").
    
    Args:
        episode_text: Text containing episode information
        
    Returns:
        Dictionary with 'start' and 'end' keys, or None if not found
    """
    if not episode_text:
        return None
    
    # Pattern for episode ranges
    range_patterns = [
        r'(\d+)\s*-\s*(\d+)',  # "1-12"
        r'Episodes?\s+(\d+)\s*-\s*(\d+)',  # "Episodes 1-12"
        r'Ep\s*(\d+)\s*-\s*(\d+)'  # "Ep 1-12"
    ]
    
    for pattern in range_patterns:
        match = re.search(pattern, episode_text, re.IGNORECASE)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            return {'start': start, 'end': end}
    
    # Pattern for single episode
    single_patterns = [
        r'Episode\s+(\d+)',  # "Episode 5"
        r'Ep\s*(\d+)',  # "Ep 5"
        r'^(\d+)$'  # Just a number
    ]
    
    for pattern in single_patterns:
        match = re.search(pattern, episode_text, re.IGNORECASE)
        if match:
            episode_num = int(match.group(1))
            return {'start': episode_num, 'end': episode_num}
    
    return None


def build_search_url(base_url: str, query: str, filters: Optional[Dict[str, str]] = None) -> str:
    """
    Build search URL with filters for HiAnime.
    
    Args:
        base_url: Base URL for HiAnime
        query: Search query
        filters: Optional search filters
        
    Returns:
        Complete search URL
    """
    from urllib.parse import urlencode, quote_plus
    
    # Start with basic search
    params = {'keyword': query}
    
    # Add filters if provided
    if filters:
        for filter_type, filter_value in filters.items():
            if filter_type in HIANIME_SEARCH_FILTERS:
                filter_options = HIANIME_SEARCH_FILTERS[filter_type]
                if filter_value in filter_options:
                    param_value = filter_options[filter_value]
                    if param_value:  # Only add non-empty values
                        params[filter_type] = param_value
    
    # Build URL
    query_string = urlencode(params, quote_via=quote_plus)
    return f"{base_url}/search?{query_string}"


def extract_quality_from_hianime_label(label: str) -> Optional[Quality]:
    """
    Extract quality from HiAnime-specific quality labels.
    
    Args:
        label: Quality label from HiAnime
        
    Returns:
        Quality enum if recognized, None otherwise
    """
    if not label:
        return None
    
    label_lower = label.lower()
    
    # Check for resolution numbers
    for resolution, quality in HIANIME_QUALITY_MAP.items():
        if resolution in label_lower:
            return quality
    
    # Check for quality keywords
    if any(keyword in label_lower for keyword in ['hd', '720']):
        return Quality.MEDIUM
    elif any(keyword in label_lower for keyword in ['full hd', 'fhd', '1080']):
        return Quality.HIGH
    elif any(keyword in label_lower for keyword in ['4k', 'uhd', '2160']):
        return Quality.FOUR_K
    elif any(keyword in label_lower for keyword in ['sd', '480', '360']):
        return Quality.LOW
    
    return None


def is_video_server_url(url: str) -> bool:
    """
    Check if URL is from a known video server.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is from a video server, False otherwise
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    for pattern in VIDEO_SERVER_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    
    return False


def clean_hianime_description(description: str) -> str:
    """
    Clean description text specific to HiAnime format.
    
    Args:
        description: Raw description text
        
    Returns:
        Cleaned description
    """
    if not description:
        return ""
    
    # Remove HiAnime-specific patterns
    description = re.sub(r'Watch\s+[^.]+\s+online\s+at\s+[^.]+\.', '', description, flags=re.IGNORECASE)
    description = re.sub(r'Stream\s+[^.]+\s+episodes?\s+online\s+for\s+free\.?', '', description, flags=re.IGNORECASE)
    
    # Remove extra whitespace and normalize
    description = re.sub(r'\s+', ' ', description.strip())
    
    return description


# Export utility functions
__all__ = [
    "HIANIME_DOMAINS",
    "HIANIME_SEARCH_FILTERS", 
    "HIANIME_QUALITY_MAP",
    "is_hianime_url",
    "extract_anime_id",
    "extract_episode_id",
    "normalize_anime_title",
    "parse_episode_range",
    "build_search_url",
    "extract_quality_from_hianime_label",
    "is_video_server_url",
    "clean_hianime_description"
]