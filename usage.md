# 🎌 AniPlux Usage Guide

Welcome to AniPlux - the modern anime episode downloader with a beautiful command-line interface! This comprehensive guide will help you master all of AniPlux's features.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🔍 Search & Discovery](#-search--discovery)
- [📺 Episode Browsing](#-episode-browsing)
- [⬇️ Download Features](#️-download-features)
- [⚙️ Configuration](#️-configuration)
- [🔌 Plugin Management](#-plugin-management)
- [🎨 Themes & UI](#-themes--ui)
- [🛠️ Advanced Features](#️-advanced-features)
- [❓ Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI (recommended)
pip install aniplux

# Or install from source
git clone https://github.com/Yui007/AniPlux.git
cd AniPlux
pip install -e .
```

### First Run Setup

Run the configuration wizard to set up AniPlux for your system:

```bash
aniplux config wizard
```

This interactive setup will guide you through:
- Download directory configuration
- Quality preferences
- Performance settings
- UI theme selection
- Source plugin setup

### Basic Usage

```bash
# Search for anime
aniplux search anime "demon slayer"

# Browse episodes
aniplux episodes browse "episode-url"

# Download an episode
aniplux download episode "episode-url"
```

---

## 🔍 Search & Discovery

### Basic Search

Search across all enabled sources:

```bash
aniplux search anime "attack on titan"
```

### Advanced Search Options

```bash
# Search with specific source
aniplux search anime "demon slayer" --source hianime_plugin

# Limit results
aniplux search anime "naruto" --limit 10

# Interactive search mode
aniplux search anime --interactive
```

### Search Results

AniPlux displays search results in a beautiful table format showing:
- 📺 Anime title
- 📊 Episode count
- 🌐 Source plugin name

Example output:
```
┌─────────────────────────────────────────────────────────────────┐
│                        🔍 Search Results                        │
├─────────────────────────────────────────────────────────────────┤
│ #    │ Title                    │ Episodes │ Source              │
├─────────────────────────────────────────────────────────────────┤
│ 1    │ Demon Slayer             │    44    │ hianime_plugin      │
│ 2    │ Attack on Titan          │    87    │ hianime_plugin      │
│ 3    │ One Piece                │  1000+   │ hianime_plugin      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📺 Episode Browsing

### Interactive Episode Browser

Launch the beautiful episode browser:

```bash
# Browse from search results
aniplux episodes browse

# Browse specific anime URL
aniplux episodes browse "https://hianime.to/demon-slayer-18056" hianime_plugin

# Browse with custom title
aniplux episodes browse "anime-url" source_name --title "Custom Title"
```

### Browser Navigation

The episode browser provides rich keyboard navigation:

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate episodes |
| `Enter` | Select episode |
| `n/p` | Next/Previous page |
| `f` | Set filters |
| `s` | Sort episodes |
| `c` | Clear filters |
| `d` | Show episode details |
| `q` | Quit browser |

### Episode Filtering

Filter episodes by various criteria:

```bash
# In the browser, press 'f' to set filters
Quality: 1080p, 720p, 480p
Range: 1-10 (episodes 1 through 10)
```

### Episode Details

Press `d` in the browser to view detailed episode information:
- 📺 Episode title and number
- ⏱️ Duration
- 📅 Release date
- 🎬 Quality options
- 🔗 Direct URL
- 💡 Download command

---

## ⬇️ Download Features

### Single Episode Download

```bash
# Download specific episode
aniplux download episode "https://hianime.to/watch/episode-url"

# Download with quality preference
aniplux download episode "episode-url" --quality 1080p

# Download to specific directory
aniplux download episode "episode-url" --output "/path/to/downloads"
```

### Bulk Download Options

AniPlux supports powerful bulk downloading directly from the episode browser:

#### 1. Download All Episodes
```bash
# In episode browser, type:
all
```
Downloads all episodes in the current filtered view.

#### 2. Download Episode Range
```bash
# In episode browser, type:
1-5      # Downloads episodes 1 through 5
10-15    # Downloads episodes 10 through 15
```

#### 3. Download Specific Episodes
```bash
# In episode browser, type:
download 1,3,5,7    # Downloads episodes 1, 3, 5, and 7
download 1,5,10     # Downloads episodes 1, 5, and 10
```

### Batch Download Commands

```bash
# Download multiple episodes from command line
aniplux download batch "url1" "url2" "url3" --quality 1080p

# Download with custom naming
aniplux download batch "url1" "url2" --template "{anime_title}_EP{episode_number}"
```

### High-Speed Downloads with aria2c

AniPlux supports aria2c for significantly faster downloads:

#### Installing aria2c

**Windows:**
```bash
# Using Chocolatey
choco install aria2

# Using Scoop
scoop install aria2

# Or download from: https://aria2.github.io/
```

**macOS:**
```bash
brew install aria2
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install aria2
```

**Linux (CentOS/RHEL):**
```bash
sudo yum install aria2
```

#### aria2c Benefits

- 🚀 **Multi-connection downloads**: Up to 16 connections per download
- 📈 **Faster speeds**: 3-5x faster than single-connection downloads
- 🔄 **Resume capability**: Better resume support for interrupted downloads
- 🛡️ **Automatic fallback**: Falls back to standard downloads if aria2c fails
- 📊 **Progress tracking**: Real-time speed and progress indicators

#### aria2c Configuration

Configure aria2c settings:

```bash
# Check current download configuration
aniplux download info

# Configure aria2c settings
aniplux config set settings.use_aria2c true
aniplux config set settings.aria2c_connections 16
aniplux config set settings.aria2c_split 16
```

### Download Management

```bash
# Check download status
aniplux download status

# View download information and capabilities
aniplux download info

# Resume failed downloads
aniplux download resume

# Clear download history
aniplux download clear
```

---

## ⚙️ Configuration

### Configuration Wizard

Run the interactive setup wizard:

```bash
aniplux config wizard
```

### Manual Configuration

#### View Current Configuration

```bash
# Show all settings
aniplux config show

# Show specific section
aniplux config show settings
aniplux config show ui
aniplux config show sources
```

#### Update Settings

```bash
# Set download directory
aniplux config set settings.download_directory "/path/to/downloads"

# Set default quality
aniplux config set settings.default_quality 1080p

# Set concurrent downloads
aniplux config set settings.concurrent_downloads 5

# Set network timeout
aniplux config set settings.timeout 30
```

#### Interactive Configuration Editor

Launch the full configuration editor:

```bash
aniplux config edit
```

This provides a menu-driven interface to modify all settings with validation and help text.

### Configuration Backup & Restore

```bash
# Create configuration backup
aniplux config backup create "Before major changes"

# List available backups
aniplux config backup list

# Restore from backup
aniplux config backup restore backup_20241210_143022.json

# Clean up old backups
aniplux config backup cleanup --keep 5
```

### Configuration Files

AniPlux stores configuration in:
- `config/settings.json` - Application settings
- `config/sources.json` - Source plugin configurations

Example settings.json:
```json
{
  "settings": {
    "download_directory": "./downloads",
    "default_quality": "1080p",
    "concurrent_downloads": 3,
    "timeout": 30,
    "use_aria2c": true,
    "aria2c_connections": 16
  },
  "ui": {
    "color_theme": "default",
    "show_banner": true,
    "progress_style": "bar"
  },
  "search": {
    "max_results_per_source": 50,
    "enable_fuzzy_search": true
  }
}
```

---

## 🔌 Plugin Management

### Source Management

```bash
# List all sources
aniplux sources list

# Enable/disable sources
aniplux sources enable hianime_plugin
aniplux sources disable old_plugin

# Test source connectivity
aniplux sources test hianime_plugin
aniplux sources test --all

# Reload plugins
aniplux sources reload
```

### Source Configuration

```bash
# Configure source settings
aniplux sources config hianime_plugin

# Export source configuration
aniplux sources export hianime_plugin config.json

# Import source configuration
aniplux sources import config.json
```

### Available Sources

AniPlux comes with several built-in source plugins:

| Source | Status | Features |
|--------|--------|----------|
| HiAnime | ✅ Active | HD quality, fast servers |
| Animetsu | ✅ Active | Multiple quality options |
| Sample | 🧪 Demo | For development/testing |

### Plugin Development

Create custom source plugins by extending the base plugin class. See the [plugin development guide](https://github.com/Yui007/AniPlux/wiki/Plugin-Development) for details.

---

## 🎨 Themes & UI

### Theme Selection

AniPlux supports multiple beautiful themes:

```bash
# List available themes
aniplux config show ui.color_theme

# Set theme
aniplux config set ui.color_theme dark
aniplux config set ui.color_theme light
aniplux config set ui.color_theme colorful
aniplux config set ui.color_theme default
```

### Theme Preview

Preview themes before applying:

```bash
# Preview specific theme
aniplux config preview theme dark

# Preview all themes
aniplux config preview themes
```

### UI Customization

```bash
# Customize progress indicators
aniplux config set ui.progress_style bar      # bar, spinner, dots
aniplux config set ui.table_style rounded    # rounded, simple, grid
aniplux config set ui.panel_style rounded    # rounded, square, heavy

# Toggle startup banner
aniplux config set ui.show_banner true

# Set animation speed
aniplux config set ui.animation_speed normal  # slow, normal, fast
```

### Theme Examples

**Default Theme:**
- Clean blue and cyan color scheme
- Professional appearance
- Good for all terminal types

**Dark Theme:**
- High contrast colors
- Bright text on dark background
- Ideal for dark terminals

**Light Theme:**
- Optimized for light backgrounds
- Darker text colors
- Perfect for light terminal themes

**Colorful Theme:**
- Vibrant color palette
- Eye-catching design
- Great for modern terminals with full color support

---

## 🛠️ Advanced Features

### System Information

```bash
# Show system information
aniplux info

# Show detailed system diagnostics
aniplux doctor

# Check system health
aniplux doctor --verbose
```

### Logging & Debugging

```bash
# Set logging level
aniplux config set logging.level DEBUG

# View logs
tail -f aniplux.log

# Enable verbose output
aniplux --verbose search "anime title"
```

### Performance Optimization

```bash
# Optimize configuration for your system
aniplux config optimize

# Check system capabilities
aniplux doctor --performance

# Benchmark download speeds
aniplux download benchmark
```

### Automation & Scripting

AniPlux can be integrated into scripts and automation workflows:

```bash
#!/bin/bash
# Example automation script

# Search and download latest episode
ANIME_URL=$(aniplux search "ongoing anime" --format json | jq -r '.[0].url')
aniplux download episode "$ANIME_URL"

# Bulk download with error handling
aniplux download batch "url1" "url2" "url3" || echo "Download failed"
```

---

## ❓ Troubleshooting

### Common Issues

#### 1. No Search Results

```bash
# Check source status
aniplux sources test --all

# Enable more sources
aniplux sources enable --all

# Check network connectivity
aniplux doctor --network
```

#### 2. Download Failures

```bash
# Check download configuration
aniplux download info

# Test with different quality
aniplux download episode "url" --quality 720p

# Check disk space and permissions
aniplux doctor --storage
```

#### 3. Plugin Issues

```bash
# Reload plugins
aniplux sources reload

# Check plugin status
aniplux sources list --verbose

# Reset plugin configuration
aniplux sources reset plugin_name
```

#### 4. Configuration Problems

```bash
# Validate configuration
aniplux config validate

# Reset to defaults
aniplux config reset

# Restore from backup
aniplux config backup restore
```

### Getting Help

```bash
# Show help for any command
aniplux --help
aniplux search --help
aniplux download --help

# Show version information
aniplux --version

# Run system diagnostics
aniplux doctor
```

### Error Reporting

If you encounter issues:

1. Run diagnostics: `aniplux doctor --verbose`
2. Check logs: `tail -f aniplux.log`
3. Report issues: [GitHub Issues](https://github.com/Yui007/AniPlux/issues)

Include the following information:
- AniPlux version
- Operating system
- Error messages
- Steps to reproduce

---

## 🎯 Pro Tips

### Efficiency Tips

1. **Use aliases** for frequently used commands:
   ```bash
   alias ans="aniplux search"
   alias and="aniplux download episode"
   alias ane="aniplux episodes browse"
   ```

2. **Set up optimal configuration**:
   ```bash
   # For fast internet connections
   aniplux config set settings.concurrent_downloads 5
   aniplux config set settings.aria2c_connections 16
   
   # For slower connections
   aniplux config set settings.concurrent_downloads 2
   aniplux config set settings.timeout 60
   ```

3. **Use filters effectively** in the episode browser to quickly find specific episodes.

4. **Bookmark frequently accessed anime** URLs for quick access.

### Quality Settings

- **1080p**: Best quality, larger file sizes
- **720p**: Good balance of quality and size (recommended)
- **480p**: Smaller files, faster downloads

### Batch Operations

- Use episode ranges (`1-10`) for season downloads
- Use specific episodes (`1,5,10`) for selective downloading
- Use `all` command for complete series downloads

---

## 📚 Additional Resources

- **GitHub Repository**: [https://github.com/Yui007/AniPlux](https://github.com/Yui007/AniPlux)
- **Documentation**: [Project Wiki](https://github.com/Yui007/AniPlux/wiki)
- **Issue Tracker**: [Report Bugs](https://github.com/Yui007/AniPlux/issues)
- **Discussions**: [Community Forum](https://github.com/Yui007/AniPlux/discussions)

---

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](https://github.com/Yui007/AniPlux/blob/main/CONTRIBUTING.md) for details on:

- Reporting bugs
- Suggesting features
- Contributing code
- Creating plugins
- Improving documentation

---

## 📄 License

AniPlux is open source software. See the [LICENSE](https://github.com/Yui007/AniPlux/blob/main/LICENSE) file for details.

---

**Happy anime watching! 🍿✨**

*Made with ❤️ by the AniPlux community*