"""Entry point for PyInstaller builds (same as `python -m scraper`)."""

import sys

from scraper.tui import main

if __name__ == "__main__":
    sys.exit(main())
