"""
Base Plugin Interface - Abstract base class for anime source plugins.

This module defines the interface that all anime source plugins must implement,
providing a consistent API for searching, episode fetching, and download URL generation.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import aiohttp
from pydantic import BaseModel, Field

from aniplux.core.models import AnimeResult, Episode, Quality
from aniplux.core.exceptions import PluginError, NetworkError


logger = logging.getLogger(__name__)


class PluginMetadata(BaseModel):
    """Metadata information for a plugin."""
    
    name: str = Field(..., description="Plugin display name")
    version: str = Field(default="1.0.0", description="Plugin version")
    author: str = Field(default="Unknown", description="Plugin author")
    description: str = Field(default="", description="Plugin description")
    website: Optional[str] = Field(None, description="Source website URL")
    supported_qualities: List[Quality] = Field(
        default_factory=lambda: [Quality.HIGH, Quality.MEDIUM, Quality.LOW],
        description="Supported video qualities"
    )
    rate_limit: float = Field(default=1.0, description="Minimum seconds between requests")
    requires_auth: bool = Field(default=False, description="Whether plugin requires authentication")


class BasePlugin(ABC):
    """
    Abstract base class for anime source plugins.
    
    All source plugins must inherit from this class and implement the required
    abstract methods to provide search, episode listing, and download functionality.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin with configuration.
        
        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0.0
        
        # Set up logging for this plugin
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize plugin-specific settings
        self._initialize_config()
    
    def _initialize_config(self) -> None:
        """Initialize plugin configuration with defaults."""
        # Set default values if not provided
        self.timeout = self.config.get('timeout', 30)
        self.user_agent = self.config.get(
            'user_agent', 
            'AniPlux/0.1.0 (https://github.com/Yui007/AniPlux)'
        )
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1.0)
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata information."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Get the base URL for the anime source."""
        pass
    
    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with proper configuration."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
        
        return self._session
    
    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        import time
        
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.metadata.rate_limit:
            sleep_time = self.metadata.rate_limit - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    async def _make_request(
        self, 
        url: str, 
        method: str = 'GET',
        **kwargs
    ) -> int:
        """
        Make an HTTP request with rate limiting and error handling.
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional arguments for the request
            
        Returns:
            HTTP status code
            
        Raises:
            NetworkError: If request fails after retries
        """
        await self._rate_limit()
        
        # Ensure URL is absolute
        if not urlparse(url).netloc:
            url = urljoin(self.base_url, url)
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                async with self.session.request(method, url, **kwargs) as response:
                    # Check for HTTP errors
                    if response.status >= 400:
                        error_text = await response.text()
                        raise NetworkError(
                            f"HTTP {response.status} error for {url}",
                            url=url,
                            status_code=response.status,
                            details=error_text
                        )
                    
                    # Read the response to ensure connection is properly closed
                    await response.read()
                    return response.status
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    break
        
        # All retries failed
        raise NetworkError(
            f"Request failed after {self.max_retries + 1} attempts: {last_exception}",
            url=url,
            details=str(last_exception)
        )
    
    async def _get_text(self, url: str, **kwargs) -> str:
        """Get text content from URL."""
        await self._rate_limit()
        
        # Ensure URL is absolute
        if not urlparse(url).netloc:
            url = urljoin(self.base_url, url)
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making GET request to {url} (attempt {attempt + 1})")
                
                async with self.session.get(url, **kwargs) as response:
                    # Check for HTTP errors
                    if response.status >= 400:
                        error_text = await response.text()
                        raise NetworkError(
                            f"HTTP {response.status} error for {url}",
                            url=url,
                            status_code=response.status,
                            details=error_text
                        )
                    
                    return await response.text()
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    break
        
        # All retries failed
        raise NetworkError(
            f"Request failed after {self.max_retries + 1} attempts: {last_exception}",
            url=url,
            details=str(last_exception)
        )
    
    async def _get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """Get JSON content from URL."""
        await self._rate_limit()
        
        # Ensure URL is absolute
        if not urlparse(url).netloc:
            url = urljoin(self.base_url, url)
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making GET request to {url} (attempt {attempt + 1})")
                
                async with self.session.get(url, **kwargs) as response:
                    # Check for HTTP errors
                    if response.status >= 400:
                        error_text = await response.text()
                        raise NetworkError(
                            f"HTTP {response.status} error for {url}",
                            url=url,
                            status_code=response.status,
                            details=error_text
                        )
                    
                    return await response.json()
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    break
        
        # All retries failed
        raise NetworkError(
            f"Request failed after {self.max_retries + 1} attempts: {last_exception}",
            url=url,
            details=str(last_exception)
        )
    
    @abstractmethod
    async def search(self, query: str) -> List[AnimeResult]:
        """
        Search for anime by title.
        
        Args:
            query: Search query string
            
        Returns:
            List of anime search results
            
        Raises:
            PluginError: If search fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    async def validate_connection(self) -> bool:
        """
        Validate that the plugin can connect to its source.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            status = await self._make_request(self.base_url)
            return status == 200
        except Exception as e:
            self.logger.error(f"Connection validation failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        if self._session and not self._session.closed:
            try:
                await self._session.close()
                self.logger.debug("HTTP session closed")
            except Exception as e:
                self.logger.debug(f"Error closing HTTP session: {e}")
        self._session = None
    
    def __str__(self) -> str:
        return f"{self.metadata.name} v{self.metadata.version}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.metadata.name}')"


# Export base plugin class and metadata
__all__ = ["BasePlugin", "PluginMetadata"]