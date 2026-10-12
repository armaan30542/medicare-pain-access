"""BVNA novelty search via NCBI E-utilities, cached to bvna/audit/novelty_raw.json.

The cache is committed so the deck's novelty slide is reproducible: PubMed
grows daily, so re-querying would silently change the counts. Delete the cache
to deliberately refresh it.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Final

import certifi

from src.bvna.config import BVNA_AUDIT

CACHE: Final = BVNA_AUDIT / "novelty_raw.json"
BASE: Final[str] = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PAUSE_S: Final[float] = 0.4
RETMAX: Final[int] = 40
CTX: Final = ssl.create_default_context(cafile=certifi.where())

QUERIES: Final[dict[str, str]] = {
    "Q1_bvna_any": "basivertebral[Title/Abstract]",
    "Q2_bvna_access": 'basivertebral[Title/Abstract] AND (Medicare OR utilization OR access '
                      'OR disparities OR geographic OR trends OR "real-world")',
    "Q3_bvna_codes": '"64628" OR "64629" OR "C9752"',
    "Q4_bvna_payer": 'basivertebral[Title/Abstract] AND (insurance OR payer OR coverage OR '
                     '"prior authorization" OR "Medicare Advantage")',
}


def _params() -> dict[str, str]:
    """NCBI asks callers to identify themselves; the email comes from the
    environment so it is never committed."""
    params = {"tool": "medicare-access-pipeline"}
    if os.environ.get("NCBI_EMAIL"):
        params["email"] = os.environ["NCBI_EMAIL"]
    return params


def _get(endpoint: str, **query: object) -> bytes:
    time.sleep(PAUSE_S)
    url = f"{BASE}{endpoint}?{urllib.parse.urlencode({**_params(), **query})}"
    with urllib.request.urlopen(url, timeout=60, context=CTX) as response:
        return response.read()


def fetch() -> dict:
    out: dict = {}
    for key, term in QUERIES.items():
        found = json.loads(_get("esearch.fcgi", db="pubmed", term=term, retmax=RETMAX,
                                retmode="json"))["esearchresult"]
        ids = found.get("idlist", [])
        records = []
        if ids:
            root = ET.fromstring(_get("esummary.fcgi", db="pubmed", id=",".join(ids), retmode="xml"))
            for doc in root.findall(".//DocSum"):
                items = {i.get("Name"): "".join(i.itertext()) for i in doc.findall("Item")}
                records.append({"pmid": doc.findtext("Id"), "date": items.get("PubDate"),
                                "journal": items.get("Source"), "title": items.get("Title")})
        out[key] = {"query": term, "count": int(found["count"]), "records": records}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(out, indent=1))
    return out


def load_or_fetch() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else fetch()
