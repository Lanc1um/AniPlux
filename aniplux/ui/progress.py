"""
Progress Management - Simple and reliable progress tracking.

This module provides a clean, simple progress system without race conditions.
"""

import asyncio
import threading
import queue
import time
from contextlib import contextmanager
from typing import Optional, Dict, List
from datetime import datetime

from rich.progress import (
    Progress,
    ProgressColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    SpinnerColumn,
    TransferSpeedColumn,
    FileSizeColumn,
    TaskID
)
from rich.live import Live
from rich.status import Status
from contextlib import contextmanager

from aniplux.ui.console import get_console


class SimpleProgressManager:
    """Simple, thread-safe progress manager."""
    
    def __init__(self):
        self.console = get_console()
        self._progress: Optional[Progress] = None
        self._live: Optional[Live] = None
        self._tasks: Dict[str, TaskID] = {}
        self._lock = threading.Lock()
        self._active = False
        
        # Thread-safe update queue
        self._update_queue = queue.Queue()
        self._update_thread: Optional[threading.Thread] = None
        self._stop_updates = threading.Event()
    
    def start_download_progress(self, episode_title: str, task_key: str) -> None:
        """Start progress tracking for a download."""
        with self._lock:
            if not self._active:
                # Create progress display
                self._progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold blue]{task.fields[title]}", justify="left"),
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    FileSizeColumn(),
                    "•",
                    TransferSpeedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    console=self.console,
                    expand=True
                )
                
                # Start live display
                self._live = Live(self._progress, console=self.console, refresh_per_second=4)
                self._live.start()
                self._active = True
                
                # Start update thread
                self._stop_updates.clear()
                self._update_thread = threading.Thread(target=self._update_worker, daemon=True)
                self._update_thread.start()
            
            # Add task
            if self._progress:
                task_id = self._progress.add_task(
                    description="",
                    title=episode_title,
                    total=100,
                    completed=0
                )
                self._tasks[task_key] = task_id
    
    def update_progress(self, task_key: str, downloaded: int, total: int, speed: float = 0) -> None:
        """Update progress for a task."""
        if not self._active:
            return
        
        # Queue update for thread-safe processing
        try:
            self._update_queue.put_nowait({
                'action': 'update',
                'task_key': task_key,
                'downloaded': downloaded,
                'total': total,
                'speed': speed
            })
        except queue.Full:
            # Skip update if queue is full to avoid blocking
            pass
    
    def finish_progress(self, task_key: str) -> None:
        """Mark a task as finished."""
        if not self._active:
            return
        
        # Queue finish action
        try:
            self._update_queue.put_nowait({
                'action': 'finish',
                'task_key': task_key
            })
        except queue.Full:
            pass
    
    def stop_progress(self) -> None:
        """Stop all progress tracking."""
        with self._lock:
            self._active = False
            
            # Stop update thread
            if self._update_thread and self._update_thread.is_alive():
                self._stop_updates.set()
                self._update_thread.join(timeout=1.0)
            
            if self._live:
                self._live.stop()
                self._live = None
            
            self._progress = None
            self._tasks.clear()
            
            # Clear update queue
            while not self._update_queue.empty():
                try:
                    self._update_queue.get_nowait()
                except queue.Empty:
                    break
    
    def _update_worker(self) -> None:
        """Worker thread for processing progress updates."""
        while not self._stop_updates.is_set():
            try:
                # Get update with timeout
                update = self._update_queue.get(timeout=0.1)
                
                with self._lock:
                    if not self._active or not self._progress:
                        continue
                    
                    task_key = update['task_key']
                    if task_key not in self._tasks:
                        continue
                    
                    task_id = self._tasks[task_key]
                    
                    if update['action'] == 'update':
                        # Update progress
                        downloaded = update['downloaded']
                        total = update['total']
                        
                        # Handle HLS streams with unknown total
                        if total <= 0:
                            # For HLS, show indeterminate progress
                            total = max(downloaded, 1)  # Avoid division by zero
                        
                        self._progress.update(
                            task_id,
                            completed=downloaded,
                            total=max(total, downloaded),
                            refresh=True
                        )
                        
                    elif update['action'] == 'finish':
                        # Mark as complete
                        task = self._progress.tasks[task_id]
                        self._progress.update(
                            task_id,
                            completed=task.total,
                            refresh=True
                        )
                
            except queue.Empty:
                continue
            except Exception as e:
                # Log error but continue
                import logging
                logging.getLogger(__name__).debug(f"Progress update error: {e}")
                continue


# Global progress manager
_progress_manager = SimpleProgressManager()


def get_progress_manager() -> SimpleProgressManager:
    """Get the global progress manager."""
    return _progress_manager


@contextmanager
def download_progress_context(episode_title: str, task_key: str):
    """Context manager for download progress."""
    manager = get_progress_manager()
    
    try:
        manager.start_download_progress(episode_title, task_key)
        yield manager
    finally:
        manager.stop_progress()


def update_download_progress(task_key: str, downloaded: int, total: int, speed: float = 0) -> None:
    """Update download progress."""
    _progress_manager.update_progress(task_key, downloaded, total, speed)


def thread_safe_update_progress(task_key: str, downloaded: int, total: int, speed: float = 0) -> None:
    """Thread-safe update download progress."""
    _progress_manager.update_progress(task_key, downloaded, total, speed)


def finish_download_progress(task_key: str) -> None:
    """Finish download progress."""
    _progress_manager.finish_progress(task_key)


@contextmanager
def status_spinner(message: str, spinner: str = "dots"):
    """Simple status spinner context manager."""
    console = get_console()
    status = Status(message, spinner=spinner, console=console)
    
    try:
        status.start()
        yield status
    finally:
        status.stop()


@contextmanager
def search_progress(sources: List[str]):
    """Simple search progress context manager."""
    console = get_console()
    status = Status(f"Searching {len(sources)} sources...", spinner="dots", console=console)
    
    try:
        status.start()
        yield None  # Simple implementation, just show spinner
    finally:
        status.stop()


# Export components
__all__ = [
    "SimpleProgressManager",
    "get_progress_manager", 
    "download_progress_context",
    "update_download_progress",
    "thread_safe_update_progress",
    "finish_download_progress",
    "status_spinner",
    "search_progress"
]