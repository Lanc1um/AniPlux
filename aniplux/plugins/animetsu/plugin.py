"""
Animetsu Plugin - Main plugin implementation for animetsu.to

This module implements the main Animetsu plugin class that provides
search, episode listing, and download URL extraction functionality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from aniplux.plugins.base import BasePlugin, PluginMetadata
from aniplux.plugins.common import create_anime_result, create_episode
from aniplux.core.models import AnimeResult, Episode, Quality
from aniplux.core.exceptions import PluginError, NetworkError

from .api import AnimetsuAPI
from .parser import AnimetsuParser
from .downloader import AnimetsuDownloadManager
from .config import AnimetsuConfig, get_default_config, merge_with_defaults, QUALITY_MAP


logger = logging.getLogger(__name__)


# Supported qualities for Animetsu
SUPPORTED_QUALITIES = [Quality.LOW, Quality.MEDIUM, Quality.HIGH]

plugin_metadata = PluginMetadata(
    name="Animetsu",
    version="1.0.0",
    author="AniPlux Team",
    description="Anime source plugin for animetsu.to and animetsu.cc with search, episodes, and download support",
    website="https://animetsu.to",
    supported_qualities=SUPPORTED_QUALITIES,
    rate_limit=1.0,  # 1 second between requests
    requires_auth=False
)


class AnimetsuPlugin(BasePlugin):
    """
    Animetsu plugin for accessing anime content from animetsu.to and animetsu.cc
    
    Provides comprehensive anime search, episode listing, and video
    URL extraction with support for multiple video qualities.
    Both domains are identical and interchangeable.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Animetsu plugin.
        
        Args:
            config: Plugin configuration dictionary
        """
        # Merge with default configuration
        merged_config = merge_with_defaults(config)
        
        super().__init__(merged_config)
        
        # Validate configuration
        try:
            self.plugin_config = AnimetsuConfig(**merged_config)
        except Exception as e:
            logger.warning(f"Invalid configuration, using defaults: {e}")
            self.plugin_config = AnimetsuConfig()
        
        # Initialize API client and parser
        self.api = AnimetsuAPI(
            self.session, 
            api_base_url=self.plugin_config.api_base_url,
            site_base_url=self.plugin_config.base_url
        )
        self.parser = AnimetsuParser(base_url=self.plugin_config.base_url)
        
        # Initialize download manager
        self.download_manager = AnimetsuDownloadManager(
            self.api, 
            self.parser, 
            merged_config
        )
        
        logger.debug("Animetsu plugin initialized successfully")
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return plugin_metadata
    
    @property
    def base_url(self) -> str:
        """Get base URL for Animetsu"""
        return self.plugin_config.base_url
    
    async def search(self, query: str) -> List[AnimeResult]:
        """
        Search for anime on animetsu.to
        
        Args:
            query: Search query string
            
        Returns:
            List of anime search results
            
        Raises:
            PluginError: If search fails
        """
        if not query or not query.strip():
            raise PluginError("Search query cannot be empty")
        
        try:
            clean_query = query.strip()
            logger.debug(f"Searching Animetsu with query: '{clean_query}'")
            
            # Search using API - fetch all available results
            search_data = await self._fetch_all_search_results(clean_query)
            
            if not search_data:
                logger.info(f"No search results found for query: '{clean_query}'")
                return []
            
            # Parse search results
            parsed_results = self.parser.parse_search_results(search_data)
            
            # Convert to AnimeResult objects
            anime_results = []
            for result_data in parsed_results:
                try:
                    result = create_anime_result(
                        title=result_data['title'],
                        url=result_data['url'],
                        source=self.metadata.name.lower() + "_plugin",
                        episode_count=result_data.get('episode_count'),
                        description=result_data.get('description'),
                        thumbnail=result_data.get('thumbnail'),
                        year=result_data.get('year'),
                        genres=result_data.get('genres', []),
                        rating=result_data.get('rating'),
                        status=result_data.get('status')
                    )
                    anime_results.append(result)
                    
                except Exception as e:
                    logger.warning(f"Failed to create AnimeResult: {e}")
                    continue
            
            logger.info(f"Found {len(anime_results)} anime results for query: '{clean_query}' (raw data: {len(search_data)} items)")
            return anime_results
            
        except NetworkError:
            raise
        except Exception as e:
            raise PluginError(f"Search failed for query '{query}': {e}")
    
    async def _fetch_all_search_results(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch all available search results by making multiple API calls if needed.
        
        Args:
            query: Search query string
            
        Returns:
            List of all search results
        """
        logger.debug(f"Starting _fetch_all_search_results for query: '{query}'")
        all_results = []
        page = 1
        per_page = 50  # Use reasonable page size
        max_pages = 10  # Prevent infinite loops
        
        while page <= max_pages:
            try:
                # Get results for current page
                page_results = await self.api.search_anime(
                    query, 
                    page=page, 
                    per_page=per_page
                )
                
                if not page_results:
                    # No more results
                    break
                
                all_results.extend(page_results)
                
                # If we got fewer results than requested, we've reached the end
                if len(page_results) < per_page:
                    break
                
                # Check if we've reached our configured limit
                if len(all_results) >= self.plugin_config.search_limit:
                    all_results = all_results[:self.plugin_config.search_limit]
                    break
                
                page += 1
                
                # Small delay between requests to be respectful
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to fetch page {page} for query '{query}': {e}")
                break
        logger.debug(f"Fetched {len(all_results)} total results across {page-1} pages for query: '{query}'")
        return all_results
    
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
            
            # Extract anime ID from URL
            anime_id = self._extract_anime_id(anime_url)
            if not anime_id:
                raise PluginError("Could not extract anime ID from URL")
            
            logger.debug(f"Extracted anime ID: {anime_id}")
            
            # Get anime info for title
            anime_info = await self.api.get_anime_info(anime_id)
            anime_title = self.parser.extract_anime_title(anime_info)
            
            # Get episodes list
            episodes_data = await self.api.get_episodes(anime_id)
            
            if not episodes_data:
                logger.warning(f"No episodes found for anime: {anime_title}")
                return []
            
            logger.debug(f"Raw episodes data type: {type(episodes_data)}, length: {len(episodes_data) if isinstance(episodes_data, (list, dict)) else 'N/A'}")
            
            # Parse episodes
            parsed_episodes = self.parser.parse_episodes(episodes_data, anime_id)
            
            # Convert to Episode objects
            episodes = []
            for ep_data in parsed_episodes:
                try:
                    episode = create_episode(
                        number=ep_data['number'],
                        title=ep_data['title'],
                        url=ep_data['url'],
                        source=self.metadata.name.lower() + "_plugin",
                        quality_options=SUPPORTED_QUALITIES.copy(),
                        base_url=self.base_url
                    )
                    episodes.append(episode)
                    
                except Exception as e:
                    logger.warning(f"Failed to create Episode: {e}")
                    continue
            
            logger.info(f"Found {len(episodes)} episodes for anime: {anime_title}")
            return episodes
            
        except NetworkError:
            raise
        except Exception as e:
            raise PluginError(f"Failed to get episodes from '{anime_url}': {e}")
    
    def _extract_anime_id(self, anime_url: str) -> Optional[str]:
        """
        Extract anime ID from anime URL.
        
        Args:
            anime_url: Anime URL
            
        Returns:
            Anime ID or None if not found
        """
        import re
        
        if not anime_url:
            logger.warning(f"Empty anime URL: {anime_url}")
            return None
        
        # Convert to string if it's a Pydantic URL object
        anime_url_str = str(anime_url)
        
        # Expected format: https://animetsu.to/anime/{anime_id} or https://animetsu.cc/anime/{anime_id}
        pattern = r'/anime/([^/]+)'
        match = re.search(pattern, anime_url_str)
        
        logger.debug(f"Trying to match pattern '{pattern}' against URL: {anime_url_str}")
        
        if match:
            anime_id = match.group(1)
            logger.debug(f"Extracted anime ID: {anime_id} from URL: {anime_url_str}")
            return anime_id
        
        logger.warning(f"Could not extract anime ID from URL: {anime_url_str}")
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
            
            # Use download manager for URL extraction
            download_url = await self.download_manager.extract_download_url(episode_url, quality)
            
            if not download_url:
                raise PluginError("No download URL found for episode")
            
            logger.info(f"Successfully extracted download URL for quality {quality}")
            return download_url
            
        except NetworkError:
            raise
        except PluginError:
            raise
        except Exception as e:
            raise PluginError(f"Failed to extract download URL from '{episode_url}': {e}")
    
    def get_download_headers(self) -> Dict[str, str]:
        """
        Get headers required for downloading from Animetsu.
        
        Returns:
            Dictionary of headers
        """
        return {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }
    
    async def validate_connection(self) -> bool:
        """
        Validate connection to animetsu.to
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            logger.debug("Validating connection to Animetsu")
            
            # Try to access the API
            test_results = await self.api.search_anime("test", page=1, per_page=1)
            
            # If we get a response (even empty), connection is working
            logger.info("Animetsu connection validation successful")
            return True
                
        except Exception as e:
            logger.error(f"Animetsu connection validation failed: {e}")
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
        preference = self.plugin_config.quality_preference
        return QUALITY_MAP.get(preference, Quality.HIGH)
    
    def can_download_externally(self) -> bool:
        """
        Check if plugin can use external download tools.
        
        Returns:
            True if external tools are available
        """
        return self.download_manager.can_download_with_external_tools()
    
    async def download_episode(self, episode_url: str, output_path: str, quality: Quality) -> bool:
        """
        Download episode using external tools.
        
        Args:
            episode_url: Episode URL
            output_path: Output file path
            quality: Video quality
            
        Returns:
            True if download succeeded
        """
        try:
            # Get download URL
            download_url = await self.get_download_url(episode_url, quality)
            
            # Download using external tools
            return await self.download_manager.download_with_external_tool(download_url, output_path)
            
        except Exception as e:
            logger.error(f"Episode download failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        try:
            # Clean up download manager
            if hasattr(self, 'download_manager'):
                self.download_manager.cleanup()
            
            await super().cleanup()
            logger.debug("Animetsu plugin cleanup completed")
        except Exception as e:
            logger.error(f"Error during Animetsu plugin cleanup: {e}")
    
    def __str__(self) -> str:
        return f"Animetsu Plugin v{self.metadata.version}"
    
    def __repr__(self) -> str:
        return f"AnimetsuPlugin(base_url='{self.base_url}', enabled={self.plugin_config.enabled})"
    
    @staticmethod
    def convert_url_domain(url: str, target_domain: str = "animetsu.to") -> str:
        """
        Convert Animetsu URL between domains (.to and .cc).
        
        Args:
            url: Original URL
            target_domain: Target domain (animetsu.to or animetsu.cc)
            
        Returns:
            URL with converted domain
        """
        import re
        
        if not url:
            return url
        
        # Replace animetsu.to or animetsu.cc with target domain
        converted_url = re.sub(r'animetsu\.(to|cc)', f'animetsu.{target_domain.split(".")[-1]}', url)
        return converted_url
    
    @staticmethod
    def get_supported_domains() -> List[str]:
        """
        Get list of supported Animetsu domains.
        
        Returns:
            List of supported domain names
        """
        return ["animetsu.to", "animetsu.cc"]


# Export plugin class and metadata
default_config = get_default_config()
__all__ = ["AnimetsuPlugin", "plugin_metadata", "default_config", "SUPPORTED_QUALITIES"]