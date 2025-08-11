"""
Doctor Command - System diagnostics and health checks.

This module implements the doctor command for running comprehensive
system diagnostics and providing health check reports.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

from aniplux.core import ConfigManager
from aniplux.core.config_utils import find_config_issues
from aniplux.ui import (
    get_console,
    UIComponents,
    display_info,
    display_warning,
    format_success,
    format_warning,
    format_error,
    status_spinner,
)


logger = logging.getLogger(__name__)


def run_system_diagnostics(config_manager: ConfigManager) -> None:
    """
    Run comprehensive system diagnostics.
    
    Args:
        config_manager: Configuration manager instance
    """
    console = get_console()
    ui = UIComponents()
    
    console.print(ui.create_banner("🔍 System Diagnostics", "bold blue"))
    console.print()
    
    # Run diagnostic checks
    with status_spinner("Running system diagnostics..."):
        results = _run_all_diagnostics(config_manager)
    
    # Display results
    _display_diagnostic_results(results, ui)
    
    # Show summary
    _display_diagnostic_summary(results, ui)


def _run_all_diagnostics(config_manager: ConfigManager) -> Dict[str, Any]:
    """Run all diagnostic checks and return results."""
    results = {
        "python_check": _check_python_version(),
        "dependencies_check": _check_dependencies(),
        "configuration_check": _check_configuration(config_manager),
        "filesystem_check": _check_filesystem(config_manager),
        "network_check": _check_network_capabilities(),
        "terminal_check": _check_terminal_capabilities(),
        "plugin_check": _check_plugin_system(config_manager),
    }
    
    return results


def _check_python_version() -> Tuple[bool, str, List[str]]:
    """Check Python version compatibility."""
    version = sys.version_info
    required_major, required_minor = 3, 8
    
    is_compatible = version >= (required_major, required_minor)
    
    status = f"Python {version.major}.{version.minor}.{version.micro}"
    
    issues = []
    if not is_compatible:
        issues.append(f"Python {required_major}.{required_minor}+ is required")
    
    return is_compatible, status, issues


def _check_dependencies() -> Tuple[bool, str, List[str]]:
    """Check required dependencies."""
    required_modules = [
        ("typer", "CLI framework"),
        ("rich", "Terminal formatting"),
        ("aiohttp", "HTTP client"),
        ("pydantic", "Data validation"),
        ("beautifulsoup4", "HTML parsing"),
    ]
    
    missing_modules = []
    available_count = 0
    
    for module_name, description in required_modules:
        try:
            __import__(module_name)
            available_count += 1
        except ImportError:
            missing_modules.append(f"{module_name} ({description})")
    
    all_available = len(missing_modules) == 0
    status = f"{available_count}/{len(required_modules)} modules available"
    
    issues = [f"Missing: {module}" for module in missing_modules]
    
    return all_available, status, issues


def _check_configuration(config_manager: ConfigManager) -> Tuple[bool, str, List[str]]:
    """Check configuration validity."""
    validation_report = config_manager.validate_configuration()
    config_issues = find_config_issues(config_manager)
    
    is_valid = validation_report["valid"] and len(config_issues) == 0
    
    issues_count = len(validation_report.get("issues", []))
    warnings_count = len(validation_report.get("warnings", []))
    
    status = f"{issues_count} errors, {warnings_count} warnings"
    
    issues = []
    issues.extend(validation_report.get("issues", []))
    
    # Add critical issues from detailed analysis
    critical_issues = [
        issue for issue in config_issues 
        if issue.get("severity") == "error"
    ]
    
    for issue in critical_issues:
        issues.append(issue["message"])
    
    return is_valid, status, issues


def _check_filesystem(config_manager: ConfigManager) -> Tuple[bool, str, List[str]]:
    """Check filesystem access and permissions."""
    issues = []
    
    # Check download directory
    download_dir = Path(config_manager.settings.settings.download_directory)
    
    try:
        # Create directory if it doesn't exist
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = download_dir / ".aniplux_write_test"
        test_file.write_text("test")
        test_file.unlink()
        
        download_ok = True
    except Exception as e:
        download_ok = False
        issues.append(f"Download directory not writable: {e}")
    
    # Check configuration directory
    config_dir = config_manager.config_dir
    
    try:
        # Test write permissions
        test_file = config_dir / ".aniplux_config_test"
        test_file.write_text("test")
        test_file.unlink()
        
        config_ok = True
    except Exception as e:
        config_ok = False
        issues.append(f"Configuration directory not writable: {e}")
    
    all_ok = download_ok and config_ok
    status = f"Download: {'✅' if download_ok else '❌'}, Config: {'✅' if config_ok else '❌'}"
    
    return all_ok, status, issues


def _check_network_capabilities() -> Tuple[bool, str, List[str]]:
    """Check network and HTTP capabilities."""
    issues = []
    
    # Test basic HTTP functionality
    try:
        import aiohttp
        # Basic import test
        network_ok = True
        status = "HTTP client available"
    except ImportError:
        network_ok = False
        status = "HTTP client not available"
        issues.append("aiohttp module not available")
    
    # Check SSL support
    try:
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_ok = True
    except Exception:
        ssl_ok = False
        issues.append("SSL support not available")
    
    overall_ok = network_ok and ssl_ok
    
    return overall_ok, status, issues


def _check_terminal_capabilities() -> Tuple[bool, str, List[str]]:
    """Check terminal capabilities."""
    from aniplux.ui.console import detect_terminal_capabilities, get_console_info
    
    capabilities = detect_terminal_capabilities()
    console_info = get_console_info()
    
    issues = []
    
    # Check color support
    if capabilities["colors"] == "none":
        issues.append("No color support detected")
    
    # Check Unicode support
    if not capabilities["unicode"]:
        issues.append("Limited Unicode support")
    
    # Check terminal size
    if console_info["width"] < 80:
        issues.append(f"Terminal width is narrow ({console_info['width']} columns)")
    
    # Overall status
    color_level = capabilities["colors"]
    unicode_status = "✅" if capabilities["unicode"] else "⚠️"
    
    status = f"Colors: {color_level}, Unicode: {unicode_status}"
    
    # Consider it OK if we have basic functionality
    terminal_ok = capabilities["colors"] != "none"
    
    return terminal_ok, status, issues


def _check_plugin_system(config_manager: ConfigManager) -> Tuple[bool, str, List[str]]:
    """Check plugin system status."""
    issues = []
    
    # Check if plugins directory exists
    plugins_dir = Path(__file__).parent.parent.parent / "plugins"
    
    if not plugins_dir.exists():
        issues.append("Plugins directory not found")
        return False, "Plugins directory missing", issues
    
    # Count available sources
    total_sources = len(config_manager.sources.sources)
    enabled_sources = len(config_manager.get_enabled_sources())
    
    if total_sources == 0:
        issues.append("No source plugins configured")
    
    if enabled_sources == 0:
        issues.append("No source plugins enabled")
    
    status = f"{enabled_sources}/{total_sources} sources enabled"
    
    # Consider OK if we have at least one enabled source
    plugins_ok = enabled_sources > 0
    
    return plugins_ok, status, issues


def _display_diagnostic_results(results: Dict[str, Any], ui: UIComponents) -> None:
    """Display detailed diagnostic results."""
    console = get_console()
    
    # Create results table
    headers = ["Check", "Status", "Result", "Issues"]
    rows = []
    
    check_names = {
        "python_check": "Python Version",
        "dependencies_check": "Dependencies",
        "configuration_check": "Configuration",
        "filesystem_check": "File System",
        "network_check": "Network",
        "terminal_check": "Terminal",
        "plugin_check": "Plugin System",
    }
    
    for check_key, check_name in check_names.items():
        is_ok, status, issues = results[check_key]
        
        # Format status
        status_icon = "✅" if is_ok else "❌"
        
        # Format issues
        issues_text = f"{len(issues)} issues" if issues else "None"
        if issues:
            issues_text = format_warning(issues_text) if is_ok else format_error(issues_text)
        else:
            issues_text = format_success("None")
        
        rows.append([
            check_name,
            status_icon,
            status,
            issues_text
        ])
    
    # Display results table
    results_table = ui.create_data_table(
        headers=headers,
        rows=rows,
        title="Diagnostic Results"
    )
    
    console.print(ui.create_info_panel(
        results_table,
        title="📊 Detailed Results"
    ))
    
    # Display issues details
    _display_issues_details(results, ui)


def _display_issues_details(results: Dict[str, Any], ui: UIComponents) -> None:
    """Display detailed issues information."""
    console = get_console()
    
    all_issues = []
    
    check_names = {
        "python_check": "Python Version",
        "dependencies_check": "Dependencies", 
        "configuration_check": "Configuration",
        "filesystem_check": "File System",
        "network_check": "Network",
        "terminal_check": "Terminal",
        "plugin_check": "Plugin System",
    }
    
    for check_key, check_name in check_names.items():
        is_ok, status, issues = results[check_key]
        
        if issues:
            all_issues.append((check_name, is_ok, issues))
    
    if all_issues:
        console.print()
        
        for check_name, is_ok, issues in all_issues:
            severity = "warning" if is_ok else "error"
            title = f"⚠️  {check_name} Issues" if is_ok else f"❌ {check_name} Errors"
            
            issues_text = "\n".join(f"• {issue}" for issue in issues)
            
            if is_ok:
                console.print(ui.create_warning_panel(issues_text, title))
            else:
                console.print(ui.create_error_panel(issues_text, title))


def _display_diagnostic_summary(results: Dict[str, Any], ui: UIComponents) -> None:
    """Display diagnostic summary."""
    console = get_console()
    
    # Count results
    total_checks = len(results)
    passed_checks = sum(1 for is_ok, _, _ in results.values() if is_ok)
    failed_checks = total_checks - passed_checks
    
    # Create summary
    if failed_checks == 0:
        summary_text = f"[green]✅ All {total_checks} diagnostic checks passed![/green]\n\nYour AniPlux installation appears to be working correctly."
        panel = ui.create_success_panel(summary_text, "🎉 Diagnostics Complete")
    else:
        summary_text = f"[yellow]⚠️  {passed_checks}/{total_checks} diagnostic checks passed[/yellow]\n\n{failed_checks} checks failed or have issues that may affect functionality."
        panel = ui.create_warning_panel(summary_text, "⚠️  Diagnostics Complete")
    
    console.print()
    console.print(panel)
    
    # Show next steps if there are issues
    if failed_checks > 0:
        console.print()
        display_info(
            "Review the issues above and:\n"
            "• Install missing dependencies with pip\n"
            "• Check file permissions for directories\n"
            "• Validate configuration with 'aniplux config validate'\n"
            "• Enable source plugins with 'aniplux sources enable <name>'",
            "💡 Next Steps"
        )


# Export doctor functions
__all__ = ["run_system_diagnostics"]