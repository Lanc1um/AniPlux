"""
Sample Plugin - Example implementation of BasePlugin for testing and development.

This plugin provides a mock implementation of the BasePlugin interface,
useful for testing the plugin system and demonstrating plugin development patterns.
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from aniplux.core.models import AnimeResult, Episode, Quality
from aniplux.core.exceptions import PluginError
from aniplux.plugins.base import BasePlugin, PluginMetadata
from aniplux.plugins.common import create_anime_result, create_episode


logger = logging.getLogger(__name__)


class SamplePlugin(BasePlugin):
    """
    Sample plugin implementation for testing and development.
    
    This plugin provides mock data and demonstrates the proper implementation
    of the BasePlugin interface without requiring external network requests.
    """
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="Sample Source",
            version="1.0.0",
            author="AniPlux Team",
            description="Sample plugin for testing and development",
            website="https://example.com",
            supported_qualities=[Quality.HIGH, Quality.MEDIUM, Quality.LOW],
            rate_limit=0.5,  # Fast rate limit for testing
            requires_auth=False
        )
    
    @property
    def base_url(self) -> str:
        """Get base URL for the sample source."""
        return "https://example.com"
    
    def _get_sample_anime_data(self) -> List[Dict[str, Any]]:
        """Get sample anime data for testing."""
        return [
            {
                "title": "Attack on Titan",
                "url": "/anime/attack-on-titan",
                "episode_count": 25,
                "description": "Humanity fights for survival against giant titans",
                "year": 2013,
                "genres": ["Action", "Drama", "Fantasy"],
                "rating": 9.0,
                "thumbnail": "/images/aot-thumb.jpg"
            },
            {
                "title": "One Piece",
                "url": "/anime/one-piece",
                "episode_count": 1000,
                "description": "A young pirate's adventure to find the legendary treasure",
                "year": 1999,
                "genres": ["Adventure", "Comedy", "Shounen"],
                "rating": 8.8,
                "thumbnail": "/images/op-thumb.jpg"
            },
            {
                "title": "Demon Slayer",
                "url": "/anime/demon-slayer",
                "episode_count": 26,
                "description": "A young boy becomes a demon slayer to save his sister",
                "year": 2019,
                "genres": ["Action", "Supernatural", "Historical"],
                "rating": 8.7,
                "thumbnail": "/images/ds-thumb.jpg"
            },
            {
                "title": "My Hero Academia",
                "url": "/anime/my-hero-academia",
                "episode_count": 138,
                "description": "In a world of superheroes, a quirkless boy dreams of becoming one",
                "year": 2016,
                "genres": ["Action", "School", "Superhero"],
                "rating": 8.5,
                "thumbnail": "/images/mha-thumb.jpg"
            },
            {
                "title": "Naruto",
                "url": "/anime/naruto",
                "episode_count": 720,
                "description": "A young ninja's journey to become the strongest in his village",
                "year": 2002,
                "genres": ["Action", "Martial Arts", "Shounen"],
                "rating": 8.3,
                "thumbnail": "/images/naruto-thumb.jpg"
            }
        ]
    
    def _get_sample_episodes(self, anime_title: str) -> List[Dict[str, Any]]:
        """Get sample episode data for an anime."""
        # Generate different episode counts based on anime
        episode_counts = {
            "Attack on Titan": 25,
            "One Piece": 50,  # Limited for testing
            "Demon Slayer": 26,
            "My Hero Academia": 25,
            "Naruto": 30  # Limited for testing
        }
        
        count = episode_counts.get(anime_title, 12)
        episodes = []
        
        for i in range(1, count + 1):
            episodes.append({
                "number": i,
                "title": f"Episode {i}: The Adventure Continues",
                "url": f"/episode/{anime_title.lower().replace(' ', '-')}-{i}",
                "quality_options": [Quality.HIGH, Quality.MEDIUM, Quality.LOW],
                "duration": "24:00",
                "description": f"Episode {i} of {anime_title}",
                "air_date": datetime(2023, 1, i).isoformat(),
                "filler": i % 10 == 0  # Every 10th episode is filler
            })
        
        return episodes
    
    async def search(self, query: str) -> List[AnimeResult]:
        """
        Search for anime by title.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching anime results
        """
        logger.debug(f"Sample plugin searching for: {query}")
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        if len(query) < 2:
            raise PluginError("Query too short for sample plugin")
        
        # Get sample data and filter by query
        sample_data = self._get_sample_anime_data()
        query_lower = query.lower()
        
        results = []
        for anime_data in sample_data:
            title_lower = anime_data["title"].lower()
            
            # Simple fuzzy matching
            if (query_lower in title_lower or 
                any(word in title_lower for word in query_lower.split())):
                
                # Create AnimeResult with absolute URLs
                result = create_anime_result(
                    title=anime_data["title"],
                    url=f"{self.base_url}{anime_data['url']}",
                    source=self.metadata.name,
                    episode_count=anime_data.get("episode_count"),
                    description=anime_data.get("description"),
                    year=anime_data.get("year"),
                    genres=anime_data.get("genres", []),
                    rating=anime_data.get("rating"),
                    thumbnail=f"{self.base_url}{anime_data['thumbnail']}" if anime_data.get("thumbnail") else None
                )
                
                results.append(result)
        
        logger.debug(f"Sample plugin found {len(results)} results")
        return results
    
    async def get_episodes(self, anime_url: str) -> List[Episode]:
        """
        Get episodes for a specific anime.
        
        Args:
            anime_url: URL to the anime page
            
        Returns:
            List of available episodes
        """
        logger.debug(f"Sample plugin getting episodes for: {anime_url}")
        
        # Simulate network delay
        await asyncio.sleep(0.2)
        
        # Extract anime title from URL for sample data
        anime_title = None
        sample_data = self._get_sample_anime_data()
        
        for anime_data in sample_data:
            if anime_data["url"] in anime_url:
                anime_title = anime_data["title"]
                break
        
        if not anime_title:
            raise PluginError(f"Anime not found for URL: {anime_url}")
        
        # Get sample episode data
        episode_data = self._get_sample_episodes(anime_title)
        
        episodes = []
        for ep_data in episode_data:
            episode = create_episode(
                number=ep_data["number"],
                title=ep_data["title"],
                url=f"{self.base_url}{ep_data['url']}",
                source="sample",
                quality_options=ep_data["quality_options"],
                duration=ep_data.get("duration"),
                description=ep_data.get("description"),
                filler=ep_data.get("filler", False)
            )
            episodes.append(episode)
        
        logger.debug(f"Sample plugin found {len(episodes)} episodes")
        return episodes
    
    async def get_download_url(self, episode_url: str, quality: Quality) -> str:
        """
        Get direct download URL for an episode.
        
        Args:
            episode_url: URL to the episode page
            quality: Requested video quality
            
        Returns:
            Direct download URL
        """
        logger.debug(f"Sample plugin getting download URL for: {episode_url} ({quality})")
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Check if quality is supported
        if quality not in self.metadata.supported_qualities:
            # Fallback to best available quality
            quality = max(self.metadata.supported_qualities, key=lambda q: q.height)
            logger.warning(f"Requested quality not supported, using {quality}")
        
        # Generate mock download URL
        # In a real plugin, this would extract the actual download URL
        episode_id = episode_url.split('/')[-1]
        download_url = f"{self.base_url}/download/{episode_id}/{quality}.mp4"
        
        logger.debug(f"Sample plugin generated download URL: {download_url}")
        return download_url
    
    async def validate_connection(self) -> bool:
        """
        Validate connection to the sample source.
        
        Returns:
            Always True for sample plugin
        """
        logger.debug("Sample plugin validating connection")
        
        # Simulate connection check
        await asyncio.sleep(0.05)
        
        # Sample plugin always has a "good" connection
        return True


# Export the plugin class
__all__ = ["SamplePlugin"]