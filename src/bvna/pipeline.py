"""The BVNA stages, callable from the single top-level entry point."""
from __future__ import annotations

import logging
from typing import Final

from src.bvna import analyze, deck, fetch, figures, literature

LOGGER: Final = logging.getLogger(__name__)


def run() -> int:
    """Fetch BVNA rows, analyse, plot and build the deck. Returns 0 on success."""
    LOGGER.info("BVNA 1/5  provider rows (CMS API, filtered)")
    try:
        fetch.ensure_all()
    except (RuntimeError, fetch.FilterIgnoredError) as exc:
        LOGGER.error("%s", exc)
        return 2
    LOGGER.info("BVNA 2/5  literature search (cached)")
    try:
        literature.load_or_fetch()
    except OSError as exc:
        LOGGER.error("could not reach NCBI and no cache exists: %s", exc)
        return 3
    LOGGER.info("BVNA 3/5  analysis")
    analyze.run()
    LOGGER.info("BVNA 4/5  figures")
    figures.run()
    LOGGER.info("BVNA 5/5  deck")
    return deck.main()
