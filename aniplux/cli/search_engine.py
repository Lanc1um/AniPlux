"""
Search Engine - Core search functionality and result processing.

This module provides the search engine that coordinates searches across
multiple plugins and handles result processing, filtering, and sorting.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict

from aniplux.core import PluginManager
from aniplux.core.models import AnimeResult
from aniplux.core.exceptions import SearchError, PluginError
from aniplux.ui import search_progress


logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Core search engine for coordinating multi-source anime searches.
    
    Handles plugin management, concurrent searching, result aggregation,
    and post-processing operations like filtering and sorting.
    """
    
    def __init__(self, config_manager: Any):
        """
        Initialize search engine.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.plugin_manager = PluginManager(config_manager)
        
        # Search settings
        self.search_settings = config_manager.settings.search
        self.max_results_per_source = self.search_settings.max_results_per_source
        self.search_timeout = self.search_settings.search_timeout
        self.enable_fuzzy_search = self.search_settings.enable_fuzzy_search
        
        # Search metadata
        self.last_raw_result_count = 0
        self.last_duplicate_count = 0
    
    async def search_anime(
        self,
        query: str,
        source_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[AnimeResult]:
        """
        Search for anime across multiple sources.
        
        Args:
            query: Search query string
            source_filter: Specific source to search (None for all)
            limit: Maximum total results to return
            
        Returns:
            List of anime search results
            
        Raises:
            SearchError: If search fails
        """
        logger.info(f"Starting search for query: '{query}'")
        
        try:
            # Get active plugins
            active_plugins = await self.plugin_manager.get_active_plugins()
            
            if not active_plugins:
                raise SearchError(
                    "No active plugins available for search. Enable sources with 'aniplux sources enable <name>'",
                    query=query
                )
            
            # Filter plugins if source specified
            if source_filter:
                if source_filter not in active_plugins:
                    available_sources = list(active_plugins.keys())
                    raise SearchError(
                        f"Source '{source_filter}' not found or not enabled. "
                        f"Available sources: {', '.join(available_sources)}",
                        query=query,
                        source=source_filter
                    )
                active_plugins = {source_filter: active_plugins[source_filter]}
            
            # Perform concurrent search
            search_results = await self._search_concurrent(query, active_plugins)
            
            # Store raw count for display purposes
            self.last_raw_result_count = len(search_results)
            
            # Remove duplicates and apply limit
            unique_results = self.remove_duplicate_results(search_results)
            self.last_duplicate_count = self.last_raw_result_count - len(unique_results)
            
            if limit:
                unique_results = unique_results[:limit]
            
            if self.last_duplicate_count > 0:
                logger.info(f"Search completed: {len(unique_results)} unique results from {len(active_plugins)} sources ({self.last_duplicate_count} duplicates removed)")
            else:
                logger.info(f"Search completed: {len(unique_results)} unique results from {len(active_plugins)} sources")
            return unique_results
            
        except Exception as e:
            if isinstance(e, SearchError):
                raise
            else:
                raise SearchError(f"Search failed: {str(e)}", query=query, details=str(e))
    
    async def _search_concurrent(
        self,
        query: str,
        plugins: Dict[str, Any]
    ) -> List[AnimeResult]:
        """
        Perform concurrent search across multiple plugins.
        
        Args:
            query: Search query
            plugins: Dictionary of plugin name to plugin instance
            
        Returns:
            Combined list of search results
        """
        source_names = list(plugins.keys())
        
        with search_progress(source_names) as progress_task_id:
            # Create search tasks
            search_tasks = []
            for source_name, plugin in plugins.items():
                task = asyncio.create_task(
                    self._search_single_source(query, source_name, plugin),
                    name=f"search_{source_name}"
                )
                search_tasks.append(task)
            
            # Wait for all searches to complete
            all_results = []
            completed_count = 0
            
            for task in asyncio.as_completed(search_tasks, timeout=self.search_timeout):
                try:
                    source_results = await task
                    all_results.extend(source_results)
                    completed_count += 1
                    
                    # Progress is handled by the search_progress context manager
                    
                except asyncio.TimeoutError:
                    task_name = getattr(task, '_name', 'unknown_task')
                    logger.warning(f"Search timeout for task: {task_name}")
                except Exception as e:
                    task_name = getattr(task, '_name', 'unknown_task')
                    logger.error(f"Search failed for task {task_name}: {e}")
        
        return all_results
    
    async def _search_single_source(
        self,
        query: str,
        source_name: str,
        plugin: Any
    ) -> List[AnimeResult]:
        """
        Search a single source plugin.
        
        Args:
            query: Search query
            source_name: Name of the source
            plugin: Plugin instance
            
        Returns:
            List of search results from this source
        """
        try:
            logger.debug(f"Searching source '{source_name}' for query: '{query}'")
            
            # Perform search with timeout
            results = await asyncio.wait_for(
                plugin.search(query),
                timeout=self.search_timeout
            )
            
            # Limit results per source
            if len(results) > self.max_results_per_source:
                results = results[:self.max_results_per_source]
                logger.debug(f"Limited results from '{source_name}' to {self.max_results_per_source}")
            
            logger.debug(f"Source '{source_name}' returned {len(results)} results")
            return results
            
        except asyncio.TimeoutError:
            logger.warning(f"Search timeout for source '{source_name}'")
            return []
        except Exception as e:
            logger.error(f"Search failed for source '{source_name}': {e}")
            return []
    
    def remove_duplicate_results(self, results: List[AnimeResult]) -> List[AnimeResult]:
        """
        Remove duplicate results based on title similarity.
        
        Args:
            results: List of anime results
            
        Returns:
            List with duplicates removed
        """
        if not results:
            return results
        
        # Group results by normalized title
        title_groups = defaultdict(list)
        
        for result in results:
            # Normalize title for comparison
            normalized_title = self._normalize_title(result.title)
            title_groups[normalized_title].append(result)
            
            # Debug logging to see what's being grouped
            if len(title_groups[normalized_title]) == 1:
                logger.debug(f"Title: '{result.title}' → Normalized: '{normalized_title}'")
            else:
                logger.debug(f"DUPLICATE DETECTED: '{result.title}' → Same normalized title: '{normalized_title}'")
        
        # Select best result from each group
        unique_results = []
        for title, group in title_groups.items():
            if len(group) == 1:
                unique_results.append(group[0])
            else:
                # Select result with highest rating, or first if no ratings
                best_result = max(
                    group,
                    key=lambda r: (r.rating or 0, r.episode_count or 0, len(r.description or ""))
                )
                unique_results.append(best_result)
        
        duplicates_removed = len(results) - len(unique_results)
        if duplicates_removed > 0:
            logger.debug(f"Removed {duplicates_removed} duplicate results (normalized title matching)")
        else:
            logger.debug("No duplicate results found")
        return unique_results
    
    def _normalize_title(self, title: str) -> str:
        """
        Normalize title for duplicate detection.
        
        Args:
            title: Original title
            
        Returns:
            Normalized title
        """
        import re
        
        # Convert to lowercase
        normalized = title.lower()
        
        # Remove common punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common words that don't affect uniqueness
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words]
        
        return ' '.join(filtered_words)
    
    def filter_and_sort_results(
        self,
        results: List[AnimeResult],
        sort_by: str = "relevance",
        min_rating: Optional[float] = None,
        year: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[AnimeResult]:
        """
        Filter and sort search results.
        
        Args:
            results: List of anime results
            sort_by: Sort criteria (relevance, rating, year, episodes)
            min_rating: Minimum rating filter
            year: Year filter
            limit: Maximum results to return
            
        Returns:
            Filtered and sorted results
        """
        filtered_results = results.copy()
        
        # Apply filters
        if min_rating is not None:
            filtered_results = [
                r for r in filtered_results
                if r.rating is not None and r.rating >= min_rating
            ]
        
        if year is not None:
            filtered_results = [
                r for r in filtered_results
                if r.year is not None and r.year == year
            ]
        
        # Sort results
        sorted_results = self.sort_results(filtered_results, sort_by)
        
        # Apply limit
        if limit:
            sorted_results = sorted_results[:limit]
        
        return sorted_results
    
    def sort_results(self, results: List[AnimeResult], sort_by: str) -> List[AnimeResult]:
        """
        Sort anime results by specified criteria.
        
        Args:
            results: List of anime results
            sort_by: Sort criteria
            
        Returns:
            Sorted results
        """
        if not results:
            return results
        
        if sort_by.lower() == "rating":
            return sorted(results, key=lambda r: r.rating or 0, reverse=True)
        elif sort_by.lower() == "year":
            return sorted(results, key=lambda r: r.year or 0, reverse=True)
        elif sort_by.lower() == "episodes":
            return sorted(results, key=lambda r: r.episode_count or 0, reverse=True)
        elif sort_by.lower() == "title":
            return sorted(results, key=lambda r: r.title.lower())
        else:  # relevance (default)
            # Sort by a combination of factors for relevance
            return sorted(
                results,
                key=lambda r: (
                    r.rating or 0,  # Higher rating = more relevant
                    len(r.description or ""),  # More description = more relevant
                    r.episode_count or 0  # More episodes = more relevant
                ),
                reverse=True
            )
    
    async def cleanup(self) -> None:
        """Clean up search engine resources."""
        if hasattr(self, 'plugin_manager'):
            await self.plugin_manager.cleanup()


# Export search engine
__all__ = ["SearchEngine"]