"""
Animetsu Download Manager

This module handles download URL extraction and management for Animetsu.
"""

import logging
import shutil
import subprocess
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from aniplux.core.models import Quality
from aniplux.core.exceptions import PluginError
from .api import AnimetsuAPI
from .parser import AnimetsuParser
from .config import get_string_from_quality


logger = logging.getLogger(__name__)


class AnimetsuDownloadManager:
    """Manages download operations for Animetsu plugin."""
    
    def __init__(self, api: AnimetsuAPI, parser: AnimetsuParser, config: Dict[str, Any]):
        """
        Initialize download manager.
        
        Args:
            api: Animetsu API client
            parser: Animetsu parser
            config: Plugin configuration
        """
        self.api = api
        self.parser = parser
        self.config = config
        
        # Check for external downloaders
        self.yt_dlp_available = shutil.which("yt-dlp") is not None
        self.aria2c_available = shutil.which("aria2c") is not None
        
        logger.debug(f"yt-dlp available: {self.yt_dlp_available}")
        logger.debug(f"aria2c available: {self.aria2c_available}")
    
    async def extract_download_url(self, episode_url: str, quality: Quality) -> str:
        """
        Extract download URL for an episode.
        
        Args:
            episode_url: Episode URL
            quality: Requested quality
            
        Returns:
            Download URL
            
        Raises:
            PluginError: If extraction fails
        """
        try:
            # Parse episode URL to extract anime_id and episode_number
            anime_id, episode_num = self._parse_episode_url(episode_url)
            
            if not anime_id or not episode_num:
                raise PluginError(f"Could not parse episode URL: {episode_url}")
            
            logger.debug(f"Extracting download URL for anime {anime_id}, episode {episode_num}")
            
            # First, get available servers
            servers = await self.api.get_servers(anime_id, episode_num)
            
            if not servers:
                raise PluginError("No servers found for episode")
            
            logger.debug(f"Found {len(servers)} servers: {[s.get('id') for s in servers]}")
            
            # Try servers in order of preference
            server_priority = ["pahe", "zoro", "zaza", "meg", "bato"]
            available_servers = [s.get('id') for s in servers if s.get('id')]
            
            # Sort servers by priority
            sorted_servers = []
            for preferred in server_priority:
                if preferred in available_servers:
                    sorted_servers.append(preferred)
            
            # Add any remaining servers
            for server in available_servers:
                if server not in sorted_servers:
                    sorted_servers.append(server)
            
            # Try each server until we find working streams
            for server in sorted_servers:
                logger.debug(f"Trying server: {server}")
                
                # Try both sub and dub
                for subtype in ["sub", "dub"]:
                    try:
                        stream_data = await self.api.get_stream_url(anime_id, episode_num, server, subtype)
                        
                        if not stream_data:
                            continue
                        
                        # Parse stream sources
                        sources = self.parser.parse_stream_sources(stream_data)
                        
                        if not sources:
                            continue
                        
                        # Find best quality match
                        quality_str = get_string_from_quality(quality)
                        download_url = self._select_best_source(sources, quality_str)
                        
                        if download_url:
                            is_hls = self.parser.is_m3u8_url(download_url)
                            logger.info(f"Successfully extracted download URL from server {server} ({subtype}) for quality {quality_str}")
                            logger.info(f"URL type: {'HLS/M3U8' if is_hls else 'Direct'} - {download_url}")
                            return download_url
                            
                    except Exception as e:
                        logger.debug(f"Server {server} ({subtype}) failed: {e}")
                        continue
            
            raise PluginError("No working streams found from any server")
            
        except Exception as e:
            if isinstance(e, PluginError):
                raise
            raise PluginError(f"Failed to extract download URL: {e}")
    
    def _parse_episode_url(self, episode_url: str) -> tuple[Optional[str], Optional[int]]:
        """
        Parse episode URL to extract anime ID and episode number.
        
        Args:
            episode_url: Episode URL
            
        Returns:
            Tuple of (anime_id, episode_number)
        """
        import re
        
        # Convert to string if it's a Pydantic URL object
        episode_url_str = str(episode_url)
        
        # Expected format: https://animetsu.to/watch/{anime_id}/{episode_num} or https://animetsu.cc/watch/{anime_id}/{episode_num}
        pattern = r'/watch/([^/]+)/(\d+)'
        match = re.search(pattern, episode_url_str)
        
        if match:
            anime_id = match.group(1)
            episode_num = int(match.group(2))
            logger.debug(f"Parsed episode URL: anime_id={anime_id}, episode_num={episode_num}")
            return anime_id, episode_num
        
        logger.warning(f"Could not parse episode URL: {episode_url_str}")
        return None, None
    
    def _select_best_source(self, sources: List[Dict[str, Any]], preferred_quality: str) -> Optional[str]:
        """
        Select the best source based on quality preference.
        
        Args:
            sources: List of available sources
            preferred_quality: Preferred quality string
            
        Returns:
            Best source URL or None
        """
        if not sources:
            return None
        
        # First, try to find exact quality match
        for source in sources:
            if source.get("quality") == preferred_quality:
                return source.get("url")
        
        # If no exact match, try quality fallback order
        quality_fallback = {
            "1080p": ["1080p", "720p", "480p"],
            "720p": ["720p", "1080p", "480p"],
            "480p": ["480p", "720p", "1080p"]
        }
        
        fallback_order = quality_fallback.get(preferred_quality, ["1080p", "720p", "480p"])
        
        for quality in fallback_order:
            for source in sources:
                if source.get("quality") == quality:
                    logger.info(f"Using fallback quality {quality} instead of {preferred_quality}")
                    return source.get("url")
        
        # If still no match, return first available source
        if sources:
            logger.warning(f"No quality match found, using first available source")
            return sources[0].get("url")
        
        return None
    
    def can_download_with_external_tools(self) -> bool:
        """
        Check if external download tools are available.
        
        Returns:
            True if external tools are available
        """
        return self.yt_dlp_available or self.aria2c_available
    
    def get_download_command(self, url: str, output_path: str, use_aria2c: bool = True) -> List[str]:
        """
        Get download command for external tools.
        
        Args:
            url: Download URL
            output_path: Output file path
            use_aria2c: Whether to use aria2c acceleration
            
        Returns:
            Command list for subprocess
            
        Raises:
            PluginError: If no suitable downloader is available
        """
        # Check if URL is M3U8 playlist
        is_m3u8 = self.parser.is_m3u8_url(url)
        
        if is_m3u8 and self.yt_dlp_available:
            # Use yt-dlp for M3U8 downloads
            cmd = ["yt-dlp"]
            
            # Add headers to match our requests
            cmd.extend([
                "--add-header", "Origin:https://animetsu.to",
                "--add-header", "Referer:https://animetsu.to/",
                "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            ])
            
            # Use aria2c if available and requested
            if use_aria2c and self.aria2c_available and self.config.get("use_aria2c", True):
                cmd.extend([
                    "--external-downloader", "aria2c",
                    "--external-downloader-args", 
                    "aria2c:-x 16 -s 16 -k 1M -j 16 --file-allocation=none"
                ])
            
            # Output file
            cmd.extend(["-o", output_path])
            cmd.append(url)
            
            return cmd
        
        elif self.aria2c_available and not is_m3u8:
            # Use aria2c for direct downloads
            output_dir = os.path.dirname(output_path)
            output_filename = os.path.basename(output_path)
            
            cmd = [
                "aria2c",
                "-x", "16",          # 16 connections
                "-s", "16",          # Split into 16 pieces
                "-k", "1M",          # Keep partial downloads
                "-j", "16",          # Max concurrent downloads
                "--file-allocation=none",  # Don't pre-allocate space
                "--allow-overwrite=true",
                "-d", output_dir,    # Output directory
                "-o", output_filename, # Output filename
                url
            ]
            
            return cmd
        
        else:
            raise PluginError("No suitable external downloader available")
    
    async def download_with_external_tool(self, url: str, output_path: str) -> bool:
        """
        Download using external tools.
        
        Args:
            url: Download URL
            output_path: Output file path
            
        Returns:
            True if download succeeded
        """
        try:
            # Create output directory if it doesn't exist
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Get download command
            use_aria2c = self.config.get("use_aria2c", True)
            cmd = self.get_download_command(url, output_path, use_aria2c)
            
            logger.info(f"Starting download with command: {' '.join(cmd)}")
            
            # Run the download command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Download completed successfully")
                return True
            else:
                logger.error(f"Download failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"External download failed: {e}")
            return False
    
    def generate_filename(self, anime_title: str, episode_num: int, quality: str) -> str:
        """
        Generate filename for downloaded episode.
        
        Args:
            anime_title: Anime title
            episode_num: Episode number
            quality: Video quality
            
        Returns:
            Generated filename
        """
        # Clean title for filename
        import re
        clean_title = re.sub(r'[<>:"/\\|?*]', '', anime_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        filename = f"{clean_title} - Episode {episode_num} [{quality}].mp4"
        return filename
    
    def cleanup(self):
        """Clean up download manager resources."""
        # Nothing to clean up for now
        pass