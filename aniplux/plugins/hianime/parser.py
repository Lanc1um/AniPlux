"""
HiAnime Parser - HTML parsing utilities for hianime.to

This module provides specialized parsing functions for extracting
anime data from hianime.to HTML pages.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, parse_qs, urlparse

from aniplux.plugins.common import HTMLParser, TextCleaner, QualityExtractor
from aniplux.core.models import Quality, AnimeResult, Episode
from aniplux.core.exceptions import PluginError


logger = logging.getLogger(__name__)


class HiAnimeParser:
    """Specialized parser for hianime.to content."""
    
    def __init__(self, html_content: str, base_url: str = "https://hianime.to"):
        """
        Initialize HiAnime parser.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative links
        """
        self.parser = HTMLParser(html_content, base_url)
        self.base_url = base_url
    
    def parse_search_results(self) -> List[Dict[str, Any]]:
        """
        Parse search results from search page.
        
        Returns:
            List of anime data dictionaries
        """
        results = []
        
        # HiAnime search results are in .flw-item containers
        items = self.parser.soup.select('.flw-item')
        
        for item in items:
            try:
                # Extract basic information
                title_elem = item.select_one('.film-name a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                # Make URL absolute
                if url and isinstance(url, str) and not url.startswith('http'):
                    url = urljoin(self.base_url, url)
                
                # Extract thumbnail
                img_elem = item.select_one('.film-poster img')
                thumbnail = None
                if img_elem:
                    thumbnail = img_elem.get('data-src') or img_elem.get('src')
                    if thumbnail and isinstance(thumbnail, str) and not thumbnail.startswith('http'):
                        thumbnail = urljoin(self.base_url, thumbnail)
                
                # Extract metadata
                metadata = self._extract_item_metadata(item)
                
                result_data = {
                    'title': title,
                    'url': url,
                    'thumbnail': thumbnail,
                    **metadata
                }
                
                results.append(result_data)
                
            except Exception as e:
                logger.warning(f"Failed to parse search result item: {e}")
                continue
        
        return results
    
    def _extract_item_metadata(self, item) -> Dict[str, Any]:
        """Extract metadata from a search result item."""
        metadata = {}
        
        # Extract episode count from .tick-item.tick-eps
        ep_info = item.select_one('.tick-item.tick-eps')
        if ep_info:
            ep_text = ep_info.get_text(strip=True)
            ep_match = re.search(r'(\d+)', ep_text)
            if ep_match:
                metadata['episode_count'] = int(ep_match.group(1))
        
        # Extract metadata from fdi-items
        fdi_items = item.select('.film-detail .fd-infor .fdi-item')
        
        if len(fdi_items) >= 1:
            # First fdi-item is usually the type (TV, Movie, Special, ONA)
            type_text = fdi_items[0].get_text(strip=True)
            metadata['type'] = type_text
            
            # For movies and specials, set episode count to 1 if not already set
            if type_text.lower() in ['movie', 'special'] and 'episode_count' not in metadata:
                metadata['episode_count'] = 1
        
        if len(fdi_items) >= 2:
            # Second fdi-item is usually duration
            duration_text = fdi_items[1].get_text(strip=True)
            if duration_text.endswith('m'):
                try:
                    duration_minutes = int(duration_text[:-1])
                    metadata['duration'] = f"{duration_minutes}m"
                except ValueError:
                    pass
        
        # Look for any year information in all fdi-items
        for fdi_item in fdi_items:
            fdi_text = fdi_item.get_text(strip=True)
            
            # Look for year patterns (4 digits)
            year_match = re.search(r'\b(19|20)\d{2}\b', fdi_text)
            if year_match and 'year' not in metadata:
                metadata['year'] = int(year_match.group(0))
            
            # Look for rating patterns
            rating_match = re.search(r'(\d+\.?\d*)\s*(?:\/10|★)', fdi_text)
            if rating_match:
                try:
                    metadata['rating'] = float(rating_match.group(1))
                except ValueError:
                    pass
        
        # Extract description from film-detail if available
        desc_elem = item.select_one('.film-detail .description')
        if desc_elem:
            description = desc_elem.get_text(strip=True)
            metadata['description'] = TextCleaner.clean_description(description)
        
        return metadata
    
    def parse_anime_details(self) -> Dict[str, Any]:
        """
        Parse anime details from anime page.
        
        Returns:
            Dictionary containing anime details
        """
        details = {}
        
        # Extract title
        title_elem = self.parser.soup.select_one('.anisc-detail h2.film-name')
        if title_elem:
            details['title'] = title_elem.get_text(strip=True)
        
        # Extract description
        desc_elem = self.parser.soup.select_one('.anisc-detail .film-description .text')
        if desc_elem:
            details['description'] = TextCleaner.clean_description(desc_elem.get_text(strip=True))
        
        # Extract metadata from info items
        info_items = self.parser.soup.select('.anisc-info .item')
        for item in info_items:
            label_elem = item.select_one('.item-head')
            value_elem = item.select_one('.name')
            
            if not label_elem or not value_elem:
                continue
            
            label = label_elem.get_text(strip=True).lower().replace(':', '')
            value = value_elem.get_text(strip=True)
            
            if 'aired' in label:
                year_match = re.search(r'(\d{4})', value)
                if year_match:
                    details['year'] = int(year_match.group(1))
            elif 'episodes' in label:
                ep_match = re.search(r'(\d+)', value)
                if ep_match:
                    details['episode_count'] = int(ep_match.group(1))
            elif 'genres' in label:
                genres = [g.strip() for g in value.split(',')]
                details['genres'] = genres
            elif 'status' in label:
                details['status'] = value
        
        # Extract rating
        rating_elem = self.parser.soup.select_one('.film-stats .tick .tick-pg')
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                details['rating'] = float(rating_match.group(1))
        
        return details
    
    def parse_episodes_list(self) -> List[Dict[str, Any]]:
        """
        Parse episodes list from anime page.
        
        Returns:
            List of episode data dictionaries
        """
        episodes = []
        
        # HiAnime episodes are in .ssl-item.ep-item containers
        episode_items = self.parser.soup.select('a.ssl-item.ep-item')
        
        # Debug logging to see what we're finding
        logger.debug(f"Found {len(episode_items)} episode items with selector 'a.ssl-item.ep-item'")
        
        for i, item in enumerate(episode_items):
            try:
                # Extract episode number from data-number attribute
                ep_num = None
                if item.has_attr('data-number'):
                    data_number = item['data-number']
                    if isinstance(data_number, list):
                        data_number = data_number[0] if data_number else None
                    if data_number and isinstance(data_number, str):
                        try:
                            ep_num = int(data_number)
                        except ValueError:
                            continue
                    else:
                        continue
                else:
                    continue
                
                # Extract episode URL
                ep_url = item.get('href', '')
                if ep_url and isinstance(ep_url, str) and not ep_url.startswith('http'):
                    ep_url = urljoin(self.base_url, ep_url)
                
                # Extract episode title from .ep-name element
                title_elem = item.select_one('.ssli-detail .ep-name')
                if title_elem:
                    ep_title = title_elem.get_text(strip=True)
                else:
                    # Fallback to title attribute
                    ep_title = item.get('title', f"Episode {ep_num}")
                
                # Clean up title - use the title attribute if the text is just Japanese
                title_attr = item.get('title', '')
                if title_attr and title_attr != ep_title:
                    ep_title = title_attr
                
                episode_data = {
                    'number': ep_num,
                    'title': ep_title,
                    'url': ep_url
                }
                
                episodes.append(episode_data)
                
            except Exception as e:
                logger.warning(f"Failed to parse episode item: {e}")
                continue
        
        # Sort episodes by number
        episodes.sort(key=lambda x: x['number'])
        
        return episodes
    
    def extract_video_sources(self) -> List[Dict[str, Any]]:
        """
        Extract video source URLs from episode page.
        
        Returns:
            List of video source dictionaries with quality and URL
        """
        sources = []
        
        # Look for embedded video data in script tags
        scripts = self.parser.soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            # Look for video source patterns
            source_patterns = [
                r'sources?\s*:\s*(\[.*?\])',
                r'file\s*:\s*["\']([^"\']+)["\']',
                r'src\s*:\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in source_patterns:
                matches = re.findall(pattern, script.string, re.DOTALL)
                for match in matches:
                    try:
                        if match.startswith('['):
                            # JSON array of sources
                            source_list = json.loads(match)
                            for source in source_list:
                                if isinstance(source, dict) and 'file' in source:
                                    quality = self._extract_quality_from_source(source)
                                    sources.append({
                                        'url': source['file'],
                                        'quality': quality,
                                        'type': source.get('type', 'mp4')
                                    })
                        else:
                            # Single URL
                            quality = QualityExtractor.extract_from_url(match)
                            if quality:
                                sources.append({
                                    'url': match,
                                    'quality': quality,
                                    'type': 'mp4'
                                })
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        # Remove duplicates and sort by quality
        unique_sources = []
        seen_urls = set()
        
        for source in sources:
            if source['url'] not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(source['url'])
        
        # Sort by quality (highest first)
        unique_sources.sort(key=lambda x: x['quality'].height if x['quality'] else 0, reverse=True)
        
        return unique_sources
    
    def _extract_quality_from_source(self, source: Dict[str, Any]) -> Optional[Quality]:
        """Extract quality from video source object."""
        # Check for explicit quality field
        if 'quality' in source:
            qualities = QualityExtractor.extract_from_text(str(source['quality']))
            return qualities[0] if qualities else None
        
        # Check for label field
        if 'label' in source:
            qualities = QualityExtractor.extract_from_text(str(source['label']))
            if qualities:
                return qualities[0]
        
        # Check URL for quality indicators
        if 'file' in source:
            return QualityExtractor.extract_from_url(source['file'])
        
        return None
    
    def extract_ajax_data(self) -> Dict[str, Any]:
        """
        Extract AJAX endpoint data from page scripts.
        
        Returns:
            Dictionary containing AJAX endpoints and parameters
        """
        ajax_data = {}
        
        scripts = self.parser.soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            # Look for common AJAX patterns
            patterns = {
                'episode_ajax': r'episode[_-]?ajax[_-]?url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                'server_ajax': r'server[_-]?ajax[_-]?url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                'video_ajax': r'video[_-]?ajax[_-]?url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                'anime_id': r'anime[_-]?id["\']?\s*[:=]\s*["\']?(\d+)["\']?',
                'episode_id': r'episode[_-]?id["\']?\s*[:=]\s*["\']?(\d+)["\']?'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, script.string, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    if key.endswith('_id'):
                        try:
                            ajax_data[key] = int(value)
                        except ValueError:
                            ajax_data[key] = value
                    else:
                        # Make URL absolute
                        if not value.startswith('http'):
                            value = urljoin(self.base_url, value)
                        ajax_data[key] = value
        
        return ajax_data


# Export parser class
__all__ = ["HiAnimeParser"]