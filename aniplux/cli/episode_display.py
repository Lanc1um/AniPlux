"""
Episode Display Utilities - Rich formatting for episode information.

This module provides specialized display utilities for episode information
with consistent formatting and enhanced visual presentation.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn

from aniplux.core.models import Episode, Quality
from aniplux.ui import (
    get_console,
    UIComponents,
    format_title,
    format_muted,
    format_success,
    format_warning,
    format_quality,
)


logger = logging.getLogger(__name__)


class EpisodeDisplayManager:
    """
    Manages rich display formatting for episode information.
    
    Provides specialized display methods for episode lists, details,
    and statistics with consistent Rich formatting.
    """
    
    def __init__(self):
        """Initialize display manager."""
        self.console = get_console()
        self.ui = UIComponents()
    
    def create_episode_summary_table(self, episodes: List[Episode]) -> Table:
        """
        Create a summary table of episodes with key information.
        
        Args:
            episodes: List of episodes to display
            
        Returns:
            Rich Table with episode summary
        """
        table = Table(
            title="📺 Episode Summary",
            show_header=True,
            header_style="bold blue",
            border_style="blue",
            expand=True
        )
        
        # Add columns
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white", min_width=25)
        table.add_column("Duration", style="cyan", width=8)
        table.add_column("Quality", style="green", width=15)
        table.add_column("Type", style="yellow", width=8)
        table.add_column("Air Date", style="dim", width=10)
        
        for episode in episodes:
            # Format quality options
            quality_text = ", ".join([q.value for q in episode.quality_options])
            
            # Format episode type
            episode_type = "Filler" if episode.filler else "Canon"
            type_style = "yellow" if episode.filler else "green"
            
            # Format air date
            air_date = ""
            if episode.air_date:
                if isinstance(episode.air_date, datetime):
                    air_date = episode.air_date.strftime("%Y-%m-%d")
                else:
                    air_date = str(episode.air_date)
            
            table.add_row(
                str(episode.number),
                episode.title,
                episode.duration or "?",
                quality_text,
                f"[{type_style}]{episode_type}[/{type_style}]",
                air_date
            )
        
        return table
    
    def create_episode_grid(self, episodes: List[Episode], columns: int = 3) -> Columns:
        """
        Create a grid layout of episode cards.
        
        Args:
            episodes: List of episodes to display
            columns: Number of columns in the grid
            
        Returns:
            Rich Columns layout with episode cards
        """
        episode_panels = []
        
        for episode in episodes:
            # Create episode card content
            card_content = self._create_episode_card_content(episode)
            
            # Create panel for episode
            panel = Panel(
                card_content,
                title=f"Episode {episode.number}",
                border_style="blue" if not episode.filler else "yellow",
                padding=(1, 1)
            )
            
            episode_panels.append(panel)
        
        # Create columns layout
        return Columns(episode_panels, equal=True, expand=True)
    
    def _create_episode_card_content(self, episode: Episode) -> str:
        """
        Create content for an episode card.
        
        Args:
            episode: Episode to create card for
            
        Returns:
            Formatted card content string
        """
        content_lines = []
        
        # Episode title (truncated if too long)
        title = episode.title
        if len(title) > 30:
            title = title[:27] + "..."
        content_lines.append(f"[bold]{title}[/bold]")
        
        # Duration
        if episode.duration:
            content_lines.append(f"[dim]Duration:[/dim] {episode.duration}")
        
        # Quality options
        if episode.quality_options:
            qualities = ", ".join([q.value for q in episode.quality_options[:2]])  # Show first 2
            if len(episode.quality_options) > 2:
                qualities += f" +{len(episode.quality_options) - 2}"
            content_lines.append(f"[dim]Quality:[/dim] {qualities}")
        
        # Episode type
        episode_type = "Filler" if episode.filler else "Canon"
        type_color = "yellow" if episode.filler else "green"
        content_lines.append(f"[dim]Type:[/dim] [{type_color}]{episode_type}[/{type_color}]")
        
        return "\n".join(content_lines)
    
    def display_episode_statistics(self, episodes: List[Episode]) -> None:
        """
        Display statistics about the episode collection.
        
        Args:
            episodes: List of episodes to analyze
        """
        if not episodes:
            return
        
        # Calculate statistics
        stats = self._calculate_episode_statistics(episodes)
        
        # Create statistics display
        stats_content = self._format_episode_statistics(stats)
        
        # Display in panel
        stats_panel = self.ui.create_info_panel(
            stats_content,
            title="📊 Episode Statistics"
        )
        
        self.console.print(stats_panel)
    
    def _calculate_episode_statistics(self, episodes: List[Episode]) -> Dict[str, Any]:
        """
        Calculate statistics for episode collection.
        
        Args:
            episodes: List of episodes to analyze
            
        Returns:
            Dictionary containing statistics
        """
        stats = {
            "total_episodes": len(episodes),
            "canon_episodes": 0,
            "filler_episodes": 0,
            "total_duration_minutes": 0,
            "quality_distribution": {},
            "episodes_with_duration": 0,
            "average_duration": 0,
        }
        
        total_duration_seconds = 0
        episodes_with_duration = 0
        
        for episode in episodes:
            # Count episode types
            if episode.filler:
                stats["filler_episodes"] += 1
            else:
                stats["canon_episodes"] += 1
            
            # Duration statistics
            if episode.duration_seconds:
                total_duration_seconds += episode.duration_seconds
                episodes_with_duration += 1
            
            # Quality distribution
            for quality in episode.quality_options:
                quality_key = quality.value
                stats["quality_distribution"][quality_key] = stats["quality_distribution"].get(quality_key, 0) + 1
        
        # Calculate averages
        if episodes_with_duration > 0:
            stats["average_duration"] = total_duration_seconds // episodes_with_duration
            stats["total_duration_minutes"] = total_duration_seconds // 60
            stats["episodes_with_duration"] = episodes_with_duration
        
        return stats
    
    def _format_episode_statistics(self, stats: Dict[str, Any]) -> str:
        """
        Format episode statistics for display.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            Formatted statistics string
        """
        lines = []
        
        # Basic counts
        lines.append(f"[bold]Total Episodes:[/bold] {stats['total_episodes']}")
        lines.append(f"[green]Canon Episodes:[/green] {stats['canon_episodes']}")
        
        if stats['filler_episodes'] > 0:
            lines.append(f"[yellow]Filler Episodes:[/yellow] {stats['filler_episodes']}")
        
        # Duration information
        if stats['episodes_with_duration'] > 0:
            lines.append("")
            lines.append(f"[bold]Duration Information:[/bold]")
            
            total_hours = stats['total_duration_minutes'] // 60
            total_minutes = stats['total_duration_minutes'] % 60
            lines.append(f"Total Runtime: {total_hours}h {total_minutes}m")
            
            avg_minutes = stats['average_duration'] // 60
            avg_seconds = stats['average_duration'] % 60
            lines.append(f"Average Episode: {avg_minutes}m {avg_seconds}s")
        
        # Quality distribution
        if stats['quality_distribution']:
            lines.append("")
            lines.append(f"[bold]Quality Availability:[/bold]")
            
            # Sort qualities by resolution (highest first)
            quality_items = sorted(
                stats['quality_distribution'].items(),
                key=lambda x: Quality(x[0]).height,
                reverse=True
            )
            
            for quality_name, count in quality_items:
                percentage = (count / stats['total_episodes']) * 100
                lines.append(f"{format_quality(Quality(quality_name))}: {count} episodes ({percentage:.1f}%)")
        
        return "\n".join(lines)
    
    def create_episode_progress_display(
        self,
        episodes: List[Episode],
        watched_episodes: Optional[List[int]] = None
    ) -> Panel:
        """
        Create a progress display showing watched vs unwatched episodes.
        
        Args:
            episodes: List of all episodes
            watched_episodes: List of watched episode numbers
            
        Returns:
            Rich Panel with progress display
        """
        if not watched_episodes:
            watched_episodes = []
        
        watched_count = len(watched_episodes)
        total_count = len(episodes)
        progress_percentage = (watched_count / total_count * 100) if total_count > 0 else 0
        
        # Create progress bar
        progress_text = f"Progress: {watched_count}/{total_count} episodes ({progress_percentage:.1f}%)"
        
        # Create visual progress bar
        bar_width = 40
        filled_width = int(bar_width * progress_percentage / 100)
        empty_width = bar_width - filled_width
        
        progress_bar = "[green]" + "█" * filled_width + "[/green]" + "[dim]" + "░" * empty_width + "[/dim]"
        
        content = f"{progress_text}\n{progress_bar}"
        
        return self.ui.create_info_panel(
            content,
            title="📈 Watching Progress"
        )
    
    def display_episode_search_results(
        self,
        episodes: List[Episode],
        search_query: str,
        total_episodes: int
    ) -> None:
        """
        Display episode search results.
        
        Args:
            episodes: Matching episodes
            search_query: Original search query
            total_episodes: Total episodes in the series
        """
        if not episodes:
            self.console.print(f"[yellow]No episodes found matching '{search_query}'[/yellow]")
            return
        
        # Display header
        header = f"🔍 Episodes matching '{search_query}' ({len(episodes)}/{total_episodes})"
        self.console.print(format_title(header))
        self.console.print()
        
        # Display results table
        results_table = self.create_episode_summary_table(episodes)
        self.console.print(results_table)
    
    def create_quality_comparison_table(self, episodes: List[Episode]) -> Table:
        """
        Create a table comparing quality availability across episodes.
        
        Args:
            episodes: List of episodes to analyze
            
        Returns:
            Rich Table with quality comparison
        """
        # Get all unique qualities
        all_qualities = set()
        for episode in episodes:
            all_qualities.update(episode.quality_options)
        
        sorted_qualities = sorted(all_qualities, key=lambda q: q.height, reverse=True)
        
        # Create table
        table = Table(
            title="📊 Quality Availability by Episode",
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        # Add columns
        table.add_column("Episode", style="white", width=8)
        table.add_column("Title", style="cyan", min_width=20)
        
        for quality in sorted_qualities:
            table.add_column(quality.value, style="green", width=8)
        
        # Add rows
        for episode in episodes[:20]:  # Limit to first 20 episodes for readability
            row = [str(episode.number), episode.title[:25]]
            
            for quality in sorted_qualities:
                if quality in episode.quality_options:
                    row.append("[green]✓[/green]")
                else:
                    row.append("[dim]✗[/dim]")
            
            table.add_row(*row)
        
        if len(episodes) > 20:
            table.add_row(*["[dim]...[/dim]"] * (len(sorted_qualities) + 2))
        
        return table


# Export display manager
__all__ = ["EpisodeDisplayManager"]