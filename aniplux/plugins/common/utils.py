"""
Plugin Utilities - Common utilities and helpers for plugin development.

This module provides utility functions and classes that are commonly needed
when developing anime source plugins, including HTML parsing, URL handling,
and data extraction helpers.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from pydantic import HttpUrl
from aniplux.core.models import Quality, AnimeResult, Episode
from aniplux.core.exceptions import PluginError


logger = logging.getLogger(__name__)


class HTMLParser:
    """Utility class for HTML parsing operations."""
    
    def __init__(self, html_content: str, base_url: str = ""):
        """
        Initialize HTML parser.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative links
        """
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.base_url = base_url
    
    def find_text(self, selector: str, default: str = "") -> str:
        """
        Find text content using CSS selector.
        
        Args:
            selector: CSS selector string
            default: Default value if element not found
            
        Returns:
            Text content or default value
        """
        element = self.soup.select_one(selector)
        if element:
            return element.get_text(strip=True)
        return default
    
    def find_attr(self, selector: str, attr: str, default: str = "") -> str:
        """
        Find attribute value using CSS selector.
        
        Args:
            selector: CSS selector string
            attr: Attribute name
            default: Default value if element/attribute not found
            
        Returns:
            Attribute value or default value
        """
        element = self.soup.select_one(selector)
        if element and element.has_attr(attr):
            value = element[attr]
            # Handle case where BeautifulSoup returns a list
            if isinstance(value, list):
                value = value[0] if value else ""
            # Resolve relative URLs
            if attr in ['href', 'src'] and self.base_url and isinstance(value, str):
                return urljoin(self.base_url, value)
            return value
        return default
    
    def find_all_text(self, selector: str) -> List[str]:
        """
        Find all text content matching CSS selector.
        
        Args:
            selector: CSS selector string
            
        Returns:
            List of text content
        """
        elements = self.soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements]
    
    def find_all_attrs(self, selector: str, attr: str) -> List[str]:
        """
        Find all attribute values matching CSS selector.
        
        Args:
            selector: CSS selector string
            attr: Attribute name
            
        Returns:
            List of attribute values
        """
        elements = self.soup.select(selector)
        values = []
        
        for elem in elements:
            if elem.has_attr(attr):
                value = elem[attr]
                # Handle case where BeautifulSoup returns a list
                if isinstance(value, list):
                    value = value[0] if value else ""
                # Resolve relative URLs
                if attr in ['href', 'src'] and self.base_url and isinstance(value, str):
                    value = urljoin(self.base_url, value)
                values.append(value)
        
        return values
    
    def extract_json_data(self, script_selector: str = "script") -> Dict[str, Any]:
        """
        Extract JSON data from script tags.
        
        Args:
            script_selector: CSS selector for script tags
            
        Returns:
            Dictionary of extracted JSON data
        """
        import json
        
        scripts = self.soup.select(script_selector)
        json_data = {}
        
        for script in scripts:
            if not script.string:
                continue
            
            # Look for JSON-like patterns
            json_matches = re.findall(r'(\{[^{}]*\})', script.string)
            
            for match in json_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict):
                        json_data.update(data)
                except json.JSONDecodeError:
                    continue
        
        return json_data


class QualityExtractor:
    """Utility class for extracting and parsing video quality information."""
    
    QUALITY_PATTERNS = {
        Quality.FOUR_K: [r'2160p?', r'4k', r'uhd'],
        Quality.ULTRA: [r'1440p?', r'2k'],
        Quality.HIGH: [r'1080p?', r'fhd', r'full.?hd'],
        Quality.MEDIUM: [r'720p?', r'hd'],
        Quality.LOW: [r'480p?', r'sd', r'360p?']
    }
    
    @classmethod
    def extract_from_text(cls, text: str) -> List[Quality]:
        """
        Extract quality options from text.
        
        Args:
            text: Text containing quality information
            
        Returns:
            List of detected qualities
        """
        text_lower = text.lower()
        detected_qualities = []
        
        for quality, patterns in cls.QUALITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    detected_qualities.append(quality)
                    break
        
        # Remove duplicates and sort by quality
        unique_qualities = list(dict.fromkeys(detected_qualities))
        return sorted(unique_qualities, key=lambda q: q.height, reverse=True)
    
    @classmethod
    def extract_from_url(cls, url: str) -> Optional[Quality]:
        """
        Extract quality from URL.
        
        Args:
            url: URL that might contain quality information
            
        Returns:
            Detected quality or None
        """
        qualities = cls.extract_from_text(url)
        return qualities[0] if qualities else None
    
    @classmethod
    def get_best_quality(cls, available_qualities: List[Quality]) -> Quality:
        """
        Get the best available quality.
        
        Args:
            available_qualities: List of available qualities
            
        Returns:
            Best quality option
        """
        if not available_qualities:
            return Quality.MEDIUM  # Default fallback
        
        return max(available_qualities, key=lambda q: q.height)


class URLHelper:
    """Utility class for URL manipulation and validation."""
    
    @staticmethod
    def is_absolute(url: str) -> bool:
        """Check if URL is absolute."""
        return bool(urlparse(url).netloc)
    
    @staticmethod
    def make_absolute(url: str, base_url: str) -> str:
        """Convert relative URL to absolute."""
        if URLHelper.is_absolute(url):
            return url
        return urljoin(base_url, url)
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc
    
    @staticmethod
    def get_query_param(url: str, param: str, default: str = "") -> str:
        """Extract query parameter from URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get(param, [default])[0]
    
    @staticmethod
    def validate_url(url: str) -> str:
        """Validate and ensure URL is properly formatted for Pydantic HttpUrl."""
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")
        
        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"URL must start with http:// or https://: {url}")
        
        # Basic URL validation
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")
        
        return url
    
    @staticmethod
    def clean_url(url: str) -> str:
        """Clean and normalize URL."""
        # Remove common tracking parameters
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'ref', 'referrer']
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Remove tracking parameters
        for param in tracking_params:
            query_params.pop(param, None)
        
        # Rebuild query string
        from urllib.parse import urlencode
        clean_query = urlencode(query_params, doseq=True)
        
        # Rebuild URL
        from urllib.parse import urlunparse
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            parsed.fragment
        ))


class TextCleaner:
    """Utility class for cleaning and normalizing text content."""
    
    @staticmethod
    def clean_title(title: str) -> str:
        """
        Clean anime title text.
        
        Args:
            title: Raw title text
            
        Returns:
            Cleaned title
        """
        if not title:
            return ""
        
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title.strip())
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(anime\s*[:\-]?\s*)', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*(anime)$', '', title, flags=re.IGNORECASE)
        
        # Remove episode indicators from titles
        title = re.sub(r'\s*-?\s*episode\s*\d+.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-?\s*ep\.?\s*\d+.*$', '', title, flags=re.IGNORECASE)
        
        return title.strip()
    
    @staticmethod
    def extract_episode_number(text: str) -> Optional[int]:
        """
        Extract episode number from text.
        
        Args:
            text: Text containing episode information
            
        Returns:
            Episode number or None if not found
        """
        # Common episode number patterns
        patterns = [
            r'episode\s*(\d+)',
            r'ep\.?\s*(\d+)',
            r'e(\d+)',
            r'#(\d+)',
            r'\b(\d+)\b'  # Fallback: any number
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def clean_description(description: str, max_length: int = 500) -> str:
        """
        Clean and truncate description text.
        
        Args:
            description: Raw description text
            max_length: Maximum length for description
            
        Returns:
            Cleaned description
        """
        if not description:
            return ""
        
        # Remove HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description.strip())
        
        # Truncate if too long
        if len(description) > max_length:
            description = description[:max_length].rsplit(' ', 1)[0] + '...'
        
        return description
    
    @staticmethod
    def parse_duration(duration_text: str) -> Optional[str]:
        """
        Parse duration text into standard format.
        
        Args:
            duration_text: Raw duration text
            
        Returns:
            Standardized duration string (MM:SS or HH:MM:SS) or None
        """
        if not duration_text:
            return None
        
        # Extract numbers from duration text
        numbers = re.findall(r'\d+', duration_text)
        
        if len(numbers) == 1:
            # Assume minutes only
            minutes = int(numbers[0])
            return f"{minutes:02d}:00"
        elif len(numbers) == 2:
            # Minutes and seconds
            minutes, seconds = map(int, numbers)
            return f"{minutes:02d}:{seconds:02d}"
        elif len(numbers) == 3:
            # Hours, minutes, seconds
            hours, minutes, seconds = map(int, numbers)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return None


def create_anime_result(
    title: str,
    url: str,
    source: str,
    **kwargs
) -> AnimeResult:
    """
    Create an AnimeResult with cleaned data.
    
    Args:
        title: Anime title
        url: Anime URL
        source: Source plugin name
        **kwargs: Additional fields for AnimeResult
        
    Returns:
        AnimeResult instance
    """
    # Clean the title
    clean_title = TextCleaner.clean_title(title)
    
    # Clean description if provided
    if 'description' in kwargs and kwargs['description']:
        kwargs['description'] = TextCleaner.clean_description(kwargs['description'])
    
    # Ensure URL is absolute
    if 'base_url' in kwargs:
        url = URLHelper.make_absolute(url, kwargs.pop('base_url'))
    
    # Validate URL format for Pydantic
    try:
        URLHelper.validate_url(url)
        # Convert to HttpUrl type for Pydantic
        validated_url = HttpUrl(url)
    except (ValueError, Exception) as e:
        raise ValueError(f"Invalid URL for AnimeResult '{clean_title}': {e}")
    
    return AnimeResult(
        title=clean_title,
        url=validated_url,
        source=source,
        **kwargs
    )


def create_episode(
    number: int,
    title: str,
    url: str,
    source: str,
    quality_options: List[Quality],
    **kwargs
) -> Episode:
    """
    Create an Episode with cleaned data.
    
    Args:
        number: Episode number
        title: Episode title
        url: Episode URL
        source: Source plugin name
        quality_options: Available quality options
        **kwargs: Additional fields for Episode
        
    Returns:
        Episode instance
    """
    # Clean the title
    clean_title = TextCleaner.clean_title(title)
    
    # If title becomes empty after cleaning, use a fallback
    if not clean_title or not clean_title.strip():
        clean_title = f"Episode {number}"
    
    # Parse duration if provided
    if 'duration' in kwargs and kwargs['duration']:
        parsed_duration = TextCleaner.parse_duration(kwargs['duration'])
        if parsed_duration:
            kwargs['duration'] = parsed_duration
    
    # Ensure URL is absolute
    if 'base_url' in kwargs:
        url = URLHelper.make_absolute(url, kwargs.pop('base_url'))
    
    # Validate URL format for Pydantic
    try:
        URLHelper.validate_url(url)
        # Convert to HttpUrl type for Pydantic
        validated_url = HttpUrl(url)
    except (ValueError, Exception) as e:
        raise ValueError(f"Invalid URL for Episode {number} '{clean_title}': {e}")
    
    return Episode(
        number=number,
        title=clean_title,
        url=validated_url,
        source=source,
        quality_options=quality_options,
        **kwargs
    )


# Export utility classes and functions
__all__ = [
    "HTMLParser",
    "QualityExtractor", 
    "URLHelper",
    "TextCleaner",
    "create_anime_result",
    "create_episode",
]