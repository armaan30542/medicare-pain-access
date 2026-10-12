"""Shared constants for the PNS access analysis.

All magic numbers, HCPCS code sets, and CMS endpoints live here so that no
downstream module hardcodes a value that a reviewer cannot trace.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final

# ---------------------------------------------------------------- paths
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
RAW_DIR: Final[Path] = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR: Final[Path] = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR: Final[Path] = PROJECT_ROOT / "figures"
AUDIT_DIR: Final[Path] = PROJECT_ROOT / "audit"

# ---------------------------------------------------------------- years
FIRST_YEAR: Final[int] = 2015
LAST_YEAR: Final[int] = 2024
YEARS: Final[tuple[int, ...]] = tuple(range(FIRST_YEAR, LAST_YEAR + 1))
# CPT 62323 was created in the 2017 CPT cycle (it replaced 62311 for lumbar or
# sacral interlaminar epidural injection WITH imaging guidance) and therefore has
# no 2015 or 2016 volume in these files - verified: zero rows for 62323 in the
# 2015 and 2016 provider files. Figure 1 is indexed to 2017, the first year in
# which all three plotted codes exist.
INDEX_BASE_YEAR: Final[int] = 2017

# ------------------------------------------------------------ HCPCS sets
# Primary exposure. In Medicare Part B, 64555 captures the 60-day temporary
# percutaneous PNS pathway (lead placed, no permanent generator implanted).
PNS_CODE: Final[str] = "64555"

ADVANCED_CODES: Final[tuple[str, ...]] = ("64555", "64590", "63650", "63685")
BASIC_CODES: Final[tuple[str, ...]] = ("62323", "64483", "64635")
ALL_CODES: Final[tuple[str, ...]] = ADVANCED_CODES + BASIC_CODES

# Expected long-descriptor keywords, checked token-wise against HCPCS_Desc in
# the downloaded file itself. Verification fails loudly on any mismatch.
# CMS publishes a consumer-friendly descriptor in HCPCS_Desc rather than the
# AMA CPT long descriptor. These token sets were read off the downloaded files
# (verified identical across all of 2015-2024) and are asserted at runtime.
# CMS reworded several descriptors in the 2022 vintage and again in 2024. These
# token sets were chosen to hold across EVERY variant observed in 2015-2024 and
# every variant is asserted at runtime, not just the first one seen.
CODE_EXPECTATIONS: Final[dict[str, tuple[str, ...]]] = {
    "64555": ("peripheral nerve neurostimulator", "electrode", "skin"),
    "64590": ("peripheral", "neurostimulator generator"),
    "63650": ("spinal neurostimulator", "electrode", "skin"),
    "63685": ("spinal neurostimulator", "generator"),
    "62323": ("injection of substance", "canal", "imaging guidance"),
    "64483": ("anesthetic", "nerve root", "imaging guidance"),
    "64635": ("destruction", "facet joint nerves", "imaging guidance"),
}

# The CMS descriptor for 64590 is "Insertion or replacement of peripheral OR
# GASTRIC neurostimulator generator". 64590 therefore is not PNS-specific: it
# also captures gastric electrical stimulators, typically placed by GI surgeons.
# Handled by reporting a sensitivity definition of neuromodulation capability
# that excludes 64590. See RESULTS.md.
NEUROMOD_CODES_STRICT: Final[tuple[str, ...]] = ("64555", "63650", "63685")

CODE_LABELS: Final[dict[str, str]] = {
    "64555": "PNS lead placement (64555)",
    "64590": "PNS/peripheral generator (64590)",
    "63650": "SCS trial lead (63650)",
    "63685": "SCS generator (63685)",
    "62323": "Lumbar epidural steroid injection (62323)",
    "64483": "Lumbar transforaminal ESI (64483)",
    "64635": "Lumbar facet RFA (64635)",
}

# --------------------------------------------------------- CMS structure
# The by-provider-and-service file suppresses provider-code rows with a small
# beneficiary count. Confirmed against the CMS methodology document; see
# DATA_PROVENANCE.md. Concentration measured on the surviving rows is therefore
# a LOWER BOUND on true concentration.
SUPPRESSION_BENE_THRESHOLD: Final[int] = 10

PROV_SVC_COLUMNS: Final[tuple[str, ...]] = (
    "Rndrng_NPI",
    "Rndrng_Prvdr_State_Abrvtn",
    "Rndrng_Prvdr_Zip5",
    "Rndrng_Prvdr_RUCA",
    "Rndrng_Prvdr_Type",
    "HCPCS_Cd",
    "HCPCS_Desc",
    "Place_Of_Srvc",
    "Tot_Benes",
    "Tot_Srvcs",
)

# ------------------------------------------------------------- analysis
RATE_PER: Final[int] = 100_000
BOOTSTRAP_RESAMPLES: Final[int] = 2000
RANDOM_SEED: Final[int] = 20260825
TOP_SHARE_QUANTILE: Final[float] = 0.90       # "top 10% of providers"
DESERT_PROVIDER_THRESHOLD: Final[int] = 3     # "fewer than 3 providers"
CI_LEVEL: Final[float] = 0.95

# SAIPE and the CMS files key on FIPS / postal abbreviation respectively.
STATE_FIPS_TO_ABBR: Final[dict[str, str]] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}

# SAIPE fixed-width layout: median household income estimate, columns 134-140
# (1-indexed, inclusive) of est<yy>all.txt. State rows carry county code "000".
SAIPE_MEDIAN_HH_INCOME_SLICE: Final[slice] = slice(133, 140)
SAIPE_STATE_FIPS_SLICE: Final[slice] = slice(0, 2)
SAIPE_COUNTY_FIPS_SLICE: Final[slice] = slice(3, 6)

# 50 states + DC. Territories and foreign are excluded from state-level models.
STATE_ABBRS: Final[frozenset[str]] = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA "
    "WV WI WY".split()
)
