"""
Aria2c Downloader - High-speed download support using aria2c.

This module provides aria2c integration for faster downloads with
multi-connection support and better resume capabilities.
"""

import asyncio
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import json

from aniplux.core.models import DownloadTask, DownloadStatus
from aniplux.core.exceptions import DownloadError


logger = logging.getLogger(__name__)


class Aria2cDownloader:
    """
    Aria2c-based downloader for high-speed downloads.
    
    Provides multi-connection downloads with progress tracking
    and better resume capabilities than standard HTTP downloads.
    """
    
    def __init__(self, config_manager: Any):
        """
        Initialize aria2c downloader.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.settings = config_manager.settings.settings
        
        # Aria2c settings
        self.aria2c_path = self._find_aria2c_executable()
        self.connections = self.settings.aria2c_connections
        self.split = self.settings.aria2c_split
        self.min_split_size = self.settings.aria2c_min_split_size
        
        # Progress callbacks
        self.progress_callbacks: List[Callable[[DownloadTask], None]] = []
    
    def _find_aria2c_executable(self) -> Optional[str]:
        """
        Find aria2c executable path.
        
        Returns:
            Path to aria2c executable or None if not found
        """
        # Check if custom path is configured
        if self.settings.aria2c_path:
            custom_path = Path(self.settings.aria2c_path)
            if custom_path.exists() and custom_path.is_file():
                return str(custom_path)
            else:
                logger.warning(f"Configured aria2c path not found: {custom_path}")
        
        # Try to find aria2c in PATH
        aria2c_path = shutil.which("aria2c")
        if aria2c_path:
            return aria2c_path
        
        logger.warning("aria2c not found in PATH. Install aria2c for faster downloads.")
        return None
    
    def is_available(self) -> bool:
        """
        Check if aria2c is available for use.
        
        Returns:
            True if aria2c is available, False otherwise
        """
        return self.aria2c_path is not None
    
    def add_progress_callback(self, callback: Callable[[DownloadTask], None]) -> None:
        """
        Add a progress callback function.
        
        Args:
            callback: Function to call on progress updates
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[DownloadTask], None]) -> None:
        """
        Remove a progress callback function.
        
        Args:
            callback: Function to remove
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
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
    
    async def download_file(self, task: DownloadTask) -> None:
        """
        Download file using aria2c.
        
        Args:
            task: Download task to execute
            
        Raises:
            DownloadError: If download fails
        """
        if not self.is_available():
            raise DownloadError("aria2c is not available", task.episode.title)
        
        if not task.download_url:
            raise DownloadError("No download URL available", task.episode.title)
        
        # Check if this is an HLS stream - aria2c can't handle these properly
        url_str = str(task.download_url)
        is_hls_stream = (url_str.lower().endswith('.m3u8') or 
                        'master.m3u8' in url_str.lower() or
                        'playlist.m3u8' in url_str.lower() or
                        'tiddies.animetsu' in url_str.lower() or
                        'animetsu.cc' in url_str.lower() or
                        'animetsu.to' in url_str.lower())
        
        if is_hls_stream:
            logger.warning("aria2c cannot handle HLS streams, should use yt-dlp instead")
            raise DownloadError("aria2c cannot handle HLS streams", task.episode.title)
        
        try:
            # Create output directory
            task.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare aria2c command
            cmd = self._build_aria2c_command(task)
            
            # Start download process
            await self._run_aria2c_download(task, cmd)
            
        except Exception as e:
            raise DownloadError(f"aria2c download failed: {e}", task.episode.title)
    
    def _build_aria2c_command(self, task: DownloadTask) -> List[str]:
        """
        Build aria2c command line arguments.
        
        Args:
            task: Download task
            
        Returns:
            List of command arguments
        """
        cmd = [
            str(self.aria2c_path),
            str(task.download_url),
            "--out", task.output_path.name,
            "--dir", str(task.output_path.parent),
            "--max-connection-per-server", str(self.connections),
            "--split", str(self.split),
            "--min-split-size", self.min_split_size,
            "--max-tries", str(task.max_retries + 1),
            "--retry-wait", "2",
            "--timeout", str(self.settings.timeout),
            "--connect-timeout", "10",
            "--continue", "true",
            "--allow-overwrite", "true",
            "--auto-file-renaming", "false",
            "--summary-interval", "1",
            "--download-result", "hide",
            "--console-log-level", "info",  # Changed to info for progress output
            "--human-readable", "true",
            "--show-console-readout", "true",
        ]
        
        # Add headers if available
        if task.headers:
            for key, value in task.headers.items():
                cmd.extend(["--header", f"{key}: {value}"])
        
        # Add user agent
        cmd.extend([
            "--user-agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ])
        
        return cmd
    
    async def _run_aria2c_download(self, task: DownloadTask, cmd: List[str]) -> None:
        """
        Run aria2c download process with progress tracking.
        
        Args:
            task: Download task
            cmd: aria2c command arguments
        """
        try:
            # Start aria2c process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Combine stderr with stdout
                cwd=task.output_path.parent
            )
            
            # Track progress by reading stdout
            await self._track_download_progress_from_output(task, process)
            
            # Wait for completion
            await process.wait()
            
            if process.returncode != 0:
                raise DownloadError(f"aria2c failed with code {process.returncode}")
            
            # Verify file was downloaded
            if not task.output_path.exists():
                raise DownloadError("Download completed but output file not found")
            
            # Update final file size
            task.file_size = task.output_path.stat().st_size
            task.downloaded_bytes = task.file_size
            task.update_progress(task.downloaded_bytes, task.file_size)
            self._notify_progress(task)
            
        except Exception as e:
            logger.error(f"aria2c download error: {e}")
            raise
    
    async def _track_download_progress_from_output(self, task: DownloadTask, process: asyncio.subprocess.Process) -> None:
        """
        Track download progress by parsing aria2c output.
        
        Args:
            task: Download task
            process: aria2c subprocess
        """
        last_update_time = 0
        total_fragments_downloaded = 0
        
        try:
            while True:
                if process.stdout is None:
                    break
                line = await process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode('utf-8', errors='ignore').strip()
                
                # Parse aria2c progress output for regular downloads
                # Format: [#1 SIZE:123.4MiB/456.7MiB(27%) CN:8 DL:1.2MiB ETA:5m30s]
                if '[#' in line_str and 'SIZE:' in line_str and '/0B' not in line_str:
                    try:
                        # Extract downloaded and total size
                        size_match = re.search(r'SIZE:([0-9.]+)([KMGT]?iB)/([0-9.]+)([KMGT]?iB)', line_str)
                        if size_match:
                            downloaded_str, downloaded_unit, total_str, total_unit = size_match.groups()
                            
                            # Convert to bytes
                            downloaded_bytes = self._parse_size_to_bytes(downloaded_str, downloaded_unit)
                            total_bytes = self._parse_size_to_bytes(total_str, total_unit)
                            
                            # Update task
                            task.downloaded_bytes = downloaded_bytes
                            task.file_size = total_bytes
                            task.update_progress(downloaded_bytes, total_bytes)
                            
                            # Extract download speed
                            speed_match = re.search(r'DL:([0-9.]+)([KMGT]?iB)', line_str)
                            if speed_match:
                                speed_str, speed_unit = speed_match.groups()
                                speed_bytes = self._parse_size_to_bytes(speed_str, speed_unit)
                                task.download_speed = speed_bytes
                            
                            # Extract ETA
                            eta_match = re.search(r'ETA:(\d+)m(\d+)s', line_str)
                            if eta_match:
                                minutes, seconds = eta_match.groups()
                                task.eta_seconds = int(minutes) * 60 + int(seconds)
                            
                            # Notify progress
                            self._notify_progress(task)
                    
                    except Exception as e:
                        logger.debug(f"Error parsing aria2c progress: {e}")
                
                # Handle HLS fragment downloads (when total size is 0B or unknown)
                elif '[#' in line_str and ('SIZE:' in line_str or 'DL:' in line_str):
                    try:
                        # Count fragments and estimate progress for HLS streams
                        if 'part-Frag' in line_str:
                            # Extract fragment number
                            frag_match = re.search(r'part-Frag(\d+)', line_str)
                            if frag_match:
                                frag_num = int(frag_match.group(1))
                                total_fragments_downloaded = max(total_fragments_downloaded, frag_num)
                        
                        # Extract download speed for HLS
                        speed_match = re.search(r'DL:([0-9.]+)([KMGT]?iB)', line_str)
                        if speed_match:
                            speed_str, speed_unit = speed_match.groups()
                            speed_bytes = self._parse_size_to_bytes(speed_str, speed_unit)
                            task.download_speed = speed_bytes
                        
                        # For HLS, estimate progress based on file size growth
                        import time
                        current_time = time.time()
                        if current_time - last_update_time >= 1.0:  # Update every second
                            if task.output_path.exists():
                                current_size = task.output_path.stat().st_size
                                task.downloaded_bytes = current_size
                                
                                # For HLS, we don't know total size, so show indeterminate progress
                                # But we can show downloaded amount and speed
                                if not task.file_size:
                                    # Estimate total size based on fragments (rough estimate)
                                    if total_fragments_downloaded > 0:
                                        # Assume average 1MB per fragment (very rough estimate)
                                        estimated_total = total_fragments_downloaded * 1024 * 1024
                                        task.file_size = max(estimated_total, current_size * 2)
                                
                                task.update_progress(task.downloaded_bytes, task.file_size)
                                self._notify_progress(task)
                                last_update_time = current_time
                    
                    except Exception as e:
                        logger.debug(f"Error parsing HLS progress: {e}")
                
                # Fallback: check file size periodically
                else:
                    import time
                    current_time = time.time()
                    if current_time - last_update_time >= 2.0:  # Update every 2 seconds as fallback
                        if task.output_path.exists():
                            current_size = task.output_path.stat().st_size
                            if current_size != task.downloaded_bytes:
                                task.downloaded_bytes = current_size
                                if task.file_size:
                                    task.update_progress(task.downloaded_bytes, task.file_size)
                                    self._notify_progress(task)
                                last_update_time = current_time
                
        except Exception as e:
            logger.debug(f"Progress tracking error: {e}")
    
    def _parse_size_to_bytes(self, size_str: str, unit: str) -> int:
        """
        Parse size string with unit to bytes.
        
        Args:
            size_str: Size as string (e.g., "123.4")
            unit: Unit (e.g., "MiB", "KiB")
            
        Returns:
            Size in bytes
        """
        try:
            size = float(size_str)
            
            # Convert based on unit (binary units)
            multipliers = {
                'B': 1,
                'iB': 1,
                'KiB': 1024,
                'MiB': 1024 ** 2,
                'GiB': 1024 ** 3,
                'TiB': 1024 ** 4,
            }
            
            multiplier = multipliers.get(unit, 1)
            return int(size * multiplier)
            
        except (ValueError, TypeError):
            return 0
    
    async def download_with_ytdlp_aria2c(self, task: DownloadTask) -> None:
        """
        Download using yt-dlp with better progress tracking.
        
        Instead of using aria2c as external downloader (which hides progress),
        we use yt-dlp's built-in progress tracking which works better for HLS.
        
        Args:
            task: Download task
        """
        try:
            import yt_dlp
            from concurrent.futures import ThreadPoolExecutor
            
            # Use yt-dlp without external downloader for better progress tracking
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
                # Don't use external downloader - yt-dlp's internal downloader has better progress
                'concurrent_fragment_downloads': min(self.connections, 4),  # Limit concurrent fragments
            }
            
            # Store reference to self for use in nested function
            downloader_self = self
            
            # Simple progress hook for yt-dlp
            def progress_hook(d):
                try:
                    if d['status'] == 'downloading':
                        # Update download progress
                        if 'total_bytes' in d and d['total_bytes']:
                            task.file_size = d['total_bytes']
                            task.downloaded_bytes = d.get('downloaded_bytes', 0)
                        elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                            task.file_size = d['total_bytes_estimate']
                            task.downloaded_bytes = d.get('downloaded_bytes', 0)
                        elif 'downloaded_bytes' in d:
                            task.downloaded_bytes = d['downloaded_bytes']
                            # Estimate total for HLS
                            if 'fragment_index' in d and 'fragment_count' in d:
                                fragment_index = d['fragment_index']
                                fragment_count = d['fragment_count']
                                if fragment_count and fragment_index and fragment_index > 0:
                                    estimated_total = (task.downloaded_bytes * fragment_count) // fragment_index
                                    task.file_size = max(task.file_size or 0, estimated_total)
                        
                        # Update speed and ETA
                        if 'speed' in d and d['speed']:
                            task.download_speed = int(d['speed'])
                        if 'eta' in d and d['eta']:
                            task.eta_seconds = int(d['eta'])
                        
                        # Update progress and notify
                        task.update_progress(task.downloaded_bytes, task.file_size)
                        downloader_self._notify_progress(task)
                        
                    elif d['status'] == 'finished':
                        # Final update
                        if task.output_path.exists():
                            final_size = task.output_path.stat().st_size
                            task.downloaded_bytes = final_size
                            task.file_size = final_size
                        
                        task.update_progress(task.downloaded_bytes, task.file_size)
                        downloader_self._notify_progress(task)
                        
                except Exception as e:
                    logger.error(f"Progress hook error: {e}")
                    # Try basic update
                    if 'downloaded_bytes' in d:
                        task.downloaded_bytes = d['downloaded_bytes']
                        task.update_progress(task.downloaded_bytes, task.file_size)
                        try:
                            downloader_self._notify_progress(task)
                        except:
                            pass
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            # Run yt-dlp in thread pool to avoid blocking
            def download_with_ytdlp():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([str(task.download_url)])
            
            # Execute in thread pool with fallback progress monitoring
            loop = asyncio.get_event_loop()
            
            # Start fallback progress monitoring
            async def monitor_file_progress():
                """Monitor file size as fallback progress tracking."""
                last_size = 0
                stall_count = 0
                
                while task.status.value == 'downloading':
                    try:
                        if task.output_path.exists():
                            current_size = task.output_path.stat().st_size
                            if current_size != last_size:
                                task.downloaded_bytes = current_size
                                # For HLS without total size, show indeterminate progress
                                if not task.file_size:
                                    # Show progress as downloaded bytes
                                    logger.debug(f"Fallback progress: {current_size} bytes downloaded")
                                else:
                                    task.update_progress(current_size, task.file_size)
                                    logger.debug(f"Fallback progress: {task.progress:.1f}%")
                                
                                self._notify_progress(task)
                                last_size = current_size
                                stall_count = 0
                            else:
                                stall_count += 1
                                # If no progress for 30 seconds, log warning
                                if stall_count >= 30:
                                    logger.warning("Download appears stalled - no file size change for 30 seconds")
                                    stall_count = 0
                        
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
            logger.error("yt-dlp not available for HLS downloads")
            raise DownloadError("yt-dlp required for HLS downloads")
        except Exception as e:
            raise DownloadError(f"yt-dlp HLS download failed: {e}", task.episode.title)


# Export aria2c downloader
__all__ = ["Aria2cDownloader"]