"""
HiAnime Extractor - Basic HTTP-based video URL extraction for hianime.to

This module provides basic HTTP-based video URL extraction from hianime.to
episode pages. For more robust extraction, use the HiAnimeDownloadManager
which includes Selenium fallback capabilities.
"""

import re
import logging
from typing import Dict, List, Optional, Any

from aniplux.plugins.common import QualityExtractor
from aniplux.core.models import Quality
from aniplux.core.exceptions import PluginError, NetworkError


logger = logging.getLogger(__name__)


class HiAnimeExtractor:
    """Basic HTTP-based video URL extractor for hianime.to episodes."""
    
    def __init__(self, session, base_url: str = "https://hianime.to"):
        """
        Initialize HiAnime extractor.
        
        Args:
            session: HTTP session for making requests
            base_url: Base URL for the site
        """
        self.session = session
        self.base_url = base_url
    
    async def extract_video_url(self, episode_url: str, quality: Quality) -> str:
        """
        Extract direct video URL for an episode using basic HTTP methods.
        
        This method attempts basic HTTP-based extraction. For more robust
        extraction with JavaScript support, use HiAnimeDownloadManager.
        
        Args:
            episode_url: URL to the episode page
            quality: Requested video quality
            
        Returns:
            Direct video URL
            
        Raises:
            PluginError: If video URL extraction fails
        """
        try:
            # Extract episode ID from URL
            episode_id = self._extract_episode_id(episode_url)
            if not episode_id:
                raise PluginError("Could not extract episode ID from URL")
            
            logger.debug(f"Extracted episode ID: {episode_id}")
            
            # Get server list for episode
            servers = await self._get_episode_servers(episode_id)
            if not servers:
                raise PluginError("No servers found for episode")
            
            logger.debug(f"Found {len(servers)} servers")
            
            # Try each server to get video sources
            all_sources = []
            for server_id in servers:
                try:
                    sources = await self._get_server_sources(server_id)
                    if sources:
                        all_sources.extend(sources)
                        logger.debug(f"Server {server_id} provided {len(sources)} sources")
                except Exception as e:
                    logger.debug(f"Server {server_id} failed: {e}")
                    continue
            
            if not all_sources:
                # If no sources found, suggest using the download manager
                raise PluginError(
                    "HTTP-based video extraction failed. This is likely due to:\n\n"
                    "1. HiAnime uses encrypted video sources that require decryption\n"
                    "2. JavaScript-based video loading\n"
                    "3. Anti-bot measures or geographic restrictions\n\n"
                    "The HiAnimeDownloadManager will automatically fall back to\n"
                    "Selenium-based extraction for better success rates."
                )
            
            # Find best matching quality
            best_source = self._select_best_quality(all_sources, quality)
            
            if best_source:
                logger.info(f"Selected source: {best_source['method']} - {best_source['quality']}")
                return best_source['url']
            elif all_sources:
                # Fallback to first available source
                logger.warning(f"Requested quality {quality} not found, using first available")
                first_source = all_sources[0]
                logger.info(f"Using fallback source: {first_source['method']} - {first_source.get('quality', 'unknown')}")
                return first_source['url']
            
            raise PluginError("No suitable video sources found")
            
        except Exception as e:
            if isinstance(e, PluginError):
                raise
            raise PluginError(f"HTTP video extraction failed: {e}")
    
    def _extract_episode_id(self, episode_url: str) -> Optional[str]:
        """Extract episode ID from episode URL."""
        match = re.search(r'ep=(\d+)', episode_url)
        return match.group(1) if match else None
    
    async def _get_episode_servers(self, episode_id: str) -> List[str]:
        """Get list of server IDs for an episode."""
        servers_url = f"{self.base_url}/ajax/v2/episode/servers"
        params = {'episodeId': episode_id}
        
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.base_url
        }
        
        try:
            async with self.session.get(servers_url, params=params, headers=headers) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                if not data.get('status') or 'html' not in data:
                    return []
                
                # Parse server IDs from HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(data['html'], 'html.parser')
                
                server_elements = soup.select('.server-item[data-id]')
                server_ids = []
                
                for elem in server_elements:
                    server_id = elem.get('data-id')
                    if server_id:
                        server_ids.append(server_id)
                
                return server_ids
                
        except Exception as e:
            logger.debug(f"Failed to get servers: {e}")
            return []
    
    async def _get_server_sources(self, server_id: str) -> List[Dict[str, Any]]:
        """Get video sources from a specific server using basic HTTP methods."""
        sources_url = f"{self.base_url}/ajax/v2/episode/sources"
        params = {'id': server_id}
        
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.base_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            async with self.session.get(sources_url, params=params, headers=headers) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                # Check if we got direct sources (rare but possible)
                if data.get('sources') and len(data['sources']) > 0:
                    sources = []
                    for source in data['sources']:
                        if isinstance(source, dict) and 'file' in source:
                            quality = self._extract_quality_from_source(source)
                            sources.append({
                                'url': source['file'],
                                'quality': quality or Quality.MEDIUM,
                                'type': source.get('type', 'mp4'),
                                'method': 'direct_http'
                            })
                    return sources
                
                # For iframe sources, we can't extract with basic HTTP
                # This will be handled by the Selenium downloader
                elif data.get('type') == 'iframe' and data.get('link'):
                    logger.debug(f"Found iframe source, requires Selenium extraction: {data['link']}")
                    return []
                
                return []
                
        except Exception as e:
            logger.debug(f"Failed to get sources from server {server_id}: {e}")
            return []
    
    def _extract_quality_from_source(self, source: Dict[str, Any]) -> Optional[Quality]:
        """Extract quality from video source object."""
        # Check for explicit quality fields
        quality_fields = ['quality', 'label', 'res', 'resolution']
        
        for field in quality_fields:
            if field in source:
                qualities = QualityExtractor.extract_from_text(str(source[field]))
                if qualities:
                    return qualities[0]
        
        # Check URL for quality indicators
        if 'file' in source:
            return QualityExtractor.extract_from_url(source['file'])
        
        return None
    
    def _select_best_quality(self, sources: List[Dict[str, Any]], requested_quality: Quality) -> Optional[Dict[str, Any]]:
        """Select the best matching quality from available sources."""
        if not sources:
            return None
        
        # First, try to find exact match
        for source in sources:
            if source.get('quality') == requested_quality:
                return source
        
        # If no exact match, find closest quality
        quality_scores = []
        for source in sources:
            source_quality = source.get('quality')
            if source_quality:
                # Calculate quality score (prefer higher quality)
                score = abs(source_quality.height - requested_quality.height)
                quality_scores.append((score, source))
        
        if quality_scores:
            # Sort by score (lower is better) and return best match
            quality_scores.sort(key=lambda x: x[0])
            return quality_scores[0][1]
        
        # Fallback to first available source
        return sources[0]


# Export extractor class
__all__ = ["HiAnimeExtractor"]