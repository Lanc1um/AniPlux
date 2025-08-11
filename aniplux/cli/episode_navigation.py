"""
Episode Navigation - Keyboard navigation and episode selection utilities.

This module provides keyboard navigation functionality for episode browsing
with support for various navigation patterns and selection methods.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any, Callable
from enum import Enum

from rich.prompt import Prompt, Confirm
from rich.text import Text

from aniplux.core.models import Episode, Quality
from aniplux.ui import (
    get_console,
    display_info,
    display_warning,
    format_success,
    format_warning,
)


logger = logging.getLogger(__name__)


class NavigationMode(Enum):
    """Navigation modes for episode browsing."""
    LIST = "list"           # Linear list navigation
    GRID = "grid"           # Grid-based navigation
    SEARCH = "search"       # Search-based navigation
    FILTER = "filter"       # Filter-based navigation


class EpisodeNavigator:
    """
    Handles keyboard navigation and episode selection.
    
    Provides various navigation modes and selection methods for
    browsing episode collections with keyboard shortcuts.
    """
    
    def __init__(self):
        """Initialize episode navigator."""
        self.console = get_console()
        
        # Navigation state
        self.current_position = 0
        self.navigation_mode = NavigationMode.LIST
        self.episodes: List[Episode] = []
        self.filtered_episodes: List[Episode] = []
        
        # Navigation settings
        self.page_size = 20
        self.grid_columns = 3
        
        # Command mappings
        self.command_handlers: Dict[str, Callable] = {
            # Navigation
            'n': self._next_page,
            'next': self._next_page,
            'p': self._previous_page,
            'prev': self._previous_page,
            'previous': self._previous_page,
            'f': self._first_page,
            'first': self._first_page,
            'l': self._last_page,
            'last': self._last_page,
            
            # Search and filter
            'search': self._search_episodes,
            'filter': self._filter_episodes,
            'clear': self._clear_filters,
            
            # Display modes
            'list': self._set_list_mode,
            'grid': self._set_grid_mode,
            
            # Selection
            'select': self._select_current,
            'details': self._show_details,
            
            # Help
            'help': self._show_help,
            'h': self._show_help,
        }
    
    def set_episodes(self, episodes: List[Episode]) -> None:
        """
        Set the episodes collection for navigation.
        
        Args:
            episodes: List of episodes to navigate
        """
        self.episodes = episodes
        self.filtered_episodes = episodes.copy()
        self.current_position = 0
    
    def get_current_page_episodes(self) -> List[Episode]:
        """
        Get episodes for the current page.
        
        Returns:
            List of episodes for current page
        """
        start_idx = self.current_position
        end_idx = min(start_idx + self.page_size, len(self.filtered_episodes))
        return self.filtered_episodes[start_idx:end_idx]
    
    def get_navigation_info(self) -> Dict[str, Any]:
        """
        Get current navigation state information.
        
        Returns:
            Dictionary with navigation state
        """
        total_episodes = len(self.filtered_episodes)
        current_page = (self.current_position // self.page_size) + 1
        total_pages = (total_episodes + self.page_size - 1) // self.page_size
        
        return {
            "current_page": current_page,
            "total_pages": total_pages,
            "total_episodes": total_episodes,
            "episodes_on_page": len(self.get_current_page_episodes()),
            "navigation_mode": self.navigation_mode.value,
            "has_filters": len(self.filtered_episodes) != len(self.episodes)
        }
    
    def process_navigation_command(self, command: str) -> Optional[str]:
        """
        Process a navigation command.
        
        Args:
            command: Navigation command string
            
        Returns:
            Result message or None
        """
        command = command.lower().strip()
        
        # Check for episode number selection
        if command.isdigit():
            return self._select_episode_by_number(int(command))
        
        # Check for range selection (e.g., "1-5")
        if '-' in command and all(part.strip().isdigit() for part in command.split('-')):
            return self._select_episode_range(command)
        
        # Process command handlers
        if command in self.command_handlers:
            return self.command_handlers[command]()
        
        return f"Unknown command: {command}"
    
    def _next_page(self) -> Optional[str]:
        """Navigate to next page."""
        total_episodes = len(self.filtered_episodes)
        next_position = self.current_position + self.page_size
        
        if next_position < total_episodes:
            self.current_position = next_position
            return None  # Success, no message needed
        else:
            return "Already on the last page"
    
    def _previous_page(self) -> Optional[str]:
        """Navigate to previous page."""
        if self.current_position > 0:
            self.current_position = max(0, self.current_position - self.page_size)
            return None  # Success, no message needed
        else:
            return "Already on the first page"
    
    def _first_page(self) -> Optional[str]:
        """Navigate to first page."""
        if self.current_position != 0:
            self.current_position = 0
            return "Moved to first page"
        else:
            return "Already on the first page"
    
    def _last_page(self) -> Optional[str]:
        """Navigate to last page."""
        total_episodes = len(self.filtered_episodes)
        last_page_start = ((total_episodes - 1) // self.page_size) * self.page_size
        
        if self.current_position != last_page_start:
            self.current_position = last_page_start
            return "Moved to last page"
        else:
            return "Already on the last page"
    
    def _search_episodes(self) -> Optional[str]:
        """Search episodes by title."""
        search_query = Prompt.ask("Enter search query").strip()
        
        if not search_query:
            return "Search cancelled"
        
        # Filter episodes by title
        matching_episodes = [
            ep for ep in self.episodes
            if search_query.lower() in ep.title.lower()
        ]
        
        if matching_episodes:
            self.filtered_episodes = matching_episodes
            self.current_position = 0
            return f"Found {len(matching_episodes)} episodes matching '{search_query}'"
        else:
            return f"No episodes found matching '{search_query}'"
    
    def _filter_episodes(self) -> Optional[str]:
        """Apply filters to episodes."""
        self.console.print("\n[bold blue]Episode Filters[/bold blue]")
        
        # Quality filter
        quality_filter = None
        quality_input = Prompt.ask(
            "Filter by quality? (480p/720p/1080p/1440p/2160p or press Enter to skip)",
            default=""
        ).strip()
        
        if quality_input:
            try:
                quality_filter = Quality(quality_input)
            except ValueError:
                return f"Invalid quality: {quality_input}"
        
        # Episode range filter
        range_filter = None
        range_input = Prompt.ask(
            "Episode range? (e.g., '1-10' or press Enter to skip)",
            default=""
        ).strip()
        
        if range_input:
            try:
                if '-' in range_input:
                    start, end = map(int, range_input.split('-', 1))
                    range_filter = (start, end)
                else:
                    episode_num = int(range_input)
                    range_filter = (episode_num, episode_num)
            except ValueError:
                return f"Invalid range format: {range_input}"
        
        # Filler filter
        hide_filler = Confirm.ask("Hide filler episodes?", default=False)
        
        # Apply filters
        filtered = self.episodes.copy()
        
        if quality_filter:
            filtered = [ep for ep in filtered if quality_filter in ep.quality_options]
        
        if range_filter:
            start, end = range_filter
            filtered = [ep for ep in filtered if start <= ep.number <= end]
        
        if hide_filler:
            filtered = [ep for ep in filtered if not ep.filler]
        
        self.filtered_episodes = filtered
        self.current_position = 0
        
        filter_count = len(filtered)
        return f"Applied filters: {filter_count} episodes match criteria"
    
    def _clear_filters(self) -> Optional[str]:
        """Clear all filters."""
        if len(self.filtered_episodes) != len(self.episodes):
            self.filtered_episodes = self.episodes.copy()
            self.current_position = 0
            return "All filters cleared"
        else:
            return "No filters to clear"
    
    def _set_list_mode(self) -> Optional[str]:
        """Set navigation to list mode."""
        if self.navigation_mode != NavigationMode.LIST:
            self.navigation_mode = NavigationMode.LIST
            return "Switched to list view"
        else:
            return "Already in list view"
    
    def _set_grid_mode(self) -> Optional[str]:
        """Set navigation to grid mode."""
        if self.navigation_mode != NavigationMode.GRID:
            self.navigation_mode = NavigationMode.GRID
            return "Switched to grid view"
        else:
            return "Already in grid view"
    
    def _select_current(self) -> Optional[str]:
        """Select current episode."""
        current_episodes = self.get_current_page_episodes()
        if current_episodes:
            # For now, select the first episode on the page
            episode = current_episodes[0]
            return f"Selected Episode {episode.number}: {episode.title}"
        else:
            return "No episodes to select"
    
    def _show_details(self) -> Optional[str]:
        """Show details for current selection."""
        return "Use episode number to view details (e.g., type '1' for episode 1)"
    
    def _show_help(self) -> Optional[str]:
        """Show navigation help."""
        help_text = """
[bold blue]Navigation Commands:[/bold blue]

[cyan]Page Navigation:[/cyan]
• n, next - Next page
• p, prev - Previous page  
• f, first - First page
• l, last - Last page

[cyan]Episode Selection:[/cyan]
• 1-999 - Select episode by number
• 1-5 - Select episode range

[cyan]Search & Filter:[/cyan]
• search - Search episodes by title
• filter - Apply episode filters
• clear - Clear all filters

[cyan]Display Modes:[/cyan]
• list - List view
• grid - Grid view

[cyan]Other:[/cyan]
• help, h - Show this help
• q, quit - Exit browser
"""
        
        self.console.print(help_text)
        return None
    
    def _select_episode_by_number(self, episode_number: int) -> Optional[str]:
        """
        Select episode by number.
        
        Args:
            episode_number: Episode number to select
            
        Returns:
            Selection result message
        """
        current_episodes = self.get_current_page_episodes()
        
        # Check if episode number is on current page
        for episode in current_episodes:
            if episode.number == episode_number:
                return f"Selected Episode {episode.number}: {episode.title}"
        
        # Check if episode exists in filtered list
        for episode in self.filtered_episodes:
            if episode.number == episode_number:
                # Navigate to the page containing this episode
                episode_index = self.filtered_episodes.index(episode)
                self.current_position = (episode_index // self.page_size) * self.page_size
                return f"Navigated to Episode {episode.number}: {episode.title}"
        
        return f"Episode {episode_number} not found in current results"
    
    def _select_episode_range(self, range_str: str) -> Optional[str]:
        """
        Select episode range.
        
        Args:
            range_str: Range string (e.g., "1-5")
            
        Returns:
            Selection result message
        """
        try:
            start, end = map(int, range_str.split('-', 1))
            
            # Find episodes in range
            episodes_in_range = [
                ep for ep in self.filtered_episodes
                if start <= ep.number <= end
            ]
            
            if episodes_in_range:
                return f"Found {len(episodes_in_range)} episodes in range {start}-{end}"
            else:
                return f"No episodes found in range {start}-{end}"
                
        except ValueError:
            return f"Invalid range format: {range_str}"
    
    def get_keyboard_shortcuts(self) -> Dict[str, str]:
        """
        Get available keyboard shortcuts.
        
        Returns:
            Dictionary of shortcut to description mappings
        """
        return {
            "n/next": "Next page",
            "p/prev": "Previous page",
            "f/first": "First page", 
            "l/last": "Last page",
            "1-999": "Select episode by number",
            "search": "Search episodes",
            "filter": "Apply filters",
            "clear": "Clear filters",
            "list": "List view",
            "grid": "Grid view",
            "help": "Show help",
            "q/quit": "Exit browser"
        }
    
    def create_navigation_status(self) -> str:
        """
        Create navigation status string.
        
        Returns:
            Formatted navigation status
        """
        info = self.get_navigation_info()
        
        status_parts = [
            f"Page {info['current_page']}/{info['total_pages']}",
            f"{info['total_episodes']} episodes"
        ]
        
        if info['has_filters']:
            status_parts.append("(filtered)")
        
        if info['navigation_mode'] != 'list':
            status_parts.append(f"{info['navigation_mode']} view")
        
        return " • ".join(status_parts)


# Export navigation utilities
__all__ = ["EpisodeNavigator", "NavigationMode"]