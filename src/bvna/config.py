"""Constants for the BVNA (basivertebral nerve ablation) access analysis.

Shares the PNS project's data cache and denominators, but every output lands
under bvna/ so the two analyses never overwrite each other.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final

from src.constants import PROJECT_ROOT, RAW_DIR

BVNA_ROOT: Final[Path] = PROJECT_ROOT / "bvna"
BVNA_FIGURES: Final[Path] = BVNA_ROOT / "figures"
BVNA_AUDIT: Final[Path] = BVNA_ROOT / "audit"
BVNA_RAW: Final[Path] = RAW_DIR / "bvna_api"

YEARS: Final[tuple[int, ...]] = (2022, 2023, 2024)
LATEST: Final[int] = 2024

# CPT 64628 / 64629 took effect 1 January 2022. Before that, BVNA was billed
# under facility-only HCPCS Level II code C9752 (verified in the 2020 and 2021
# geography files: 28 and 325 national services; absent from 2022 on).
BVNA_PRIMARY: Final[str] = "64628"     # first two vertebral bodies
BVNA_ADDON: Final[str] = "64629"       # each additional vertebral body
BVNA_CODES: Final[tuple[str, ...]] = (BVNA_PRIMARY, BVNA_ADDON)
BVNA_LEGACY: Final[str] = "C9752"

# Comparators, already cached from the PNS project for 2015-2024.
COMPARATORS: Final[dict[str, str]] = {
    "64555": "PNS (64555)",
    "64635": "Lumbar facet RFA (64635)",
    "62323": "Lumbar epidural (62323)",
}
LABELS: Final[dict[str, str]] = {"64628": "BVNA (64628)", **COMPARATORS}
COMPARISON_ORDER: Final[tuple[str, ...]] = ("64628", "64555", "64635", "62323")

EXPECTED_TOKENS: Final[dict[str, tuple[str, ...]]] = {
    "64628": ("basivertebral", "first two"),
    "64629": ("basivertebral", "additional"),
}

# Verified per-year API datasets for "by Provider and Service". 2024 is served
# under two identifiers; both are checked and must agree (see fetch.py).
API_DATASETS: Final[dict[int, tuple[str, ...]]] = {
    2022: ("e650987d-01b7-4f09-b75e-b0b075afbf98",),
    2023: ("0e9f2f2b-7bf9-451a-912c-e02e654dd725",),
    2024: ("92396110-2aed-4d63-a6a2-5d6207d46a29",
           "335e5f35-eca6-482d-87b3-f99883e213e3"),
}

# Rendering-provider types that are facilities, not clinicians. A surgery
# centre files its own claim for a case a physician also bills, so counting it
# double-counts the procedure and inflates the provider count.
FACILITY_PROVIDER_TYPES: Final[frozenset[str]] = frozenset({
    "Ambulatory Surgical Center",
    "Independent Diagnostic Testing Facility (IDTF)",
    "Clinical Laboratory",
})

# Specialty buckets requested in the brief, mapped from Rndrng_Prvdr_Type.
SPECIALTY_BUCKETS: Final[dict[str, tuple[str, ...]]] = {
    "Pain medicine": ("Pain Management", "Interventional Pain Management"),
    "Anesthesiology": ("Anesthesiology", "Certified Registered Nurse Anesthetist (CRNA)"),
    "PM&R": ("Physical Medicine and Rehabilitation",),
    "Interventional radiology": ("Interventional Radiology", "Diagnostic Radiology"),
    "Orthopedics": ("Orthopedic Surgery",),
    "Neurosurgery": ("Neurosurgery",),
}

# RUCA 1-3 = metropolitan; 4-10 = micropolitan, small town or rural.
RUCA_URBAN_MAX: Final[float] = 3.99

DESERT_THRESHOLD: Final[int] = 3
API_PAGE_SIZE: Final[int] = 1000
API_TIMEOUT_S: Final[int] = 90
API_PAUSE_S: Final[float] = 0.3
