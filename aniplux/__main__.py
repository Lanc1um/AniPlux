"""
AniPlux Main Entry Point - Package execution entry point.

This module allows the package to be executed directly with:
python -m aniplux
"""

from aniplux.cli.main import cli_main

if __name__ == "__main__":
    cli_main()