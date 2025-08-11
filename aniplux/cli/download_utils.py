"""
Download Utilities - Helper functions for download operations.

This module provides utility functions for download-related operations
including URL validation, file handling, and download preparation.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urlparse, unquote

from aniplux.core.models import Episode, Quality
from aniplux.core.exceptions import DownloadError, ValidationError
from aniplux.core.utils import sanitize_filename


logger = logging.getLogger(__name__)


def validate_download_url(url: str) -> bool:
    """
    Validate if a URL is suitable for downloading.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid for downloading
    """
    try:
        parsed = urlparse(url)
        
        # Check basic URL structure
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check for supported schemes
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check for obvious non-video URLs
        path_lower = parsed.path.lower()
        invalid_extensions = ['.html', '.php', '.asp', '.jsp', '.txt', '.json', '.xml']
        
        for ext in invalid_extensions:
            if path_lower.endswith(ext):
                return False
        
        return True
        
    except Exception:
        return False


def extract_filename_from_url(url: str) -> Optional[str]:
    """
    Extract filename from URL.
    
    Args:
        url: URL to extract filename from
        
    Returns:
        Extracted filename or None if not found
    """
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        if path and '/' in path:
            filename = path.split('/')[-1]
            if filename and '.' in filename:
                return sanitize_filename(filename)
        
        return None
        
    except Exception:
        return None


def guess_quality_from_url(url: str) -> Optional[Quality]:
    """
    Guess video quality from URL patterns.
    
    Args:
        url: URL to analyze
        
    Returns:
        Guessed quality or None if not determinable
    """
    url_lower = url.lower()
    
    # Common quality patterns in URLs
    quality_patterns = {
        Quality.FOUR_K: [r'2160p?', r'4k', r'uhd'],
        Quality.ULTRA: [r'1440p?', r'2k'],
        Quality.HIGH: [r'1080p?', r'fhd', r'full.?hd'],
        Quality.MEDIUM: [r'720p?', r'hd'],
        Quality.LOW: [r'480p?', r'sd', r'360p?']
    }
    
    for quality, patterns in quality_patterns.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return quality
    
    return None


def prepare_download_directory(output_path: Path) -> None:
    """
    Prepare download directory and validate permissions.
    
    Args:
        output_path: Path where file will be downloaded
        
    Raises:
        DownloadError: If directory cannot be prepared
    """
    try:
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = output_path.parent / ".aniplux_write_test"
        test_file.touch()
        test_file.unlink()
        
    except PermissionError:
        raise DownloadError(f"No write permission for directory: {output_path.parent}")
    except OSError as e:
        raise DownloadError(f"Cannot create download directory: {e}")


def check_disk_space(output_path: Path, required_bytes: Optional[int] = None) -> bool:
    """
    Check if there's enough disk space for download.
    
    Args:
        output_path: Path where file will be downloaded
        required_bytes: Required space in bytes (optional)
        
    Returns:
        True if there's enough space
    """
    try:
        import shutil
        
        # Get available disk space
        free_bytes = shutil.disk_usage(output_path.parent).free
        
        # If no specific requirement, check for at least 100MB
        min_required = required_bytes or (100 * 1024 * 1024)
        
        return free_bytes >= min_required
        
    except Exception:
        # If we can't check, assume it's okay
        return True


def generate_download_filename(
    episode: Episode,
    quality: Quality,
    anime_title: Optional[str] = None,
    extension: str = "mp4"
) -> str:
    """
    Generate a standardized filename for episode download.
    
    Args:
        episode: Episode to download
        quality: Video quality
        anime_title: Anime title (optional)
        extension: File extension
        
    Returns:
        Generated filename
    """
    # Use anime title or fallback
    title = anime_title or "Unknown Anime"
    
    # Format episode number with leading zeros
    episode_num = f"E{episode.number:02d}"
    
    # Clean episode title
    episode_title = episode.title.replace(':', ' -')
    
    # Create filename
    filename = f"{title} - {episode_num} - {episode_title} [{quality.value}].{extension}"
    
    return sanitize_filename(filename)


def parse_episode_urls(urls: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Parse episode URLs and extract metadata.
    
    Args:
        urls: List of episode URLs
        
    Returns:
        List of tuples (url, metadata_dict)
    """
    parsed_urls = []
    
    for url in urls:
        metadata = {
            'url': url,
            'filename': extract_filename_from_url(url),
            'quality': guess_quality_from_url(url),
            'valid': validate_download_url(url)
        }
        
        parsed_urls.append((url, metadata))
    
    return parsed_urls


def estimate_download_time(
    file_size: int,
    download_speed: float,
    concurrent_downloads: int = 1
) -> int:
    """
    Estimate download time in seconds.
    
    Args:
        file_size: File size in bytes
        download_speed: Download speed in bytes per second
        concurrent_downloads: Number of concurrent downloads
        
    Returns:
        Estimated time in seconds
    """
    if download_speed <= 0:
        return 0
    
    # Account for overhead with concurrent downloads
    effective_speed = download_speed * (0.8 if concurrent_downloads > 1 else 1.0)
    
    return int(file_size / effective_speed)


def format_download_summary(
    total_files: int,
    successful: int,
    failed: int,
    total_size: int,
    total_time: float
) -> str:
    """
    Format download summary statistics.
    
    Args:
        total_files: Total number of files
        successful: Number of successful downloads
        failed: Number of failed downloads
        total_size: Total bytes downloaded
        total_time: Total time in seconds
        
    Returns:
        Formatted summary string
    """
    from aniplux.core.utils import format_file_size
    
    # Format file size
    size_str = format_file_size(total_size)
    
    # Calculate average speed
    if total_time > 0:
        avg_speed = total_size / total_time
        speed_str = format_file_size(int(avg_speed)) + "/s"
    else:
        speed_str = "N/A"
    
    # Format time
    if total_time >= 3600:
        time_str = f"{total_time // 3600:.0f}h {(total_time % 3600) // 60:.0f}m"
    elif total_time >= 60:
        time_str = f"{total_time // 60:.0f}m {total_time % 60:.0f}s"
    else:
        time_str = f"{total_time:.1f}s"
    
    # Create summary
    summary_parts = [
        f"Files: {successful}/{total_files}",
        f"Size: {size_str}",
        f"Speed: {speed_str}",
        f"Time: {time_str}"
    ]
    
    if failed > 0:
        summary_parts.insert(1, f"Failed: {failed}")
    
    return " • ".join(summary_parts)


def create_download_report(download_tasks: List[Any]) -> Dict[str, Any]:
    """
    Create a comprehensive download report.
    
    Args:
        download_tasks: List of completed download tasks
        
    Returns:
        Dictionary containing download statistics
    """
    if not download_tasks:
        return {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "total_size": 0,
            "total_time": 0,
            "average_speed": 0,
            "success_rate": 0
        }
    
    successful_tasks = [t for t in download_tasks if t.is_complete]
    failed_tasks = [t for t in download_tasks if t.is_failed]
    
    total_size = sum(t.downloaded_bytes for t in successful_tasks)
    
    # Calculate total time (from first start to last completion)
    start_times = [t.start_time for t in download_tasks if t.start_time]
    end_times = [t.end_time for t in download_tasks if t.end_time]
    
    if start_times and end_times:
        total_time = (max(end_times) - min(start_times)).total_seconds()
    else:
        total_time = 0
    
    # Calculate average speed
    avg_speed = total_size / total_time if total_time > 0 else 0
    
    # Calculate success rate
    success_rate = len(successful_tasks) / len(download_tasks) * 100 if download_tasks else 0
    
    return {
        "total_files": len(download_tasks),
        "successful": len(successful_tasks),
        "failed": len(failed_tasks),
        "total_size": total_size,
        "total_time": total_time,
        "average_speed": avg_speed,
        "success_rate": success_rate,
        "summary": format_download_summary(
            len(download_tasks),
            len(successful_tasks),
            len(failed_tasks),
            total_size,
            total_time
        )
    }


# Export utility functions
__all__ = [
    "validate_download_url",
    "extract_filename_from_url",
    "guess_quality_from_url",
    "prepare_download_directory",
    "check_disk_space",
    "generate_download_filename",
    "parse_episode_urls",
    "estimate_download_time",
    "format_download_summary",
    "create_download_report",
]