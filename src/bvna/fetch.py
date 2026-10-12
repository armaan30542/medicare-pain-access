"""Pull BVNA provider-level rows from the CMS data API, filtered server-side.

In August 2026 the API appeared to ignore filters (its /stats endpoint returned
the full row count with or without one). The /data endpoint now honours
filter[HCPCS_Cd]=<code>, which turns a ~10 GB stream into a few hundred KB.
Because that behaviour has changed once already, every page is checked: if any
returned row carries a code other than the one requested, the pull stops.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from src.bvna.config import (
    API_DATASETS,
    API_PAGE_SIZE,
    API_PAUSE_S,
    API_TIMEOUT_S,
    BVNA_AUDIT,
    BVNA_CODES,
    BVNA_RAW,
    YEARS,
)
from src.download import SSL_CONTEXT, USER_AGENT, manual_instructions

LOGGER: Final = logging.getLogger(__name__)
API_BASE: Final[str] = "https://data.cms.gov/data-api/v1/dataset/{id}/data"


class FilterIgnoredError(RuntimeError):
    """The API returned rows for a code we did not ask for."""


def _page(dataset: str, code: str, offset: int) -> list[dict]:
    query = urllib.parse.urlencode(
        {"filter[HCPCS_Cd]": code, "size": API_PAGE_SIZE, "offset": offset}
    )
    url = f"{API_BASE.format(id=dataset)}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=API_TIMEOUT_S,
                                context=SSL_CONTEXT) as response:
        return json.loads(response.read())


def pull_code(dataset: str, code: str) -> list[dict]:
    """Every row for one HCPCS code in one dataset, paging until exhausted."""
    rows: list[dict] = []
    offset = 0
    while True:
        batch = _page(dataset, code, offset)
        stray = {r.get("HCPCS_Cd") for r in batch} - {code}
        if stray:
            raise FilterIgnoredError(
                f"Asked dataset {dataset} for {code} and got {sorted(stray)[:5]}. "
                "The API filter is being ignored again; do not trust this pull."
            )
        rows.extend(batch)
        if len(batch) < API_PAGE_SIZE:
            return rows
        offset += API_PAGE_SIZE
        time.sleep(API_PAUSE_S)


def ensure_year(year: int) -> Path:
    """Cache all BVNA rows for one data year as gzipped JSON. Never re-fetches."""
    target = BVNA_RAW / f"bvna_prov_svc_{year}.json.gz"
    if target.exists():
        LOGGER.info("bvna %d: cached", year)
        return target

    datasets = API_DATASETS[year]
    pulls: list[list[dict]] = []
    for dataset in datasets:
        rows = [r for code in BVNA_CODES for r in pull_code(dataset, code)]
        pulls.append(rows)
        LOGGER.info("bvna %d: %s rows from dataset %s", year, f"{len(rows):,}", dataset[:8])

    if len(pulls) > 1:
        fingerprints = {
            json.dumps(sorted(json.dumps(r, sort_keys=True) for r in p)) for p in pulls
        }
        if len(fingerprints) != 1:
            raise RuntimeError(
                f"The {len(datasets)} API identifiers for {year} disagree. "
                "Resolve which is canonical before analysing."
            )

    payload = json.dumps(pulls[0]).encode("utf-8")
    BVNA_RAW.mkdir(parents=True, exist_ok=True)
    with gzip.open(target, "wb") as handle:
        handle.write(payload)

    record = {
        "cached_file": target.name,
        "source": [API_BASE.format(id=d) + "?filter[HCPCS_Cd]=..." for d in datasets],
        "codes": list(BVNA_CODES),
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": len(pulls[0]),
        "bytes_uncompressed": len(payload),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    BVNA_AUDIT.mkdir(parents=True, exist_ok=True)
    ledger = BVNA_AUDIT / "provenance.json"
    entries = json.loads(ledger.read_text()) if ledger.exists() else []
    entries = [e for e in entries if e["cached_file"] != target.name] + [record]
    ledger.write_text(json.dumps(entries, indent=1))
    return target


def ensure_all() -> list[Path]:
    paths: list[Path] = []
    for year in YEARS:
        try:
            paths.append(ensure_year(year))
        except OSError as exc:
            dataset = API_DATASETS[year][0]
            raise RuntimeError(
                f"Could not reach the CMS API for {year}: {exc}"
                + manual_instructions(
                    API_BASE.format(id=dataset) + "?filter[HCPCS_Cd]=64628&size=1000",
                    BVNA_RAW / f"bvna_prov_svc_{year}.json.gz",
                )
            ) from exc
    return paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s",
                        datefmt="%H:%M:%S")
    ensure_all()
