"""Stream CMS public-use files and cache a slim, code-filtered extract.

The CMS by-provider-and-service files are ~2 GB per year and the data.cms.gov
API ignores column filters (verified: /data/stats returns the same found_rows
with and without a filter clause). We therefore stream each yearly CSV over
HTTPS and retain only rows whose HCPCS_Cd is in the study code set, writing a
compact gzipped CSV to data/raw/. Cached files are never re-downloaded.

Every cached file gets a provenance record: URL, timestamp, bytes streamed,
rows scanned, rows kept, and the SHA256 of the cached extract.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import ssl
import logging
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Iterator, Sequence

from src.constants import ALL_CODES, AUDIT_DIR, PROV_SVC_COLUMNS, RAW_DIR, YEARS

LOGGER: Final = logging.getLogger(__name__)

# ------------------------------------------------------------------ config
USER_AGENT: Final[str] = (
    "pns-medicare-access-study/1.0 (research; contact via project README)"
)
STREAM_CHUNK_BYTES: Final[int] = 1 << 22          # 4 MiB
HTTP_TIMEOUT_SECONDS: Final[int] = 900
PROGRESS_EVERY_ROWS: Final[int] = 2_000_000
MAX_PARALLEL_STREAMS: Final[int] = 5

CATALOG_URL: Final[str] = "https://data.cms.gov/data.json"


def _ssl_context() -> ssl.SSLContext:
    """Build a verifying SSL context backed by certifi's CA bundle.

    Framework Python builds on macOS ship without a populated trust store, so
    the interpreter default raises CERTIFICATE_VERIFY_FAILED even where curl
    succeeds. We never disable verification; we point it at a real bundle.
    """
    import certifi

    return ssl.create_default_context(cafile=certifi.where())


SSL_CONTEXT: Final[ssl.SSLContext] = _ssl_context()

PROV_SVC_DATASET: Final[str] = (
    "Medicare Physician & Other Practitioners - by Provider and Service"
)
GEO_SVC_DATASET: Final[str] = (
    "Medicare Physician & Other Practitioners - by Geography and Service"
)
GEOVAR_DATASET: Final[str] = (
    "Medicare Geographic Variation - by National, State & County"
)

# Census fallback. The ACS API began requiring a key for every request
# (an unkeyed call returns an HTML "Missing Key" page, verified 2026-08-25), so
# state median household income comes from SAIPE, which is a plain fixed-width
# file on the Census FTP with no key and no login. Documented in README.md.
SAIPE_URL_TEMPLATE: Final[str] = (
    "https://www2.census.gov/programs-surveys/saipe/datasets/"
    "{year}/{year}-state-and-county/est{yy}all.txt"
)


class DownloadUnavailableError(RuntimeError):
    """Raised when a required file cannot be fetched and has no cached copy."""


@dataclass(frozen=True)
class Provenance:
    """One row of DATA_PROVENANCE.md."""

    cached_file: str
    source_url: str
    downloaded_utc: str
    bytes_streamed: int
    rows_scanned: int
    rows_kept: int
    cached_bytes: int
    sha256: str


def _open_stream(url: str) -> io.BufferedReader:
    """Open an HTTPS byte stream for `url`, raising on any non-200."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(
        request, timeout=HTTP_TIMEOUT_SECONDS, context=SSL_CONTEXT
    )


def _sha256_of(path: Path) -> str:
    """Return the hex SHA256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(STREAM_CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _counting_line_iter(stream: io.BufferedReader, counter: list[int]) -> Iterator[str]:
    """Yield decoded lines from `stream`, accumulating byte count into counter[0]."""
    for raw in stream:
        counter[0] += len(raw)
        yield raw.decode("utf-8", errors="replace")


def manual_instructions(url: str, target: Path) -> str:
    """Exact copy-paste instructions for a human to fetch a file by hand."""
    return (
        "\n"
        "================= MANUAL DOWNLOAD REQUIRED =================\n"
        f"  URL    : {url}\n"
        f"  Save as: {target}\n"
        "\n"
        "  Run this, then re-run `python run.py`:\n"
        f"    curl -L -o '{target}' '{url}'\n"
        "============================================================\n"
    )


def fetch_catalog(cache: Path | None = None) -> dict:
    """Fetch (or load) the data.cms.gov DCAT catalog."""
    cache = cache or AUDIT_DIR / "cms_datajson.json"
    if cache.exists():
        LOGGER.info("catalog: using cached %s", cache.name)
        return json.loads(cache.read_text())
    LOGGER.info("catalog: fetching %s", CATALOG_URL)
    try:
        with _open_stream(CATALOG_URL) as stream:
            payload = stream.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DownloadUnavailableError(
            f"Could not reach {CATALOG_URL}: {exc}"
            + manual_instructions(CATALOG_URL, cache)
        ) from exc
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(payload)
    return json.loads(payload)


def csv_urls_by_year(catalog: dict, dataset_title: str) -> dict[int, str]:
    """Map data year -> CSV download URL for one CMS dataset in the catalog.

    CMS stamps each distribution title with a temporal end date whose year is
    the data year (e.g. "... : 2023-12-31" is data year 2023).
    """
    import re

    for entry in catalog.get("dataset", []):
        if entry.get("title") != dataset_title:
            continue
        found: dict[int, str] = {}
        for dist in entry.get("distribution", []):
            url = dist.get("downloadURL") or ""
            if not url.endswith(".csv"):
                continue
            match = re.search(r":\s*(\d{4})-\d{2}-\d{2}", dist.get("title", ""))
            if match:
                found[int(match.group(1))] = url
        if found:
            return found
    raise DownloadUnavailableError(
        f"Dataset {dataset_title!r} not found in the CMS catalog."
    )


def stream_filter_prov_svc(
    url: str,
    target: Path,
    codes: Sequence[str] = ALL_CODES,
    keep_columns: Sequence[str] = PROV_SVC_COLUMNS,
) -> Provenance:
    """Stream one by-provider-and-service CSV, keep only study-code rows.

    Filtering is done by *column name* resolved from the file's own header, so
    a change in CMS column order between vintages cannot silently corrupt the
    extract. Returns the provenance record for the cached file.
    """
    code_set = frozenset(codes)
    byte_counter = [0]
    rows_scanned = 0
    rows_kept = 0
    started = datetime.now(timezone.utc)

    tmp = target.with_suffix(target.suffix + ".partial")
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with _open_stream(url) as stream:
            reader = csv.reader(_counting_line_iter(stream, byte_counter))
            header = next(reader)
            missing = [c for c in keep_columns if c not in header]
            if missing:
                raise DownloadUnavailableError(
                    f"{url} is missing expected columns {missing}. "
                    "CMS may have renamed fields; update PROV_SVC_COLUMNS."
                )
            index = {name: header.index(name) for name in keep_columns}
            code_at = header.index("HCPCS_Cd")

            with gzip.open(tmp, "wt", newline="", encoding="utf-8") as out:
                writer = csv.writer(out)
                writer.writerow(keep_columns)
                for row in reader:
                    rows_scanned += 1
                    if rows_scanned % PROGRESS_EVERY_ROWS == 0:
                        LOGGER.info(
                            "  %s: %s rows scanned, %s kept",
                            target.name, f"{rows_scanned:,}", f"{rows_kept:,}",
                        )
                    if len(row) <= code_at or row[code_at] not in code_set:
                        continue
                    rows_kept += 1
                    writer.writerow([row[index[c]] for c in keep_columns])
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadUnavailableError(
            f"Stream failed for {url}: {exc}" + manual_instructions(url, target)
        ) from exc

    tmp.replace(target)
    return Provenance(
        cached_file=target.name,
        source_url=url,
        downloaded_utc=started.isoformat(timespec="seconds"),
        bytes_streamed=byte_counter[0],
        rows_scanned=rows_scanned,
        rows_kept=rows_kept,
        cached_bytes=target.stat().st_size,
        sha256=_sha256_of(target),
    )


def download_whole_csv(url: str, target: Path) -> Provenance:
    """Download a small CSV in full (geography / geographic-variation files)."""
    started = datetime.now(timezone.utc)
    tmp = target.with_suffix(target.suffix + ".partial")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _open_stream(url) as stream, gzip.open(tmp, "wb") as out:
            streamed = 0
            while chunk := stream.read(STREAM_CHUNK_BYTES):
                streamed += len(chunk)
                out.write(chunk)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadUnavailableError(
            f"Download failed for {url}: {exc}" + manual_instructions(url, target)
        ) from exc
    tmp.replace(target)
    with gzip.open(target, "rt", encoding="utf-8", errors="replace") as handle:
        rows = sum(1 for _ in handle) - 1
    return Provenance(
        cached_file=target.name,
        source_url=url,
        downloaded_utc=started.isoformat(timespec="seconds"),
        bytes_streamed=streamed,
        rows_scanned=rows,
        rows_kept=rows,
        cached_bytes=target.stat().st_size,
        sha256=_sha256_of(target),
    )


def _record(provenances: list[Provenance], item: Provenance) -> None:
    provenances.append(item)
    path = AUDIT_DIR / "provenance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [e for e in existing if e["cached_file"] != item.cached_file]
    existing.append(asdict(item))
    path.write_text(json.dumps(existing, indent=1))


def ensure_all(years: Sequence[int] = YEARS) -> list[Provenance]:
    """Download and cache every raw input the analysis needs.

    Idempotent: a cached file is never re-fetched.
    """
    catalog = fetch_catalog()
    prov_svc = csv_urls_by_year(catalog, PROV_SVC_DATASET)
    geo_svc = csv_urls_by_year(catalog, GEO_SVC_DATASET)
    geovar = csv_urls_by_year(catalog, GEOVAR_DATASET)
    provenances: list[Provenance] = []

    missing_years = []
    for year in years:
        if year not in prov_svc:
            raise DownloadUnavailableError(
                f"CMS catalog has no by-provider-and-service file for {year}."
            )
        target = RAW_DIR / f"prov_svc_{year}_studycodes.csv.gz"
        if target.exists():
            LOGGER.info("prov_svc %d: cached", year)
        else:
            missing_years.append(year)

    # The per-year streams are network-bound and independent, so they run
    # concurrently. Each writes to its own .partial file and renames on success.
    if missing_years:
        LOGGER.info("prov_svc: streaming %d year(s) concurrently", len(missing_years))
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_STREAMS) as pool:
            futures = {
                pool.submit(
                    stream_filter_prov_svc,
                    prov_svc[year],
                    RAW_DIR / f"prov_svc_{year}_studycodes.csv.gz",
                ): year
                for year in missing_years
            }
            for future in as_completed(futures):
                year = futures[future]
                record = future.result()
                _record(provenances, record)
                LOGGER.info(
                    "prov_svc %d: done - %s rows scanned, %s kept (%.1f GB streamed)",
                    year, f"{record.rows_scanned:,}", f"{record.rows_kept:,}",
                    record.bytes_streamed / 1e9,
                )

    for year in years:
        if year not in geo_svc:
            LOGGER.warning("no geography-and-service file for %d; skipping", year)
            continue
        target = RAW_DIR / f"geo_svc_{year}.csv.gz"
        if target.exists():
            LOGGER.info("geo_svc %d: cached", year)
            continue
        LOGGER.info("geo_svc %d: downloading", year)
        _record(provenances, download_whole_csv(geo_svc[year], target))

    saipe_year = max(years)
    saipe_url = SAIPE_URL_TEMPLATE.format(year=saipe_year, yy=str(saipe_year)[2:])
    saipe_target = RAW_DIR / f"saipe_{saipe_year}_state_county.txt.gz"
    if saipe_target.exists():
        LOGGER.info("SAIPE %d: cached", saipe_year)
    else:
        LOGGER.info("SAIPE %d: downloading %s", saipe_year, saipe_url)
        _record(provenances, download_whole_csv(saipe_url, saipe_target))

    gv_url = geovar[max(geovar)]
    gv_target = RAW_DIR / "geo_variation_national_state_county.csv.gz"
    if gv_target.exists():
        LOGGER.info("geographic variation: cached")
    else:
        LOGGER.info("geographic variation: downloading %s", gv_url)
        _record(provenances, download_whole_csv(gv_url, gv_target))

    return provenances


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        ensure_all()
    except DownloadUnavailableError as exc:
        LOGGER.error("%s", exc)
        return 1
    LOGGER.info("all raw inputs cached in %s", RAW_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
