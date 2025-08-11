"""
Configuration Wizard - First-time setup and guided configuration.

This module provides a step-by-step configuration wizard for new users,
helping them set up AniPlux with optimal settings for their system.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from aniplux.core import ConfigManager
from aniplux.core.config_utils import optimize_config_for_system
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    ThemeName,
    set_theme,
    update_console_theme,
)


logger = logging.getLogger(__name__)


class ConfigurationWizard:
    """
    Guided configuration wizard for first-time setup.
    
    Provides step-by-step configuration with system detection,
    optimization suggestions, and user-friendly prompts.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize configuration wizard.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.console = get_console()
        self.ui = UIComponents()
        
        # Wizard state
        self.wizard_config = {}
        self.current_step = 0
        self.total_steps = 6
    
    def run_wizard(self) -> bool:
        """
        Run the complete configuration wizard.
        
        Returns:
            True if wizard completed successfully, False if cancelled
        """
        try:
            self._show_welcome()
            
            if not self._confirm_start():
                return False
            
            # Run wizard steps
            steps = [
                self._step_download_directory,
                self._step_quality_preferences,
                self._step_performance_settings,
                self._step_ui_preferences,
                self._step_source_configuration,
                self._step_final_review,
            ]
            
            for i, step in enumerate(steps, 1):
                self.current_step = i
                self._show_step_header(i, step.__name__.replace('_step_', '').replace('_', ' ').title())
                
                if not step():
                    if not self._confirm_continue():
                        return False
            
            # Apply configuration
            self._apply_configuration()
            self._show_completion()
            
            return True
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Configuration wizard cancelled by user.[/yellow]")
            return False
        except Exception as e:
            self.console.print(f"\n[red]❌ Wizard failed: {e}[/red]")
            return False
    
    def _show_welcome(self) -> None:
        """Show welcome message and wizard overview."""
        welcome_text = (
            "[bold blue]🎉 Welcome to AniPlux![/bold blue]\n\n"
            "This wizard will help you configure AniPlux for optimal performance "
            "on your system. We'll guide you through:\n\n"
            "• Download directory setup\n"
            "• Quality and performance preferences\n"
            "• User interface customization\n"
            "• Source plugin configuration\n\n"
            "[dim]The wizard takes about 2-3 minutes to complete.[/dim]"
        )
        
        panel = Panel(
            welcome_text,
            title="🚀 Configuration Wizard",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _confirm_start(self) -> bool:
        """Confirm user wants to start the wizard."""
        return Confirm.ask(
            "\n[bold blue]Ready to start the configuration wizard?[/bold blue]",
            default=True
        )
    
    def _show_step_header(self, step_num: int, step_name: str) -> None:
        """Show step header with progress."""
        progress_bar = "█" * step_num + "░" * (self.total_steps - step_num)
        
        header = (
            f"[bold blue]Step {step_num}/{self.total_steps}: {step_name}[/bold blue]\n"
            f"[dim]Progress: [{progress_bar}] {step_num}/{self.total_steps}[/dim]"
        )
        
        self.console.print(f"\n{header}\n")
    
    def _step_download_directory(self) -> bool:
        """Configure download directory."""
        self.console.print("📁 Let's set up your download directory.\n")
        
        # Get current directory
        current_dir = self.config_manager.settings.settings.download_directory
        self.console.print(f"[dim]Current: {current_dir}[/dim]")
        
        # Suggest common directories
        suggestions = [
            str(Path.home() / "Downloads" / "AniPlux"),
            str(Path.home() / "Videos" / "Anime"),
            "./downloads",
            "Custom path"
        ]
        
        self.console.print("\n[cyan]Suggested directories:[/cyan]")
        for i, suggestion in enumerate(suggestions, 1):
            self.console.print(f"  {i}. {suggestion}")
        
        choice = Prompt.ask(
            "\nSelect a directory or enter custom path",
            choices=[str(i) for i in range(1, len(suggestions) + 1)] + ["custom"],
            default="1"
        )
        
        if choice == "custom" or choice == str(len(suggestions)):
            download_dir = Prompt.ask("Enter custom download directory path")
        else:
            download_dir = suggestions[int(choice) - 1]
        
        # Validate and create directory
        try:
            path = Path(download_dir).expanduser().resolve()
            path.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            self.wizard_config["download_directory"] = str(path)
            self.console.print(f"[green]✅ Download directory set: {path}[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Error with directory: {e}[/red]")
            return False
    
    def _step_quality_preferences(self) -> bool:
        """Configure quality and download preferences."""
        self.console.print("🎬 Let's configure your quality preferences.\n")
        
        # Default quality
        qualities = ["480p", "720p", "1080p", "1440p", "2160p"]
        self.console.print("[cyan]Available qualities:[/cyan]")
        for i, quality in enumerate(qualities, 1):
            self.console.print(f"  {i}. {quality}")
        
        quality_choice = Prompt.ask(
            "Select default quality",
            choices=[str(i) for i in range(1, len(qualities) + 1)],
            default="2"  # 720p
        )
        
        self.wizard_config["default_quality"] = qualities[int(quality_choice) - 1]
        
        # Retry settings
        max_retries = IntPrompt.ask(
            "Maximum retry attempts for failed downloads",
            default=3,
            show_default=True
        )
        
        self.wizard_config["max_retries"] = max_retries
        
        self.console.print(
            f"[green]✅ Quality preferences set: {self.wizard_config['default_quality']}, "
            f"{max_retries} retries[/green]"
        )
        return True
    
    def _step_performance_settings(self) -> bool:
        """Configure performance settings based on system."""
        self.console.print("⚡ Let's optimize performance for your system.\n")
        
        # Detect system capabilities
        with self.console.status("Analyzing system capabilities..."):
            suggestions = optimize_config_for_system(self.config_manager)
        
        if suggestions:
            self.console.print("[yellow]System analysis suggestions:[/yellow]")
            for suggestion in suggestions:
                self.console.print(f"  • {suggestion}")
            self.console.print()
        
        # Concurrent downloads
        try:
            import os
            cpu_count = os.cpu_count() or 2
            suggested_concurrent = min(cpu_count, 4)
        except:
            suggested_concurrent = 3
        
        concurrent = IntPrompt.ask(
            f"Concurrent downloads (recommended: {suggested_concurrent})",
            default=suggested_concurrent,
            show_default=True
        )
        
        # Timeout settings
        timeout = IntPrompt.ask(
            "Network timeout in seconds",
            default=30,
            show_default=True
        )
        
        self.wizard_config.update({
            "concurrent_downloads": concurrent,
            "timeout": timeout
        })
        
        self.console.print(
            f"[green]✅ Performance settings: {concurrent} concurrent, {timeout}s timeout[/green]"
        )
        return True
    
    def _step_ui_preferences(self) -> bool:
        """Configure UI preferences and theme."""
        self.console.print("🎨 Let's customize your user interface.\n")
        
        # Theme selection
        themes = ["default", "dark", "light", "colorful"]
        self.console.print("[cyan]Available themes:[/cyan]")
        for i, theme in enumerate(themes, 1):
            self.console.print(f"  {i}. {theme.title()}")
        
        # Show theme preview option
        if Confirm.ask("Would you like to preview themes?", default=False):
            from aniplux.cli.config_preview import ConfigurationPreview
            preview = ConfigurationPreview()
            preview.preview_all_themes()
        
        theme_choice = Prompt.ask(
            "Select theme",
            choices=[str(i) for i in range(1, len(themes) + 1)],
            default="1"
        )
        
        selected_theme = themes[int(theme_choice) - 1]
        self.wizard_config["color_theme"] = selected_theme
        
        # Apply theme immediately for preview
        try:
            theme = ThemeName(selected_theme)
            set_theme(theme)
            update_console_theme(theme)
        except:
            pass
        
        # Banner preference
        show_banner = Confirm.ask("Show startup banner?", default=True)
        self.wizard_config["show_banner"] = show_banner
        
        # Progress style
        progress_styles = ["bar", "spinner", "dots"]
        progress_choice = Prompt.ask(
            "Progress indicator style",
            choices=progress_styles,
            default="bar"
        )
        self.wizard_config["progress_style"] = progress_choice
        
        self.console.print(
            f"[green]✅ UI preferences set: {selected_theme} theme, "
            f"banner {'enabled' if show_banner else 'disabled'}[/green]"
        )
        return True
    
    def _step_source_configuration(self) -> bool:
        """Configure source plugins."""
        self.console.print("🔌 Let's configure your anime sources.\n")
        
        # Get available sources
        sources = self.config_manager.sources.sources
        
        if not sources:
            self.console.print("[yellow]⚠️  No source plugins found. You can add them later.[/yellow]")
            return True
        
        self.console.print("[cyan]Available sources:[/cyan]")
        enabled_sources = []
        
        for source_name, source_config in sources.items():
            current_status = "enabled" if source_config.enabled else "disabled"
            self.console.print(f"  • {source_name} ({current_status})")
            
            enable = Confirm.ask(f"Enable {source_name}?", default=True)
            if enable:
                enabled_sources.append(source_name)
        
        self.wizard_config["enabled_sources"] = enabled_sources
        
        self.console.print(
            f"[green]✅ Sources configured: {len(enabled_sources)} enabled[/green]"
        )
        return True
    
    def _step_final_review(self) -> bool:
        """Show final configuration review."""
        self.console.print("📋 Let's review your configuration.\n")
        
        # Create review table
        from rich.table import Table
        
        table = Table(
            title="Configuration Summary",
            show_header=True,
            header_style="bold blue",
            border_style="blue"
        )
        
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", style="white", width=30)
        
        # Add configuration items
        config_items = [
            ("Download Directory", self.wizard_config.get("download_directory", "Not set")),
            ("Default Quality", self.wizard_config.get("default_quality", "Not set")),
            ("Concurrent Downloads", str(self.wizard_config.get("concurrent_downloads", "Not set"))),
            ("Network Timeout", f"{self.wizard_config.get('timeout', 'Not set')}s"),
            ("Max Retries", str(self.wizard_config.get("max_retries", "Not set"))),
            ("Color Theme", self.wizard_config.get("color_theme", "Not set")),
            ("Show Banner", "Yes" if self.wizard_config.get("show_banner", False) else "No"),
            ("Progress Style", self.wizard_config.get("progress_style", "Not set")),
            ("Enabled Sources", str(len(self.wizard_config.get("enabled_sources", [])))),
        ]
        
        for setting, value in config_items:
            table.add_row(setting, str(value))
        
        self.console.print(table)
        
        return Confirm.ask(
            "\n[bold blue]Apply this configuration?[/bold blue]",
            default=True
        )
    
    def _apply_configuration(self) -> None:
        """Apply the wizard configuration to the config manager."""
        self.console.print("\n[bold blue]Applying configuration...[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("Updating settings...", total=None)
            
            try:
                # Update settings
                if "download_directory" in self.wizard_config:
                    self.config_manager.update_setting("settings.download_directory", self.wizard_config["download_directory"])
                
                if "default_quality" in self.wizard_config:
                    self.config_manager.update_setting("settings.default_quality", self.wizard_config["default_quality"])
                
                if "concurrent_downloads" in self.wizard_config:
                    self.config_manager.update_setting("settings.concurrent_downloads", self.wizard_config["concurrent_downloads"])
                
                if "timeout" in self.wizard_config:
                    self.config_manager.update_setting("settings.timeout", self.wizard_config["timeout"])
                
                if "max_retries" in self.wizard_config:
                    self.config_manager.update_setting("settings.max_retries", self.wizard_config["max_retries"])
                
                # Update UI settings
                if "color_theme" in self.wizard_config:
                    self.config_manager.update_setting("ui.color_theme", self.wizard_config["color_theme"])
                
                if "show_banner" in self.wizard_config:
                    self.config_manager.update_setting("ui.show_banner", self.wizard_config["show_banner"])
                
                if "progress_style" in self.wizard_config:
                    self.config_manager.update_setting("ui.progress_style", self.wizard_config["progress_style"])
                
                # Update source configurations
                if "enabled_sources" in self.wizard_config:
                    for source_name in self.config_manager.sources.sources:
                        enabled = source_name in self.wizard_config["enabled_sources"]
                        self.config_manager.update_source_config(source_name, {"enabled": enabled})
                
                progress.update(task, description="Configuration applied!")
                
            except Exception as e:
                progress.update(task, description=f"Error: {e}")
                raise
    
    def _show_completion(self) -> None:
        """Show wizard completion message."""
        completion_text = (
            "[bold green]🎉 Configuration Complete![/bold green]\n\n"
            "AniPlux has been configured successfully! You can now:\n\n"
            "• Search for anime: [cyan]aniplux search \"anime title\"[/cyan]\n"
            "• Browse episodes: [cyan]aniplux episodes[/cyan]\n"
            "• Download content: [cyan]aniplux download[/cyan]\n"
            "• Manage sources: [cyan]aniplux sources[/cyan]\n\n"
            "You can always reconfigure settings with:\n"
            "[cyan]aniplux config edit[/cyan]\n\n"
            "[dim]Happy anime watching! 🍿[/dim]"
        )
        
        panel = Panel(
            completion_text,
            title="✅ Setup Complete",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _confirm_continue(self) -> bool:
        """Ask user if they want to continue after a step failure."""
        return Confirm.ask(
            "[yellow]Step had issues. Continue with wizard?[/yellow]",
            default=True
        )


# Export wizard
__all__ = ["ConfigurationWizard"]