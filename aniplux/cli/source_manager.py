"""
Source Manager - High-level source plugin management and operations.

This module provides the source manager that coordinates plugin operations
with the UI system, configuration management, and user interaction.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from aniplux.core import PluginManager, ConfigManager
from aniplux.core.config_schemas import SourceConfig
from aniplux.core.exceptions import PluginError, ConfigurationError
from aniplux.plugins.base import BasePlugin
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    handle_error,
    status_spinner,
    format_success,
    format_warning,
    format_error,
)


logger = logging.getLogger(__name__)


class SourceManager:
    """
    High-level source plugin manager with UI integration.
    
    Coordinates plugin management operations with user feedback,
    configuration updates, and plugin testing capabilities.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize source manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.console = get_console()
        self.ui = UIComponents()
        
        # Initialize plugin manager
        self.plugin_manager = PluginManager(config_manager)
        
        # Cache for plugin status
        self._plugin_status_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 30  # seconds
    
    async def list_sources(
        self,
        enabled_only: bool = False,
        show_details: bool = False
    ) -> None:
        """
        List available source plugins with status information.
        
        Args:
            enabled_only: Show only enabled sources
            show_details: Show detailed plugin information
        """
        try:
            # Discover plugins
            with status_spinner("Discovering source plugins..."):
                await self.plugin_manager.discover_plugins()
            
            # Get plugin status
            plugin_status = self.plugin_manager.get_plugin_status()
            
            if not plugin_status["plugins"]:
                display_warning(
                    "No source plugins found.\n\n"
                    "Make sure plugins are installed in the plugins directory:\n"
                    "• Check if the plugins directory exists\n"
                    "• Verify plugin files are properly formatted\n"
                    "• Ensure plugins inherit from BasePlugin",
                    "🔌 No Plugins Found"
                )
                return
            
            # Filter plugins if needed
            plugins_to_show = plugin_status["plugins"]
            if enabled_only:
                plugins_to_show = {
                    name: info for name, info in plugins_to_show.items()
                    if info.get("enabled", False)
                }
            
            if not plugins_to_show:
                display_warning(
                    "No enabled source plugins found.\n\n"
                    "Enable sources with: aniplux sources enable <name>",
                    "🔌 No Enabled Sources"
                )
                return
            
            # Display plugin list
            if show_details:
                self._display_detailed_sources(plugins_to_show)
            else:
                self._display_sources_table(plugins_to_show)
            
            # Display summary
            self._display_sources_summary(plugin_status, enabled_only)
            
        except Exception as e:
            handle_error(e, "Failed to list source plugins")
    
    def _display_sources_table(self, plugins: Dict[str, Dict[str, Any]]) -> None:
        """Display sources in a formatted table."""
        # Create sources table
        headers = ["Name", "Status", "Priority", "Version", "Description"]
        rows = []
        
        # Sort plugins by priority (enabled first, then by priority number)
        sorted_plugins = sorted(
            plugins.items(),
            key=lambda x: (not x[1].get("enabled", False), x[1].get("priority", 999))
        )
        
        for name, info in sorted_plugins:
            # Status with emoji
            if info.get("error"):
                status = "[red]❌ Error[/red]"
            elif info.get("enabled", False):
                status = "[green]✅ Enabled[/green]"
            else:
                status = "[dim]⭕ Disabled[/dim]"
            
            # Get metadata if available
            metadata = info.get("metadata", {})
            version = metadata.get("version", "Unknown")
            description = metadata.get("description", "No description")
            
            # Get priority from configuration
            source_config = self.config_manager.sources.get_source(name)
            priority = source_config.priority if source_config else 999
            
            # Truncate long descriptions
            if len(description) > 40:
                description = description[:37] + "..."
            
            rows.append([
                name,
                status,
                str(priority),
                version,
                description
            ])
        
        # Create and display table
        sources_table = self.ui.create_data_table(
            headers=headers,
            rows=rows,
            title="🔌 Source Plugins"
        )
        
        self.console.print(sources_table)
    
    def _display_detailed_sources(self, plugins: Dict[str, Dict[str, Any]]) -> None:
        """Display detailed source information."""
        for name, info in plugins.items():
            self._display_source_details(name, info)
            self.console.print()
    
    def _display_source_details(self, name: str, info: Dict[str, Any]) -> None:
        """Display detailed information for a single source."""
        details = []
        
        # Plugin name and status
        if info.get("error"):
            status_text = f"[red]❌ Error: {info['error']}[/red]"
        elif info.get("enabled", False):
            status_text = "[green]✅ Enabled[/green]"
        else:
            status_text = "[dim]⭕ Disabled[/dim]"
        
        details.append(f"[bold blue]{name}[/bold blue] - {status_text}")
        
        # Metadata information
        metadata = info.get("metadata", {})
        if metadata:
            details.append("")
            details.append(f"[dim]Version:[/dim] {metadata.get('version', 'Unknown')}")
            details.append(f"[dim]Author:[/dim] {metadata.get('author', 'Unknown')}")
            
            if metadata.get("description"):
                details.append(f"[dim]Description:[/dim] {metadata['description']}")
            
            if metadata.get("website"):
                details.append(f"[dim]Website:[/dim] [blue]{metadata['website']}[/blue]")
            
            # Supported qualities
            if metadata.get("supported_qualities"):
                qualities = ", ".join([q.value for q in metadata["supported_qualities"]])
                details.append(f"[dim]Supported Qualities:[/dim] {qualities}")
            
            # Rate limit
            if metadata.get("rate_limit"):
                details.append(f"[dim]Rate Limit:[/dim] {metadata['rate_limit']}s")
        
        # Configuration information
        source_config = self.config_manager.sources.get_source(name)
        if source_config:
            details.append("")
            details.append(f"[dim]Priority:[/dim] {source_config.priority}")
            
            if source_config.config:
                details.append(f"[dim]Configuration:[/dim] {len(source_config.config)} settings")
        
        # Create and display panel
        content = "\n".join(details)
        panel = self.ui.create_info_panel(content, title=f"🔌 {name}")
        
        self.console.print(panel)
    
    def _display_sources_summary(
        self,
        plugin_status: Dict[str, Any],
        enabled_only: bool
    ) -> None:
        """Display sources summary statistics."""
        total = plugin_status["discovered"]
        loaded = plugin_status["loaded"]
        errors = plugin_status["errors"]
        
        enabled_count = sum(
            1 for info in plugin_status["plugins"].values()
            if info.get("enabled", False)
        )
        
        summary_parts = []
        
        if not enabled_only:
            summary_parts.append(f"Total: {total}")
            summary_parts.append(f"Loaded: {loaded}")
        
        summary_parts.append(f"Enabled: {enabled_count}")
        
        if errors > 0:
            summary_parts.append(f"[red]Errors: {errors}[/red]")
        
        summary_text = " • ".join(summary_parts)
        
        self.console.print()
        self.console.print(f"[dim]{summary_text}[/dim]")
    
    async def enable_source(self, source_name: str) -> bool:
        """
        Enable a source plugin.
        
        Args:
            source_name: Name of the source to enable
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if source exists
            await self.plugin_manager.discover_plugins()
            plugin_status = self.plugin_manager.get_plugin_status()
            
            if source_name not in plugin_status["plugins"]:
                available_sources = list(plugin_status["plugins"].keys())
                display_warning(
                    f"Source '{source_name}' not found.\n\n"
                    f"Available sources: {', '.join(available_sources) if available_sources else 'None'}",
                    "🔌 Source Not Found"
                )
                return False
            
            # Enable the source
            self.config_manager.enable_source(source_name)
            
            # Test the source
            with status_spinner(f"Testing {source_name}..."):
                test_result = await self._test_single_source(source_name)
            
            if test_result["success"]:
                display_info(
                    f"Source '{source_name}' enabled successfully!\n\n"
                    f"Connection test: [green]✅ Passed[/green]\n"
                    f"Response time: {test_result.get('response_time', 0):.2f}s",
                    "✅ Source Enabled"
                )
            else:
                display_warning(
                    f"Source '{source_name}' enabled but connection test failed.\n\n"
                    f"Error: {test_result.get('error', 'Unknown error')}\n\n"
                    "The source may still work for searches and downloads.",
                    "⚠️  Source Enabled (Test Failed)"
                )
            
            return True
            
        except ConfigurationError as e:
            handle_error(e, f"Failed to enable source '{source_name}'")
            return False
        except Exception as e:
            handle_error(e, f"Unexpected error enabling source '{source_name}'")
            return False
    
    async def disable_source(self, source_name: str) -> bool:
        """
        Disable a source plugin.
        
        Args:
            source_name: Name of the source to disable
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if source exists and is enabled
            source_config = self.config_manager.sources.get_source(source_name)
            
            if not source_config:
                display_warning(
                    f"Source '{source_name}' not found in configuration.",
                    "🔌 Source Not Found"
                )
                return False
            
            if not source_config.enabled:
                display_info(
                    f"Source '{source_name}' is already disabled.",
                    "ℹ️  Already Disabled"
                )
                return True
            
            # Disable the source
            self.config_manager.disable_source(source_name)
            
            display_info(
                f"Source '{source_name}' disabled successfully.\n\n"
                "The source will no longer be used for searches and downloads.",
                "❌ Source Disabled"
            )
            
            return True
            
        except ConfigurationError as e:
            handle_error(e, f"Failed to disable source '{source_name}'")
            return False
        except Exception as e:
            handle_error(e, f"Unexpected error disabling source '{source_name}'")
            return False
    
    async def test_sources(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Test source plugin connectivity.
        
        Args:
            source_name: Specific source to test (None for all enabled sources)
            
        Returns:
            Dictionary with test results
        """
        try:
            if source_name:
                # Test single source
                with status_spinner(f"Testing {source_name}..."):
                    result = await self._test_single_source(source_name)
                
                self._display_single_test_result(source_name, result)
                return {source_name: result}
            else:
                # Test all enabled sources
                enabled_sources = self.config_manager.get_enabled_sources()
                
                if not enabled_sources:
                    display_warning(
                        "No enabled sources to test.\n\n"
                        "Enable sources with: aniplux sources enable <name>",
                        "🔌 No Enabled Sources"
                    )
                    return {}
                
                with status_spinner("Testing enabled sources..."):
                    results = await self._test_multiple_sources(list(enabled_sources.keys()))
                
                self._display_test_results(results)
                return results
                
        except Exception as e:
            handle_error(e, "Failed to test source connectivity")
            return {}
    
    async def _test_single_source(self, source_name: str) -> Dict[str, Any]:
        """Test a single source plugin."""
        start_time = datetime.now()
        
        try:
            # Load the plugin
            plugin = await self.plugin_manager.load_plugin(source_name)
            
            if not plugin:
                return {
                    "success": False,
                    "error": "Failed to load plugin",
                    "response_time": 0
                }
            
            # Test connection
            connection_ok = await plugin.validate_connection()
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            if connection_ok:
                return {
                    "success": True,
                    "response_time": response_time,
                    "plugin_info": {
                        "name": plugin.metadata.name,
                        "version": plugin.metadata.version,
                        "base_url": plugin.base_url
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Connection validation failed",
                    "response_time": response_time
                }
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            return {
                "success": False,
                "error": str(e),
                "response_time": response_time
            }
    
    async def _test_multiple_sources(self, source_names: List[str]) -> Dict[str, Any]:
        """Test multiple sources concurrently."""
        # Create test tasks
        test_tasks = [
            self._test_single_source(name) for name in source_names
        ]
        
        # Execute tests concurrently
        results = await asyncio.gather(*test_tasks, return_exceptions=True)
        
        # Process results
        test_results = {}
        for i, result in enumerate(results):
            source_name = source_names[i]
            
            if isinstance(result, Exception):
                test_results[source_name] = {
                    "success": False,
                    "error": str(result),
                    "response_time": 0
                }
            else:
                test_results[source_name] = result
        
        return test_results
    
    def _display_single_test_result(self, source_name: str, result: Dict[str, Any]) -> None:
        """Display test result for a single source."""
        if result["success"]:
            plugin_info = result.get("plugin_info", {})
            
            success_text = f"""
[green]✅ Connection test passed![/green]

[bold]Source:[/bold] {source_name}
[bold]Plugin Name:[/bold] {plugin_info.get('name', 'Unknown')}
[bold]Version:[/bold] {plugin_info.get('version', 'Unknown')}
[bold]Base URL:[/bold] {plugin_info.get('base_url', 'Unknown')}
[bold]Response Time:[/bold] {result['response_time']:.2f}s

[dim]The source is ready for searches and downloads.[/dim]
"""
            
            panel = self.ui.create_success_panel(
                success_text.strip(),
                title="🧪 Connection Test"
            )
        else:
            error_text = f"""
[red]❌ Connection test failed[/red]

[bold]Source:[/bold] {source_name}
[bold]Error:[/bold] {result.get('error', 'Unknown error')}
[bold]Response Time:[/bold] {result['response_time']:.2f}s

[yellow]💡 Troubleshooting:[/yellow]
• Check your internet connection
• Verify the source website is accessible
• Check if the plugin needs updates
• Try testing again in a few moments
"""
            
            panel = self.ui.create_error_panel(
                error_text.strip(),
                title="🧪 Connection Test"
            )
        
        self.console.print()
        self.console.print(panel)
    
    def _display_test_results(self, results: Dict[str, Any]) -> None:
        """Display test results for multiple sources."""
        if not results:
            return
        
        # Create results table
        headers = ["Source", "Status", "Response Time", "Error"]
        rows = []
        
        successful_tests = 0
        total_tests = len(results)
        
        for source_name, result in results.items():
            if result["success"]:
                status = "[green]✅ Pass[/green]"
                error = ""
                successful_tests += 1
            else:
                status = "[red]❌ Fail[/red]"
                error = result.get("error", "Unknown error")
                if len(error) > 30:
                    error = error[:27] + "..."
            
            response_time = f"{result['response_time']:.2f}s"
            
            rows.append([source_name, status, response_time, error])
        
        # Create and display table
        results_table = self.ui.create_data_table(
            headers=headers,
            rows=rows,
            title="🧪 Source Connectivity Tests"
        )
        
        self.console.print()
        self.console.print(results_table)
        
        # Display summary
        if successful_tests == total_tests:
            summary_text = f"[green]All {total_tests} sources passed connectivity tests![/green]"
            panel = self.ui.create_success_panel(summary_text, "🎉 All Tests Passed")
        elif successful_tests == 0:
            summary_text = f"[red]All {total_tests} sources failed connectivity tests.[/red]\n\nCheck your internet connection and try again."
            panel = self.ui.create_error_panel(summary_text, "❌ All Tests Failed")
        else:
            summary_text = f"[yellow]{successful_tests}/{total_tests} sources passed connectivity tests.[/yellow]\n\nSome sources may have connectivity issues."
            panel = self.ui.create_warning_panel(summary_text, "⚠️  Mixed Results")
        
        self.console.print()
        self.console.print(panel)
    
    async def reload_sources(self) -> bool:
        """
        Reload all source plugins.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with status_spinner("Reloading source plugins..."):
                # Clear plugin manager cache
                await self.plugin_manager.cleanup()
                
                # Reinitialize plugin manager
                self.plugin_manager = PluginManager(self.config_manager)
                
                # Discover plugins again
                await self.plugin_manager.discover_plugins()
            
            # Get updated status
            plugin_status = self.plugin_manager.get_plugin_status()
            
            display_info(
                f"Source plugins reloaded successfully!\n\n"
                f"Discovered: {plugin_status['discovered']} plugins\n"
                f"Loaded: {plugin_status['loaded']} plugins\n"
                f"Errors: {plugin_status['errors']} plugins",
                "🔄 Sources Reloaded"
            )
            
            return True
            
        except Exception as e:
            handle_error(e, "Failed to reload source plugins")
            return False
    
    async def show_source_info(self, source_name: str) -> bool:
        """
        Show detailed information about a specific source.
        
        Args:
            source_name: Name of the source to show info for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Discover plugins
            await self.plugin_manager.discover_plugins()
            plugin_status = self.plugin_manager.get_plugin_status()
            
            if source_name not in plugin_status["plugins"]:
                available_sources = list(plugin_status["plugins"].keys())
                display_warning(
                    f"Source '{source_name}' not found.\n\n"
                    f"Available sources: {', '.join(available_sources) if available_sources else 'None'}",
                    "🔌 Source Not Found"
                )
                return False
            
            # Display detailed information
            plugin_info = plugin_status["plugins"][source_name]
            self._display_source_details(source_name, plugin_info)
            
            return True
            
        except Exception as e:
            handle_error(e, f"Failed to get information for source '{source_name}'")
            return False
    
    async def cleanup(self) -> None:
        """Clean up source manager resources."""
        await self.plugin_manager.cleanup()
        self._plugin_status_cache.clear()
        logger.info("Source manager cleanup complete")


# Export source manager
__all__ = ["SourceManager"]