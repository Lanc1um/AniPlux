<div align="center">

# 🎌 AniPlux

**Modern anime episode downloader with a beautiful command-line interface**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checked](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy.readthedocs.io/)

*Download your favorite anime episodes with style and speed* ✨

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🌟 Features

### 🔍 **Smart Search & Discovery**
- **Multi-source search** - Find anime across multiple streaming sources
- **Fuzzy matching** - Smart search that handles typos and variations
- **Interactive mode** - Browse and select anime with rich formatting
- **Source filtering** - Search specific sources or all at once

### 📺 **Beautiful Episode Browser**
- **Rich terminal UI** - Stunning tables and progress bars with Rich
- **Episode filtering** - Filter by quality, range, or episode type
- **Pagination support** - Navigate large episode lists easily
- **Detailed info** - View episode metadata, quality options, and more

### ⚡ **High-Performance Downloads**
- **aria2c integration** - Multi-connection downloads up to 16x faster
- **Concurrent downloads** - Download multiple episodes simultaneously
- **Progress tracking** - Real-time speed and progress indicators
- **Resume capability** - Automatic resume for interrupted downloads
- **Smart fallback** - Falls back to standard downloads if needed

### 📦 **Flexible Download Options**
- **Bulk downloads** - Download entire seasons or specific episode ranges
- **Quality selection** - Choose from 480p, 720p, 1080p, and higher
- **Custom naming** - Configurable file naming templates
- **Directory management** - Organized downloads with custom paths

### 🎨 **Customizable Interface**
- **Multiple themes** - Dark, light, colorful, and default themes
- **Rich animations** - Smooth progress bars and loading indicators
- **Configurable UI** - Customize colors, styles, and layout
- **Cross-platform** - Works on Windows, macOS, and Linux

### 🔌 **Extensible Plugin System**
- **Modular architecture** - Easy to add new anime sources
- **Plugin management** - Enable, disable, and configure sources
- **Developer-friendly** - Clean APIs for plugin development
- **Built-in sources** - HiAnime, Animetsu, and more included

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Install from Source
```bash
# Clone the repository
git clone https://github.com/Yui007/AniPlux.git
cd AniPlux

# Install in development mode
pip install -e .

# Or install with all dependencies
pip install -e ".[dev]"
```

### Optional: Install aria2c for High-Speed Downloads
```bash
# Windows (Chocolatey)
choco install aria2

# Windows (Scoop)
scoop install aria2

# macOS
brew install aria2

# Ubuntu/Debian
sudo apt install aria2

# CentOS/RHEL
sudo yum install aria2
```

### Plugin-Specific Requirements

#### HiAnime Plugin
The HiAnime plugin may require additional setup for optimal performance:

- **AdBlock Extension** (Recommended): For better scraping reliability, you can configure an AdBlock extension path in the HiAnime plugin settings. This helps bypass ads and improves extraction success rates.
- **Selenium WebDriver** (Optional): For JavaScript-heavy content, install Selenium support:
  ```bash
  pip install -e ".[selenium]"
  ```

To configure AdBlock for HiAnime:
```bash
# Configure HiAnime plugin settings
aniplux sources config hianime_plugin

# Or manually set the AdBlock extension path
aniplux config set sources.hianime_plugin.config.adblock_extension_path "/path/to/adblock/extension"
```

---

## ⚡ Quick Start

### 1. First Run Setup
```bash
# Run the configuration wizard
aniplux config wizard
```

### 2. Search for Anime
```bash
# Basic search
aniplux search anime "demon slayer"

# Search with specific source
aniplux search anime "attack on titan" --source hianime_plugin

# Interactive search mode
aniplux search anime --interactive
```

### 3. Browse Episodes
```bash
# Browse episodes interactively
aniplux episodes browse "anime-url" source_name

# Browse with custom title
aniplux episodes browse "anime-url" source_name --title "My Anime"
```

### 4. Download Episodes
```bash
# Download single episode
aniplux download episode "episode-url"

# Download with quality preference
aniplux download episode "episode-url" --quality 1080p

# Download to specific directory
aniplux download episode "episode-url" --output "/path/to/downloads"
```

### 5. Bulk Downloads
From the episode browser, you can:
- Type `all` - Download all episodes
- Type `1-10` - Download episodes 1 through 10
- Type `download 1,5,10` - Download specific episodes

---

## 📖 Documentation

### 📚 **Comprehensive Guides**
- **[Usage Guide](usage.md)** - Complete user manual with examples
- **[Plugin Development](Plugin-Development.md)** - Create custom source plugins
- **Configuration** - Detailed settings and customization options

### 🎯 **Quick References**
```bash
# View all available commands
aniplux --help

# Get help for specific commands
aniplux search --help
aniplux download --help
aniplux config --help

# Check system information
aniplux info

# Run diagnostics
aniplux doctor
```

### 🔧 **Configuration Management**
```bash
# View current configuration
aniplux config show

# Edit configuration interactively
aniplux config edit

# Set specific values
aniplux config set settings.default_quality 1080p
aniplux config set settings.concurrent_downloads 5

# Backup and restore
aniplux config backup create "my-backup"
aniplux config backup restore backup_file.json
```

### 🔌 **Plugin Management**
```bash
# List available sources
aniplux sources list

# Test source connectivity
aniplux sources test --all

# Enable/disable sources
aniplux sources enable hianime_plugin
aniplux sources disable old_plugin

# Configure source settings
aniplux sources config hianime_plugin
```

---

## 🏗️ Architecture

AniPlux follows a clean, modular architecture designed for extensibility and maintainability:

```
aniplux/
├── cli/           # Command-line interface layer
├── core/          # Core business logic and models
├── plugins/       # Plugin system and source implementations
├── ui/            # User interface components and themes
└── config/        # Configuration management
```

### 🔧 **Technology Stack**
- **Python 3.8+** - Modern Python with type hints
- **Typer** - CLI framework with Rich integration
- **Rich** - Beautiful terminal UI components
- **Pydantic** - Data validation and settings management
- **aiohttp** - Async HTTP client for web scraping
- **BeautifulSoup4** - HTML parsing for web scraping
- **yt-dlp** - Video extraction capabilities

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### 🐛 **Bug Reports**
- Use the [issue tracker](https://github.com/Yui007/AniPlux/issues) to report bugs
- Include system information, error messages, and steps to reproduce
- Run `aniplux doctor --verbose` and include the output

### 💡 **Feature Requests**
- Suggest new features through [GitHub Issues](https://github.com/Yui007/AniPlux/issues)
- Check existing issues to avoid duplicates
- Provide detailed use cases and examples

### 🔧 **Code Contributions**
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with tests
4. **Run** the test suite (`pytest`)
5. **Format** code (`black aniplux/ && isort aniplux/`)
6. **Type check** (`mypy aniplux/`)
7. **Commit** your changes (`git commit -m 'Add amazing feature'`)
8. **Push** to the branch (`git push origin feature/amazing-feature`)
9. **Open** a Pull Request

### 🔌 **Plugin Development**
- Read the [Plugin Development Guide](Plugin-Development.md)
- Use the sample plugin as a starting point
- Test your plugin thoroughly before submitting
- Follow the plugin naming conventions

### 📝 **Documentation**
- Improve existing documentation
- Add examples and use cases
- Fix typos and clarify instructions
- Translate documentation to other languages

---

## 🧪 Development Setup

```bash
# Clone the repository
git clone https://github.com/Yui007/AniPlux.git
cd AniPlux

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=aniplux

# Format code
black aniplux/
isort aniplux/

# Type checking
mypy aniplux/

# Run pre-commit hooks
pre-commit run --all-files
```

### 🧪 **Testing**
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=aniplux --cov-report=html
```

---

## 📊 **Project Status**

### ✅ **Completed Features**
- [x] Multi-source anime search
- [x] Interactive episode browser
- [x] High-speed downloads with aria2c
- [x] Plugin system architecture
- [x] Configuration management
- [x] Rich terminal UI
- [x] HiAnime and Animetsu plugins
- [x] Bulk download capabilities

### 🚧 **In Development**
- [ ] Additional anime source plugins
- [ ] Download queue management
- [ ] Automatic episode tracking
- [ ] Web interface (optional)
- [ ] Mobile companion app

### 💭 **Planned Features**
- [ ] Subtitle download support
- [ ] Torrent integration
- [ ] Cloud storage sync
- [ ] Notification system
- [ ] Advanced filtering options

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[Rich](https://github.com/Textualize/rich)** - For the beautiful terminal UI
- **[Typer](https://github.com/tiangolo/typer)** - For the excellent CLI framework
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - For video extraction capabilities
- **[aria2](https://aria2.github.io/)** - For high-speed download support
- **Community contributors** - For bug reports, feature requests, and code contributions

---

## 📞 Support

- **Documentation**: [Usage Guide](usage.md) | [Plugin Development](Plugin-Development.md)
- **Issues**: [GitHub Issues](https://github.com/Yui007/AniPlux/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Yui007/AniPlux/discussions)

---

<div align="center">

**Made with ❤️ by the AniPlux community**

*Happy anime watching! 🍿✨*

[⬆ Back to top](#-aniplux)

</div>