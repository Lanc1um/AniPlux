"""
Downloader - Core download orchestration and management.

This module provides the core download functionality with async support,
progress tracking, and concurrent download management.
"""

import asyncio
import logging
import aiohttp
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from urllib.parse import urlparse

from aniplux.core.models import DownloadTask, Episode, Quality, DownloadStatus
from aniplux.core.exceptions import DownloadError, NetworkError
from aniplux.core.utils import sanitize_filename, generate_episode_filename
from aniplux.core.aria2c_downloader import Aria2cDownloader


logger = logging.getLogger(__name__)


class Downloader:
    """
    Core download manager with async support and progress tracking.
    
    Handles individual and batch downloads with concurrent execution,
    progress callbacks, and error recovery mechanisms.
    """
    
    def __init__(self, config_manager: Any):
        """
        Initialize downloader.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.settings = config_manager.settings.settings
        
        # Download settings
        self.concurrent_downloads = self.settings.concurrent_downloads
        self.timeout = self.settings.timeout
        self.max_retries = self.settings.max_retries
        self.chunk_size = self.settings.chunk_size
        
        # Active downloads tracking
        self.active_downloads: Dict[str, DownloadTask] = {}
        self.download_semaphore = asyncio.Semaphore(self.concurrent_downloads)
        
        # Progress callbacks
        self.progress_callbacks: List[Callable[[DownloadTask], None]] = []
        
        # Shared plugin manager to avoid multiple instances
        self._plugin_manager = None
        
        # Initialize aria2c downloader if enabled
        self.aria2c_downloader = None
        if self.settings.use_aria2c:
            self.aria2c_downloader = Aria2cDownloader(config_manager)
            if not self.aria2c_downloader.is_available():
                logger.warning("aria2c requested but not available, falling back to standard downloads")
                self.aria2c_downloader = None
    
    def add_progress_callback(self, callback: Callable[[DownloadTask], None]) -> None:
        """
        Add a progress callback function.
        
        Args:
            callback: Function to call on progress updates
        """
        self.progress_callbacks.append(callback)
        
        # Also add to aria2c downloader if available
        if self.aria2c_downloader:
            self.aria2c_downloader.add_progress_callback(callback)
    
    def remove_progress_callback(self, callback: Callable[[DownloadTask], None]) -> None:
        """
        Remove a progress callback function.
        
        Args:
            callback: Function to remove
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
        
        # Also remove from aria2c downloader if available
        if self.aria2c_downloader:
            self.aria2c_downloader.remove_progress_callback(callback)
    
    def _notify_progress(self, task: DownloadTask) -> None:
        """
        Notify all progress callbacks of task update.
        
        Args:
            task: Updated download task
        """
        for callback in self.progress_callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    async def download_episode(
        self,
        episode: Episode,
        quality: Optional[Quality] = None,
        output_path: Optional[Path] = None,
        anime_title: Optional[str] = None
    ) -> DownloadTask:
        """
        Download a single episode.
        
        Args:
            episode: Episode to download
            quality: Preferred quality (uses best available if None)
            output_path: Custom output path
            anime_title: Anime title for filename generation
            
        Returns:
            DownloadTask with final status
            
        Raises:
            DownloadError: If download fails
        """
        # Determine quality
        if quality is None:
            quality = episode.best_quality
        elif quality not in episode.quality_options:
            # Fallback to best available quality
            logger.warning(f"Quality {quality} not available, using {episode.best_quality}")
            quality = episode.best_quality
        
        # Generate output path if not provided
        if output_path is None:
            download_dir = Path(self.settings.download_directory)
            filename = generate_episode_filename(
                anime_title or "Unknown Anime",
                episode,
                quality
            )
            output_path = download_dir / filename
        
        # Create download task
        task = DownloadTask(
            episode=episode,
            quality=quality,
            output_path=output_path,
            max_retries=self.max_retries,
            download_url=None,
            headers=None,
            progress=0.0,
            status=DownloadStatus.PENDING,
            file_size=None,
            downloaded_bytes=0,
            download_speed=0.0,
            eta_seconds=None,
            start_time=None,
            end_time=None,
            error_message=None,
            retry_count=0
        )
        
        # Add to active downloads
        task_id = f"{episode.url}_{quality.value}"
        self.active_downloads[task_id] = task
        
        try:
            # Perform download
            await self._download_task(task)
            return task
        finally:
            # Remove from active downloads
            self.active_downloads.pop(task_id, None)
    
    async def download_batch(
        self,
        episodes: List[Episode],
        quality: Optional[Quality] = None,
        output_dir: Optional[Path] = None,
        anime_title: Optional[str] = None
    ) -> List[DownloadTask]:
        """
        Download multiple episodes concurrently.
        
        Args:
            episodes: List of episodes to download
            quality: Preferred quality for all episodes
            output_dir: Output directory
            anime_title: Anime title for filename generation
            
        Returns:
            List of DownloadTask results
        """
        if not episodes:
            return []
        
        # Create download tasks
        tasks = []
        for episode in episodes:
            # Generate output path
            if output_dir:
                filename = generate_episode_filename(
                    anime_title or "Unknown Anime",
                    episode,
                    quality or episode.best_quality
                )
                output_path = output_dir / filename
            else:
                output_path = None
            
            # Create task coroutine
            task_coro = self.download_episode(
                episode=episode,
                quality=quality,
                output_path=output_path,
                anime_title=anime_title
            )
            tasks.append(task_coro)
        
        # Execute downloads concurrently
        logger.info(f"Starting batch download of {len(episodes)} episodes")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        download_tasks = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create failed task for exception
                episode = episodes[i]
                task = DownloadTask(
                    episode=episode,
                    quality=quality or episode.best_quality,
                    output_path=Path("failed"),
                    max_retries=self.max_retries,
                    download_url=None,
                    headers=None,
                    progress=0.0,
                    status=DownloadStatus.FAILED,
                    file_size=None,
                    downloaded_bytes=0,
                    download_speed=0.0,
                    eta_seconds=None,
                    start_time=None,
                    end_time=None,
                    error_message=str(result),
                    retry_count=0
                )
                task.mark_failed(str(result))
                download_tasks.append(task)
            else:
                download_tasks.append(result)
        
        return download_tasks
    
    async def _download_task(self, task: DownloadTask) -> None:
        """
        Execute a single download task.
        
        Args:
            task: Download task to execute
        """
        plugin_manager = None
        try:
            async with self.download_semaphore:
                # Get download URL from plugin
                download_url = await self._get_download_url(task)
                from pydantic import HttpUrl
                task.download_url = HttpUrl(download_url)
                
                # Start download
                task.mark_started()
                self._notify_progress(task)
                
                # Perform download with retries
                await self._download_with_retries(task)
                
                # Mark as completed
                task.mark_completed()
                self._notify_progress(task)
                
        except Exception as e:
            task.mark_failed(str(e))
            self._notify_progress(task)
            logger.error(f"Download failed: {task.episode.title} - {e}")
            raise DownloadError(f"Failed to download episode: {e}", task.episode.title)
    
    async def _get_plugin_manager(self):
        """Get or create shared plugin manager instance."""
        if self._plugin_manager is None:
            from aniplux.core import PluginManager
            self._plugin_manager = PluginManager(self.config_manager)
        return self._plugin_manager
    
    async def _get_download_url(self, task: DownloadTask) -> str:
        """
        Get download URL from plugin.
        
        Args:
            task: Download task
            
        Returns:
            Direct download URL
            
        Raises:
            DownloadError: If URL extraction fails
        """
        plugin_manager = None
        try:
            # Use shared plugin manager
            plugin_manager = await self._get_plugin_manager()
            
            # Get source from episode metadata or extract from URL
            source_name = getattr(task.episode, 'source', None)
            
            if not source_name:
                # Extract source from episode URL as fallback
                url_str = str(task.episode.url)
                if 'hianime.to' in url_str:
                    source_name = 'hianime_plugin'
                elif 'animetsu.to' in url_str or 'animetsu.cc' in url_str:
                    source_name = 'animetsu_plugin'
                else:
                    # Extract domain-based source name
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url_str)
                    domain_parts = parsed_url.netloc.split('.')
                    if len(domain_parts) >= 2:
                        source_name = f"{domain_parts[-2]}_plugin"
                    else:
                        source_name = "sample"  # fallback
            
            download_url = await plugin_manager.get_download_url(
                plugin_name=source_name,
                episode_url=str(task.episode.url),
                quality=task.quality
            )
            
            # Get headers from plugins if available
            if source_name == 'hianime_plugin':
                try:
                    plugin = await plugin_manager.load_plugin(source_name)
                    if plugin and hasattr(plugin, 'download_manager'):
                        download_manager = getattr(plugin, 'download_manager')
                        headers = download_manager.get_last_headers()
                        if headers:
                            task.headers = headers
                            logger.debug(f"Using headers from HiAnime plugin: {list(headers.keys())}")
                except Exception as e:
                    logger.debug(f"Could not get headers from HiAnime plugin: {e}")
            elif source_name == 'animetsu_plugin':
                try:
                    plugin = await plugin_manager.load_plugin(source_name)
                    if plugin and hasattr(plugin, 'get_download_headers'):
                        get_headers_method = getattr(plugin, 'get_download_headers')
                        headers = get_headers_method()
                        if headers:
                            task.headers = headers
                            logger.debug(f"Using headers from Animetsu plugin: {list(headers.keys())}")
                except Exception as e:
                    logger.debug(f"Could not get headers from Animetsu plugin: {e}")
            
            return download_url
            
        except Exception as e:
            raise DownloadError(f"Failed to get download URL: {e}", task.episode.title)
        finally:
            # Clean up plugin sessions after URL extraction
            if plugin_manager:
                try:
                    await plugin_manager.cleanup_all_plugins()
                except Exception as cleanup_error:
                    logger.debug(f"Plugin cleanup error in _get_download_url: {cleanup_error}")
    
    async def _download_with_retries(self, task: DownloadTask) -> None:
        """
        Download file with retry logic.
        
        Args:
            task: Download task
        """
        last_exception = None
        
        for attempt in range(task.max_retries + 1):
            try:
                await self._download_file(task)
                return  # Success
                
            except Exception as e:
                last_exception = e
                task.retry_count = attempt + 1
                
                if attempt < task.max_retries:
                    logger.warning(f"Download attempt {attempt + 1} failed, retrying: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Download failed after {task.max_retries + 1} attempts")
        
        # All retries failed
        raise last_exception or DownloadError("Download failed after all retries")
    
    async def _download_file(self, task: DownloadTask) -> None:
        """
        Download file from URL with progress tracking.
        
        Args:
            task: Download task
        """
        if not task.download_url:
            raise DownloadError("No download URL available")
        
        # Create output directory
        task.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if this is an HLS stream (.m3u8) - use yt-dlp for HLS
        url_str = str(task.download_url)
        is_hls_stream = (url_str.lower().endswith('.m3u8') or 
                        'master.m3u8' in url_str.lower() or
                        'playlist.m3u8' in url_str.lower() or
                        'tiddies.animetsu' in url_str.lower() or
                        'animetsu.cc' in url_str.lower() or
                        'animetsu.to' in url_str.lower())
        
        if is_hls_stream:
            logger.info(f"Detected HLS stream, using yt-dlp: {url_str}")
            await self._download_hls_stream(task)
        else:
            # Use aria2c for direct downloads if available
            if self.aria2c_downloader and self.aria2c_downloader.is_available():
                try:
                    await self.aria2c_downloader.download_file(task)
                    return
                except Exception as e:
                    logger.warning(f"aria2c download failed, falling back to standard download: {e}")
            
            # Fallback to standard download
            await self._download_direct_file(task)
    
    async def _download_hls_stream(self, task: DownloadTask) -> None:
        """
        Download HLS stream using yt-dlp (for .m3u8 files).
        
        Args:
            task: Download task
        """
        try:
            # Try yt-dlp with aria2c first if available
            if self.aria2c_downloader and self.aria2c_downloader.is_available():
                try:
                    await self.aria2c_downloader.download_with_ytdlp_aria2c(task)
                    return
                except Exception as e:
                    logger.warning(f"yt-dlp + aria2c failed, falling back to standard yt-dlp: {e}")
            
            # Fallback to standard yt-dlp
            import yt_dlp
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            # Prepare yt-dlp options
            ydl_opts = {
                'outtmpl': str(task.output_path),
                'format': 'best',
                'http_headers': task.headers or {},
                'fragment_retries': 10,
                'retries': 5,
                'no_warnings': False,  # Enable warnings for debugging
                'quiet': False,  # Disable quiet mode for debugging
                'no_color': True,
                'extract_flat': False,
                'noprogress': False,  # Ensure progress is enabled
            }
            
            # Store reference to self for use in nested function
            downloader_self = self
            
            # Enhanced progress hook for yt-dlp with HLS support
            def progress_hook(d):
                try:
                    if d['status'] == 'downloading':
                        # Handle different progress data formats
                        downloaded = d.get('downloaded_bytes', 0)
                        
                        # Update downloaded bytes
                        task.downloaded_bytes = downloaded
                        
                        # Handle total size estimation for HLS
                        if 'total_bytes' in d and d['total_bytes']:
                            task.file_size = d['total_bytes']
                        elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                            task.file_size = d['total_bytes_estimate']
                        elif 'fragment_index' in d and 'fragment_count' in d:
                            # HLS fragment-based estimation
                            fragment_index = d.get('fragment_index', 0)
                            fragment_count = d.get('fragment_count', 0)
                            
                            if fragment_count and fragment_index and fragment_index > 0:
                                # Estimate total based on current progress
                                estimated_total = (downloaded * fragment_count) // fragment_index
                                # Only update if estimate is reasonable
                                if estimated_total > task.file_size or 0:
                                    task.file_size = estimated_total
                                
                                logger.debug(f"HLS Progress: {fragment_index}/{fragment_count} fragments, "
                                           f"{downloaded} bytes, estimated total: {estimated_total}")
                        
                        # Update speed and ETA
                        if 'speed' in d and d['speed']:
                            task.download_speed = max(0, int(d['speed']))
                        if 'eta' in d and d['eta']:
                            task.eta_seconds = max(0, int(d['eta']))
                        
                        # Update progress percentage
                        if task.file_size and task.file_size > 0:
                            task.update_progress(task.downloaded_bytes, task.file_size)
                        else:
                            # For HLS without total, show indeterminate progress
                            task.progress = min(99.0, (downloaded / (1024 * 1024)) * 0.1)  # Rough estimate
                        
                        # Notify progress callbacks
                        downloader_self._notify_progress(task)
                        
                    elif d['status'] == 'finished':
                        # Final update when download completes
                        try:
                            if task.output_path.exists():
                                final_size = task.output_path.stat().st_size
                                task.downloaded_bytes = final_size
                                task.file_size = final_size
                            else:
                                # Use last known values
                                task.downloaded_bytes = task.file_size or task.downloaded_bytes
                            
                            # Mark as 100% complete
                            task.progress = 100.0
                            task.download_speed = 0
                            task.eta_seconds = 0
                            
                            downloader_self._notify_progress(task)
                            logger.info(f"Download finished: {task.downloaded_bytes} bytes")
                            
                        except Exception as finish_error:
                            logger.warning(f"Error in finish handling: {finish_error}")
                        
                except Exception as e:
                    logger.warning(f"Progress hook error: {e}")
                    # Fallback: still try to update with basic info
                    try:
                        if 'downloaded_bytes' in d:
                            task.downloaded_bytes = d['downloaded_bytes']
                            if task.file_size:
                                task.update_progress(task.downloaded_bytes, task.file_size)
                            downloader_self._notify_progress(task)
                    except Exception:
                        pass  # Ignore secondary errors
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            # Run yt-dlp in thread pool to avoid blocking
            def download_with_ytdlp():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([str(task.download_url)])
            
            # Execute in thread pool with fallback progress monitoring
            loop = asyncio.get_event_loop()
            
            # Enhanced fallback progress monitoring for HLS
            async def monitor_file_progress():
                """Monitor file size as fallback progress tracking."""
                last_size = 0
                stall_count = 0
                last_update_time = time.time()
                
                while task.status == DownloadStatus.DOWNLOADING:
                    try:
                        current_time = time.time()
                        
                        if task.output_path.exists():
                            current_size = task.output_path.stat().st_size
                            
                            if current_size != last_size:
                                # Calculate speed
                                time_diff = current_time - last_update_time
                                if time_diff > 0:
                                    speed = (current_size - last_size) / time_diff
                                    task.download_speed = max(0, int(speed))
                                
                                task.downloaded_bytes = current_size
                                
                                # For HLS streams, estimate progress differently
                                if not task.file_size or task.file_size <= current_size:
                                    # Show indeterminate progress for HLS
                                    # Use a logarithmic scale to show progress without knowing total
                                    mb_downloaded = current_size / (1024 * 1024)
                                    estimated_progress = min(95.0, mb_downloaded * 2)  # 2% per MB, max 95%
                                    task.progress = estimated_progress
                                    logger.debug(f"HLS fallback progress: {current_size} bytes ({estimated_progress:.1f}%)")
                                else:
                                    task.update_progress(current_size, task.file_size)
                                    logger.debug(f"Fallback progress: {task.progress:.1f}%")
                                
                                self._notify_progress(task)
                                last_size = current_size
                                last_update_time = current_time
                                stall_count = 0
                            else:
                                stall_count += 1
                                # If no progress for 15 seconds, log info
                                if stall_count == 15:
                                    logger.info("Download in progress - processing video segments...")
                                elif stall_count >= 60:
                                    logger.warning("Download appears stalled - no file size change for 60 seconds")
                                    stall_count = 0
                        else:
                            # File doesn't exist yet
                            if stall_count == 0:
                                logger.debug("Waiting for download file to be created...")
                            stall_count += 1
                        
                        await asyncio.sleep(1)  # Check every second
                        
                    except Exception as e:
                        logger.debug(f"File monitoring error: {e}")
                        await asyncio.sleep(1)
            
            # Start both download and monitoring
            monitor_task = asyncio.create_task(monitor_file_progress())
            
            try:
                with ThreadPoolExecutor() as executor:
                    await loop.run_in_executor(executor, download_with_ytdlp)
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            

            
        except ImportError:
            logger.error("yt-dlp not available, falling back to direct download")
            await self._download_direct_file(task)
        except Exception as e:
            raise DownloadError(f"HLS download failed: {e}", task.episode.title)
    
    async def _download_direct_file(self, task: DownloadTask) -> None:
        """
        Download file directly using aiohttp (for regular files).
        
        Args:
            task: Download task
        """
        # Set up HTTP session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        # Prepare headers
        headers = task.headers or {}
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(str(task.download_url), headers=headers) as response:
                    # Check response status
                    if response.status >= 400:
                        raise NetworkError(
                            f"HTTP {response.status} error",
                            url=str(task.download_url),
                            status_code=response.status
                        )
                    
                    # Get file size
                    content_length = response.headers.get('content-length')
                    if content_length:
                        task.file_size = int(content_length)
                    
                    # Download file
                    with open(task.output_path, 'wb') as file:
                        async for chunk in response.content.iter_chunked(self.chunk_size):
                            file.write(chunk)
                            task.downloaded_bytes += len(chunk)
                            
                            # Update progress
                            task.update_progress(task.downloaded_bytes, task.file_size)
                            self._notify_progress(task)
            
            except aiohttp.ClientError as e:
                raise NetworkError(f"Network error during download: {e}", str(task.download_url))
            except OSError as e:
                raise DownloadError(f"File system error: {e}", task.episode.title)
    
    def get_active_downloads(self) -> List[DownloadTask]:
        """
        Get list of currently active downloads.
        
        Returns:
            List of active download tasks
        """
        return list(self.active_downloads.values())
    
    def cancel_download(self, task_id: str) -> bool:
        """
        Cancel an active download.
        
        Args:
            task_id: ID of the download task to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        if task_id in self.active_downloads:
            task = self.active_downloads[task_id]
            task.status = DownloadStatus.CANCELLED
            self._notify_progress(task)
            return True
        return False
    
    def cancel_all_downloads(self) -> int:
        """
        Cancel all active downloads.
        
        Returns:
            Number of downloads cancelled
        """
        cancelled_count = 0
        for task in self.active_downloads.values():
            if task.is_active:
                task.status = DownloadStatus.CANCELLED
                self._notify_progress(task)
                cancelled_count += 1
        
        return cancelled_count
    
    async def cleanup(self) -> None:
        """Clean up downloader resources."""
        # Cancel any remaining downloads
        self.cancel_all_downloads()
        
        # Clear callbacks
        self.progress_callbacks.clear()
        
        # Clean up shared plugin manager
        if self._plugin_manager:
            try:
                await self._plugin_manager.cleanup()
                self._plugin_manager = None
            except Exception as e:
                logger.debug(f"Error cleaning up plugin manager: {e}")
        
        # Clean up aria2c downloader
        if self.aria2c_downloader:
            try:
                cleanup_method = getattr(self.aria2c_downloader, 'cleanup', None)
                if cleanup_method:
                    await cleanup_method()
            except Exception as e:
                logger.debug(f"Error cleaning up aria2c downloader: {e}")
        logger.info("Downloader cleanup complete")


# Export downloader
__all__ = ["Downloader"]