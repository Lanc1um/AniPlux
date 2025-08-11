"""
Animetsu API Client

This module handles all API interactions with the Animetsu backend.
"""

import logging
from typing import Dict, List, Optional, Any
import aiohttp

from aniplux.core.exceptions import PluginError, NetworkError


logger = logging.getLogger(__name__)


class AnimetsuAPI:
    """Client for interacting with Animetsu API."""
    
    def __init__(self, session: aiohttp.ClientSession, api_base_url: str = "https://backend.animetsu.to/api", site_base_url: str = "https://animetsu.to"):
        """
        Initialize Animetsu API client.
        
        Args:
            session: aiohttp session for making requests
            api_base_url: Base URL for Animetsu API
            site_base_url: Base URL for Animetsu website (for headers)
        """
        self.session = session
        self.base_url = api_base_url
        self.site_base_url = site_base_url
        
        # Default headers for Animetsu API
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": site_base_url,
            "Referer": f"{site_base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/138.0.0.0 Safari/537.36"
        }
    
    async def search_anime(self, query: str, page: int = 1, per_page: int = 35) -> List[Dict[str, Any]]:
        """
        Search for anime on Animetsu.
        
        Args:
            query: Search query string
            page: Page number (default: 1)
            per_page: Results per page (default: 35)
            
        Returns:
            List of anime search results
            
        Raises:
            PluginError: If search fails
        """
        params = {
            "query": query,
            "page": page,
            "perPage": per_page,
            "year": "any",
            "sort": "POPULARITY_DESC",
            "season": "any",
            "format": "any",
            "status": "any"
        }
        
        url = f"{self.base_url}/anime/search"
        
        try:
            
            async with self.session.get(url, headers=self.headers, params=params, timeout=15) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise NetworkError(
                        f"Search request failed with status {response.status}",
                        url=url,
                        status_code=response.status,
                        details=error_text
                    )
                
                data = await response.json()
                results = data.get("results") or data.get("data") or []
                
                logger.debug(f"Found {len(results)} search results for query: '{query}'")
                return results
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error during search: {e}", url=url)
        except Exception as e:
            raise PluginError(f"Search failed for query '{query}': {e}")
    
    async def get_anime_info(self, anime_id: str) -> Dict[str, Any]:
        """
        Get detailed anime information.
        
        Args:
            anime_id: Anime ID
            
        Returns:
            Anime information dictionary
            
        Raises:
            PluginError: If info retrieval fails
        """
        url = f"{self.base_url}/anime/info/{anime_id}"
        
        try:
            
            async with self.session.get(url, headers=self.headers, timeout=15) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise NetworkError(
                        f"Info request failed with status {response.status}",
                        url=url,
                        status_code=response.status,
                        details=error_text
                    )
                
                data = await response.json()
                logger.debug(f"Retrieved info for anime ID: {anime_id}")
                return data
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error getting anime info: {e}", url=url)
        except Exception as e:
            raise PluginError(f"Failed to get anime info for ID '{anime_id}': {e}")
    
    async def get_episodes(self, anime_id: str) -> List[Dict[str, Any]]:
        """
        Get episodes list for an anime.
        
        Args:
            anime_id: Anime ID
            
        Returns:
            List of episode dictionaries
            
        Raises:
            PluginError: If episodes retrieval fails
        """
        url = f"{self.base_url}/anime/eps/{anime_id}"
        
        try:
            
            async with self.session.get(url, headers=self.headers, timeout=15) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise NetworkError(
                        f"Episodes request failed with status {response.status}",
                        url=url,
                        status_code=response.status,
                        details=error_text
                    )
                
                episodes = await response.json()
                logger.debug(f"Retrieved {len(episodes)} episodes for anime ID: {anime_id}")
                return episodes
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error getting episodes: {e}", url=url)
        except Exception as e:
            raise PluginError(f"Failed to get episodes for anime ID '{anime_id}': {e}")
    
    async def get_episode_streams(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """
        Get streaming sources for an episode using multiple endpoint attempts.
        
        Args:
            episode_id: Episode ID
            
        Returns:
            Stream data dictionary or None if not found
            
        Raises:
            PluginError: If stream retrieval fails
        """
        candidate_endpoints = [
            f"{self.base_url}/anime/episode-srcs",
            f"{self.base_url}/anime/sources",
            f"{self.base_url}/anime/episode-sources",
            f"{self.base_url}/episode/sources",
            f"{self.base_url}/episode/srcs",
        ]
        
        param_names = ["id", "animeEpisodeId", "episodeId", "episode_id", "animeEpisode_id"]
        
        # Try query parameter combinations
        for endpoint in candidate_endpoints:
            for param_name in param_names:
                try:
                    params = {param_name: episode_id}
                    
                    async with self.session.get(endpoint, headers=self.headers, params=params, timeout=12) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                if data:  # Check if we got actual data
                                    logger.debug(f"Successfully got streams from {endpoint}?{param_name}={episode_id}")
                                    return data
                            except Exception:
                                # Try as text if JSON parsing fails
                                text_data = await response.text()
                                if text_data and text_data.strip():
                                    logger.debug(f"Got text response from {endpoint}")
                                    return {"raw_response": text_data}
                                
                except Exception as e:
                    logger.debug(f"Failed {endpoint}?{param_name}={episode_id}: {e}")
                    continue
        
        # Try path-style endpoints
        for endpoint in candidate_endpoints:
            endpoint_path = endpoint.rstrip("/") + "/" + str(episode_id)
            try:
                async with self.session.get(endpoint_path, headers=self.headers, timeout=12) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            if data:
                                logger.debug(f"Successfully got streams from {endpoint_path}")
                                return data
                        except Exception:
                            text_data = await response.text()
                            if text_data and text_data.strip():
                                logger.debug(f"Got text response from {endpoint_path}")
                                return {"raw_response": text_data}
                            
            except Exception as e:
                logger.debug(f"Failed {endpoint_path}: {e}")
                continue
        
        logger.warning(f"No stream data found for episode ID: {episode_id}")
        return None
    
    async def get_stream_url(self, anime_id: str, episode_num: int, server: str, subtype: str) -> Optional[Dict[str, Any]]:
        """
        Get streaming URL for a specific episode using the tiddies endpoint.
        
        Args:
            anime_id: Anime ID
            episode_num: Episode number
            server: Server name (e.g., "pahe", "zoro", "zaza", "meg", "bato")
            subtype: Subtitle type (e.g., "sub", "dub")
            
        Returns:
            Stream URL data or None if not found
            
        Raises:
            PluginError: If stream URL retrieval fails
        """
        try:
            url = f"{self.base_url}/anime/tiddies"
            params = {
                "server": server,
                "id": anime_id,
                "num": episode_num,
                "subType": subtype
            }
            
            logger.debug(f"Getting stream URL: {url} with params: {params}")
            
            async with self.session.get(url, headers=self.headers, params=params, timeout=15) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.warning(f"Stream URL request failed with status {response.status}: {error_text}")
                    return None
                
                data = await response.json()
                logger.debug(f"Retrieved stream URL for anime {anime_id}, episode {episode_num}, server {server}")
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error getting stream URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            return None
    
    async def get_servers(self, anime_id: str, episode_num: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get available servers for an episode.
        
        Args:
            anime_id: Anime ID
            episode_num: Episode number
            
        Returns:
            List of available servers or None if not found
        """
        try:
            url = f"{self.base_url}/anime/servers"
            params = {
                "id": anime_id,
                "num": episode_num
            }
            
            async with self.session.get(url, headers=self.headers, params=params, timeout=15) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.warning(f"Servers request failed with status {response.status}: {error_text}")
                    return None
                
                servers = await response.json()
                logger.debug(f"Retrieved {len(servers) if isinstance(servers, list) else 0} servers for anime {anime_id}, episode {episode_num}")
                return servers
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error getting servers: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get servers: {e}")
            return None