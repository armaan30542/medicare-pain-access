#!/usr/bin/env python3
"""Rebuild only the BVNA study. `python run.py` rebuilds everything, including this."""
from __future__ import annotations

import logging
import sys

from src.bvna.pipeline import run
from src.constants import PROCESSED_DIR

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S")
    if not (PROCESSED_DIR / "denominators.parquet").exists():
        logging.error("Run `python run.py` first: BVNA reuses its geography files and denominators.")
        sys.exit(1)
    sys.exit(run())
