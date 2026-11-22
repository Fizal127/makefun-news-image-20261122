#!/usr/bin/env python3
"""Entry program for the news-image-20261122 bounty.

Renders the Sunday 22 November 2026 front page and writes
/output/entry.png (or ./output/entry.png when /output is absent).
Standard library only, no network, no clock: the same bytes on
every run. The renderer lives in main_src.py next to this file.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main_src

if __name__ == "__main__":
    sys.exit(main_src.main())
