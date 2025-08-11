"""
HiAnime Downloader - Advanced video URL extraction using Selenium

This module provides Selenium-based video URL extraction for hianime.to
when standard HTTP requests fail due to JavaScript protection or encryption.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from urllib.parse import urljoin

from aniplux.core.models import Quality
from aniplux.core.exceptions import PluginError, NetworkError

if TYPE_CHECKING:
    from seleniumwire.webdriver import Chrome


logger = logging.getLogger(__name__)


class HiAnimeSeleniumDownloader:
    """
    Selenium-based downloader for HiAnime episodes.
    
    This class handles JavaScript-heavy pages and popup blocking
    to extract video URLs that are not accessible via standard HTTP requests.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Selenium downloader.
        
        Args:
            config: Configuration dictionary with browser settings
        """
        self.config = config or {}
        self.driver: Optional["Chrome"] = None
        self.base_url = "https://hianime.to"
        
        # Default configuration
        self.default_config = {
            "headless": True,
            "timeout": 30,
            "max_attempts": 60,
            "adblock_extension_path": None,
            "mobile_emulation": True,
            "popup_blocking": True
        }
        
        # Merge with provided config
        self.config = {**self.default_config, **self.config}
    
    def setup_driver(self) -> bool:
        """
        Configure and initialize Chrome driver with stealth settings.
        
        Returns:
            True if driver setup successful, False otherwise
        """
        try:
            # Import required modules
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from seleniumwire import webdriver as wire_driver
            
            # Reduce selenium-wire logging noise
            import logging as selenium_logging
            selenium_logging.getLogger('seleniumwire.server').setLevel(selenium_logging.WARNING)
            selenium_logging.getLogger('seleniumwire.handler').setLevel(selenium_logging.WARNING)
            selenium_logging.getLogger('seleniumwire.storage').setLevel(selenium_logging.WARNING)
            selenium_logging.getLogger('seleniumwire.backend').setLevel(selenium_logging.WARNING)
            
            try:
                from selenium_stealth import stealth
                stealth_available = True
                stealth_func = stealth
            except ImportError:
                logger.warning("selenium-stealth not available, using basic stealth settings")
                stealth_available = False
                stealth_func = None
            
            options = Options()
            
            # Basic Chrome options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--log-level=3")
            options.add_argument("--disable-popup-blocking")
            
            # Headless mode
            if self.config.get("headless", True):
                options.add_argument("--headless")
            
            # Mobile emulation for better compatibility
            if self.config.get("mobile_emulation", True):
                mobile_emulation = {"deviceName": "iPhone 12 Pro"}
                options.add_experimental_option("mobileEmulation", mobile_emulation)
            
            # AdBlock extension loading (exact method from debug_hianime.py)
            adblock_path = self.config.get("adblock_extension_path")
            if adblock_path and os.path.exists(adblock_path):
                logger.info(f"Loading AdBlock extension from: {adblock_path}")
                options.add_argument(f"--load-extension={adblock_path}")
                
                # Additional options to ensure extension loading (from debug_hianime.py)
                options.add_argument("--disable-extensions-except=" + adblock_path)
                options.add_argument("--disable-default-apps")
            else:
                if adblock_path:
                    logger.warning(f"AdBlock extension path not found: {adblock_path}")
                    logger.warning("Continuing without AdBlock extension...")
            
            # Preferences to allow extensions and disable welcome pages (from debug_hianime.py)
            options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.popups": 0,
                "extensions.ui.developer_mode": False,
            })
            
            # Additional arguments to prevent extension welcome pages (from debug_hianime.py)
            options.add_argument("--disable-extensions-file-access-check")
            options.add_argument("--disable-extensions-http-throttling")
            options.add_argument("--disable-component-extensions-with-background-pages")
            
            # Selenium Wire options for request interception
            seleniumwire_options = {
                "verify_ssl": False,
                "disable_encoding": True,
                "suppress_connection_errors": True,
            }
            
            # Initialize driver
            self.driver = wire_driver.Chrome(
                options=options,
                seleniumwire_options=seleniumwire_options
            )
            
            # Apply stealth if available
            if stealth_available and stealth_func:
                stealth_func(
                    self.driver,
                    languages=["en-US", "en"],
                    vendor="Apple Computer, Inc.",
                    platform="iPhone",
                    webgl_vendor="Apple Inc.",
                    renderer="Apple GPU",
                    fix_hairline=True,
                )
            
            # Set implicit wait
            timeout = self.config.get("timeout", 30)
            self.driver.implicitly_wait(timeout)
            
            # Handle AdBlock welcome page if extension was loaded (from debug_hianime.py)
            if adblock_path and os.path.exists(adblock_path):
                self._quick_close_adblock_page()
            
            logger.info("Selenium driver initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Required Selenium packages not installed: {e}")
            logger.error("Install with: pip install selenium seleniumwire selenium-stealth")
            return False
        except Exception as e:
            logger.error(f"Failed to setup Selenium driver: {e}")
            return False
    
    def _quick_close_adblock_page(self) -> None:
        """Wait for AdBlock welcome page to load and then close it (exact method from debug_hianime.py)."""
        if not self.driver:
            return
            
        try:
            # Wait 7 seconds for AdBlock welcome page to fully load
            logger.info("Waiting 7 seconds for AdBlock welcome page to load...")
            time.sleep(7)
            
            all_windows = self.driver.window_handles
            
            if len(all_windows) > 1:
                logger.info(f"Found {len(all_windows)} tabs, closing AdBlock welcome page...")
                
                # Keep track of the first tab (usually the main one)
                main_window = all_windows[0]
                
                # Close all additional tabs (likely AdBlock welcome pages)
                for window in all_windows[1:]:
                    try:
                        self.driver.switch_to.window(window)
                        current_url = self.driver.current_url
                        logger.info(f"Closing tab: {current_url}")
                        self.driver.close()
                    except:
                        pass
                
                # Switch back to main window
                try:
                    self.driver.switch_to.window(main_window)
                except:
                    # If main window was closed, switch to any remaining window
                    remaining_windows = self.driver.window_handles
                    if remaining_windows:
                        self.driver.switch_to.window(remaining_windows[0])
                
                logger.info("AdBlock welcome page closed successfully!")
            else:
                logger.info("No additional tabs to close")
                
        except Exception as e:
            logger.error(f"Error closing AdBlock page: {e}")
    
    def _inject_popup_blocker(self) -> None:
        """Inject JavaScript popup blocker into the page (from debug_hianime.py)."""
        if not self.driver:
            return
            
        try:
            popup_blocker_script = """
            // Block popups and redirects
            window.open = function() { return null; };
            
            // Block common popup triggers
            document.addEventListener('click', function(e) {
                if (e.target.tagName === 'A' && e.target.target === '_blank') {
                    e.preventDefault();
                    e.stopPropagation();
                }
            }, true);
            
            // Block overlay ads
            setInterval(function() {
                var overlays = document.querySelectorAll('[style*="position: fixed"], [style*="z-index"]');
                overlays.forEach(function(overlay) {
                    if (overlay.offsetWidth > window.innerWidth * 0.8 || 
                        overlay.offsetHeight > window.innerHeight * 0.8) {
                        overlay.style.display = 'none';
                    }
                });
            }, 1000);
            """
            
            self.driver.execute_script(popup_blocker_script)
            logger.debug("Popup blocker injected successfully")
            
        except Exception as e:
            logger.debug(f"Failed to inject popup blocker: {e}")
    
    def inject_ad_blocker(self) -> None:
        """Inject ad blocker script (from debug_hianime.py)."""
        if not self.driver:
            return
            
        try:
            ad_blocker_script = """
            // Remove ads and overlays
            function removeAds() {
                // Remove common ad selectors
                var adSelectors = [
                    '[id*="ad"]', '[class*="ad"]', '[id*="banner"]', '[class*="banner"]',
                    '[id*="popup"]', '[class*="popup"]', '[id*="overlay"]', '[class*="overlay"]',
                    'iframe[src*="ads"]', 'iframe[src*="doubleclick"]'
                ];
                
                adSelectors.forEach(function(selector) {
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {
                        if (el.offsetHeight > 100 || el.offsetWidth > 100) {
                            el.style.display = 'none';
                        }
                    });
                });
            }
            
            // Run immediately and every 2 seconds
            removeAds();
            setInterval(removeAds, 2000);
            """
            
            self.driver.execute_script(ad_blocker_script)
            logger.debug("Ad blocker script injected")
            
        except Exception as e:
            logger.debug(f"Failed to inject ad blocker: {e}")
    
    def _handle_popups_and_tabs(self) -> None:
        """Handle and close any popup windows or unwanted tabs."""
        if not self.driver:
            return
            
        try:
            current_window = self.driver.current_window_handle
            all_windows = self.driver.window_handles
            
            # Close any additional windows/tabs
            for window in all_windows:
                if window != current_window:
                    try:
                        self.driver.switch_to.window(window)
                        self.driver.close()
                    except Exception:
                        pass
            
            # Switch back to main window
            try:
                self.driver.switch_to.window(current_window)
            except Exception:
                # If main window was closed, switch to any remaining window
                remaining_windows = self.driver.window_handles
                if remaining_windows:
                    self.driver.switch_to.window(remaining_windows[0])
            
        except Exception as e:
            logger.debug(f"Error handling popups: {e}")
    
    async def extract_video_info(self, episode_url: str, quality: Quality) -> Optional[Dict[str, Any]]:
        """
        Extract video URL using Selenium (exact method from debug_hianime.py).
        
        Args:
            episode_url: URL to the episode page
            quality: Requested video quality
            
        Returns:
            Dictionary with 'url' and 'headers' or None if extraction fails
            
        Raises:
            PluginError: If extraction fails
        """
        if not self.driver:
            if not self.setup_driver():
                raise PluginError("Failed to initialize Selenium driver")
        
        # Double-check driver is available after setup
        if not self.driver:
            raise PluginError("Selenium driver is not available")
        
        # Type assertion for mypy/pylance - driver is guaranteed to be non-None here
        assert self.driver is not None
        
        try:
            logger.info(f"Loading episode: {episode_url}")
            
            # Clear previous requests
            if hasattr(self.driver, 'requests'):
                self.driver.requests.clear()
            
            # Load episode page
            self.driver.get(episode_url)
            
            # Inject ad blocker (from debug_hianime.py)
            self.inject_ad_blocker()
            
            # Handle popups immediately after page load (from debug_hianime.py)
            time.sleep(2)
            
            # Run popup killer a few times only (from debug_hianime.py)
            for i in range(3):
                self._handle_popups_and_tabs()
                time.sleep(0.5)
            
            # Select server (from debug_hianime.py)
            if not await self._select_server():
                logger.error("Failed to select server")
                return None
            
            # Capture video stream URL (from debug_hianime.py)
            video_info = await self._capture_video_stream()
            
            if video_info:
                return video_info  # Return the full dict with url and headers
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error capturing video URL: {e}")
            return None
    
    async def _select_server(self) -> bool:
        """Select the first available video server (from debug_hianime.py)."""
        if not self.driver:
            return False
            
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            
            logger.info("Looking for servers...")
            
            # Wait for servers to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "servers-content"))
            )
            
            # Find and click first server
            servers = self.driver.find_elements(By.CSS_SELECTOR, "#servers-content a")
            if servers:
                server_name = servers[0].text or "Unknown Server"
                logger.info(f"Selecting server: {server_name}")
                
                self.driver.execute_script("arguments[0].click();", servers[0])
                time.sleep(3)
                # AdBlock handles any popups automatically
                return True
            else:
                logger.warning("No video servers found")
                return False
                
        except Exception as e:
            logger.error(f"Error selecting server: {e}")
            return False
    
    async def _capture_video_stream(self) -> Optional[Dict[str, Any]]:
        """Capture video stream URL from network requests (from debug_hianime.py)."""
        if not self.driver:
            return None
            
        try:
            from selenium.webdriver.common.by import By
            
            # Wait for video player
            logger.info("Waiting for video player...")
            time.sleep(5)
            
            # Try to start video (from debug_hianime.py)
            try:
                play_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, .play-btn, [class*='play']")
                for btn in play_buttons:
                    class_attr = btn.get_attribute("class")
                    if btn.is_displayed() and class_attr and ("play" in class_attr.lower() or "play" in btn.text.lower()):
                        logger.info("Clicking play button...")
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        break
            except:
                pass
            
            # Wait and capture requests (exact method from debug_hianime.py)
            max_attempts = self.config.get("max_attempts", 60)
            logger.info("Monitoring network requests for video stream...")
            
            for attempt in range(max_attempts):
                # Only log every 10 attempts to reduce noise
                if attempt % 10 == 0 and attempt > 0:
                    logger.info(f"Still searching... attempt {attempt + 1}/{max_attempts}")
                
                # Check for .m3u8 files (exact logic from debug_hianime.py)
                if hasattr(self.driver, 'requests'):
                    for request in self.driver.requests:
                        if request.response and request.url.lower().endswith('.m3u8'):
                            if 'master' in request.url.lower() or 'playlist' in request.url.lower():
                                video_url = request.url
                                headers = dict(request.headers)
                                logger.info(f"Found video stream: {video_url[:80]}...")
                                return {"url": video_url, "headers": headers}
                
                time.sleep(1)
            
            logger.warning(f"No video stream found after {max_attempts} attempts")
            return None
            
        except Exception as e:
            logger.error(f"Error capturing video stream: {e}")
            return None
    
    def _is_video_stream_url(self, url: str) -> bool:
        """Check if URL appears to be a video stream."""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Check for video stream indicators
        video_indicators = [
            '.m3u8',           # HLS streams
            '.ts',             # Transport stream segments
            '.mp4',            # MP4 files
            '.mkv',            # MKV files
            '.webm',           # WebM files
            'master.m3u8',     # HLS master playlist
            'playlist.m3u8',   # HLS playlist
            'googlevideo.com', # Google Video CDN
            'googleapis.com',  # Google APIs
            'cloudflare.com',  # Cloudflare CDN
            'amazonaws.com',   # AWS CDN
            'cloudfront.net',  # AWS CloudFront
            'megacloud',       # Megacloud streaming
            'vidstream'        # Vidstream
        ]
        
        return any(indicator in url_lower for indicator in video_indicators)
    
    def cleanup(self) -> None:
        """Clean up Selenium driver resources."""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.debug("Selenium driver cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during Selenium cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class HiAnimeDownloadManager:
    """
    Download manager that combines HTTP and Selenium extraction methods.
    
    This class provides a unified interface for video URL extraction,
    falling back to Selenium when standard HTTP requests fail.
    """
    
    def __init__(self, http_extractor, config: Optional[Dict[str, Any]] = None):
        """
        Initialize download manager.
        
        Args:
            http_extractor: HTTP-based extractor (HiAnimeExtractor)
            config: Configuration for Selenium fallback
        """
        self.http_extractor = http_extractor
        self.selenium_config = config or {}
        self._selenium_downloader = None
        self.last_headers = None  # Store headers from last successful extraction
    
    async def extract_video_url(self, episode_url: str, quality: Quality) -> str:
        """
        Extract video URL using HTTP first, then Selenium fallback.
        
        Args:
            episode_url: URL to the episode page
            quality: Requested video quality
            
        Returns:
            Direct video URL
            
        Raises:
            PluginError: If both extraction methods fail
        """
        # First, try HTTP-based extraction
        try:
            logger.debug("Attempting HTTP-based video extraction...")
            video_url = await self.http_extractor.extract_video_url(episode_url, quality)
            
            if video_url:
                logger.info("HTTP extraction successful")
                return video_url
                
        except Exception as e:
            logger.debug(f"HTTP extraction failed: {e}")
        
        # Fallback to Selenium-based extraction
        try:
            logger.info("Falling back to Selenium-based extraction...")
            
            if not self._selenium_downloader:
                self._selenium_downloader = HiAnimeSeleniumDownloader(self.selenium_config)
            
            video_info = await self._selenium_downloader.extract_video_info(episode_url, quality)
            
            if video_info and video_info.get('url'):
                logger.info("Selenium extraction successful")
                # Store headers for download
                self.last_headers = video_info.get('headers', {})
                return video_info['url']
            else:
                raise PluginError("Selenium extraction returned no URL")
                
        except Exception as e:
            logger.error(f"Selenium extraction failed: {e}")
            
            # Provide helpful error message
            raise PluginError(
                f"Video extraction failed for {episode_url}\n\n"
                "Both HTTP and Selenium extraction methods failed. This could be due to:\n"
                "1. Geographic restrictions or IP blocking\n"
                "2. Changes in the website's video protection\n"
                "3. Missing browser dependencies (Chrome, ChromeDriver)\n"
                "4. Network connectivity issues\n\n"
                "Try using yt-dlp directly:\n"
                f"  yt-dlp \"{episode_url}\""
            )
    
    def get_last_headers(self) -> Dict[str, str]:
        """Get headers from the last successful extraction."""
        return self.last_headers or {}
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self._selenium_downloader:
                self._selenium_downloader.cleanup()
                self._selenium_downloader = None
        except Exception as e:
            logger.error(f"Error during download manager cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Export main classes
__all__ = ["HiAnimeSeleniumDownloader", "HiAnimeDownloadManager"]