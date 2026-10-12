"""Turn the cached raw files into tidy, analysis-ready tables.

Outputs (all written to data/processed/):
  prov_svc_study.parquet    provider x code x year, study codes only
  denominators.parquet      state x year FFS beneficiary count, dual %, risk
  income.parquet            state median household income (SAIPE)
  state_year_panel.parquet  the modelling panel for Figure 4
  national_by_code.parquet  national service/provider counts per code-year

Nothing here imputes, simulates, or back-fills. A missing input raises.
"""
from __future__ import annotations

import gzip
import logging
from pathlib import Path
from typing import Final

import pandas as pd

from src.constants import (
    ADVANCED_CODES,
    ALL_CODES,
    BASIC_CODES,
    CODE_EXPECTATIONS,
    PNS_CODE,
    PROCESSED_DIR,
    RAW_DIR,
    SAIPE_COUNTY_FIPS_SLICE,
    SAIPE_MEDIAN_HH_INCOME_SLICE,
    SAIPE_STATE_FIPS_SLICE,
    STATE_ABBRS,
    STATE_FIPS_TO_ABBR,
    YEARS,
)

LOGGER: Final = logging.getLogger(__name__)

# Geographic Variation file selectors.
GEO_LEVEL_STATE: Final[str] = "State"
AGE_LEVEL_ALL: Final[str] = "All"
FFS_BENE_COLUMN: Final[str] = "BENES_OM_CNT"        # Original (fee-for-service) Medicare
DUAL_PCT_COLUMN: Final[str] = "BENE_DUAL_PCT"
TOTAL_BENE_COLUMN: Final[str] = "BENES_TOTAL_CNT"


class DataIntegrityError(RuntimeError):
    """Raised when a required file or column is missing or fails a check."""


def _require(path: Path) -> Path:
    if not path.exists():
        raise DataIntegrityError(
            f"Required input {path} is missing. Run `python run.py` to download it."
        )
    return path


# ------------------------------------------------------------------ codes
def verify_hcpcs_descriptions(prov_svc: pd.DataFrame) -> pd.DataFrame:
    """Check every study code's HCPCS_Desc against expected tokens.

    Returns the verification table. Raises DataIntegrityError on any mismatch,
    because silently analysing the wrong code would invalidate every figure.
    """
    rows: list[dict[str, object]] = []
    for code in ALL_CODES:
        descriptions = (
            prov_svc.loc[prov_svc["hcpcs_code"] == code, "hcpcs_desc"].unique().tolist()
        )
        if not descriptions:
            raise DataIntegrityError(f"Code {code} has no rows in the downloaded data.")
        expected = CODE_EXPECTATIONS[code]
        # Every observed wording must pass, not merely the first one seen: CMS
        # reworded these descriptors in 2022 and again in 2024.
        missing = sorted({
            token
            for description in descriptions
            for token in expected
            if token.lower() not in description.lower()
        })
        years_present = sorted(
            prov_svc.loc[prov_svc["hcpcs_code"] == code, "year"].unique().tolist()
        )
        rows.append(
            {
                "hcpcs_code": code,
                "tier": "ADVANCED" if code in ADVANCED_CODES else "BASIC",
                "hcpcs_desc_from_file": max(descriptions, key=len),
                "expected_tokens": ", ".join(expected),
                "missing_tokens": ", ".join(missing) if missing else "-",
                "status": "FAIL" if missing else "PASS",
                "n_distinct_desc": len(descriptions),
                "years_present": f"{min(years_present)}-{max(years_present)}",
            }
        )
    table = pd.DataFrame(rows)
    failures = table.loc[table["status"] == "FAIL"]
    if not failures.empty:
        raise DataIntegrityError(
            "HCPCS descriptor verification FAILED for: "
            + ", ".join(failures["hcpcs_code"])
            + ". Refusing to proceed with possibly-wrong codes."
        )
    return table


# ----------------------------------------------------------- provider file
def load_prov_svc(years: tuple[int, ...] = YEARS) -> pd.DataFrame:
    """Load and concatenate the cached, code-filtered provider-service extracts."""
    frames: list[pd.DataFrame] = []
    for year in years:
        path = _require(RAW_DIR / f"prov_svc_{year}_studycodes.csv.gz")
        frame = pd.read_csv(
            path,
            dtype={
                "Rndrng_NPI": "string",
                "Rndrng_Prvdr_State_Abrvtn": "string",
                "Rndrng_Prvdr_Zip5": "string",
                "Rndrng_Prvdr_RUCA": "string",
                "Rndrng_Prvdr_Type": "string",
                "HCPCS_Cd": "string",
                "HCPCS_Desc": "string",
                "Place_Of_Srvc": "string",
            },
        )
        frame["year"] = year
        frames.append(frame)
        LOGGER.info("prov_svc %d: %s rows", year, f"{len(frame):,}")

    data = pd.concat(frames, ignore_index=True)
    data = data.rename(
        columns={
            "Rndrng_NPI": "npi",
            "Rndrng_Prvdr_State_Abrvtn": "state",
            "Rndrng_Prvdr_Zip5": "zip5",
            "Rndrng_Prvdr_RUCA": "ruca",
            "Rndrng_Prvdr_Type": "provider_type",
            "HCPCS_Cd": "hcpcs_code",
            "HCPCS_Desc": "hcpcs_desc",
            "Place_Of_Srvc": "place_of_service",
            "Tot_Benes": "total_benes",
            "Tot_Srvcs": "total_services",
        }
    )
    data["total_services"] = pd.to_numeric(data["total_services"], errors="raise")
    data["total_benes"] = pd.to_numeric(data["total_benes"], errors="raise")

    if (data["total_services"] < 0).any() or (data["total_benes"] < 0).any():
        raise DataIntegrityError("Negative service or beneficiary counts in raw data.")
    unexpected = set(data["hcpcs_code"].unique()) - set(ALL_CODES)
    if unexpected:
        raise DataIntegrityError(f"Unexpected HCPCS codes in extract: {unexpected}")
    return data


def collapse_provider_year_code(prov_svc: pd.DataFrame) -> pd.DataFrame:
    """Sum services across place-of-service so one row = provider x code x year.

    CMS splits each provider-code pair into facility and non-facility rows. A
    provider who bills both would otherwise be counted twice in a Lorenz curve.
    """
    collapsed = (
        prov_svc.groupby(["year", "hcpcs_code", "npi", "state"], as_index=False, observed=True)
        .agg(total_services=("total_services", "sum"),
             total_benes=("total_benes", "sum"))
    )
    return collapsed


# ------------------------------------------------------------ denominators
def load_denominators() -> pd.DataFrame:
    """State x year FFS beneficiary counts, dual-eligible share, from CMS.

    Uses BENE_GEO_LVL == "State" and BENE_AGE_LVL == "All". The fee-for-service
    denominator is BENES_OM_CNT (Original Medicare), which is the population the
    Part B claims in the provider file can actually come from.
    """
    path = _require(RAW_DIR / "geo_variation_national_state_county.csv.gz")
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        frame = pd.read_csv(handle, low_memory=False)

    needed = {"YEAR", "BENE_GEO_LVL", "BENE_GEO_DESC", "BENE_AGE_LVL",
              FFS_BENE_COLUMN, DUAL_PCT_COLUMN, TOTAL_BENE_COLUMN}
    missing = needed - set(frame.columns)
    if missing:
        raise DataIntegrityError(f"Geographic Variation file missing columns: {missing}")

    state = frame.loc[
        (frame["BENE_GEO_LVL"] == GEO_LEVEL_STATE)
        & (frame["BENE_AGE_LVL"] == AGE_LEVEL_ALL)
    ].copy()

    # BENE_GEO_DESC carries the two-letter postal abbreviation at the State
    # level (verified against the file); full names appear only at other levels.
    state["state"] = state["BENE_GEO_DESC"].astype("string").str.strip()
    state = state.loc[state["state"].isin(STATE_ABBRS)]
    if state.empty:
        raise DataIntegrityError(
            "No state rows survived the Geographic Variation filter; "
            "BENE_GEO_DESC may have changed format."
        )

    out = state.rename(
        columns={
            "YEAR": "year",
            FFS_BENE_COLUMN: "ffs_benes",
            DUAL_PCT_COLUMN: "dual_pct",
            TOTAL_BENE_COLUMN: "total_benes_all",
        }
    )[["year", "state", "ffs_benes", "dual_pct", "total_benes_all"]]
    out["year"] = pd.to_numeric(out["year"], errors="raise").astype(int)
    for column in ("ffs_benes", "dual_pct", "total_benes_all"):
        out[column] = pd.to_numeric(out[column], errors="coerce")

    # CMS publishes BENE_DUAL_PCT as a proportion (0.2381); express as percent.
    out["dual_pct"] = out["dual_pct"] * 100.0

    if out["ffs_benes"].isna().any():
        raise DataIntegrityError("Missing FFS beneficiary counts after cleaning.")
    if (out["ffs_benes"] <= 0).any():
        raise DataIntegrityError("Non-positive FFS beneficiary count encountered.")
    return out.reset_index(drop=True)


# Retained for readable labelling in figures.
STATE_NAME_BY_ABBR: Final[dict[str, str]] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


def load_income(year: int) -> pd.DataFrame:
    """State median household income from the SAIPE fixed-width file."""
    path = _require(RAW_DIR / f"saipe_{year}_state_county.txt.gz")
    records: list[dict[str, object]] = []
    with gzip.open(path, "rt", encoding="latin-1") as handle:
        for line in handle:
            if line[SAIPE_COUNTY_FIPS_SLICE].strip() != "0":
                continue  # keep state-level rows only (county code 000)
            abbr = STATE_FIPS_TO_ABBR.get(line[SAIPE_STATE_FIPS_SLICE])
            if abbr is None:
                continue
            raw = line[SAIPE_MEDIAN_HH_INCOME_SLICE].strip().replace(",", "")
            if not raw.isdigit():
                raise DataIntegrityError(
                    f"SAIPE median-income field did not parse for {abbr}: {raw!r}"
                )
            records.append({"state": abbr, "median_hh_income": int(raw),
                            "income_year": year})
    frame = pd.DataFrame(records)
    if len(frame) != len(STATE_ABBRS):
        raise DataIntegrityError(
            f"SAIPE gave {len(frame)} states, expected {len(STATE_ABBRS)}."
        )
    if (frame["median_hh_income"] < 20_000).any() or (frame["median_hh_income"] > 200_000).any():
        raise DataIntegrityError("SAIPE income values outside a plausible range.")
    return frame


# ------------------------------------------------------------------ panel
def build_state_year_panel(
    collapsed: pd.DataFrame, denominators: pd.DataFrame
) -> pd.DataFrame:
    """Balanced state x year panel with the covariates Figure 4 needs.

    Provider-density terms are defined by *billing*, not by self-reported
    specialty: a "general interventional pain provider" is an NPI that billed
    any BASIC code in that state-year; a "neuromodulation-capable provider" is
    an NPI that billed any ADVANCED code. This keeps both exposures on the same
    footing and inside the same file.
    """
    core = collapsed.loc[collapsed["state"].isin(STATE_ABBRS)].copy()

    pns = (
        core.loc[core["hcpcs_code"] == PNS_CODE]
        .groupby(["state", "year"], as_index=False)
        .agg(pns_services=("total_services", "sum"),
             pns_providers=("npi", "nunique"))
    )
    basic = (
        core.loc[core["hcpcs_code"].isin(BASIC_CODES)]
        .groupby(["state", "year"], as_index=False)
        .agg(basic_services=("total_services", "sum"),
             basic_providers=("npi", "nunique"))
    )
    advanced = (
        core.loc[core["hcpcs_code"].isin(ADVANCED_CODES)]
        .groupby(["state", "year"], as_index=False)
        .agg(advanced_services=("total_services", "sum"),
             neuromod_providers=("npi", "nunique"))
    )

    grid = pd.MultiIndex.from_product(
        [sorted(STATE_ABBRS), list(YEARS)], names=["state", "year"]
    ).to_frame(index=False)

    panel = (
        grid.merge(denominators, on=["state", "year"], how="left")
        .merge(pns, on=["state", "year"], how="left")
        .merge(basic, on=["state", "year"], how="left")
        .merge(advanced, on=["state", "year"], how="left")
    )
    # A state-year absent from the provider file has zero *observed* volume.
    # That is a true zero in the published data, which is exactly what Figure 3
    # measures; the suppression caveat is carried in the write-up, not imputed.
    count_columns = [
        "pns_services", "pns_providers", "basic_services", "basic_providers",
        "advanced_services", "neuromod_providers",
    ]
    panel[count_columns] = panel[count_columns].fillna(0).astype(int)

    if panel["ffs_benes"].isna().any():
        gaps = panel.loc[panel["ffs_benes"].isna(), ["state", "year"]]
        raise DataIntegrityError(
            "No FFS denominator for these state-years:\n" + gaps.to_string(index=False)
        )

    panel["basic_density_per_100k"] = (
        panel["basic_providers"] / panel["ffs_benes"] * 100_000
    )
    panel["neuromod_density_per_100k"] = (
        panel["neuromod_providers"] / panel["ffs_benes"] * 100_000
    )
    panel["pns_per_100k"] = panel["pns_services"] / panel["ffs_benes"] * 100_000
    return panel


def national_by_code(collapsed: pd.DataFrame, denominators: pd.DataFrame) -> pd.DataFrame:
    """National services and unique providers per code-year, plus FFS rate."""
    national = (
        collapsed.groupby(["year", "hcpcs_code"], as_index=False)
        .agg(total_services=("total_services", "sum"),
             n_providers=("npi", "nunique"))
    )
    ffs = denominators.groupby("year", as_index=False).agg(ffs_benes=("ffs_benes", "sum"))
    national = national.merge(ffs, on="year", how="left", validate="many_to_one")
    if national["ffs_benes"].isna().any():
        raise DataIntegrityError("Missing national FFS denominator for some year.")
    national["services_per_100k"] = (
        national["total_services"] / national["ffs_benes"] * 100_000
    )
    if (national["services_per_100k"] < 0).any():
        raise DataIntegrityError("Negative rate computed.")
    return national


def run() -> dict[str, pd.DataFrame]:
    """Build every processed table and write it to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    prov_svc = load_prov_svc()
    verification = verify_hcpcs_descriptions(prov_svc)
    collapsed = collapse_provider_year_code(prov_svc)
    denominators = load_denominators()
    income = load_income(max(YEARS))
    panel = build_state_year_panel(collapsed, denominators)
    national = national_by_code(collapsed, denominators)

    tables = {
        "hcpcs_verification": verification,
        "prov_svc_study": collapsed,
        "denominators": denominators,
        "income": income,
        "state_year_panel": panel,
        "national_by_code": national,
    }
    for name, table in tables.items():
        table.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
        LOGGER.info("wrote %s.parquet (%s rows)", name, f"{len(table):,}")
    return tables
