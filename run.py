#!/usr/bin/env python3
"""Single entry point: download, clean, analyse, plot, and write every document.

    python run.py

Every stage is idempotent. Cached downloads are never re-fetched. If the network
is unavailable, the download stage prints exact manual instructions and exits
cleanly with a non-zero status rather than proceeding on partial data.
"""
from __future__ import annotations

import json
import logging
import sys
import warnings
from datetime import date
from pathlib import Path
from typing import Final

import pandas as pd

from src import analysis, build_deck, build_pptx, clean, figures, literature, report
from src.clean import DataIntegrityError
from src.constants import AUDIT_DIR, FIGURES_DIR, PROCESSED_DIR, YEARS
from src.download import DownloadUnavailableError, ensure_all
from src.bvna import pipeline as bvna_pipeline

LOGGER: Final = logging.getLogger("run")
MIN_PYTHON: Final[tuple[int, int]] = (3, 12)   # numpy 2.5 and scipy 1.18 require 3.12

PROCESSED_TABLES: Final[tuple[str, ...]] = (
    "hcpcs_verification", "prov_svc_study", "denominators",
    "income", "state_year_panel", "national_by_code",
)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)


def _print_verification(table: pd.DataFrame) -> None:
    """Print the HCPCS verification table, as required before any analysis."""
    columns = ["hcpcs_code", "tier", "status", "years_present",
               "n_distinct_desc", "hcpcs_desc_from_file"]
    LOGGER.info("HCPCS CODE VERIFICATION (descriptors read from the downloaded files)")
    for line in table[columns].to_string(index=False, max_colwidth=78).splitlines():
        LOGGER.info("  %s", line)


def build_deck_pptx() -> int:
    """Build the PowerPoint deck. Kept separate so a pptx failure is reported
    distinctly from an html failure."""
    return build_pptx.main()


def _accessed_date() -> str:
    """When the CMS files were actually downloaded, read from the provenance
    ledger. Using today's date would silently change every figure footnote on
    each rerun even though the underlying data had not changed."""
    ledger = AUDIT_DIR / "provenance.json"
    if ledger.exists():
        entries = json.loads(ledger.read_text())
        if entries:
            return max(e["downloaded_utc"] for e in entries)[:10]
    LOGGER.warning("no provenance ledger yet; using today's date as the access date")
    return date.today().isoformat()


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required "
              f"(found {sys.version.split()[0]}).", file=sys.stderr)
        return 1
    _configure_logging()

    LOGGER.info("STAGE 1/8  download (cached files are skipped)")
    try:
        ensure_all()
    except DownloadUnavailableError as exc:
        LOGGER.error("%s", exc)
        return 1

    accessed = _accessed_date()

    LOGGER.info("STAGE 2/8  clean")
    try:
        tables = clean.run()
    except DataIntegrityError as exc:
        LOGGER.error("data integrity failure: %s", exc)
        return 2
    _print_verification(tables["hcpcs_verification"])

    LOGGER.info("STAGE 3/8  literature counts (NCBI E-utilities)")
    try:
        payload = literature.load_or_fetch()
    except OSError as exc:
        LOGGER.error("could not reach NCBI E-utilities and no cache exists: %s", exc)
        LOGGER.error("Run `python -m src.literature` once with network access.")
        return 3

    LOGGER.info("STAGE 4/8  analysis")
    computed = analysis.run(tables, payload["fig6"])
    results, objects = computed["results"], computed["objects"]
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "results.json").write_text(json.dumps(results, indent=1, default=str))

    LOGGER.info("STAGE 5/8  figures and documents")
    national = tables["national_by_code"]
    pns_raw = national[national["hcpcs_code"] == "64555"].sort_values("year")
    year_span = f"{min(YEARS)}-{max(YEARS)}"

    figures.figure1(objects["indexed"], results["pns_inflection_year"], accessed, pns_raw)
    figures.figure2(objects["pns_conc_base"], objects["basic_conc_base"],
                    objects["pns_conc"], objects["basic_conc"], accessed)
    figures.figure3(objects["deserts"], accessed)
    figures.figure4(objects["models"], accessed, year_span)
    figures.figure5(objects["income_gradient"], accessed)
    figures.figure5b(objects["dual_gradient"], accessed)
    figures.figure6(payload["fig6"]["counts"], payload["fig6"]["queries"], accessed)

    written = report.write_all(results, accessed)
    for path in written:
        LOGGER.info("wrote %s", path.name)

    LOGGER.info("STAGE 6/8  presentation deck (html)")
    deck_status = build_deck.main()

    LOGGER.info("STAGE 7/8  presentation deck (pptx)")
    pptx_status = build_deck_pptx()

    LOGGER.info("STAGE 8/8  BVNA study")
    bvna_status = bvna_pipeline.run()

    LOGGER.info("DONE. Figures in %s and bvna/figures, tables in %s.", FIGURES_DIR, PROCESSED_DIR)
    if deck_status:
        LOGGER.error("deck.html failed self-containment checks; see above.")
        return 4
    if pptx_status:
        LOGGER.error("deck.pptx failed its structural checks; see above.")
        return 5
    if bvna_status:
        LOGGER.error("BVNA study failed; see above.")
        return 6
    LOGGER.info("Read RESULTS.md and TALKING_POINTS.md - two hypotheses did not survive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
