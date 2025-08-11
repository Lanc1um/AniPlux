"""
HiAnime Selenium Configuration Helper

This module provides utilities for configuring Selenium-based video extraction
for the HiAnime plugin, including browser setup and extension management.
"""

import os
import platform
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path


logger = logging.getLogger(__name__)


class SeleniumConfigHelper:
    """Helper class for Selenium configuration management."""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        Get default Selenium configuration based on system.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "headless": True,
            "timeout": 30,
            "max_attempts": 60,
            "adblock_extension_path": None,
            "mobile_emulation": True,
            "popup_blocking": True,
            "user_data_dir": None,
            "window_size": "1920,1080",
            "disable_images": False,
            "disable_javascript": False
        }
    
    @staticmethod
    def detect_chrome_driver() -> Optional[str]:
        """
        Detect ChromeDriver installation.
        
        Returns:
            Path to ChromeDriver or None if not found
        """
        try:
            import shutil
            
            # Check if chromedriver is in PATH
            chromedriver_path = shutil.which("chromedriver")
            if chromedriver_path:
                logger.debug(f"Found ChromeDriver in PATH: {chromedriver_path}")
                return chromedriver_path
            
            # Check common installation paths
            system = platform.system().lower()
            common_paths = []
            
            if system == "windows":
                common_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe",
                    r"C:\chromedriver\chromedriver.exe",
                    os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chromedriver.exe")
                ]
            elif system == "darwin":  # macOS
                common_paths = [
                    "/usr/local/bin/chromedriver",
                    "/opt/homebrew/bin/chromedriver",
                    "/Applications/Google Chrome.app/Contents/MacOS/chromedriver"
                ]
            else:  # Linux
                common_paths = [
                    "/usr/bin/chromedriver",
                    "/usr/local/bin/chromedriver",
                    "/opt/google/chrome/chromedriver"
                ]
            
            for path in common_paths:
                if os.path.isfile(path):
                    logger.debug(f"Found ChromeDriver at: {path}")
                    return path
            
            logger.warning("ChromeDriver not found. Install it from: https://chromedriver.chromium.org/")
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting ChromeDriver: {e}")
            return None
    
    @staticmethod
    def find_adblock_extensions() -> List[Dict[str, str]]:
        """
        Find AdBlock extensions in common locations.
        
        Returns:
            List of found extensions with name and path
        """
        extensions = []
        
        try:
            system = platform.system().lower()
            
            # Common Chrome extension paths
            if system == "windows":
                base_paths = [
                    os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/Extensions"),
                    os.path.expanduser("~/AppData/Roaming/Google/Chrome/User Data/Default/Extensions")
                ]
            elif system == "darwin":  # macOS
                base_paths = [
                    os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Extensions")
                ]
            else:  # Linux
                base_paths = [
                    os.path.expanduser("~/.config/google-chrome/Default/Extensions"),
                    os.path.expanduser("~/.config/chromium/Default/Extensions")
                ]
            
            # Known AdBlock extension IDs
            adblock_ids = {
                "gighmmpiobklfepjocnamgkkbiglidom": "AdBlock",
                "cfhdojbkjhnklbpkdaibdccddilifddb": "AdBlock Plus",
                "cjpalhdlnbpafiamejdnhcphjbkeiagm": "uBlock Origin"
            }
            
            for base_path in base_paths:
                if not os.path.exists(base_path):
                    continue
                
                for ext_id, ext_name in adblock_ids.items():
                    ext_path = os.path.join(base_path, ext_id)
                    if os.path.exists(ext_path):
                        # Find the latest version folder
                        try:
                            versions = [d for d in os.listdir(ext_path) 
                                      if os.path.isdir(os.path.join(ext_path, d))]
                            if versions:
                                latest_version = max(versions)
                                full_path = os.path.join(ext_path, latest_version)
                                extensions.append({
                                    "name": ext_name,
                                    "path": full_path,
                                    "id": ext_id
                                })
                        except Exception as e:
                            logger.debug(f"Error processing extension {ext_name}: {e}")
            
        except Exception as e:
            logger.debug(f"Error finding AdBlock extensions: {e}")
        
        return extensions
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize Selenium configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Validated and normalized configuration
        """
        validated = SeleniumConfigHelper.get_default_config()
        validated.update(config)
        
        # Validate timeout
        if not isinstance(validated["timeout"], (int, float)) or validated["timeout"] <= 0:
            logger.warning("Invalid timeout value, using default (30)")
            validated["timeout"] = 30
        
        # Validate max_attempts
        if not isinstance(validated["max_attempts"], int) or validated["max_attempts"] <= 0:
            logger.warning("Invalid max_attempts value, using default (60)")
            validated["max_attempts"] = 60
        
        # Validate AdBlock extension path
        adblock_path = validated.get("adblock_extension_path")
        if adblock_path:
            if not os.path.exists(adblock_path):
                logger.warning(f"AdBlock extension path does not exist: {adblock_path}")
                validated["adblock_extension_path"] = None
            elif not os.path.isdir(adblock_path):
                logger.warning(f"AdBlock extension path is not a directory: {adblock_path}")
                validated["adblock_extension_path"] = None
        
        # Validate window size
        window_size = validated.get("window_size", "1920,1080")
        if isinstance(window_size, str) and "," in window_size:
            try:
                width, height = map(int, window_size.split(","))
                if width <= 0 or height <= 0:
                    raise ValueError("Invalid dimensions")
            except ValueError:
                logger.warning("Invalid window_size format, using default")
                validated["window_size"] = "1920,1080"
        
        return validated
    
    @staticmethod
    def create_user_config_template() -> Dict[str, Any]:
        """
        Create a user-friendly configuration template.
        
        Returns:
            Configuration template with comments
        """
        extensions = SeleniumConfigHelper.find_adblock_extensions()
        
        template = {
            # Basic settings
            "selenium_headless": True,  # Run browser in background (recommended)
            "selenium_timeout": 30,     # Timeout for page loading (seconds)
            "selenium_max_attempts": 60, # Max attempts to find video stream
            
            # Browser optimization
            "mobile_emulation": True,   # Use mobile user agent (better compatibility)
            "popup_blocking": True,     # Enable popup blocking
            "disable_images": False,    # Disable image loading (faster)
            "disable_javascript": False, # Disable JavaScript (not recommended)
            
            # AdBlock extension (helps with popups and ads)
            "adblock_extension_path": None,  # Path to unpacked AdBlock extension
            
            # Window settings (for non-headless mode)
            "window_size": "1920,1080",  # Browser window size
            "user_data_dir": None,       # Custom Chrome user data directory
        }
        
        # Add found extensions as comments
        if extensions:
            template["_found_adblock_extensions"] = [
                f"{ext['name']}: {ext['path']}" for ext in extensions
            ]
        
        return template
    
    @staticmethod
    def get_installation_instructions() -> str:
        """
        Get installation instructions for Selenium dependencies.
        
        Returns:
            Installation instructions string
        """
        return """
HiAnime Selenium Dependencies Installation:

1. Install Python packages:
   pip install "aniplux[selenium]"
   
   Or manually:
   pip install selenium selenium-wire selenium-stealth yt-dlp

2. Install ChromeDriver:
   - Download from: https://chromedriver.chromium.org/
   - Make sure it matches your Chrome version
   - Add to PATH or place in project directory

3. Optional - AdBlock Extension:
   - Download AdBlock extension as unpacked
   - Set path in plugin configuration
   - Helps reduce popups and ads

4. Test installation:
   aniplux doctor  # Check system dependencies
   
For more help, visit: https://github.com/Yui007/aniplux/wiki/selenium-setup
"""
    
    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """
        Check if all Selenium dependencies are available.
        
        Returns:
            Dictionary with dependency status
        """
        dependencies = {
            "selenium": False,
            "selenium_wire": False,
            "selenium_stealth": False,
            "yt_dlp": False,
            "chromedriver": False
        }
        
        # Check Python packages
        try:
            import selenium
            dependencies["selenium"] = True
        except ImportError:
            pass
        
        try:
            import seleniumwire
            dependencies["selenium_wire"] = True
        except ImportError:
            pass
        
        try:
            import selenium_stealth
            dependencies["selenium_stealth"] = True
        except ImportError:
            pass
        
        try:
            import yt_dlp
            dependencies["yt_dlp"] = True
        except ImportError:
            pass
        
        # Check ChromeDriver
        dependencies["chromedriver"] = SeleniumConfigHelper.detect_chrome_driver() is not None
        
        return dependencies


# Export main class
__all__ = ["SeleniumConfigHelper"]