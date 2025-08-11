"""
Search Display Manager - Clean search results display with Rich components.

This module handles the display of search results using Rich components
with proper formatting, pagination, and user-friendly presentation.
"""

import logging
from typing import List, Optional
from math import ceil

from aniplux.core.models import AnimeResult
from aniplux.ui import (
    get_console,
    UIComponents,
    format_title,
    format_muted,
    format_success,
    format_warning,
)


logger = logging.getLogger(__name__)


class SearchDisplayManager:
    """
    Manages the display of search results with Rich formatting.
    
    Provides clean, formatted display of anime search results with
    pagination support and detailed information presentation.
    """
    
    def __init__(self):
        """Initialize display manager."""
        self.console = get_console()
        self.ui = UIComponents()
    
    def display_search_results(
        self,
        results: List[AnimeResult],
        query: str,
        total_found: Optional[int] = None,
        title: Optional[str] = None,
        page_size: int = 20
    ) -> None:
        """
        Display search results in a formatted table.
        
        Args:
            results: List of anime search results
            query: Original search query
            total_found: Total number of results found (before filtering)
            title: Custom title for the results display
            page_size: Number of results per page (ignored - shows all results)
        """
        if not results:
            self._display_no_results(query)
            return
        
        # Display header
        self._display_search_header(query, len(results), total_found, title)
        
        # Display all results at once (no pagination)
        self._display_results_page(results, 1, 1)
        
        # Display footer with tips
        self._display_search_footer(len(results))
    
    def _display_search_header(
        self,
        query: str,
        displayed_count: int,
        total_found: Optional[int],
        title: Optional[str]
    ) -> None:
        """Display search results header."""
        if title:
            header_title = title
        else:
            header_title = f"🔍 Search Results for '{query}'"
        
        # Create result count text
        if total_found and total_found != displayed_count:
            count_text = f"Showing {displayed_count} of {total_found} results"
        else:
            count_text = f"Found {displayed_count} result{'s' if displayed_count != 1 else ''}"
        
        # Display header
        self.console.print(format_title(header_title))
        self.console.print(format_muted(count_text))
        self.console.print()
    
    def _display_results_page(
        self,
        results: List[AnimeResult],
        page_num: int,
        total_pages: int
    ) -> None:
        """Display a single page of results."""
        # Create and display results table
        results_table = self.ui.create_anime_results_table(results)
        self.console.print(results_table)
        
        # Display page info if multiple pages
        if total_pages > 1:
            self.console.print()
            page_info = f"Page {page_num} of {total_pages}"
            self.console.print(format_muted(page_info))
    
    def _display_paginated_results(
        self,
        results: List[AnimeResult],
        page_size: int
    ) -> None:
        """Display results with pagination."""
        total_pages = ceil(len(results) / page_size)
        
        for page_num in range(1, total_pages + 1):
            start_idx = (page_num - 1) * page_size
            end_idx = min(start_idx + page_size, len(results))
            page_results = results[start_idx:end_idx]
            
            self._display_results_page(page_results, page_num, total_pages)
            
            # Ask user if they want to continue (except for last page)
            if page_num < total_pages:
                self.console.print()
                try:
                    continue_viewing = self.console.input(
                        f"[dim]Press Enter to see more results, or 'q' to quit: [/dim]"
                    ).strip().lower()
                    
                    if continue_viewing in ['q', 'quit', 'exit']:
                        remaining = len(results) - end_idx
                        self.console.print(format_muted(f"({remaining} more results not shown)"))
                        break
                    
                    self.console.print()
                    
                except (KeyboardInterrupt, EOFError):
                    self.console.print()
                    break
    
    def _display_no_results(self, query: str) -> None:
        """Display message when no results are found."""
        no_results_text = f"""
No anime found for '[cyan]{query}[/cyan]'

[yellow]💡 Try these suggestions:[/yellow]
• Check spelling and try alternative titles
• Use broader search terms (e.g., 'naruto' instead of 'naruto shippuden')
• Try different keywords or partial titles
• Enable more sources with [cyan]aniplux sources enable <name>[/cyan]
• Check if sources are working with [cyan]aniplux sources test[/cyan]
"""
        
        panel = self.ui.create_warning_panel(
            no_results_text.strip(),
            title="🔍 No Results Found"
        )
        
        self.console.print(panel)
    
    def _display_search_footer(self, result_count: int) -> None:
        """Display search results footer with helpful tips."""
        if result_count == 0:
            return
        
        footer_text = """
[dim]💡 Next steps:[/dim]
• Use [cyan]--interactive[/cyan] flag to browse episodes interactively
• Limit results with [cyan]--limit 20[/cyan] for faster searches
• Search specific sources with [cyan]--source <name>[/cyan]
"""
        
        self.console.print()
        self.console.print(footer_text.strip())
    
    def display_detailed_result(self, result: AnimeResult, index: int) -> None:
        """
        Display detailed information for a single anime result.
        
        Args:
            result: Anime result to display
            index: Index number for display
        """
        # Create detailed info
        details = []
        
        # Basic info
        details.append(f"[bold]{index}. {result.title}[/bold]")
        
        if result.description:
            details.append(f"\n[dim]Description:[/dim] {result.description}")
        
        # Metadata
        metadata_parts = []
        
        if result.year:
            metadata_parts.append(f"Year: {result.year}")
        
        if result.episode_count:
            metadata_parts.append(f"Episodes: {result.episode_count}")
        
        if result.rating:
            rating_color = "green" if result.rating >= 8.0 else "yellow" if result.rating >= 7.0 else "red"
            metadata_parts.append(f"Rating: [{rating_color}]{result.rating:.1f}[/{rating_color}]")
        
        if result.genres:
            genres_text = ", ".join(result.genres[:3])  # Show first 3 genres
            if len(result.genres) > 3:
                genres_text += f" (+{len(result.genres) - 3} more)"
            metadata_parts.append(f"Genres: {genres_text}")
        
        if metadata_parts:
            details.append(f"\n[dim]{' • '.join(metadata_parts)}[/dim]")
        
        # Source info
        details.append(f"\n[dim]Source:[/dim] [cyan]{result.source}[/cyan]")
        details.append(f"[dim]URL:[/dim] [blue]{result.url}[/blue]")
        
        # Create and display panel
        content = "\n".join(details)
        panel = self.ui.create_info_panel(content, title=f"📺 Anime Details")
        
        self.console.print(panel)
    
    def display_search_summary(
        self,
        total_results: int,
        sources_searched: List[str],
        search_time: float
    ) -> None:
        """
        Display search operation summary.
        
        Args:
            total_results: Total number of results found
            sources_searched: List of sources that were searched
            search_time: Time taken for search in seconds
        """
        summary_parts = []
        
        # Results summary
        if total_results == 0:
            summary_parts.append("[yellow]No results found[/yellow]")
        elif total_results == 1:
            summary_parts.append("[green]1 result found[/green]")
        else:
            summary_parts.append(f"[green]{total_results} results found[/green]")
        
        # Sources summary
        if len(sources_searched) == 1:
            summary_parts.append(f"from [cyan]{sources_searched[0]}[/cyan]")
        else:
            summary_parts.append(f"from [cyan]{len(sources_searched)} sources[/cyan]")
        
        # Timing
        summary_parts.append(f"in [dim]{search_time:.1f}s[/dim]")
        
        summary_text = " ".join(summary_parts)
        
        # Display in a subtle way
        self.console.print()
        self.console.print(f"[dim]Search completed: {summary_text}[/dim]")
    
    def display_source_status(self, sources_status: dict) -> None:
        """
        Display status of sources used in search.
        
        Args:
            sources_status: Dictionary of source name to status info
        """
        if not sources_status:
            return
        
        # Create status table
        headers = ["Source", "Status", "Results", "Time"]
        rows = []
        
        for source_name, status in sources_status.items():
            status_icon = "✅" if status.get("success", False) else "❌"
            result_count = status.get("results", 0)
            search_time = status.get("time", 0)
            
            rows.append([
                source_name,
                status_icon,
                str(result_count),
                f"{search_time:.1f}s"
            ])
        
        status_table = self.ui.create_data_table(
            headers=headers,
            rows=rows,
            title="Source Performance"
        )
        
        panel = self.ui.create_info_panel(
            status_table,
            title="📊 Search Statistics"
        )
        
        self.console.print()
        self.console.print(panel)


# Export display manager
__all__ = ["SearchDisplayManager"]