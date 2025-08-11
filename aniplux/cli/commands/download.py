"""
Download Command - Episode download functionality.

This module implements the download command for downloading anime episodes
with progress tracking and quality selection.
"""

import asyncio
import logging
import typer
from typing import Optional, List, Any
from pathlib import Path

from aniplux.cli.context import get_config_manager
from aniplux.cli.download_manager import DownloadManager
from aniplux.core.models import Quality, Episode
from aniplux.core.exceptions import DownloadError, PluginError
from aniplux.ui import (
    get_console,
    handle_error,
    display_info,
    display_warning,
    status_spinner,
)

# Create download command group
app = typer.Typer(
    name="download",
    help="⬇️  Download anime episodes with progress tracking",
    no_args_is_help=True,
)

console = get_console()
logger = logging.getLogger(__name__)


async def _extract_anime_title_from_episode_url(url: str, source: str, config_manager: Any) -> str:
    """
    Extract anime title from episode URL using the appropriate plugin.
    
    Args:
        url: Episode URL
        source: Source plugin name
        config_manager: Configuration manager instance
        
    Returns:
        Anime title or "Unknown Anime" if extraction fails
    """
    plugin_manager = None
    try:
        from aniplux.core import PluginManager
        from urllib.parse import urlparse
        import re
        
        # For Animetsu URLs, extract anime ID and fetch title from API
        if ('animetsu.to' in url or 'animetsu.cc' in url) and source == 'animetsu_plugin':
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            
            # URL format: https://animetsu.to/watch/{anime_id}/{episode_number}
            if len(path_parts) >= 3 and path_parts[1] == 'watch':
                anime_id = path_parts[2]
                
                try:
                    # Load the plugin and get anime info
                    plugin_manager = PluginManager(config_manager)
                    plugin = await plugin_manager.load_plugin('animetsu_plugin')
                    
                    if plugin and hasattr(plugin, 'api') and hasattr(plugin, 'parser'):
                        api = getattr(plugin, 'api')
                        parser = getattr(plugin, 'parser')
                        anime_info = await api.get_anime_info(anime_id)
                        if anime_info:
                            title = parser.extract_anime_title(anime_info)
                            if title and title != "Unknown Anime":
                                return title
                except Exception as e:
                    logger.debug(f"Failed to fetch anime title from Animetsu API: {e}")
        
        # Fallback to URL-based extraction
        from aniplux.core.utils import extract_anime_title_from_url
        return extract_anime_title_from_url(url)
        
    except Exception as e:
        logger.debug(f"Failed to extract anime title from URL: {e}")
        return "Unknown Anime"
    finally:
        # Clean up plugin manager after title extraction
        if plugin_manager:
            try:
                await plugin_manager.cleanup()
            except Exception as cleanup_error:
                logger.debug(f"Plugin manager cleanup error in title extraction: {cleanup_error}")


def _extract_episode_number_from_url(url: str) -> int:
    """
    Extract episode number from episode URL.
    
    Args:
        url: Episode URL
        
    Returns:
        Episode number or 1 if extraction fails
    """
    try:
        from urllib.parse import urlparse, parse_qs
        import re
        
        parsed_url = urlparse(url)
        
        # For Animetsu URLs: https://animetsu.to/watch/{anime_id}/{episode_number}
        if 'animetsu.to' in parsed_url.netloc:
            path_parts = parsed_url.path.split('/')
            if len(path_parts) >= 4 and path_parts[1] == 'watch':
                try:
                    return int(path_parts[3])
                except (ValueError, IndexError):
                    pass
        
        # For HiAnime URLs: extract from query parameter
        elif 'hianime.to' in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            if 'ep' in query_params:
                # This is usually an internal ID, not the actual episode number
                # For now, we'll extract from the URL path or default to 1
                pass
        
        # Generic approach: look for numbers in the path
        path_parts = parsed_url.path.split('/')
        for part in reversed(path_parts):  # Check from end to beginning
            if part.isdigit():
                return int(part)
            # Look for patterns like "episode-5" or "ep5"
            match = re.search(r'(?:episode|ep)[-_]?(\d+)', part, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return 1  # Default episode number
        
    except Exception as e:
        logger.debug(f"Failed to extract episode number from URL: {e}")
        return 1


def _extract_hianime_info(url: str) -> tuple[str, int]:
    """
    Extract anime title and episode number from HiAnime URL.
    
    Args:
        url: HiAnime episode URL
        
    Returns:
        Tuple of (anime_title, episode_number)
    """
    try:
        import re
        from urllib.parse import parse_qs, urlparse
        
        # Extract anime title from URL path
        # URL format: https://hianime.to/watch/demon-slayer-kimetsu-no-yaiba-swordsmith-village-arc-18056?ep=100090
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        
        if len(path_parts) >= 3 and path_parts[1] == 'watch':
            anime_slug = path_parts[2]
            # Remove the ID at the end (e.g., -18056)
            anime_slug = re.sub(r'-\d+$', '', anime_slug)
            # Convert slug to title and clean it up
            anime_title = anime_slug.replace('-', ' ').title()
            # Fix common title issues
            anime_title = anime_title.replace(' And ', ' and ')
            anime_title = anime_title.replace(' Of ', ' of ')
            anime_title = anime_title.replace(' The ', ' the ')
            anime_title = anime_title.replace(' To ', ' to ')
            anime_title = anime_title.replace(' No ', ' no ')
        else:
            anime_title = "Unknown Anime"
        
        # Extract episode number from query parameter
        query_params = parse_qs(parsed_url.query)
        episode_number = 1
        if 'ep' in query_params:
            try:
                # The ep parameter might be an internal ID, so we'll just use 1 for now
                # In a real implementation, you'd need to map this to the actual episode number
                episode_number = 1
            except ValueError:
                episode_number = 1
        
        return anime_title, episode_number
        
    except Exception as e:
        logger.debug(f"Failed to extract HiAnime info from URL: {e}")
        return "Unknown Anime", 1


@app.command()
def episode(
    url: str = typer.Argument(..., help="Episode URL to download"),
    quality: Optional[Quality] = typer.Option(
        None,
        "--quality",
        "-q",
        help="Video quality preference",
        case_sensitive=False
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path"
    ),
    anime_title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="Anime title for filename generation"
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Source plugin name (auto-detected if not specified)"
    ),
) -> None:
    """
    ⬇️  Download a single episode.
    
    Download an anime episode from the provided URL with optional
    quality selection and custom output path.
    
    Examples:
    
        aniplux download episode "https://example.com/episode/1"
        
        aniplux download episode "https://example.com/ep/1" --quality 1080p --title "Naruto"
        
        aniplux download episode "https://example.com/ep/1" --output "/path/to/file.mp4"
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_download_single_episode(
            url=url,
            quality=quality,
            output_path=output,
            anime_title=anime_title,
            source=source,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Download cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During episode download")
        raise typer.Exit(1)


async def _download_single_episode(
    url: str,
    quality: Optional[Quality],
    output_path: Optional[Path],
    anime_title: Optional[str],
    source: Optional[str],
    config_manager: Any
) -> None:
    """
    Download a single episode.
    
    Args:
        url: Episode URL
        quality: Preferred quality
        output_path: Custom output path
        anime_title: Anime title
        source: Source plugin name
        config_manager: Configuration manager instance
    """
    try:
        # Determine source plugin if not provided
        if not source:
            if 'hianime.to' in url:
                source = 'hianime_plugin'
            elif 'animetsu.to' in url or 'animetsu.cc' in url:
                source = 'animetsu_plugin'
            else:
                source = 'sample'  # fallback
        
        # Extract anime info from URL for better filename
        if not anime_title:
            anime_title = await _extract_anime_title_from_episode_url(url, source, config_manager)
        
        # Extract episode number from URL
        episode_number = _extract_episode_number_from_url(url)
        
        # Create episode object from URL
        from pydantic import HttpUrl
        episode = Episode(
            number=episode_number,
            title=anime_title or "Unknown Episode",
            url=HttpUrl(url),
            source=source,
            quality_options=[quality] if quality else [Quality.HIGH, Quality.MEDIUM, Quality.LOW],
            duration=None,
            description=None,
            thumbnail=None,
            air_date=None,
            filler=False
        )
        
        # Initialize download manager
        download_manager = DownloadManager(config_manager)
        
        try:
            # Start download
            await download_manager.download_single_episode(
                episode=episode,
                quality=quality,
                output_path=output_path,
                anime_title=anime_title
            )
        finally:
            # Clean up download manager resources
            try:
                await download_manager.cleanup()
            except Exception as cleanup_error:
                logger.debug(f"Download manager cleanup error: {cleanup_error}")
        
    except DownloadError as e:
        handle_error(e, "Download failed")
    except Exception as e:
        handle_error(e, "Unexpected error during download")


@app.command(name="batch")
def download_batch(
    urls: List[str] = typer.Argument(..., help="Episode URLs to download"),
    quality: Optional[Quality] = typer.Option(
        None,
        "--quality",
        "-q",
        help="Video quality preference",
        case_sensitive=False
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-d",
        help="Output directory"
    ),
    anime_title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="Anime title for filename generation"
    ),
    concurrent: Optional[int] = typer.Option(
        None,
        "--concurrent",
        "-c",
        help="Override concurrent downloads setting",
        min=1,
        max=10
    ),
) -> None:
    """
    📦 Download multiple episodes in batch.
    
    Download multiple anime episodes concurrently with progress tracking
    for each episode and overall batch statistics.
    
    Examples:
    
        aniplux download batch "https://example.com/ep/1" "https://example.com/ep/2"
        
        aniplux download batch "https://example.com/ep/1" "https://example.com/ep/2" --quality 720p
        
        aniplux download batch "https://example.com/ep/1" "https://example.com/ep/2" --output-dir ./downloads
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_download_batch_episodes(
            urls=urls,
            quality=quality,
            output_dir=output_dir,
            anime_title=anime_title,
            concurrent=concurrent,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Batch download cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During batch download")
        raise typer.Exit(1)


async def _download_batch_episodes(
    urls: List[str],
    quality: Optional[Quality],
    output_dir: Optional[Path],
    anime_title: Optional[str],
    concurrent: Optional[int],
    config_manager: Any
) -> None:
    """
    Download multiple episodes in batch.
    
    Args:
        urls: List of episode URLs
        quality: Preferred quality
        output_dir: Output directory
        anime_title: Anime title
        concurrent: Concurrent downloads override
        config_manager: Configuration manager instance
    """
    if not urls:
        display_warning("No URLs provided for batch download.")
        return
    
    try:
        # Create episode objects from URLs
        episodes = []
        from pydantic import HttpUrl
        for i, url in enumerate(urls, 1):
            episode = Episode(
                number=i,  # Sequential numbering for batch
                title=f"{anime_title or 'Episode'} {i}",
                url=HttpUrl(url),
                source="unknown",
                quality_options=[quality] if quality else [Quality.HIGH, Quality.MEDIUM, Quality.LOW],
                duration=None,
                description=None,
                thumbnail=None,
                air_date=None,
                filler=False
            )
            episodes.append(episode)
        
        # Initialize download manager
        download_manager = DownloadManager(config_manager)
        
        # Override concurrent downloads if specified
        if concurrent:
            download_manager.downloader.concurrent_downloads = concurrent
            download_manager.downloader.download_semaphore = asyncio.Semaphore(concurrent)
        
        # Start batch download
        await download_manager.download_batch_episodes(
            episodes=episodes,
            quality=quality,
            output_dir=output_dir,
            anime_title=anime_title
        )
        
    except DownloadError as e:
        handle_error(e, "Batch download failed")
    except Exception as e:
        handle_error(e, "Unexpected error during batch download")


@app.command(name="status")
def download_status() -> None:
    """
    📊 Show download queue status.
    
    Display current download progress, completed downloads,
    failed downloads, and overall statistics.
    """
    try:
        config_manager = get_config_manager()
        download_manager = DownloadManager(config_manager)
        
        download_manager.display_download_status()
        
    except Exception as e:
        handle_error(e, "Failed to get download status")
        raise typer.Exit(1)


@app.command(name="info")
def download_info() -> None:
    """
    ℹ️  Show download configuration and capabilities.
    
    Display current download settings, aria2c availability,
    and other download-related information.
    """
    try:
        config_manager = get_config_manager()
        settings = config_manager.settings.settings
        
        # Check aria2c availability
        from aniplux.core.aria2c_downloader import Aria2cDownloader
        aria2c_downloader = Aria2cDownloader(config_manager)
        aria2c_available = aria2c_downloader.is_available()
        
        # Prepare info text
        info_parts = []
        
        # Download settings
        info_parts.append("[bold blue]Download Settings:[/bold blue]")
        info_parts.append(f"• Download Directory: {settings.download_directory}")
        info_parts.append(f"• Default Quality: {settings.default_quality}")
        info_parts.append(f"• Concurrent Downloads: {settings.concurrent_downloads}")
        info_parts.append(f"• Timeout: {settings.timeout}s")
        info_parts.append(f"• Max Retries: {settings.max_retries}")
        info_parts.append("")
        
        # Aria2c settings
        info_parts.append("[bold blue]Aria2c Configuration:[/bold blue]")
        info_parts.append(f"• Enabled: {'✅ Yes' if settings.use_aria2c else '❌ No'}")
        info_parts.append(f"• Available: {'✅ Yes' if aria2c_available else '❌ No'}")
        
        if aria2c_available:
            info_parts.append(f"• Path: {aria2c_downloader.aria2c_path}")
            info_parts.append(f"• Connections per server: {settings.aria2c_connections}")
            info_parts.append(f"• Split pieces: {settings.aria2c_split}")
            info_parts.append(f"• Min split size: {settings.aria2c_min_split_size}")
        elif settings.use_aria2c:
            info_parts.append("• [yellow]aria2c is enabled but not found in PATH[/yellow]")
            info_parts.append("• [dim]Install aria2c for faster downloads[/dim]")
        
        info_parts.append("")
        
        # Download capabilities
        info_parts.append("[bold blue]Download Capabilities:[/bold blue]")
        info_parts.append("• Direct HTTP/HTTPS downloads: ✅ Yes")
        info_parts.append("• HLS streams (.m3u8): ✅ Yes (via yt-dlp)")
        info_parts.append(f"• Multi-connection downloads: {'✅ Yes (aria2c)' if aria2c_available else '❌ No (aria2c required)'}")
        info_parts.append(f"• Resume downloads: {'✅ Yes (aria2c)' if aria2c_available else '⚠️  Limited'}")
        
        info_text = "\n".join(info_parts)
        
        display_info(info_text, "⬇️  Download Information")
        
        # Show installation instructions if aria2c is not available
        if settings.use_aria2c and not aria2c_available:
            console.print()
            display_warning(
                "aria2c is not available but enabled in settings.\n\n"
                "[bold]To install aria2c:[/bold]\n"
                "• Windows: Download from https://aria2.github.io/ or use chocolatey: choco install aria2\n"
                "• macOS: brew install aria2\n"
                "• Ubuntu/Debian: sudo apt install aria2\n"
                "• Other Linux: Check your package manager\n\n"
                "After installation, restart AniPlux to enable faster downloads.",
                "⚠️  aria2c Not Found"
            )
        
    except Exception as e:
        handle_error(e, "Failed to get download information")
        raise typer.Exit(1)


@app.command(name="retry")
def retry_downloads() -> None:
    """
    🔄 Retry failed downloads.
    
    Retry all previously failed downloads with the same settings.
    Useful for recovering from network issues or temporary failures.
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_retry_failed_downloads(config_manager))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Retry cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During download retry")
        raise typer.Exit(1)


async def _retry_failed_downloads(config_manager: Any) -> None:
    """
    Retry failed downloads.
    
    Args:
        config_manager: Configuration manager instance
    """
    download_manager = DownloadManager(config_manager)
    
    failed_downloads = download_manager.get_failed_downloads()
    
    if not failed_downloads:
        display_info("No failed downloads to retry.", "🔄 Retry Downloads")
        return
    
    await download_manager.retry_failed_downloads()


@app.command(name="clear")
def clear_downloads(
    completed: bool = typer.Option(
        False,
        "--completed",
        help="Clear completed downloads from history"
    ),
    failed: bool = typer.Option(
        False,
        "--failed",
        help="Clear failed downloads from history"
    ),
    all_downloads: bool = typer.Option(
        False,
        "--all",
        help="Clear all downloads from history"
    ),
) -> None:
    """
    🗑️  Clear download history.
    
    Clear completed or failed downloads from the download history.
    Useful for cleaning up the download status display.
    
    Examples:
    
        aniplux download clear --completed
        
        aniplux download clear --failed
        
        aniplux download clear --all
    """
    try:
        config_manager = get_config_manager()
        download_manager = DownloadManager(config_manager)
        
        if all_downloads:
            completed_count = download_manager.clear_completed_downloads()
            failed_count = download_manager.clear_failed_downloads()
            total_cleared = completed_count + failed_count
            
            display_info(
                f"Cleared {total_cleared} downloads from history "
                f"({completed_count} completed, {failed_count} failed).",
                "🗑️  History Cleared"
            )
        elif completed:
            count = download_manager.clear_completed_downloads()
            display_info(
                f"Cleared {count} completed downloads from history.",
                "🗑️  Completed Downloads Cleared"
            )
        elif failed:
            count = download_manager.clear_failed_downloads()
            display_info(
                f"Cleared {count} failed downloads from history.",
                "🗑️  Failed Downloads Cleared"
            )
        else:
            display_warning(
                "Please specify what to clear: --completed, --failed, or --all",
                "❓ Clear What?"
            )
        
    except Exception as e:
        handle_error(e, "Failed to clear download history")
        raise typer.Exit(1)


# Export the command app
__all__ = ["app"]