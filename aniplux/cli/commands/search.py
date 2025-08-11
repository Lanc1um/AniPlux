"""
Search Command - Anime search functionality.

This module implements the search command for finding anime across
multiple sources with clean results display.
"""

import asyncio
import logging
import typer
from typing import Optional, List, Dict, Any

from aniplux.cli.context import get_config_manager
from aniplux.cli.search_engine import SearchEngine
from aniplux.cli.search_interactive import InteractiveSearchHandler
from aniplux.cli.search_display import SearchDisplayManager
from aniplux.core.exceptions import SearchError, PluginError
from aniplux.ui import (
    get_console,
    handle_error,
    display_warning,
    display_info,
    status_spinner,
)

# Create search command group
app = typer.Typer(
    name="search",
    help="🔍 Search for anime across multiple sources",
    no_args_is_help=True,
)

console = get_console()
logger = logging.getLogger(__name__)


@app.command()
def anime(
    query: str = typer.Argument(..., help="Anime title to search for"),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Enable interactive mode for result selection"
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Search specific source only"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of results to display (default: show all)",
        min=1,
        max=200
    ),
) -> None:
    """
    🔍 Search for anime by title.
    
    Search across all enabled sources for anime matching the given query.
    Results are displayed in a formatted table with episode counts, ratings,
    and source information.
    
    Examples:
    
        aniplux search "attack on titan"
        
        aniplux search "naruto" --interactive --min-rating 8.0
        
        aniplux search "one piece" --source sample --limit 10
    """
    try:
        # Validate query length
        config_manager = get_config_manager()
        min_query_length = config_manager.settings.search.min_query_length
        
        if len(query.strip()) < min_query_length:
            display_warning(
                f"Search query must be at least {min_query_length} characters long.",
                "⚠️  Query Too Short"
            )
            raise typer.Exit(1)
        
        # Run the search
        asyncio.run(_perform_search(
            query=query.strip(),
            interactive=interactive,
            source_filter=source,
            limit=limit,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Search cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During anime search")
        raise typer.Exit(1)


async def _perform_search(
    query: str,
    interactive: bool,
    source_filter: Optional[str],
    limit: Optional[int],
    config_manager: Any
) -> None:
    """
    Perform the actual search operation.
    
    Args:
        query: Search query
        interactive: Enable interactive mode
        source_filter: Specific source to search
        limit: Maximum results to display (None for no limit)
        config_manager: Configuration manager instance
    """
    # Initialize search components
    search_engine = SearchEngine(config_manager)
    display_manager = SearchDisplayManager()
    
    try:
        # Perform search
        search_results = await search_engine.search_anime(
            query=query,
            source_filter=source_filter,
            limit=limit
        )
        
        # Check if any results found
        if not search_results:
            display_warning(
                f"No results found for '{query}'.\n\n"
                "Try:\n"
                "• Different search terms or keywords\n"
                "• Checking spelling and alternative titles\n"
                "• Using broader search terms\n"
                "• Enabling more sources with 'aniplux sources'",
                "🔍 No Results Found"
            )
            return
        
        # Apply limit if specified
        if limit:
            search_results = search_results[:limit]
        
        # Display results
        display_manager.display_search_results(
            results=search_results,
            query=query,
            total_found=search_engine.last_raw_result_count
        )
        
        # Handle interactive mode
        if interactive and search_results:
            interactive_handler = InteractiveSearchHandler(config_manager)
            await interactive_handler.handle_interactive_selection(search_results)
    
    except SearchError as e:
        handle_error(e, f"Search failed for query '{query}'")
    except PluginError as e:
        handle_error(e, "Plugin error during search")
    except Exception as e:
        handle_error(e, "Unexpected error during search")
    finally:
        # Clean up plugin resources
        try:
            await search_engine.cleanup()
        except Exception as e:
            logger.warning(f"Error during search engine cleanup: {e}")


@app.command(name="recent")
def search_recent(
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Maximum number of results to display",
        min=1,
        max=50
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Search specific source only"
    ),
) -> None:
    """
    📅 Search for recently released anime.
    
    Display recently released or updated anime from enabled sources.
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_search_recent_anime(
            limit=limit,
            source_filter=source,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Search cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During recent anime search")
        raise typer.Exit(1)


async def _search_recent_anime(
    limit: int,
    source_filter: Optional[str],
    config_manager: Any
) -> None:
    """Search for recent anime releases."""
    search_engine = SearchEngine(config_manager)
    display_manager = SearchDisplayManager()
    
    try:
        with status_spinner("Finding recent anime releases..."):
            # Use a broad search query to get recent content
            # This is a simplified implementation - real sources would have dedicated recent/trending endpoints
            recent_queries = ["2024", "new", "latest", "recent"]
            all_results = []
            
            for query in recent_queries:
                results = await search_engine.search_anime(
                    query=query,
                    source_filter=source_filter,
                    limit=limit // len(recent_queries)
                )
                all_results.extend(results)
        
        if not all_results:
            display_warning(
                "No recent anime found.\n\n"
                "This may be because:\n"
                "• No sources are enabled\n"
                "• Sources don't support recent anime queries\n"
                "• Network connectivity issues",
                "📅 No Recent Anime"
            )
            return
        
        # Sort by year (most recent first) and remove duplicates
        unique_results = search_engine.remove_duplicate_results(all_results)
        sorted_results = search_engine.sort_results(unique_results, "year")[:limit]
        
        display_manager.display_search_results(
            results=sorted_results,
            query="recent releases",
            total_found=len(unique_results),
            title="📅 Recent Anime Releases"
        )
        
    except Exception as e:
        handle_error(e, "Failed to search recent anime")


@app.command(name="popular")
def search_popular(
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Maximum number of results to display",
        min=1,
        max=50
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Search specific source only"
    ),
    min_rating: float = typer.Option(
        7.0,
        "--min-rating",
        help="Minimum rating for popular anime",
        min=0.0,
        max=10.0
    ),
) -> None:
    """
    ⭐ Search for popular anime.
    
    Display popular anime based on ratings and popularity metrics.
    """
    try:
        config_manager = get_config_manager()
        
        asyncio.run(_search_popular_anime(
            limit=limit,
            source_filter=source,
            min_rating=min_rating,
            config_manager=config_manager
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Search cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, "During popular anime search")
        raise typer.Exit(1)


async def _search_popular_anime(
    limit: int,
    source_filter: Optional[str],
    min_rating: float,
    config_manager: Any
) -> None:
    """Search for popular anime."""
    search_engine = SearchEngine(config_manager)
    display_manager = SearchDisplayManager()
    
    try:
        with status_spinner("Finding popular anime..."):
            # Use popular anime keywords
            popular_queries = ["popular", "top", "best", "trending"]
            all_results = []
            
            for query in popular_queries:
                results = await search_engine.search_anime(
                    query=query,
                    source_filter=source_filter,
                    limit=limit // len(popular_queries)
                )
                all_results.extend(results)
        
        if not all_results:
            display_warning(
                "No popular anime found.\n\n"
                "This may be because:\n"
                "• No sources are enabled\n"
                "• Sources don't support popularity queries\n"
                "• Network connectivity issues",
                "⭐ No Popular Anime"
            )
            return
        
        # Filter by rating and sort by rating (highest first)
        unique_results = search_engine.remove_duplicate_results(all_results)
        filtered_results = [r for r in unique_results if r.rating and r.rating >= min_rating]
        sorted_results = search_engine.sort_results(filtered_results, "rating")[:limit]
        
        display_manager.display_search_results(
            results=sorted_results,
            query=f"popular anime (rating ≥ {min_rating})",
            total_found=len(filtered_results),
            title="⭐ Popular Anime"
        )
        
    except Exception as e:
        handle_error(e, "Failed to search popular anime")


# Export the command app
__all__ = ["app"]