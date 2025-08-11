"""
Episodes Command - Episode browsing and management functionality.

This module implements commands for browsing episodes with rich
interface and keyboard navigation support.
"""

import asyncio
import typer
from typing import Optional, Any
from pathlib import Path

from aniplux.cli.context import get_config_manager
from aniplux.cli.episode_browser import EpisodeBrowser
from aniplux.cli.episode_display import EpisodeDisplayManager
from aniplux.core.models import AnimeResult
from aniplux.core.exceptions import PluginError
from aniplux.ui import (
    get_console,
    handle_error,
    display_warning,
    display_info,
    status_spinner,
)

# Create episodes command group
app = typer.Typer(
    name="episodes",
    help="📺 Browse and manage anime episodes",
    no_args_is_help=True,
)

console = get_console()


@app.command(name="browse")
def browse_episodes(
    anime_url: str = typer.Argument(..., help="Anime URL to browse episodes for"),
    source: str = typer.Argument(..., help="Source plugin name"),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="Anime title for display"
    ),
    auto_select: bool = typer.Option(
        False,
        "--auto-select",
        help="Auto-select if only one episode available"
    ),
) -> None:
    """
    📺 Browse episodes for a specific anime.
    
    Launch the interactive episode browser for the specified anime URL.
    Provides rich interface with filtering, sorting, and detailed views.
    
    Examples:
    
        aniplux episodes browse "https://example.com/anime/naruto" sample
        
        aniplux episodes browse "https://example.com/anime/aot" sample --title "Attack on Titan"
    """
    try:
        config_manager = get_config_manager()
        
        # Extract title from URL if not provided
        if not title:
            from aniplux.core.utils import extract_anime_title_from_url
            title = extract_anime_title_from_url(anime_url)
        
        # Create anime result object
        from pydantic import HttpUrl
        anime = AnimeResult(
            title=title,
            url=HttpUrl(anime_url),
            source=source,
            episode_count=None,
            description=None,
            thumbnail=None,
            year=None,
            rating=None,
            status=None
        )
        
        asyncio.run(_browse_anime_episodes(anime, auto_select, config_manager))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Episode browsing cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During episode browsing")
        raise typer.Exit(1)


async def _browse_anime_episodes(
    anime: AnimeResult,
    auto_select: bool,
    config_manager: Any
) -> None:
    """
    Browse episodes for an anime.
    
    Args:
        anime: Anime to browse episodes for
        auto_select: Auto-select single episodes
        config_manager: Configuration manager instance
    """
    episode_browser = EpisodeBrowser(config_manager)
    
    try:
        selected_episode = await episode_browser.browse_anime_episodes(
            anime=anime,
            auto_select=auto_select
        )
        
        if selected_episode:
            # Check if this was a single episode selection or bulk download
            # If it's a single episode, show the command
            display_info(
                f"Episode selected: {selected_episode.title}\n\n"
                f"To download this episode, use:\n"
                f"[cyan]aniplux download episode {selected_episode.url}[/cyan]",
                "📺 Episode Selected"
            )
    finally:
        # Clean up episode browser resources
        try:
            cleanup_method = getattr(episode_browser, 'cleanup', None)
            if cleanup_method:
                await cleanup_method()
        except Exception:
            # Episode browser might not have cleanup method or cleanup might fail
            pass


@app.command(name="list")
def list_episodes(
    anime_url: str = typer.Argument(..., help="Anime URL to list episodes for"),
    source: str = typer.Argument(..., help="Source plugin name"),
    format_type: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, grid, summary",
        case_sensitive=False
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of episodes to display"
    ),
    show_stats: bool = typer.Option(
        False,
        "--stats",
        help="Show episode statistics"
    ),
) -> None:
    """
    📋 List episodes for a specific anime.
    
    Display episodes in various formats without interactive browsing.
    Useful for quick episode overview or scripting.
    
    Examples:
    
        aniplux episodes list "https://example.com/anime/naruto" sample
        
        aniplux episodes list "https://example.com/anime/aot" sample --format grid --limit 10
        
        aniplux episodes list "https://example.com/anime/op" sample --stats
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_list_anime_episodes(
            anime_url=anime_url,
            source=source,
            format_type=format_type,
            limit=limit,
            show_stats=show_stats,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Episode listing cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During episode listing")
        raise typer.Exit(1)


async def _list_anime_episodes(
    anime_url: str,
    source: str,
    format_type: str,
    limit: Optional[int],
    show_stats: bool,
    config_manager: Any
) -> None:
    """
    List episodes for an anime.
    
    Args:
        anime_url: URL of the anime
        source: Source plugin name
        format_type: Display format
        limit: Episode limit
        show_stats: Whether to show statistics
        config_manager: Configuration manager instance
    """
    plugin_manager = None
    try:
        # Load episodes
        from aniplux.core import PluginManager
        
        plugin_manager = PluginManager(config_manager)
        
        with status_spinner("Loading episodes..."):
            episodes = await plugin_manager.get_plugin_episodes(
                plugin_name=source,
                anime_url=anime_url
            )
        
        if not episodes:
            display_warning(
                "No episodes found for the specified anime.\n\n"
                "This might be because:\n"
                "• The anime page has no episode links\n"
                "• The source plugin couldn't parse episodes\n"
                "• Network connectivity issues",
                "📺 No Episodes Found"
            )
            return
        
        # Apply limit
        if limit:
            episodes = episodes[:limit]
        
        # Display episodes
        display_manager = EpisodeDisplayManager()
        
        if format_type.lower() == "grid":
            episodes_grid = display_manager.create_episode_grid(episodes)
            console.print(episodes_grid)
        elif format_type.lower() == "summary":
            episodes_table = display_manager.create_episode_summary_table(episodes)
            console.print(episodes_table)
        else:  # table (default)
            from aniplux.ui import UIComponents
            ui = UIComponents()
            episodes_table = ui.create_episodes_table(episodes)
            console.print(episodes_table)
        
        # Show statistics if requested
        if show_stats:
            console.print()
            display_manager.display_episode_statistics(episodes)
    
    except PluginError as e:
        handle_error(e, f"Failed to load episodes from {source}")
    except Exception as e:
        handle_error(e, "Unexpected error loading episodes")
    finally:
        # Clean up plugin manager resources
        if plugin_manager:
            try:
                await plugin_manager.cleanup()
            except Exception as e:
                # Don't let cleanup errors affect the main operation
                pass


@app.command(name="search")
def search_episodes(
    anime_url: str = typer.Argument(..., help="Anime URL to search episodes in"),
    source: str = typer.Argument(..., help="Source plugin name"),
    query: str = typer.Argument(..., help="Search query for episode titles"),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of results to display"
    ),
) -> None:
    """
    🔍 Search episodes within a specific anime.
    
    Search for episodes by title within a specific anime series.
    Useful for finding specific episodes or story arcs.
    
    Examples:
    
        aniplux episodes search "https://example.com/anime/naruto" sample "chunin"
        
        aniplux episodes search "https://example.com/anime/op" sample "luffy" --limit 5
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_search_anime_episodes(
            anime_url=anime_url,
            source=source,
            query=query,
            limit=limit,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Episode search cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During episode search")
        raise typer.Exit(1)


async def _search_anime_episodes(
    anime_url: str,
    source: str,
    query: str,
    limit: Optional[int],
    config_manager: Any
) -> None:
    """
    Search episodes within an anime.
    
    Args:
        anime_url: URL of the anime
        source: Source plugin name
        query: Search query
        limit: Result limit
        config_manager: Configuration manager instance
    """
    plugin_manager = None
    try:
        # Load episodes
        from aniplux.core import PluginManager
        
        plugin_manager = PluginManager(config_manager)
        
        with status_spinner("Loading episodes..."):
            episodes = await plugin_manager.get_plugin_episodes(
                plugin_name=source,
                anime_url=anime_url
            )
        
        if not episodes:
            display_warning("No episodes found for the specified anime.")
            return
        
        # Search episodes
        query_lower = query.lower()
        matching_episodes = [
            ep for ep in episodes
            if query_lower in ep.title.lower() or query_lower in (ep.description or "").lower()
        ]
        
        # Apply limit
        if limit:
            matching_episodes = matching_episodes[:limit]
        
        # Display results
        display_manager = EpisodeDisplayManager()
        display_manager.display_episode_search_results(
            episodes=matching_episodes,
            search_query=query,
            total_episodes=len(episodes)
        )
    
    except PluginError as e:
        handle_error(e, f"Failed to load episodes from {source}")
    except Exception as e:
        handle_error(e, "Unexpected error searching episodes")
    finally:
        # Clean up plugin manager resources
        if plugin_manager:
            try:
                await plugin_manager.cleanup()
            except Exception as e:
                # Don't let cleanup errors affect the main operation
                pass


# Export the command app
__all__ = ["app"]