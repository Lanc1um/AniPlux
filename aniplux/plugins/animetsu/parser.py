"""
Animetsu Data Parser

This module handles parsing and processing of data from Animetsu API responses.
"""

import logging
from typing import Dict, List, Optional, Any
import re

from aniplux.core.models import Quality
from .config import get_quality_from_string


logger = logging.getLogger(__name__)


class AnimetsuParser:
    """Parser for Animetsu API responses."""
    
    def __init__(self, base_url: str = "https://animetsu.to"):
        """
        Initialize parser.
        
        Args:
            base_url: Base URL for constructing full URLs
        """
        self.base_url = base_url
    
    def parse_search_results(self, search_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse search results from Animetsu API.
        
        Args:
            search_data: Raw search results from API
            
        Returns:
            List of parsed anime data
        """
        parsed_results = []
        
        for anime in search_data:
            try:
                # Extract basic info
                anime_id = str(anime.get("id", ""))
                title_data = anime.get("title", {})
                
                # Handle different title formats
                if isinstance(title_data, dict):
                    title = (title_data.get("english") or 
                            title_data.get("romaji") or 
                            title_data.get("native") or
                            "Unknown Title")
                else:
                    title = str(title_data) if title_data else "Unknown Title"
                
                # Construct anime URL
                anime_url = f"{self.base_url}/anime/{anime_id}"
                
                # Extract additional metadata
                description = anime.get("description", "")
                if description and len(description) > 200:
                    description = description[:200] + "..."
                
                # Parse genres
                genres = []
                if "genres" in anime and isinstance(anime["genres"], list):
                    genres = [genre.get("name", "") for genre in anime["genres"] if isinstance(genre, dict)]
                
                # Extract other fields
                episode_count = anime.get("episodes") or anime.get("totalEpisodes")
                year = anime.get("releaseDate") or anime.get("startDate", {}).get("year")
                status = anime.get("status", "").replace("_", " ").title()
                rating = anime.get("averageScore")
                
                # Handle cover image
                cover_image = anime.get("coverImage", {})
                thumbnail = None
                if isinstance(cover_image, dict):
                    thumbnail = (cover_image.get("large") or 
                               cover_image.get("medium") or 
                               cover_image.get("small"))
                elif isinstance(cover_image, str):
                    thumbnail = cover_image
                
                parsed_anime = {
                    "id": anime_id,
                    "title": title,
                    "url": anime_url,
                    "description": description,
                    "thumbnail": thumbnail,
                    "episode_count": episode_count,
                    "year": year,
                    "genres": genres,
                    "rating": rating,
                    "status": status
                }
                
                parsed_results.append(parsed_anime)
                
            except Exception as e:
                logger.warning(f"Failed to parse anime data: {e}")
                continue
        
        logger.debug(f"Parsed {len(parsed_results)} anime results")
        return parsed_results
    
    def parse_episodes(self, episodes_data: List[Dict[str, Any]], anime_id: str) -> List[Dict[str, Any]]:
        """
        Parse episodes data from Animetsu API.
        
        Args:
            episodes_data: Raw episodes data from API
            anime_id: Anime ID for constructing URLs
            
        Returns:
            List of parsed episode data
        """
        parsed_episodes = []
        
        # Ensure episodes_data is a list
        if not isinstance(episodes_data, list):
            logger.warning(f"Expected list for episodes_data, got {type(episodes_data)}")
            return parsed_episodes
        
        for episode in episodes_data:
            try:
                if not isinstance(episode, dict):
                    logger.warning(f"Expected dict for episode, got {type(episode)}")
                    continue
                
                # Extract episode ID and number
                episode_id = (episode.get("id") or 
                             episode.get("_id") or 
                             episode.get("episodeId") or 
                             episode.get("animeEpisodeId"))
                
                episode_number = (episode.get("number") or 
                                episode.get("episode") or 
                                episode.get("ep") or 
                                episode.get("episodeNumber"))
                
                # Ensure episode_number is valid
                if episode_number is None:
                    logger.warning(f"No episode number found in episode data: {episode}")
                    continue
                
                # Convert to int if it's a string
                try:
                    episode_number = int(episode_number)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid episode number: {episode_number}")
                    continue
                
                # Extract title
                episode_title = (episode.get("title") or 
                               episode.get("name"))
                
                # Skip episodes without proper titles (likely invalid/non-existent)
                if not episode_title or not episode_title.strip():
                    logger.debug(f"Skipping episode {episode_number} - no title found")
                    continue
                
                # Clean the title
                episode_title = episode_title.strip()
                
                # Skip episodes with generic/empty titles that indicate invalid data
                if (episode_title.lower() in ['', 'null', 'none', 'undefined'] or
                    episode_title == str(episode_number) or
                    episode_title.lower() == f"episode {episode_number}".lower()):
                    logger.debug(f"Skipping episode {episode_number} - generic/invalid title: '{episode_title}'")
                    continue
                
                # Ensure anime_id is a string
                if not isinstance(anime_id, str):
                    anime_id = str(anime_id)
                
                # Construct episode URL
                episode_url = f"{self.base_url}/watch/{anime_id}/{episode_number}"
                
                # Extract additional metadata
                duration = episode.get("duration")
                air_date = episode.get("airDate") or episode.get("airedAt")
                
                parsed_episode = {
                    "id": str(episode_id) if episode_id else "",
                    "number": episode_number,
                    "title": str(episode_title),
                    "url": episode_url,
                    "duration": duration,
                    "air_date": air_date
                }
                
                parsed_episodes.append(parsed_episode)
                
            except Exception as e:
                logger.warning(f"Failed to parse episode data: {e}")
                logger.debug(f"Episode data that failed: {episode}")
                continue
        
        # Sort episodes by number
        parsed_episodes.sort(key=lambda x: x.get("number", 0))
        
        logger.debug(f"Parsed {len(parsed_episodes)} episodes")
        return parsed_episodes
    
    def parse_stream_sources(self, stream_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse streaming sources from API response.
        
        Args:
            stream_data: Raw stream data from API
            
        Returns:
            List of parsed stream sources
        """
        sources = []
        
        try:
            # Handle different response formats
            if "sources" in stream_data:
                raw_sources = stream_data["sources"]
            elif isinstance(stream_data, list):
                raw_sources = stream_data
            else:
                logger.warning("Unexpected stream data format")
                return sources
            
            for source in raw_sources:
                try:
                    if not isinstance(source, dict):
                        continue
                    
                    url = source.get("url") or source.get("file")
                    quality = source.get("quality") or source.get("label", "1080p")
                    
                    if not url:
                        continue
                    
                    # Normalize quality string
                    quality = self._normalize_quality(quality)
                    
                    parsed_source = {
                        "url": url,
                        "quality": quality,
                        "type": source.get("type", "mp4"),
                        "server": source.get("server", "default")
                    }
                    
                    sources.append(parsed_source)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse stream source: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse stream sources: {e}")
        
        logger.debug(f"Parsed {len(sources)} stream sources")
        return sources
    
    def _normalize_quality(self, quality_str: str) -> str:
        """
        Normalize quality string to standard format.
        
        Args:
            quality_str: Raw quality string
            
        Returns:
            Normalized quality string
        """
        if not quality_str:
            return "1080p"
        
        # Extract numbers from quality string
        quality_lower = str(quality_str).lower()
        
        # Map common quality indicators
        if "480" in quality_lower or "sd" in quality_lower:
            return "480p"
        elif "720" in quality_lower or "hd" in quality_lower:
            return "720p"
        elif "1080" in quality_lower or "fhd" in quality_lower or "full" in quality_lower:
            return "1080p"
        else:
            # Default to 1080p for unknown qualities
            return "1080p"
    
    def extract_anime_title(self, anime_info: Dict[str, Any]) -> str:
        """
        Extract clean anime title from info data.
        
        Args:
            anime_info: Anime information dictionary
            
        Returns:
            Clean anime title
        """
        title_data = anime_info.get("title", {})
        
        if isinstance(title_data, dict):
            title = (title_data.get("english") or 
                    title_data.get("romaji") or 
                    title_data.get("native") or
                    "Unknown Anime")
        else:
            title = str(title_data) if title_data else "Unknown Anime"
        
        # Clean title for filename use
        title = re.sub(r'[<>:"/\\|?*]', '', title)  # Remove invalid filename characters
        title = re.sub(r'\s+', ' ', title).strip()  # Normalize whitespace
        
        return title
    
    def is_m3u8_url(self, url: str) -> bool:
        """
        Check if URL is an M3U8 playlist or HLS stream.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be M3U8/HLS
        """
        if not url:
            return False
        
        url_lower = url.lower()
        return (".m3u8" in url_lower or 
                ".m3u" in url_lower or 
                "playlist" in url_lower or
                "master.m3u8" in url_lower or
                "tiddies.animetsu" in url_lower or
                "animetsu.cc" in url_lower or
                "animetsu.to" in url_lower)
    
    def extract_quality_from_url(self, url: str) -> str:
        """
        Try to extract quality information from URL.
        
        Args:
            url: Stream URL
            
        Returns:
            Quality string
        """
        if not url:
            return "1080p"
        
        url_lower = url.lower()
        
        if "480" in url_lower:
            return "480p"
        elif "720" in url_lower:
            return "720p"
        elif "1080" in url_lower:
            return "1080p"
        else:
            return "1080p"  # Default