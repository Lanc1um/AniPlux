"""
UI Components - Standardized Rich components for consistent interface.

This module provides reusable UI components with consistent styling
and behavior across all CLI commands.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from rich.align import Align
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich.layout import Layout
from rich.rule import Rule

from aniplux.core.models import AnimeResult, Episode, DownloadTask, Quality
from aniplux.ui.console import get_console
from aniplux.ui.themes import get_palette


class UIComponents:
    """Collection of standardized UI components with consistent styling."""
    
    def __init__(self):
        """Initialize UI components with current theme."""
        self.console = get_console()
        self.palette = get_palette()
    
    def create_panel(
        self,
        content: Any,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        border_style: Optional[str] = None,
        padding: tuple[int, int] = (1, 2),
        expand: bool = True
    ) -> Panel:
        """
        Create a styled panel with consistent theming.
        
        Args:
            content: Panel content
            title: Panel title
            subtitle: Panel subtitle
            border_style: Border style override
            padding: Panel padding (vertical, horizontal)
            expand: Whether panel should expand to full width
            
        Returns:
            Styled Panel object
        """
        return Panel(
            content,
            title=title,
            subtitle=subtitle,
            border_style=border_style or self.palette.border_primary,
            padding=padding,
            expand=expand
        )
    
    def create_info_panel(self, content: Any, title: str = "ℹ️  Information") -> Panel:
        """Create an information panel with info styling."""
        return self.create_panel(
            content,
            title=f"[{self.palette.info}]{title}[/{self.palette.info}]",
            border_style=self.palette.info
        )
    
    def create_success_panel(self, content: Any, title: str = "✅ Success") -> Panel:
        """Create a success panel with success styling."""
        return self.create_panel(
            content,
            title=f"[{self.palette.success}]{title}[/{self.palette.success}]",
            border_style=self.palette.success
        )
    
    def create_warning_panel(self, content: Any, title: str = "⚠️  Warning") -> Panel:
        """Create a warning panel with warning styling."""
        return self.create_panel(
            content,
            title=f"[{self.palette.warning}]{title}[/{self.palette.warning}]",
            border_style=self.palette.warning
        )
    
    def create_error_panel(self, content: Any, title: str = "❌ Error") -> Panel:
        """Create an error panel with error styling."""
        return self.create_panel(
            content,
            title=f"[{self.palette.error}]{title}[/{self.palette.error}]",
            border_style=self.palette.error
        )
    
    def create_data_table(
        self,
        headers: List[str],
        rows: List[List[str]],
        title: Optional[str] = None,
        show_lines: bool = False,
        expand: bool = True
    ) -> Table:
        """
        Create a data table with consistent styling.
        
        Args:
            headers: Column headers
            rows: Table rows
            title: Table title
            show_lines: Whether to show row lines
            expand: Whether table should expand to full width
            
        Returns:
            Styled Table object
        """
        table = Table(
            title=title,
            show_header=True,
            header_style=f"bold {self.palette.secondary}",
            border_style=self.palette.border_secondary,
            show_lines=show_lines,
            expand=expand
        )
        
        # Add columns
        for header in headers:
            table.add_column(header)
        
        # Add rows
        for row in rows:
            table.add_row(*row)
        
        return table
    
    def create_anime_results_table(self, results: List[AnimeResult]) -> Table:
        """
        Create a table displaying anime search results.
        
        Args:
            results: List of anime search results
            
        Returns:
            Formatted table with anime results
        """
        table = Table(
            title="🔍 Search Results",
            show_header=True,
            header_style=f"bold {self.palette.secondary}",
            border_style=self.palette.border_primary,
            expand=True
        )
        
        table.add_column("#", style="dim", width=6)
        table.add_column("Title", style=self.palette.primary, min_width=40)
        table.add_column("Episodes", style=self.palette.text_secondary, width=12)
        table.add_column("Source", style=self.palette.text_muted, width=17)
        
        for i, result in enumerate(results, 1):
            # Format episode count
            episodes = str(result.episode_count) if result.episode_count else "?"
            
            table.add_row(
                str(i),
                result.title,
                episodes,
                result.source
            )
        
        return table
    
    def create_episodes_table(self, episodes: List[Episode]) -> Table:
        """
        Create a table displaying episode list.
        
        Args:
            episodes: List of episodes
            
        Returns:
            Formatted table with episodes
        """
        table = Table(
            title="📺 Episodes",
            show_header=True,
            header_style=f"bold {self.palette.secondary}",
            border_style=self.palette.border_primary,
            expand=True
        )
        
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style=self.palette.primary, min_width=25)
        table.add_column("Duration", style=self.palette.text_secondary, width=8)
        table.add_column("Quality", style=self.palette.accent, width=15)
        table.add_column("Type", style=self.palette.text_muted, width=8)
        
        for episode in episodes:
            # Format quality options
            quality_text = ", ".join([q.value for q in episode.quality_options])
            
            # Format episode type
            episode_type = "Filler" if episode.filler else "Canon"
            type_color = self.palette.text_muted if episode.filler else self.palette.success
            
            table.add_row(
                str(episode.number),
                episode.title,
                episode.duration or "?",
                quality_text,
                f"[{type_color}]{episode_type}[/{type_color}]"
            )
        
        return table
    
    def create_download_status_table(self, tasks: List[DownloadTask]) -> Table:
        """
        Create a table showing download task status.
        
        Args:
            tasks: List of download tasks
            
        Returns:
            Formatted table with download status
        """
        table = Table(
            title="⬇️  Downloads",
            show_header=True,
            header_style=f"bold {self.palette.secondary}",
            border_style=self.palette.border_primary,
            expand=True
        )
        
        table.add_column("Episode", style=self.palette.primary, min_width=20)
        table.add_column("Quality", style=self.palette.accent, width=8)
        table.add_column("Progress", style=self.palette.text_secondary, width=10)
        table.add_column("Speed", style=self.palette.text_secondary, width=12)
        table.add_column("ETA", style=self.palette.text_secondary, width=8)
        table.add_column("Status", width=12)
        
        for task in tasks:
            # Format status with color
            status_colors = {
                "pending": self.palette.text_muted,
                "downloading": self.palette.info,
                "completed": self.palette.success,
                "failed": self.palette.error,
                "paused": self.palette.warning,
                "cancelled": self.palette.text_muted
            }
            
            status_color = status_colors.get(task.status.value, self.palette.text_secondary)
            status_text = f"[{status_color}]{task.status.value.title()}[/{status_color}]"
            
            table.add_row(
                task.episode.title,
                task.quality.value,
                f"{task.progress:.1f}%",
                task.formatted_speed,
                task.formatted_eta,
                status_text
            )
        
        return table
    
    def create_status_grid(self, status_items: Dict[str, Any]) -> Table:
        """
        Create a grid showing status information.
        
        Args:
            status_items: Dictionary of status key-value pairs
            
        Returns:
            Formatted status table
        """
        table = Table(
            show_header=False,
            border_style=self.palette.border_secondary,
            expand=True,
            padding=(0, 1)
        )
        
        table.add_column("Key", style=f"bold {self.palette.secondary}", width=20)
        table.add_column("Value", style=self.palette.text_primary)
        
        for key, value in status_items.items():
            table.add_row(key, str(value))
        
        return table
    
    def create_banner(self, text: str, style: Optional[str] = None) -> Panel:
        """
        Create a banner with large text.
        
        Args:
            text: Banner text
            style: Text style override
            
        Returns:
            Banner panel
        """
        banner_text = Text(text, style=style or f"bold {self.palette.primary}")
        centered_text = Align.center(banner_text)
        
        return Panel(
            centered_text,
            border_style=self.palette.border_primary,
            padding=(1, 2)
        )
    
    def create_rule(self, title: Optional[str] = None, style: Optional[str] = None) -> Rule:
        """
        Create a horizontal rule separator.
        
        Args:
            title: Rule title
            style: Rule style override
            
        Returns:
            Styled Rule object
        """
        return Rule(
            title=title or "",
            style=style or self.palette.border_secondary
        )
    
    def create_tree(self, label: str) -> Tree:
        """
        Create a tree structure for hierarchical data.
        
        Args:
            label: Root label
            
        Returns:
            Tree object
        """
        return Tree(
            label,
            style=self.palette.primary,
            guide_style=self.palette.border_secondary
        )
    
    def create_columns(self, renderables: List[Any], equal: bool = False) -> Columns:
        """
        Create columns layout for side-by-side content.
        
        Args:
            renderables: List of content to display in columns
            equal: Whether columns should be equal width
            
        Returns:
            Columns layout
        """
        return Columns(renderables, equal=equal, expand=True)


# Export UI components
__all__ = ["UIComponents"]