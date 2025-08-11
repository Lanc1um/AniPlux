"""
Plugin Manager - Dynamic plugin discovery and management system.

This module handles the discovery, loading, and management of anime source plugins,
providing a unified interface for plugin operations with error handling and graceful degradation.
"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Set
from concurrent.futures import ThreadPoolExecutor

from aniplux.core.config_manager import ConfigManager
from aniplux.core.models import AnimeResult, Episode, Quality
from aniplux.core.exceptions import PluginError, ConfigurationError
from aniplux.plugins.base import BasePlugin


logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages anime source plugins with dynamic discovery and loading.
    
    Provides centralized plugin management including discovery, loading,
    configuration, and coordinated operations across multiple plugins.
    """
    
    def __init__(self, config_manager: ConfigManager, plugins_dir: Optional[Path] = None):
        """
        Initialize plugin manager.
        
        Args:
            config_manager: Configuration manager instance
            plugins_dir: Directory containing plugin modules (defaults to ./aniplux/plugins)
        """
        self.config_manager = config_manager
        self.plugins_dir = plugins_dir or Path(__file__).parent.parent / "plugins"
        
        # Plugin storage
        self._available_plugins: Dict[str, Type[BasePlugin]] = {}
        self._loaded_plugins: Dict[str, BasePlugin] = {}
        self._plugin_errors: Dict[str, Exception] = {}
        
        # Thread pool for CPU-bound operations
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="plugin-")
        
        # Discovery state
        self._discovery_complete = False
    
    async def discover_plugins(self) -> None:
        """
        Discover available plugins in the plugins directory.
        
        Scans the plugins directory for Python modules containing BasePlugin
        subclasses and registers them for loading.
        """
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory does not exist: {self.plugins_dir}")
            return
        
        logger.info(f"Discovering plugins in {self.plugins_dir}")
        
        # Clear previous discovery results
        self._available_plugins.clear()
        self._plugin_errors.clear()
        
        # Scan for plugin modules
        plugin_files = list(self.plugins_dir.glob("*.py"))
        plugin_files = [f for f in plugin_files if f.name not in ["__init__.py", "base.py"]]
        
        discovered_count = 0
        
        for plugin_file in plugin_files:
            try:
                await self._discover_plugin_module(plugin_file)
                discovered_count += 1
            except Exception as e:
                plugin_name = plugin_file.stem
                self._plugin_errors[plugin_name] = e
                logger.error(f"Failed to discover plugin {plugin_name}: {e}")
        
        self._discovery_complete = True
        logger.info(f"Plugin discovery complete: {discovered_count} plugins found")
    
    async def _discover_plugin_module(self, plugin_file: Path) -> None:
        """
        Discover plugins in a specific module file.
        
        Args:
            plugin_file: Path to the plugin module file
        """
        module_name = f"aniplux.plugins.{plugin_file.stem}"
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                raise PluginError(f"Could not load module spec for {plugin_file}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find BasePlugin subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BasePlugin) and 
                    obj is not BasePlugin and 
                    not inspect.isabstract(obj)):
                    
                    plugin_name = plugin_file.stem
                    self._available_plugins[plugin_name] = obj
                    logger.debug(f"Discovered plugin: {plugin_name} ({obj.__name__})")
                    break
            else:
                logger.warning(f"No valid plugin class found in {plugin_file}")
                
        except Exception as e:
            raise PluginError(f"Failed to import plugin module {plugin_file}: {e}")
    
    async def load_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Load a specific plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            Loaded plugin instance or None if loading failed
        """
        if plugin_name in self._loaded_plugins:
            return self._loaded_plugins[plugin_name]
        
        if plugin_name not in self._available_plugins:
            if not self._discovery_complete:
                await self.discover_plugins()
            
            if plugin_name not in self._available_plugins:
                logger.error(f"Plugin not found: {plugin_name}")
                return None
        
        try:
            # Get plugin configuration
            sources_config = self.config_manager.sources
            plugin_config = sources_config.get_source(plugin_name)
            
            if plugin_config is None:
                logger.warning(f"No configuration found for plugin {plugin_name}")
                config_dict = {}
            else:
                config_dict = plugin_config.config
            
            # Instantiate the plugin
            plugin_class = self._available_plugins[plugin_name]
            plugin_instance = plugin_class(config=config_dict)
            
            # Validate the plugin
            if not await plugin_instance.validate_connection():
                logger.warning(f"Plugin {plugin_name} failed connection validation")
            
            self._loaded_plugins[plugin_name] = plugin_instance
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            
            return plugin_instance
            
        except Exception as e:
            self._plugin_errors[plugin_name] = e
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return None
    
    async def get_active_plugins(self) -> Dict[str, BasePlugin]:
        """
        Get all currently active (enabled and loaded) plugins.
        
        Returns:
            Dictionary of plugin name to plugin instance
        """
        if not self._discovery_complete:
            await self.discover_plugins()
        
        enabled_sources = self.config_manager.sources.get_enabled_sources()
        active_plugins = {}
        
        for plugin_name in enabled_sources.keys():
            plugin = await self.load_plugin(plugin_name)
            if plugin is not None:
                active_plugins[plugin_name] = plugin
        
        return active_plugins
    
    async def search_all(
        self, 
        query: str, 
        max_concurrent: Optional[int] = None
    ) -> Dict[str, List[AnimeResult]]:
        """
        Search across all active plugins concurrently.
        
        Args:
            query: Search query string
            max_concurrent: Maximum number of concurrent plugin searches
            
        Returns:
            Dictionary mapping plugin names to their search results
        """
        active_plugins = await self.get_active_plugins()
        
        if not active_plugins:
            logger.warning("No active plugins available for search")
            return {}
        
        # Limit concurrency if specified
        if max_concurrent is None:
            max_concurrent = self.config_manager.sources.global_config.max_concurrent_plugins
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def search_plugin(name: str, plugin: BasePlugin) -> tuple[str, List[AnimeResult]]:
            """Search a single plugin with error handling."""
            async with semaphore:
                try:
                    logger.debug(f"Searching plugin {name} for: {query}")
                    results = await plugin.search(query)
                    logger.debug(f"Plugin {name} returned {len(results)} results")
                    return name, results
                except Exception as e:
                    logger.error(f"Search failed for plugin {name}: {e}")
                    self._plugin_errors[name] = e
                    return name, []
        
        # Execute searches concurrently
        search_tasks = [
            search_plugin(name, plugin) 
            for name, plugin in active_plugins.items()
        ]
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        search_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Search task failed: {result}")
                continue
            
            # At this point, result is guaranteed to be a tuple, not an exception
            if isinstance(result, tuple) and len(result) == 2:
                plugin_name, plugin_results = result
                search_results[plugin_name] = plugin_results
            else:
                logger.error(f"Unexpected result format: {result}")
        
        total_results = sum(len(results) for results in search_results.values())
        logger.info(f"Search complete: {total_results} total results from {len(search_results)} plugins")
        
        return search_results
    
    async def get_plugin_episodes(
        self, 
        plugin_name: str, 
        anime_url: str
    ) -> List[Episode]:
        """
        Get episodes from a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            anime_url: URL to the anime page
            
        Returns:
            List of episodes
            
        Raises:
            PluginError: If plugin is not available or episodes cannot be fetched
        """
        plugin = await self.load_plugin(plugin_name)
        if plugin is None:
            raise PluginError(f"Plugin {plugin_name} is not available")
        
        try:
            episodes = await plugin.get_episodes(anime_url)
            logger.debug(f"Plugin {plugin_name} returned {len(episodes)} episodes")
            return episodes
        except Exception as e:
            self._plugin_errors[plugin_name] = e
            raise PluginError(f"Failed to get episodes from {plugin_name}: {e}")
    
    async def get_download_url(
        self, 
        plugin_name: str, 
        episode_url: str, 
        quality: Quality
    ) -> str:
        """
        Get download URL from a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            episode_url: URL to the episode page
            quality: Requested video quality
            
        Returns:
            Direct download URL
            
        Raises:
            PluginError: If plugin is not available or URL cannot be extracted
        """
        plugin = await self.load_plugin(plugin_name)
        if plugin is None:
            raise PluginError(f"Plugin {plugin_name} is not available")
        
        try:
            download_url = await plugin.get_download_url(episode_url, quality)
            logger.debug(f"Plugin {plugin_name} provided download URL for {quality}")
            return download_url
        except Exception as e:
            self._plugin_errors[plugin_name] = e
            raise PluginError(f"Failed to get download URL from {plugin_name}: {e}")
    
    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all plugins.
        
        Returns:
            Dictionary containing plugin status information
        """
        status = {
            "discovered": len(self._available_plugins),
            "loaded": len(self._loaded_plugins),
            "errors": len(self._plugin_errors),
            "plugins": {}
        }
        
        # Add information for each discovered plugin
        for name, plugin_class in self._available_plugins.items():
            plugin_info = {
                "class": plugin_class.__name__,
                "loaded": name in self._loaded_plugins,
                "enabled": False,
                "error": None
            }
            
            # Check if plugin is enabled
            source_config = self.config_manager.sources.get_source(name)
            if source_config:
                plugin_info["enabled"] = source_config.enabled
            
            # Add error information if any
            if name in self._plugin_errors:
                plugin_info["error"] = str(self._plugin_errors[name])
            
            # Add metadata if plugin is loaded
            if name in self._loaded_plugins:
                plugin = self._loaded_plugins[name]
                plugin_info["metadata"] = plugin.metadata.model_dump()
            
            status["plugins"][name] = plugin_info
        
        return status
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to reload
            
        Returns:
            True if reload was successful, False otherwise
        """
        # Clean up existing plugin
        if plugin_name in self._loaded_plugins:
            await self._loaded_plugins[plugin_name].cleanup()
            del self._loaded_plugins[plugin_name]
        
        # Clear any previous errors
        self._plugin_errors.pop(plugin_name, None)
        
        # Reload the plugin
        plugin = await self.load_plugin(plugin_name)
        return plugin is not None
    
    async def cleanup_all_plugins(self) -> None:
        """Clean up all loaded plugins without shutting down the manager."""
        logger.debug("Cleaning up all loaded plugins")
        
        # Clean up all loaded plugins
        cleanup_tasks = [
            plugin.cleanup() 
            for plugin in self._loaded_plugins.values()
        ]
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clear loaded plugins but keep available plugins for future use
        self._loaded_plugins.clear()
        
        logger.debug("All plugins cleaned up")
    
    async def cleanup(self) -> None:
        """Clean up all loaded plugins and resources."""
        logger.info("Cleaning up plugin manager")
        
        # Clean up all loaded plugins
        cleanup_tasks = [
            plugin.cleanup() 
            for plugin in self._loaded_plugins.values()
        ]
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clear plugin storage
        self._loaded_plugins.clear()
        self._available_plugins.clear()
        self._plugin_errors.clear()
        
        # Shutdown thread pool
        self._executor.shutdown(wait=True)
        
        logger.info("Plugin manager cleanup complete")


# Export plugin manager
__all__ = ["PluginManager"]