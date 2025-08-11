"""
Interactive Search Handler - Interactive result selection and episode browsing.

This module provides interactive functionality for search results,
allowing users to select anime and browse episodes with clean prompts.
"""

import asyncio
import logging
from typing import List, Optional, Any

from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from aniplux.core.models import AnimeResult, Episode
from aniplux.core.exceptions import PluginError
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    handle_error,
    status_spinner,
)


logger = logging.getLogger(__name__)


class InteractiveSearchHandler:
    """
    Handles interactive search result selection and episode browsing.
    
    Provides user-friendly prompts for selecting anime from search results
    and browsing available episodes with detailed information.
    """
    
    def __init__(self, config_manager: Any):
        """
        Initialize interactive handler.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.console = get_console()
        self.ui = UIComponents()
    
    async def handle_interactive_selection(self, results: List[AnimeResult]) -> None:
        """
        Handle interactive selection from search results.
        
        Args:
            results: List of anime search results
        """
        if not results:
            display_warning("No results available for interactive selection.")
            return
        
        try:
            # Show interactive menu
            self._display_interactive_header(len(results))
            
            while True:
                # Get user selection
                selection = self._get_user_selection(results)
                
                if selection is None:
                    # User chose to exit
                    self.console.print("[dim]Exiting interactive mode.[/dim]")
                    break
                
                # Show selected anime details and episodes
                await self._handle_anime_selection(results[selection])
                
                # Ask if user wants to select another anime
                if not Confirm.ask("\nSelect another anime?", default=False):
                    break
                
                self.console.print()
        
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interactive mode cancelled.[/yellow]")
        except Exception as e:
            handle_error(e, "During interactive selection")
    
    def _display_interactive_header(self, result_count: int) -> None:
        """Display interactive mode header."""
        header_text = f"""
[bold blue]🎯 Interactive Mode[/bold blue]

Select an anime from the {result_count} results below to view episodes and details.
Enter the number of your choice, or 'q' to quit.
"""
        
        panel = Panel(
            header_text.strip(),
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
    
    def _get_user_selection(self, results: List[AnimeResult]) -> Optional[int]:
        """
        Get user selection from search results.
        
        Args:
            results: List of anime results
            
        Returns:
            Selected index (0-based) or None if user wants to quit
        """
        while True:
            try:
                # Create choices list
                choices = [str(i + 1) for i in range(len(results))]
                choices.extend(['q', 'quit', 'exit'])
                
                # Get user input
                selection = Prompt.ask(
                    f"Select anime [1-{len(results)}] or 'q' to quit",
                    choices=choices,
                    show_choices=False
                ).strip().lower()
                
                # Handle quit
                if selection in ['q', 'quit', 'exit']:
                    return None
                
                # Convert to index
                try:
                    index = int(selection) - 1
                    if 0 <= index < len(results):
                        return index
                    else:
                        self.console.print(f"[red]Please enter a number between 1 and {len(results)}[/red]")
                except ValueError:
                    self.console.print("[red]Please enter a valid number or 'q' to quit[/red]")
            
            except (KeyboardInterrupt, EOFError):
                return None
    
    async def _handle_anime_selection(self, anime: AnimeResult) -> None:
        """
        Handle selection of a specific anime.
        
        Args:
            anime: Selected anime result
        """
        self.console.print()
        
        # Display detailed anime information
        self._display_anime_details(anime)
        
        # Ask if user wants to view episodes
        if Confirm.ask("View available episodes?", default=True):
            await self._display_anime_episodes(anime)
    
    def _display_anime_details(self, anime: AnimeResult) -> None:
        """
        Display detailed information about selected anime.
        
        Args:
            anime: Anime to display details for
        """
        details = []
        
        # Title
        details.append(f"[bold blue]{anime.title}[/bold blue]")
        
        # Description
        if anime.description:
            details.append(f"\n[dim]Description:[/dim]\n{anime.description}")
        
        # Metadata
        metadata_lines = []
        
        if anime.year:
            metadata_lines.append(f"[dim]Year:[/dim] {anime.year}")
        
        if anime.episode_count:
            metadata_lines.append(f"[dim]Episodes:[/dim] {anime.episode_count}")
        
        if anime.rating:
            rating_color = "green" if anime.rating >= 8.0 else "yellow" if anime.rating >= 7.0 else "red"
            metadata_lines.append(f"[dim]Rating:[/dim] [{rating_color}]{anime.rating:.1f}/10[/{rating_color}]")
        
        if anime.genres:
            genres_text = ", ".join(anime.genres)
            metadata_lines.append(f"[dim]Genres:[/dim] {genres_text}")
        
        if metadata_lines:
            details.append("\n" + "\n".join(metadata_lines))
        
        # Source information
        details.append(f"\n[dim]Source:[/dim] [cyan]{anime.source}[/cyan]")
        
        # Create and display panel
        content = "\n".join(details)
        panel = self.ui.create_info_panel(content, title="📺 Anime Information")
        
        self.console.print(panel)
    
    async def _display_anime_episodes(self, anime: AnimeResult) -> None:
        """
        Display episodes for the selected anime.
        
        Args:
            anime: Anime to show episodes for
        """
        try:
            # Use the episode browser for a richer experience
            from aniplux.cli.episode_browser import EpisodeBrowser
            
            episode_browser = EpisodeBrowser(self.config_manager)
            selected_episode = await episode_browser.browse_anime_episodes(anime)
            
            if selected_episode:
                display_info(
                    f"Episode selected: {selected_episode.title}\n\n"
                    f"To download this episode, use:\n"
                    f"[cyan]aniplux download episode {selected_episode.url}[/cyan]",
                    "📺 Episode Selected"
                )
        
        except PluginError as e:
            handle_error(e, f"Failed to load episodes for {anime.title}")
        except Exception as e:
            handle_error(e, f"Unexpected error loading episodes for {anime.title}")
    
    def _display_episodes_list(self, episodes: List[Episode], anime_title: str) -> None:
        """
        Display list of episodes in a formatted table.
        
        Args:
            episodes: List of episodes
            anime_title: Title of the anime
        """
        self.console.print()
        
        # Create episodes table
        episodes_table = self.ui.create_episodes_table(episodes)
        
        panel = self.ui.create_info_panel(
            episodes_table,
            title=f"📺 Episodes - {anime_title}"
        )
        
        self.console.print(panel)
    
    async def _handle_episode_selection(
        self,
        episodes: List[Episode],
        anime: AnimeResult
    ) -> None:
        """
        Handle interactive episode selection.
        
        Args:
            episodes: List of available episodes
            anime: Parent anime result
        """
        while True:
            try:
                # Get episode selection
                episode_selection = self._get_episode_selection(episodes)
                
                if episode_selection is None:
                    break
                
                # Display episode details
                selected_episode = episodes[episode_selection]
                self._display_episode_details(selected_episode, anime)
                
                # Ask if user wants to select another episode
                if not Confirm.ask("Select another episode?", default=False):
                    break
                
                self.console.print()
            
            except (KeyboardInterrupt, EOFError):
                break
    
    def _get_episode_selection(self, episodes: List[Episode]) -> Optional[int]:
        """
        Get user selection for episode.
        
        Args:
            episodes: List of episodes
            
        Returns:
            Selected episode index or None if user wants to quit
        """
        while True:
            try:
                # Create choices
                choices = [str(i + 1) for i in range(len(episodes))]
                choices.extend(['q', 'quit', 'exit'])
                
                selection = Prompt.ask(
                    f"Select episode [1-{len(episodes)}] or 'q' to quit",
                    choices=choices,
                    show_choices=False
                ).strip().lower()
                
                if selection in ['q', 'quit', 'exit']:
                    return None
                
                try:
                    index = int(selection) - 1
                    if 0 <= index < len(episodes):
                        return index
                    else:
                        self.console.print(f"[red]Please enter a number between 1 and {len(episodes)}[/red]")
                except ValueError:
                    self.console.print("[red]Please enter a valid number or 'q' to quit[/red]")
            
            except (KeyboardInterrupt, EOFError):
                return None
    
    def _display_episode_details(self, episode: Episode, anime: AnimeResult) -> None:
        """
        Display detailed information about selected episode.
        
        Args:
            episode: Episode to display
            anime: Parent anime
        """
        details = []
        
        # Episode title
        details.append(f"[bold blue]Episode {episode.number}: {episode.title}[/bold blue]")
        
        # Description
        if episode.description:
            details.append(f"\n[dim]Description:[/dim]\n{episode.description}")
        
        # Episode metadata
        metadata_lines = []
        
        if episode.duration:
            metadata_lines.append(f"[dim]Duration:[/dim] {episode.duration}")
        
        if episode.quality_options:
            qualities = ", ".join([q.value for q in episode.quality_options])
            metadata_lines.append(f"[dim]Available Qualities:[/dim] {qualities}")
        
        if episode.air_date:
            metadata_lines.append(f"[dim]Air Date:[/dim] {episode.air_date}")
        
        episode_type = "Filler" if episode.filler else "Canon"
        type_color = "yellow" if episode.filler else "green"
        metadata_lines.append(f"[dim]Type:[/dim] [{type_color}]{episode_type}[/{type_color}]")
        
        if metadata_lines:
            details.append("\n" + "\n".join(metadata_lines))
        
        # URL
        details.append(f"\n[dim]Episode URL:[/dim] [blue]{episode.url}[/blue]")
        
        # Download hint
        details.append(f"\n[dim]💡 To download this episode, use:[/dim]")
        details.append(f"[cyan]aniplux download episode {episode.url}[/cyan]")
        
        # Create and display panel
        content = "\n".join(details)
        panel = self.ui.create_info_panel(
            content,
            title=f"📺 Episode Details - {anime.title}"
        )
        
        self.console.print()
        self.console.print(panel)


# Export interactive handler
__all__ = ["InteractiveSearchHandler"]