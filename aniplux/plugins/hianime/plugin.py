"""
HiAnime Plugin - Main plugin implementation for hianime.to

This module implements the main HiAnime plugin class that provides
search with pagination support, episode listing, and download URL extraction functionality.
"""

import logging
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus

from aniplux.plugins.base import BasePlugin, PluginMetadata
from aniplux.plugins.common import create_anime_result, create_episode
from aniplux.core.models import AnimeResult, Episode, Quality
from aniplux.core.exceptions import PluginError, NetworkError

from .parser import HiAnimeParser
from .extractor import HiAnimeExtractor
from .downloader import HiAnimeDownloadManager
from .selenium_config import SeleniumConfigHelper


logger = logging.getLogger(__name__)


# Plugin configuration
SUPPORTED_QUALITIES = [Quality.LOW, Quality.MEDIUM, Quality.HIGH, Quality.ULTRA]

plugin_metadata = PluginMetadata(
    name="HiAnime",
    version="1.0.0",
    author="AniPlux Team",
    description="Anime source plugin for hianime.to with search, episodes, and download support",
    website="https://hianime.to",
    supported_qualities=SUPPORTED_QUALITIES,
    rate_limit=1.5,  # 1.5 seconds between requests
    requires_auth=False
)

default_config = {
    "enabled": True,
    "priority": 1,
    "timeout": 30,
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "search_limit": 200,  # Increased to support pagination (was 50)
    "max_search_pages": 20,  # Maximum pages to fetch during search
    "quality_preference": "high",
    # Selenium-specific settings
    "selenium_headless": True,
    "selenium_timeout": 30,
    "selenium_max_attempts": 60,
    "adblock_extension_path": None,  # Path to unpacked AdBlock extension
    "mobile_emulation": True,
    "popup_blocking": True
}


class HiAnimePlugin(BasePlugin):
    """
    HiAnime plugin for accessing anime content from hianime.to
    
    Provides comprehensive anime search, episode listing, and video
    URL extraction with support for multiple video qualities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize HiAnime plugin.
        
        Args:
            config: Plugin configuration dictionary
        """
        # Merge default config with provided config
        merged_config = {**default_config}
        if config:
            merged_config.update(config)
        
        super().__init__(merged_config)
        
        # Initialize extractor and download manager
        self.extractor = HiAnimeExtractor(self.session, self.base_url)
        
        # Configure Selenium downloader settings using helper
        selenium_config = SeleniumConfigHelper.validate_config({
            "headless": merged_config.get("selenium_headless", True),
            "timeout": merged_config.get("selenium_timeout", 30),
            "max_attempts": merged_config.get("selenium_max_attempts", 60),
            "adblock_extension_path": merged_config.get("adblock_extension_path"),
            "mobile_emulation": merged_config.get("mobile_emulation", True),
            "popup_blocking": merged_config.get("popup_blocking", True),
            "disable_images": merged_config.get("disable_images", False),
            "window_size": merged_config.get("window_size", "1920,1080"),
            "user_data_dir": merged_config.get("user_data_dir")
        })
        
        self.download_manager = HiAnimeDownloadManager(self.extractor, selenium_config)
        

    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return plugin_metadata
    
    @property
    def base_url(self) -> str:
        """Get base URL for hianime.to"""
        return "https://hianime.to"
    
    async def search(self, query: str) -> List[AnimeResult]:
        """
        Search for anime on hianime.to with pagination support
        
        Args:
            query: Search query string
            
        Returns:
            List of anime search results from all pages
            
        Raises:
            PluginError: If search fails
        """
        if not query or not query.strip():
            raise PluginError("Search query cannot be empty")
        
        try:
            # Clean and encode query
            clean_query = query.strip()
            encoded_query = quote_plus(clean_query)
            
            logger.debug(f"Searching HiAnime with query: '{clean_query}' (with pagination)")
            
            all_results: List[AnimeResult] = []
            page = 1
            search_limit = self.config.get('search_limit', 200)  # Increased default limit
            
            while len(all_results) < search_limit:
                # Build search URL with page parameter
                search_url = f"{self.base_url}/search?keyword={encoded_query}&page={page}"
                
                logger.debug(f"Fetching page {page}: {search_url}")
                
                # Fetch search results page
                html_content = await self._get_text(search_url)
                
                # Parse search results
                parser = HiAnimeParser(html_content, self.base_url)
                search_data = parser.parse_search_results()
                
                # If no results found on this page, we've reached the end
                if not search_data:
                    logger.debug(f"No results found on page {page}, stopping pagination")
                    break
                
                logger.debug(f"Found {len(search_data)} results on page {page}")
                
                # Convert to AnimeResult objects
                page_results = []
                for item_data in search_data:
                    try:
                        result = create_anime_result(
                            title=item_data['title'],
                            url=item_data['url'],
                            source=self.metadata.name.lower() + "_plugin",
                            episode_count=item_data.get('episode_count'),
                            description=item_data.get('description'),
                            thumbnail=item_data.get('thumbnail'),
                            year=item_data.get('year'),
                            genres=item_data.get('genres', []),
                            rating=item_data.get('rating'),
                            status=item_data.get('status')
                        )
                        page_results.append(result)
                        
                    except Exception as e:
                        logger.warning(f"Failed to create AnimeResult from data: {e}")
                        continue
                
                # Add page results to total results
                all_results.extend(page_results)
                
                # If we got fewer results than expected (typically 36 per page),
                # this might be the last page
                if len(search_data) < 36:
                    logger.debug(f"Page {page} returned {len(search_data)} results (< 36), likely last page")
                    break
                
                # Move to next page
                page += 1
                
                # Safety check to prevent infinite loops
                max_pages = self.config.get('max_search_pages', 20)
                if page > max_pages:
                    logger.warning(f"Reached maximum page limit ({max_pages}), stopping search")
                    break
            
            # Apply search limit to final results
            if len(all_results) > search_limit:
                all_results = all_results[:search_limit]
            
            if not all_results:
                logger.info(f"No search results found for query: '{clean_query}'")
                return []
            
            logger.info(f"Found {len(all_results)} total anime results for query: '{clean_query}' across {page} pages")
            return all_results
            
        except NetworkError:
            raise
        except Exception as e:
            raise PluginError(f"Search failed for query '{query}': {e}")
    
    async def get_episodes(self, anime_url: str) -> List[Episode]:
        """
        Get episodes for a specific anime.
        
        Args:
            anime_url: URL to the anime page
            
        Returns:
            List of available episodes
            
        Raises:
            PluginError: If episode fetching fails
        """
        if not anime_url:
            raise PluginError("Anime URL cannot be empty")
        
        try:
            logger.debug(f"Fetching episodes from: {anime_url}")
            
            # Fetch anime page
            html_content = await self._get_text(anime_url)
            
            # Parse anime details and extract anime ID
            parser = HiAnimeParser(html_content, self.base_url)
            
            # Get anime details for context
            anime_details = parser.parse_anime_details()
            anime_title = anime_details.get('title', 'Unknown Anime')
            
            # Extract anime ID from the page
            anime_id = self._extract_anime_id(html_content)
            if not anime_id:
                raise PluginError("Could not extract anime ID from page")
            
            logger.debug(f"Extracted anime ID: {anime_id}")
            
            # Fetch episodes via AJAX
            ajax_url = f"{self.base_url}/ajax/v2/episode/list/{anime_id}"
            ajax_response = await self._get_json(ajax_url)
            
            if not ajax_response.get('status') or 'html' not in ajax_response:
                raise PluginError("Invalid AJAX response for episodes")
            
            # Parse episodes from AJAX HTML
            episodes_html = ajax_response['html']
            episodes_parser = HiAnimeParser(episodes_html, self.base_url)
            episodes_data = episodes_parser.parse_episodes_list()
            
            if not episodes_data:
                logger.warning(f"No episodes found for anime: {anime_title}")
                return []
            
            # Convert to Episode objects
            episodes = []
            
            for ep_data in episodes_data:
                try:
                    # All episodes support the same qualities (determined at extraction time)
                    quality_options = SUPPORTED_QUALITIES.copy()
                    
                    episode = create_episode(
                        number=ep_data['number'],
                        title=ep_data['title'],
                        url=ep_data['url'],
                        source=self.metadata.name.lower() + "_plugin",
                        quality_options=quality_options,
                        base_url=self.base_url
                    )
                    
                    episodes.append(episode)
                    
                except Exception as e:
                    logger.warning(f"Failed to create Episode from data: {e}")
                    continue
            
            logger.info(f"Found {len(episodes)} episodes for anime: {anime_title}")
            return episodes
            
        except NetworkError:
            raise
        except Exception as e:
            raise PluginError(f"Failed to get episodes from '{anime_url}': {e}")
    
    def _extract_anime_id(self, html_content: str) -> Optional[str]:
        """
        Extract anime ID from the HTML content.
        
        Args:
            html_content: HTML content of the anime page
            
        Returns:
            Anime ID string or None if not found
        """
        import re
        import json
        
        # Look for anime_id in script tags
        script_patterns = [
            r'"anime_id"\s*:\s*"(\d+)"',
            r'"anime_id"\s*:\s*(\d+)',
            r'anime_id["\']?\s*[:=]\s*["\']?(\d+)["\']?'
        ]
        
        for pattern in script_patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
        
        # Look for data-id attribute on elements
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check for elements with data-id that might be the anime ID
        data_id_elements = soup.select('[data-id]')
        for elem in data_id_elements:
            data_id = elem.get('data-id')
            if data_id and isinstance(data_id, str) and data_id.isdigit() and len(data_id) >= 4:
                # This is likely the anime ID
                return data_id
        
        return None
    
    async def get_download_url(self, episode_url: str, quality: Quality) -> str:
        """
        Get direct download URL for an episode.
        
        Args:
            episode_url: URL to the episode page
            quality: Requested video quality
            
        Returns:
            Direct download URL
            
        Raises:
            PluginError: If download URL extraction fails
        """
        if not episode_url:
            raise PluginError("Episode URL cannot be empty")
        
        if quality not in SUPPORTED_QUALITIES:
            logger.warning(f"Quality {quality} not officially supported, attempting anyway")
        
        try:
            logger.debug(f"Extracting download URL from: {episode_url} (quality: {quality})")
            
            # Use download manager for robust extraction (HTTP + Selenium fallback)
            video_url = await self.download_manager.extract_video_url(episode_url, quality)
            
            if not video_url:
                raise PluginError("No video URL found for episode")
            
            logger.info(f"Successfully extracted video URL for quality {quality}")
            return video_url
            
        except NetworkError:
            raise
        except PluginError:
            # Re-raise PluginError with additional context
            raise
        except Exception as e:
            raise PluginError(f"Failed to extract download URL from '{episode_url}': {e}")
    
    async def validate_connection(self) -> bool:
        """
        Validate connection to hianime.to
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            logger.debug("Validating connection to HiAnime")
            
            # Try to access the main page
            status = await self._make_request(self.base_url)
            
            if status == 200:
                # Check if we can access search (basic functionality test)
                search_url = f"{self.base_url}/search?keyword=test"
                search_status = await self._make_request(search_url)
                
                if search_status == 200:
                    logger.info("HiAnime connection validation successful")
                    return True
                else:
                    logger.warning(f"HiAnime search endpoint returned status {search_status}")
                    return False
            else:
                logger.warning(f"HiAnime main page returned status {status}")
                return False
                
        except Exception as e:
            logger.error(f"HiAnime connection validation failed: {e}")
            return False
    
    def get_supported_qualities(self) -> List[Quality]:
        """
        Get list of supported video qualities.
        
        Returns:
            List of supported Quality enums
        """
        return SUPPORTED_QUALITIES.copy()
    
    def get_quality_preference(self) -> Quality:
        """
        Get preferred quality based on configuration.
        
        Returns:
            Preferred Quality enum
        """
        preference = self.config.get('quality_preference', 'high').lower()
        
        quality_map = {
            'low': Quality.LOW,
            'medium': Quality.MEDIUM,
            'high': Quality.HIGH,
            'ultra': Quality.ULTRA,
            '4k': Quality.FOUR_K
        }
        
        return quality_map.get(preference, Quality.HIGH)
    
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        try:
            # Clean up download manager (includes Selenium driver)
            if hasattr(self, 'download_manager'):
                self.download_manager.cleanup()
            
            await super().cleanup()
            logger.debug("HiAnime plugin cleanup completed")
        except Exception as e:
            logger.error(f"Error during HiAnime plugin cleanup: {e}")
    
    def __str__(self) -> str:
        return f"HiAnime Plugin v{self.metadata.version}"
    
    def __repr__(self) -> str:
        return f"HiAnimePlugin(base_url='{self.base_url}', enabled={self.config.get('enabled', True)})"


# Export plugin class and metadata
__all__ = ["HiAnimePlugin", "plugin_metadata", "default_config", "SUPPORTED_QUALITIES"]