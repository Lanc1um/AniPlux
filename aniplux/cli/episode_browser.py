"""
Episode Browser - Interactive episode browsing and selection interface.

This module provides a comprehensive episode browsing interface with
Rich panels, keyboard navigation, and detailed episode information display.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from aniplux.core.models import AnimeResult, Episode, Quality
from aniplux.core.exceptions import PluginError
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    handle_error,
    status_spinner,
    format_title,
    format_muted,
    format_success,
    format_warning,
    format_quality,
)


logger = logging.getLogger(__name__)


class EpisodeBrowser:
    """
    Interactive episode browser with Rich interface and keyboard navigation.
    
    Provides comprehensive episode browsing functionality including filtering,
    sorting, detailed views, and episode selection for downloads.
    """
    
    def __init__(self, config_manager: Any):
        """
        Initialize episode browser.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.console = get_console()
        self.ui = UIComponents()
        
        # Browser state
        self.current_anime: Optional[AnimeResult] = None
        self.episodes: List[Episode] = []
        self.filtered_episodes: List[Episode] = []
        self.current_page = 0
        self.episodes_per_page = 20
        
        # Filters
        self.quality_filter: Optional[Quality] = None
        self.episode_range: Optional[Tuple[int, int]] = None
        self.hide_filler = False
        self.sort_order = "number"  # number, title, duration
    
    async def browse_anime_episodes(
        self,
        anime: AnimeResult,
        auto_select: bool = False
    ) -> Optional[Episode]:
        """
        Browse episodes for a specific anime.
        
        Args:
            anime: Anime to browse episodes for
            auto_select: Automatically select episode if only one available
            
        Returns:
            Selected episode or None if cancelled
        """
        self.current_anime = anime
        
        try:
            # Load episodes
            await self._load_episodes()
            
            if not self.episodes:
                display_warning(
                    f"No episodes found for '{anime.title}'.\n\n"
                    "This might be because:\n"
                    "• The anime page has no episode links\n"
                    "• The source plugin couldn't parse episodes\n"
                    "• Network connectivity issues\n"
                    "• The anime is not yet released",
                    "📺 No Episodes Available"
                )
                return None
            
            # Auto-select if only one episode
            if auto_select and len(self.episodes) == 1:
                return self.episodes[0]
            
            # Start interactive browsing
            return await self._interactive_browse()
            
        except PluginError as e:
            handle_error(e, f"Failed to load episodes for {anime.title}")
            return None
        except Exception as e:
            handle_error(e, f"Unexpected error browsing episodes for {anime.title}")
            return None
    
    async def _load_episodes(self) -> None:
        """Load episodes from the plugin."""
        from aniplux.core import PluginManager
        
        plugin_manager = PluginManager(self.config_manager)
        
        if not self.current_anime:
            raise ValueError("No anime selected for episode loading")
            
        with status_spinner(f"Loading episodes for {self.current_anime.title}..."):
            self.episodes = await plugin_manager.get_plugin_episodes(
                plugin_name=self.current_anime.source,
                anime_url=str(self.current_anime.url)
            )
        
        # Initialize filtered episodes
        self._apply_filters()
        
        logger.info(f"Loaded {len(self.episodes)} episodes for {self.current_anime.title}")
    
    async def _interactive_browse(self) -> Optional[Episode]:
        """
        Main interactive browsing loop.
        
        Returns:
            Selected episode or None if cancelled
        """
        try:
            while True:
                # Display current view
                self._display_browser_interface()
                
                # Get user command
                command = await self._get_user_command()
                
                if command is None:
                    # User wants to quit
                    return None
                
                # Process command
                result = await self._process_command(command)
                
                if isinstance(result, Episode):
                    # Episode selected
                    return result
                elif result == "quit":
                    return None
                
                # Continue browsing
                self.console.print()
        
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Episode browsing cancelled.[/yellow]")
            return None
    
    def _display_browser_interface(self) -> None:
        """Display the main browser interface."""
        self.console.clear()
        
        # Display header
        self._display_browser_header()
        
        # Display episodes
        self._display_episodes_page()
        
        # Display navigation help
        self._display_navigation_help()
    
    def _display_browser_header(self) -> None:
        """Display browser header with anime info and filters."""
        if not self.current_anime:
            return
            
        # Anime title
        title_text = f"📺 {self.current_anime.title}"
        if self.current_anime.year:
            title_text += f" ({self.current_anime.year})"
        
        self.console.print(format_title(title_text))
        
        # Episode count and filters
        total_episodes = len(self.episodes)
        filtered_count = len(self.filtered_episodes)
        
        info_parts = [f"{filtered_count}/{total_episodes} episodes"]
        
        if self.quality_filter:
            info_parts.append(f"Quality: {self.quality_filter.value}")
        
        if self.episode_range:
            start, end = self.episode_range
            info_parts.append(f"Range: {start}-{end}")
        
        if self.hide_filler:
            info_parts.append("No filler")
        
        if self.sort_order != "number":
            info_parts.append(f"Sort: {self.sort_order}")
        
        info_text = " • ".join(info_parts)
        self.console.print(format_muted(info_text))
        self.console.print()
    
    def _display_episodes_page(self) -> None:
        """Display current page of episodes."""
        if not self.filtered_episodes:
            self._display_no_episodes()
            return
        
        # Calculate page bounds
        start_idx = self.current_page * self.episodes_per_page
        end_idx = min(start_idx + self.episodes_per_page, len(self.filtered_episodes))
        page_episodes = self.filtered_episodes[start_idx:end_idx]
        
        # Create episodes table
        episodes_table = self.ui.create_episodes_table(page_episodes)
        self.console.print(episodes_table)
        
        # Display page info
        total_pages = (len(self.filtered_episodes) + self.episodes_per_page - 1) // self.episodes_per_page
        if total_pages > 1:
            page_info = f"Page {self.current_page + 1} of {total_pages}"
            self.console.print()
            self.console.print(format_muted(page_info))
    
    def _display_no_episodes(self) -> None:
        """Display message when no episodes match filters."""
        if len(self.episodes) == 0:
            message = "No episodes available for this anime."
        else:
            message = "No episodes match the current filters."
        
        no_episodes_panel = self.ui.create_warning_panel(
            message + "\n\nTry adjusting your filters or clearing them with 'clear'.",
            title="📺 No Episodes"
        )
        
        self.console.print(no_episodes_panel)
    
    def _display_navigation_help(self) -> None:
        """Display navigation help and commands."""
        help_text = """
[bold blue]Navigation:[/bold blue]
• [cyan]1-{max_num}[/cyan] - Select episode by number
• [cyan]n/next[/cyan] - Next page  • [cyan]p/prev[/cyan] - Previous page
• [cyan]f/filter[/cyan] - Set filters  • [cyan]s/sort[/cyan] - Change sort order
• [cyan]d/details[/cyan] - Show episode details  • [cyan]clear[/cyan] - Clear filters

[bold blue]Download Options:[/bold blue]
• [cyan]all[/cyan] - Download all episodes
• [cyan]1-5[/cyan] - Download episode range (e.g., episodes 1 to 5)
• [cyan]download 1,3,5[/cyan] - Download specific episodes (comma-separated)
• [cyan]q/quit[/cyan] - Exit browser

[dim]Enter command:[/dim]
""".format(max_num=min(len(self.filtered_episodes), self.episodes_per_page))
        
        self.console.print(help_text.strip())
    
    async def _get_user_command(self) -> Optional[str]:
        """
        Get user command input.
        
        Returns:
            User command or None if quit
        """
        try:
            command = self.console.input("[dim]> [/dim]").strip().lower()
            return command if command else None
        except (KeyboardInterrupt, EOFError):
            return None
    
    async def _process_command(self, command: str) -> Any:
        """
        Process user command.
        
        Args:
            command: User command string
            
        Returns:
            Episode if selected, "quit" to exit, or None to continue
        """
        # Quit commands
        if command in ['q', 'quit', 'exit']:
            return "quit"
        
        # Navigation commands
        elif command in ['n', 'next']:
            self._next_page()
        elif command in ['p', 'prev', 'previous']:
            self._previous_page()
        
        # Filter and sort commands
        elif command in ['f', 'filter']:
            await self._set_filters()
        elif command in ['s', 'sort']:
            await self._set_sort_order()
        elif command == 'clear':
            self._clear_filters()
        
        # Episode selection and details
        elif command in ['d', 'details']:
            await self._show_episode_details()
        elif command.isdigit():
            return await self._select_episode_by_number(int(command))
        
        # Bulk download commands
        elif command == 'all':
            await self._download_all_episodes()
            return "quit"  # Exit after download
        elif '-' in command and command.replace('-', '').replace(' ', '').isdigit():
            # Range download (e.g., "1-5")
            await self._download_episode_range(command)
            return "quit"  # Exit after download
        elif command.startswith('download '):
            # Specific episodes download (e.g., "download 1,3,5")
            episodes_str = command[9:]  # Remove "download " prefix
            await self._download_specific_episodes(episodes_str)
            return "quit"  # Exit after download
        
        # Unknown command
        else:
            display_warning(f"Unknown command: {command}", "❓ Invalid Command")
        
        return None
    
    def _next_page(self) -> None:
        """Navigate to next page."""
        total_pages = (len(self.filtered_episodes) + self.episodes_per_page - 1) // self.episodes_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
        else:
            display_info("Already on the last page.", "📄 Page Navigation")
    
    def _previous_page(self) -> None:
        """Navigate to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
        else:
            display_info("Already on the first page.", "📄 Page Navigation")
    
    async def _set_filters(self) -> None:
        """Interactive filter setting."""
        self.console.print("\n[bold blue]🔍 Episode Filters[/bold blue]\n")
        
        # Quality filter
        quality_choice = Prompt.ask(
            "Filter by quality? (480p/720p/1080p/1440p/2160p or 'none')",
            default="none"
        ).strip().lower()
        
        if quality_choice != "none":
            try:
                self.quality_filter = Quality(quality_choice)
            except ValueError:
                display_warning(f"Invalid quality: {quality_choice}")
                return
        else:
            self.quality_filter = None
        
        # Episode range filter
        range_choice = Prompt.ask(
            "Episode range? (e.g., '1-10' or 'none')",
            default="none"
        ).strip().lower()
        
        if range_choice != "none":
            try:
                if '-' in range_choice:
                    start, end = map(int, range_choice.split('-', 1))
                    self.episode_range = (start, end)
                else:
                    episode_num = int(range_choice)
                    self.episode_range = (episode_num, episode_num)
            except ValueError:
                display_warning(f"Invalid range format: {range_choice}")
                return
        else:
            self.episode_range = None
        
        # Filler filter
        self.hide_filler = Confirm.ask("Hide filler episodes?", default=self.hide_filler)
        
        # Apply filters
        self._apply_filters()
        self.current_page = 0  # Reset to first page
        
        display_info("Filters applied successfully!", "✅ Filters Applied")
    
    async def _set_sort_order(self) -> None:
        """Interactive sort order setting."""
        sort_options = ["number", "title", "duration"]
        
        sort_choice = Prompt.ask(
            "Sort episodes by",
            choices=sort_options,
            default=self.sort_order
        )
        
        self.sort_order = sort_choice
        self._apply_filters()  # Re-apply filters with new sort
        self.current_page = 0  # Reset to first page
        
        display_info(f"Episodes sorted by {sort_choice}!", "✅ Sort Applied")
    
    def _clear_filters(self) -> None:
        """Clear all filters."""
        self.quality_filter = None
        self.episode_range = None
        self.hide_filler = False
        self.sort_order = "number"
        
        self._apply_filters()
        self.current_page = 0
        
        display_info("All filters cleared!", "✅ Filters Cleared")
    
    def _apply_filters(self) -> None:
        """Apply current filters to episodes list."""
        filtered = self.episodes.copy()
        
        # Quality filter
        if self.quality_filter:
            filtered = [
                ep for ep in filtered
                if self.quality_filter in ep.quality_options
            ]
        
        # Episode range filter
        if self.episode_range:
            start, end = self.episode_range
            filtered = [
                ep for ep in filtered
                if start <= ep.number <= end
            ]
        
        # Filler filter
        if self.hide_filler:
            filtered = [ep for ep in filtered if not ep.filler]
        
        # Sort episodes
        if self.sort_order == "title":
            filtered.sort(key=lambda ep: ep.title.lower())
        elif self.sort_order == "duration":
            filtered.sort(key=lambda ep: ep.duration_seconds or 0, reverse=True)
        else:  # number (default)
            filtered.sort(key=lambda ep: ep.number)
        
        self.filtered_episodes = filtered
    
    async def _show_episode_details(self) -> None:
        """Show detailed episode selection and information."""
        if not self.filtered_episodes:
            display_warning("No episodes available to show details for.")
            return
        
        # Get episode selection
        episode_num = Prompt.ask(
            f"Enter episode number to view details [1-{len(self.filtered_episodes)}]",
            default="1"
        )
        
        try:
            index = int(episode_num) - 1
            if 0 <= index < len(self.filtered_episodes):
                episode = self.filtered_episodes[index]
                self._display_episode_details(episode)
                
                # Wait for user to continue
                self.console.input("\n[dim]Press Enter to continue...[/dim]")
            else:
                display_warning(f"Invalid episode number: {episode_num}")
        except ValueError:
            display_warning(f"Invalid number: {episode_num}")
    
    def _display_episode_details(self, episode: Episode) -> None:
        """
        Display detailed information for an episode.
        
        Args:
            episode: Episode to display details for
        """
        details = []
        
        # Episode title
        details.append(f"[bold blue]Episode {episode.number}: {episode.title}[/bold blue]")
        
        # Description
        if episode.description:
            details.append(f"\n[dim]Description:[/dim]\n{episode.description}")
        
        # Metadata
        metadata_lines = []
        
        if episode.duration:
            metadata_lines.append(f"[dim]Duration:[/dim] {episode.duration}")
        
        if episode.quality_options:
            qualities = ", ".join([format_quality(q) for q in episode.quality_options])
            metadata_lines.append(f"[dim]Available Qualities:[/dim] {qualities}")
        
        if episode.air_date:
            air_date_str = episode.air_date.strftime("%Y-%m-%d") if isinstance(episode.air_date, datetime) else str(episode.air_date)
            metadata_lines.append(f"[dim]Air Date:[/dim] {air_date_str}")
        
        episode_type = "Filler" if episode.filler else "Canon"
        type_color = "yellow" if episode.filler else "green"
        metadata_lines.append(f"[dim]Type:[/dim] [{type_color}]{episode_type}[/{type_color}]")
        
        if metadata_lines:
            details.append("\n" + "\n".join(metadata_lines))
        
        # URL
        details.append(f"\n[dim]Episode URL:[/dim] [blue]{episode.url}[/blue]")
        
        # Download command
        details.append(f"\n[dim]💡 To download this episode:[/dim]")
        details.append(f"[cyan]aniplux download episode {episode.url}[/cyan]")
        
        # Create and display panel
        content = "\n".join(details)
        anime_title = self.current_anime.title if self.current_anime else "Unknown"
        panel = self.ui.create_info_panel(
            content,
            title=f"📺 Episode Details - {anime_title}"
        )
        
        self.console.print()
        self.console.print(panel)
    
    async def _select_episode_by_number(self, number: int) -> Optional[Episode]:
        """
        Select episode by number.
        
        Args:
            number: Episode number (1-based)
            
        Returns:
            Selected episode or None if invalid
        """
        if not self.filtered_episodes:
            display_warning("No episodes available for selection.")
            return None
        
        if 1 <= number <= len(self.filtered_episodes):
            episode = self.filtered_episodes[number - 1]
            
            # Show episode details and confirm selection
            self.console.print()
            self._display_episode_details(episode)
            
            if Confirm.ask(f"\nSelect Episode {episode.number} for download?", default=True):
                return episode
        else:
            display_warning(f"Invalid episode number: {number}. Valid range: 1-{len(self.filtered_episodes)}")
        
        return None
    
    async def _download_all_episodes(self) -> None:
        """Download all filtered episodes."""
        if not self.filtered_episodes:
            display_warning("No episodes available for download.")
            return
        
        from rich.prompt import Confirm
        
        # Confirm download
        if not Confirm.ask(
            f"Download all {len(self.filtered_episodes)} episodes?",
            default=True
        ):
            display_info("Download cancelled.", "📺 Download Cancelled")
            return
        
        # Get quality preference
        quality = await self._get_quality_preference()
        
        # Start download
        await self._start_bulk_download(self.filtered_episodes, quality, "all episodes")
    
    async def _download_episode_range(self, range_str: str) -> None:
        """
        Download episodes in a range.
        
        Args:
            range_str: Range string like "1-5"
        """
        try:
            # Parse range
            start_str, end_str = range_str.split('-', 1)
            start_num = int(start_str.strip())
            end_num = int(end_str.strip())
            
            if start_num > end_num:
                display_warning("Invalid range: start number must be less than or equal to end number.")
                return
            
            # Find episodes in range
            episodes_in_range = [
                ep for ep in self.filtered_episodes
                if start_num <= ep.number <= end_num
            ]
            
            if not episodes_in_range:
                display_warning(f"No episodes found in range {start_num}-{end_num}.")
                return
            
            from rich.prompt import Confirm
            
            # Confirm download
            if not Confirm.ask(
                f"Download {len(episodes_in_range)} episodes (episodes {start_num}-{end_num})?",
                default=True
            ):
                display_info("Download cancelled.", "📺 Download Cancelled")
                return
            
            # Get quality preference
            quality = await self._get_quality_preference()
            
            # Start download
            await self._start_bulk_download(
                episodes_in_range, 
                quality, 
                f"episodes {start_num}-{end_num}"
            )
            
        except ValueError:
            display_warning(f"Invalid range format: {range_str}. Use format like '1-5'.")
    
    async def _download_specific_episodes(self, episodes_str: str) -> None:
        """
        Download specific episodes by numbers.
        
        Args:
            episodes_str: Comma-separated episode numbers like "1,3,5"
        """
        try:
            # Parse episode numbers
            episode_numbers = []
            for num_str in episodes_str.split(','):
                num_str = num_str.strip()
                if num_str.isdigit():
                    episode_numbers.append(int(num_str))
                else:
                    display_warning(f"Invalid episode number: {num_str}")
                    return
            
            if not episode_numbers:
                display_warning("No valid episode numbers provided.")
                return
            
            # Find episodes by numbers
            episodes_to_download = []
            for ep in self.filtered_episodes:
                if ep.number in episode_numbers:
                    episodes_to_download.append(ep)
            
            if not episodes_to_download:
                display_warning(f"No episodes found for numbers: {episodes_str}")
                return
            
            # Check if all requested episodes were found
            found_numbers = [ep.number for ep in episodes_to_download]
            missing_numbers = [num for num in episode_numbers if num not in found_numbers]
            
            if missing_numbers:
                display_warning(
                    f"Episodes not found: {', '.join(map(str, missing_numbers))}\n"
                    f"Found episodes: {', '.join(map(str, found_numbers))}"
                )
                
                from rich.prompt import Confirm
                if not Confirm.ask("Continue with found episodes?", default=True):
                    display_info("Download cancelled.", "📺 Download Cancelled")
                    return
            
            from rich.prompt import Confirm
            
            # Confirm download
            episode_list = ', '.join(str(ep.number) for ep in episodes_to_download)
            if not Confirm.ask(
                f"Download {len(episodes_to_download)} episodes ({episode_list})?",
                default=True
            ):
                display_info("Download cancelled.", "📺 Download Cancelled")
                return
            
            # Get quality preference
            quality = await self._get_quality_preference()
            
            # Start download
            await self._start_bulk_download(
                episodes_to_download, 
                quality, 
                f"episodes {episode_list}"
            )
            
        except ValueError as e:
            display_warning(f"Invalid episode format: {episodes_str}. Use format like '1,3,5'.")
    
    async def _get_quality_preference(self) -> Optional[Quality]:
        """
        Get user's quality preference for downloads.
        
        Returns:
            Selected quality or None for auto-selection
        """
        from rich.prompt import Prompt
        
        # Get available qualities from episodes
        all_qualities = set()
        for episode in self.filtered_episodes:
            all_qualities.update(episode.quality_options)
        
        if not all_qualities:
            return None
        
        # Sort qualities by preference (highest first)
        quality_order = [Quality.ULTRA, Quality.HIGH, Quality.MEDIUM, Quality.LOW]
        available_qualities = [q for q in quality_order if q in all_qualities]
        
        if len(available_qualities) == 1:
            return available_qualities[0]
        
        # Ask user for quality preference
        quality_choices = [q.value for q in available_qualities] + ["auto"]
        
        quality_choice = Prompt.ask(
            "Select quality for downloads",
            choices=quality_choices,
            default="auto"
        )
        
        if quality_choice == "auto":
            return None
        
        # Find matching quality
        for quality in available_qualities:
            if quality.value == quality_choice:
                return quality
        
        return None
    
    async def _start_bulk_download(
        self, 
        episodes: List[Episode], 
        quality: Optional[Quality],
        description: str
    ) -> None:
        """
        Start bulk download of episodes.
        
        Args:
            episodes: Episodes to download
            quality: Quality preference
            description: Description for user feedback
        """
        try:
            source_name = self.current_anime.source if self.current_anime else "Unknown"
            display_info(
                f"Starting download of {description}...\n"
                f"Episodes: {len(episodes)}\n"
                f"Quality: {quality.value if quality else 'Auto'}\n"
                f"Source: {source_name}",
                "⬇️  Starting Download"
            )
            
            # Import download manager
            from aniplux.cli.download_manager import DownloadManager
            
            # Initialize download manager
            download_manager = DownloadManager(self.config_manager)
            
            # Start batch download
            anime_title = self.current_anime.title if self.current_anime else "Unknown"
            await download_manager.download_batch_episodes(
                episodes=episodes,
                quality=quality,
                anime_title=anime_title
            )
            
        except Exception as e:
            handle_error(e, f"Failed to download {description}")


# Export episode browser
__all__ = ["EpisodeBrowser"]