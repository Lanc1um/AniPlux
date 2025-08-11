"""
Configuration Preview - Theme and setting preview functionality.

This module provides preview capabilities for configuration changes,
allowing users to see how settings will look before applying them.
"""

import logging
from typing import Dict, Any, Optional

from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.console import Group

from aniplux.ui import (
    get_console,
    UIComponents,
    ThemeName,
    get_theme,
    setup_console,
)


logger = logging.getLogger(__name__)


class ConfigurationPreview:
    """
    Provides preview functionality for configuration changes.
    
    Allows users to preview themes, UI styles, and other visual
    settings before applying them to their configuration.
    """
    
    def __init__(self):
        """Initialize configuration preview."""
        self.console = get_console()
        self.ui = UIComponents()
    
    def preview_theme(self, theme_name: str) -> None:
        """
        Preview a color theme with sample UI components.
        
        Args:
            theme_name: Name of the theme to preview
        """
        try:
            theme = ThemeName(theme_name)
        except ValueError:
            self.console.print(f"[red]❌ Invalid theme: {theme_name}[/red]")
            return
        
        # Create themed console for preview
        preview_console = setup_console(theme)
        
        self.console.print(f"\n[bold blue]🎨 Theme Preview: {theme_name.title()}[/bold blue]\n")
        
        # Preview different UI components
        self._preview_panels(preview_console, theme)
        self._preview_tables(preview_console, theme)
        self._preview_progress(preview_console, theme)
        self._preview_status_messages(preview_console, theme)
        
        self.console.print("\n[dim]Preview complete. Use 'aniplux config set ui.color_theme {theme_name}' to apply.[/dim]")
    
    def preview_all_themes(self) -> None:
        """Preview all available themes side by side."""
        themes = ["default", "dark", "light", "colorful"]
        
        self.console.print("[bold blue]🎨 All Theme Previews[/bold blue]\n")
        
        for theme_name in themes:
            self.console.print(f"[bold cyan]═══ {theme_name.upper()} THEME ═══[/bold cyan]")
            self.preview_theme(theme_name)
            self.console.print()
    
    def preview_ui_styles(self, style_type: str, style_value: str) -> None:
        """
        Preview UI style changes.
        
        Args:
            style_type: Type of style (table_style, panel_style, progress_style)
            style_value: Style value to preview
        """
        self.console.print(f"\n[bold blue]🎨 {style_type.title()} Preview: {style_value}[/bold blue]\n")
        
        if style_type == "table_style":
            self._preview_table_style(style_value)
        elif style_type == "panel_style":
            self._preview_panel_style(style_value)
        elif style_type == "progress_style":
            self._preview_progress_style(style_value)
        else:
            self.console.print(f"[red]❌ Unknown style type: {style_type}[/red]")
    
    def _preview_panels(self, console, theme: ThemeName) -> None:
        """Preview panel styles with the theme."""
        # Info panel
        info_panel = Panel(
            "This is an information panel with sample content.\n"
            "It shows how informational messages will appear.",
            title="📋 Information",
            border_style="blue",
            padding=(1, 2)
        )
        
        # Success panel
        success_panel = Panel(
            "This is a success panel showing positive feedback.\n"
            "Operations completed successfully will look like this.",
            title="✅ Success",
            border_style="green",
            padding=(1, 2)
        )
        
        # Warning panel
        warning_panel = Panel(
            "This is a warning panel for important notices.\n"
            "Warnings and cautions will be displayed this way.",
            title="⚠️  Warning",
            border_style="yellow",
            padding=(1, 2)
        )
        
        # Error panel
        error_panel = Panel(
            "This is an error panel for critical issues.\n"
            "Errors and failures will be shown like this.",
            title="❌ Error",
            border_style="red",
            padding=(1, 2)
        )
        
        console.print("Panel Styles:")
        console.print(info_panel)
        console.print(success_panel)
        console.print(warning_panel)
        console.print(error_panel)
        console.print()
    
    def _preview_tables(self, console, theme: ThemeName) -> None:
        """Preview table styles with the theme."""
        table = Table(
            title="📊 Sample Data Table",
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Anime Title", style="cyan", width=25)
        table.add_column("Episodes", style="white", width=10)
        table.add_column("Quality", style="green", width=10)
        table.add_column("Status", style="yellow", width=15)
        
        # Sample data
        sample_data = [
            ("Attack on Titan", "87", "1080p", "✅ Available"),
            ("Demon Slayer", "44", "720p", "🔄 Downloading"),
            ("One Piece", "1000+", "1080p", "⚠️  Limited"),
            ("Naruto", "720", "480p", "❌ Unavailable"),
        ]
        
        for row in sample_data:
            table.add_row(*row)
        
        console.print("Table Styles:")
        console.print(table)
        console.print()
    
    def _preview_progress(self, console, theme: ThemeName) -> None:
        """Preview progress indicators with the theme."""
        console.print("Progress Indicators:")
        
        # Progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Sample download progress", total=100)
            progress.update(task, advance=65)
            console.print()  # Force display
        
        # Status indicators
        console.print("Status Indicators:")
        console.print("🔍 [cyan]Searching for anime...[/cyan]")
        console.print("📥 [green]Download completed successfully[/green]")
        console.print("⚠️  [yellow]Connection timeout, retrying...[/yellow]")
        console.print("❌ [red]Failed to parse episode data[/red]")
        console.print()
    
    def _preview_status_messages(self, console, theme: ThemeName) -> None:
        """Preview status message styles with the theme."""
        console.print("Status Messages:")
        
        # Different message types
        messages = [
            ("info", "ℹ️  Configuration loaded successfully"),
            ("success", "✅ Settings updated and saved"),
            ("warning", "⚠️  Some sources are disabled"),
            ("error", "❌ Failed to connect to source"),
            ("debug", "🔧 Plugin manager initialized"),
        ]
        
        for msg_type, message in messages:
            if msg_type == "info":
                console.print(f"[blue]{message}[/blue]")
            elif msg_type == "success":
                console.print(f"[green]{message}[/green]")
            elif msg_type == "warning":
                console.print(f"[yellow]{message}[/yellow]")
            elif msg_type == "error":
                console.print(f"[red]{message}[/red]")
            elif msg_type == "debug":
                console.print(f"[dim]{message}[/dim]")
        
        console.print()
    
    def _preview_table_style(self, style: str) -> None:
        """Preview specific table style."""
        # Map style names to Rich table styles
        style_map = {
            "rounded": "rounded",
            "simple": "simple",
            "grid": "grid",
            "minimal": "minimal"
        }
        
        rich_style = style_map.get(style, "rounded")
        
        from rich import box
        
        box_obj = getattr(box, rich_style.upper(), box.ROUNDED)
        
        table = Table(
            title=f"Table Style: {style}",
            show_header=True,
            header_style="bold blue",
            border_style="blue",
            box=box_obj
        )
        
        table.add_column("Column 1", style="cyan")
        table.add_column("Column 2", style="white")
        table.add_column("Column 3", style="green")
        
        table.add_row("Sample", "Data", "Row 1")
        table.add_row("Another", "Example", "Row 2")
        table.add_row("Final", "Sample", "Row 3")
        
        self.console.print(table)
    
    def _preview_panel_style(self, style: str) -> None:
        """Preview specific panel style."""
        # Map style names to Rich box styles
        style_map = {
            "rounded": "ROUNDED",
            "square": "SQUARE", 
            "heavy": "HEAVY",
            "double": "DOUBLE"
        }
        
        box_style = style_map.get(style, "ROUNDED")
        
        from rich import box
        
        box_obj = getattr(box, box_style, box.ROUNDED)
        
        panel = Panel(
            f"This is a sample panel using the '{style}' style.\n"
            "Panel content will be displayed with this border style.",
            title=f"Panel Style: {style}",
            border_style="blue",
            padding=(1, 2),
            box=box_obj
        )
        
        self.console.print(panel)
    
    def _preview_progress_style(self, style: str) -> None:
        """Preview specific progress style."""
        self.console.print(f"Progress Style: {style}")
        
        if style == "bar":
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                transient=True
            ) as progress:
                task = progress.add_task("Sample progress bar", total=100)
                progress.update(task, advance=75)
                self.console.print()
        
        elif style == "spinner":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("Sample spinner progress")
                self.console.print()
        
        elif style == "dots":
            self.console.print("🔄 Sample dots progress... ⚫⚫⚫⚪⚪")
        
        else:
            self.console.print(f"[red]❌ Unknown progress style: {style}[/red]")
    
    def preview_setting_change(self, setting_path: str, old_value: Any, new_value: Any) -> None:
        """
        Preview the effect of a setting change.
        
        Args:
            setting_path: Dot notation path of the setting
            old_value: Current value
            new_value: Proposed new value
        """
        self.console.print(f"\n[bold blue]🔍 Setting Change Preview[/bold blue]\n")
        
        # Create comparison table
        table = Table(
            title=f"Setting: {setting_path}",
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Aspect", style="cyan", width=20)
        table.add_column("Current Value", style="white", width=20)
        table.add_column("New Value", style="green", width=20)
        table.add_column("Impact", style="yellow", width=30)
        
        # Analyze impact
        impact = self._analyze_setting_impact(setting_path, old_value, new_value)
        
        table.add_row(
            "Value",
            str(old_value),
            str(new_value),
            impact
        )
        
        self.console.print(table)
        
        # Show specific previews for visual settings
        if setting_path.startswith("ui."):
            setting_name = setting_path.split(".")[-1]
            if setting_name == "color_theme":
                self.console.print("\n[dim]Theme preview:[/dim]")
                self.preview_theme(str(new_value))
            elif setting_name.endswith("_style"):
                style_type = setting_name
                self.console.print(f"\n[dim]{style_type} preview:[/dim]")
                self.preview_ui_styles(style_type, str(new_value))
    
    def _analyze_setting_impact(self, setting_path: str, old_value: Any, new_value: Any) -> str:
        """Analyze the impact of a setting change."""
        if setting_path.startswith("ui."):
            return "Visual appearance change"
        elif setting_path.startswith("settings."):
            if "download" in setting_path:
                return "Download behavior change"
            elif "timeout" in setting_path:
                return "Network behavior change"
            else:
                return "Application behavior change"
        elif setting_path.startswith("search."):
            return "Search behavior change"
        elif setting_path.startswith("logging."):
            return "Logging behavior change"
        else:
            return "Configuration change"


# Export preview functionality
__all__ = ["ConfigurationPreview"]