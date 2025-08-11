"""
Download Manager - High-level download coordination and UI integration.

This module provides the download manager that coordinates downloads
with the UI system, progress tracking, and user interaction.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from aniplux.core.downloader import Downloader
from aniplux.core.models import DownloadTask, Episode, Quality, DownloadStatus
from aniplux.core.exceptions import DownloadError
from aniplux.core.utils import generate_episode_filename
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    handle_error,
    format_success,
    format_warning,
    format_error,
)
from aniplux.ui.progress import download_progress_context


logger = logging.getLogger(__name__)


class DownloadManager:
    """
    High-level download manager with UI integration.
    
    Coordinates downloads with progress display, user feedback,
    and download queue management.
    """
    
    def __init__(self, config_manager: Any):
        """
        Initialize download manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.console = get_console()
        self.ui = UIComponents()
        
        # Initialize core downloader
        self.downloader = Downloader(config_manager)
        
        # Download tracking
        self.completed_downloads: List[DownloadTask] = []
        self.failed_downloads: List[DownloadTask] = []
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.total_bytes_downloaded = 0
    
    async def download_single_episode(
        self,
        episode: Episode,
        quality: Optional[Quality] = None,
        output_path: Optional[Path] = None,
        anime_title: Optional[str] = None,
        show_progress: bool = True
    ) -> DownloadTask:
        """
        Download a single episode with progress display.
        
        Args:
            episode: Episode to download
            quality: Preferred quality
            output_path: Custom output path
            anime_title: Anime title for filename
            show_progress: Whether to show progress bar
            
        Returns:
            Completed download task
        """
        self.start_time = datetime.now()
        
        try:
            if show_progress:
                # Determine actual quality that will be used
                actual_quality = quality or episode.best_quality
                
                # Create consistent task key
                task_key = f"{episode.url}_{actual_quality.value}"
                
                # Set up progress tracking with thread-safe callback
                with download_progress_context(episode.title, task_key):
                    # Add thread-safe progress callback
                    def progress_callback(updated_task):
                        try:
                            # Use consistent key generation
                            updated_key = f"{updated_task.episode.url}_{updated_task.quality.value}"
                            if updated_key == task_key:
                                # Use thread-safe progress update
                                from aniplux.ui.progress import thread_safe_update_progress
                                thread_safe_update_progress(
                                    task_key,
                                    updated_task.downloaded_bytes,
                                    updated_task.file_size or updated_task.downloaded_bytes,
                                    updated_task.download_speed
                                )
                        except Exception as e:
                            logger.debug(f"Progress callback error: {e}")
                    
                    self.downloader.add_progress_callback(progress_callback)
                    
                    try:
                        # Start download
                        task = await self.downloader.download_episode(
                            episode=episode,
                            quality=quality,
                            output_path=output_path,
                            anime_title=anime_title
                        )
                        
                        # Mark as finished
                        from aniplux.ui.progress import finish_download_progress
                        finish_download_progress(task_key)
                        
                    finally:
                        self.downloader.remove_progress_callback(progress_callback)
            else:
                # Download without progress display
                task = await self.downloader.download_episode(
                    episode=episode,
                    quality=quality,
                    output_path=output_path,
                    anime_title=anime_title
                )
            
            # Handle result
            if task.is_complete:
                self.completed_downloads.append(task)
                self.total_bytes_downloaded += task.downloaded_bytes
                
                self._display_download_success(task)
            else:
                self.failed_downloads.append(task)
                self._display_download_failure(task)
            
            return task
            
        except Exception as e:
            handle_error(e, f"Failed to download {episode.title}")
            raise
    
    async def download_batch_episodes(
        self,
        episodes: List[Episode],
        quality: Optional[Quality] = None,
        output_dir: Optional[Path] = None,
        anime_title: Optional[str] = None,
        show_progress: bool = True
    ) -> List[DownloadTask]:
        """
        Download multiple episodes with batch progress display.
        
        Args:
            episodes: List of episodes to download
            quality: Preferred quality for all episodes
            output_dir: Output directory
            anime_title: Anime title for filenames
            show_progress: Whether to show progress bars
            
        Returns:
            List of completed download tasks
        """
        if not episodes:
            display_warning("No episodes to download.")
            return []
        
        self.start_time = datetime.now()
        
        display_info(
            f"Starting batch download of {len(episodes)} episodes...",
            "📦 Batch Download"
        )
        
        try:
            # For batch downloads, download one at a time with individual progress
            tasks = []
            for episode in episodes:
                try:
                    task = await self.download_single_episode(
                        episode=episode,
                        quality=quality,
                        output_path=output_dir / generate_episode_filename(
                            anime_title or "Unknown Anime", episode, quality or episode.best_quality
                        ) if output_dir else None,
                        anime_title=anime_title,
                        show_progress=show_progress
                    )
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Failed to download {episode.title}: {e}")
                    # Create failed task
                    from aniplux.core.models import DownloadTask, DownloadStatus
                    failed_task = DownloadTask(
                        episode=episode,
                        quality=quality or episode.best_quality,
                        output_path=Path("failed"),
                        max_retries=3,
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
                        error_message=str(e),
                        retry_count=0
                    )
                    tasks.append(failed_task)
            
            # Process results
            successful_tasks = [t for t in tasks if t.is_complete]
            failed_tasks = [t for t in tasks if t.is_failed]
            
            self.completed_downloads.extend(successful_tasks)
            self.failed_downloads.extend(failed_tasks)
            
            # Update statistics
            for task in successful_tasks:
                self.total_bytes_downloaded += task.downloaded_bytes
            
            # Display batch results
            self._display_batch_results(successful_tasks, failed_tasks)
            
            return tasks
            
        except Exception as e:
            handle_error(e, "Batch download failed")
            raise
    
    def _display_download_success(self, task: DownloadTask) -> None:
        """Display successful download information."""
        duration = task.duration_seconds or 0
        file_size = task.formatted_file_size
        
        success_text = f"""
[green]✅ Download completed successfully![/green]

[bold]Episode:[/bold] {task.episode.title}
[bold]Quality:[/bold] {task.quality.value}
[bold]File Size:[/bold] {file_size}
[bold]Duration:[/bold] {duration}s
[bold]Output:[/bold] {task.output_path}

[dim]💡 File saved to: {task.output_path}[/dim]
"""
        
        panel = self.ui.create_success_panel(
            success_text.strip(),
            title="🎉 Download Complete"
        )
        
        self.console.print()
        self.console.print(panel)
    
    def _display_download_failure(self, task: DownloadTask) -> None:
        """Display failed download information."""
        error_text = f"""
[red]❌ Download failed[/red]

[bold]Episode:[/bold] {task.episode.title}
[bold]Quality:[/bold] {task.quality.value}
[bold]Error:[/bold] {task.error_message or 'Unknown error'}
[bold]Retries:[/bold] {task.retry_count}/{task.max_retries}

[yellow]💡 Suggestions:[/yellow]
• Check your internet connection
• Try a different quality setting
• Verify the episode URL is still valid
• Check available disk space
"""
        
        panel = self.ui.create_error_panel(
            error_text.strip(),
            title="💥 Download Failed"
        )
        
        self.console.print()
        self.console.print(panel)
    
    def _display_batch_results(
        self,
        successful_tasks: List[DownloadTask],
        failed_tasks: List[DownloadTask]
    ) -> None:
        """Display batch download results summary."""
        total_tasks = len(successful_tasks) + len(failed_tasks)
        success_count = len(successful_tasks)
        failure_count = len(failed_tasks)
        
        # Calculate total size and time
        total_size = sum(task.downloaded_bytes for task in successful_tasks)
        total_time = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        # Format statistics
        from aniplux.core.utils import format_file_size
        total_size_str = format_file_size(total_size)
        avg_speed = total_size / total_time if total_time > 0 else 0
        avg_speed_str = format_file_size(int(avg_speed)) + "/s"
        
        # Create results summary
        if failure_count == 0:
            # All successful
            summary_text = f"""
[green]🎉 Batch download completed successfully![/green]

[bold]Results:[/bold]
• {success_count}/{total_tasks} episodes downloaded
• Total size: {total_size_str}
• Average speed: {avg_speed_str}
• Total time: {total_time:.1f}s

[dim]All files saved to the configured download directory.[/dim]
"""
            panel = self.ui.create_success_panel(
                summary_text.strip(),
                title="📦 Batch Download Complete"
            )
        else:
            # Some failures
            summary_text = f"""
[yellow]⚠️  Batch download completed with some failures[/yellow]

[bold]Results:[/bold]
• [green]{success_count} successful[/green]
• [red]{failure_count} failed[/red]
• Total size: {total_size_str}
• Average speed: {avg_speed_str}
• Total time: {total_time:.1f}s

[bold]Failed episodes:[/bold]
"""
            
            # Add failed episode details
            for task in failed_tasks[:5]:  # Show first 5 failures
                summary_text += f"\n• {task.episode.title}: {task.error_message or 'Unknown error'}"
            
            if len(failed_tasks) > 5:
                summary_text += f"\n• ... and {len(failed_tasks) - 5} more"
            
            summary_text += "\n\n[dim]Use 'aniplux download retry' to retry failed downloads.[/dim]"
            
            panel = self.ui.create_warning_panel(
                summary_text.strip(),
                title="📦 Batch Download Results"
            )
        
        self.console.print()
        self.console.print(panel)
    
    def display_download_status(self) -> None:
        """Display current download status and statistics."""
        active_downloads = self.downloader.get_active_downloads()
        
        if not active_downloads and not self.completed_downloads and not self.failed_downloads:
            display_info("No downloads in progress or completed.", "📊 Download Status")
            return
        
        # Create status display
        status_parts = []
        
        # Active downloads
        if active_downloads:
            status_parts.append(f"[blue]Active Downloads:[/blue] {len(active_downloads)}")
            
            # Show active downloads table
            active_table = self.ui.create_download_status_table(active_downloads)
            self.console.print(active_table)
            self.console.print()
        
        # Completed downloads
        if self.completed_downloads:
            status_parts.append(f"[green]Completed:[/green] {len(self.completed_downloads)}")
        
        # Failed downloads
        if self.failed_downloads:
            status_parts.append(f"[red]Failed:[/red] {len(self.failed_downloads)}")
        
        # Statistics
        if self.total_bytes_downloaded > 0:
            from aniplux.core.utils import format_file_size
            total_size_str = format_file_size(self.total_bytes_downloaded)
            status_parts.append(f"[dim]Total Downloaded:[/dim] {total_size_str}")
        
        # Display summary
        if status_parts:
            summary_text = " • ".join(status_parts)
            
            panel = self.ui.create_info_panel(
                summary_text,
                title="📊 Download Statistics"
            )
            
            self.console.print(panel)
    
    def get_failed_downloads(self) -> List[DownloadTask]:
        """
        Get list of failed downloads for retry.
        
        Returns:
            List of failed download tasks
        """
        return self.failed_downloads.copy()
    
    def clear_completed_downloads(self) -> int:
        """
        Clear completed downloads from history.
        
        Returns:
            Number of downloads cleared
        """
        count = len(self.completed_downloads)
        self.completed_downloads.clear()
        return count
    
    def clear_failed_downloads(self) -> int:
        """
        Clear failed downloads from history.
        
        Returns:
            Number of downloads cleared
        """
        count = len(self.failed_downloads)
        self.failed_downloads.clear()
        return count
    
    async def retry_failed_downloads(self) -> List[DownloadTask]:
        """
        Retry all failed downloads.
        
        Returns:
            List of retry results
        """
        if not self.failed_downloads:
            display_info("No failed downloads to retry.", "🔄 Retry Downloads")
            return []
        
        display_info(
            f"Retrying {len(self.failed_downloads)} failed downloads...",
            "🔄 Retry Downloads"
        )
        
        # Extract episodes from failed tasks
        episodes = [task.episode for task in self.failed_downloads]
        qualities = [task.quality for task in self.failed_downloads]
        
        # Clear failed downloads
        self.failed_downloads.clear()
        
        # Retry downloads
        retry_tasks = []
        for episode, quality in zip(episodes, qualities):
            try:
                task = await self.download_single_episode(
                    episode=episode,
                    quality=quality,
                    show_progress=False  # Don't show individual progress for retries
                )
                retry_tasks.append(task)
            except Exception as e:
                logger.error(f"Retry failed for {episode.title}: {e}")
        
        return retry_tasks
    
    async def cleanup(self) -> None:
        """Clean up download manager resources."""
        await self.downloader.cleanup()
        
        # Clear download history
        self.completed_downloads.clear()
        self.failed_downloads.clear()
        
        logger.info("Download manager cleanup complete")


# Export download manager
__all__ = ["DownloadManager"]