"""Every BVNA statistic, computed once and written to bvna/audit/results.json.

Method, revised after the PNS audit:
  * Totals and growth come from the GEOGRAPHY file, which is not truncated at
    the provider level, so low-volume providers are counted.
  * Concentration comes from the PROVIDER file restricted to clinicians:
    surgery-centre facility claims are excluded so a case is not counted twice.
  * Every concentration number is reported next to the share of national
    volume the provider file can actually see.
"""
from __future__ import annotations

import gzip
import json
import logging
from typing import Final

import numpy as np
import pandas as pd

from src.analysis import bootstrap_gini_ci, gini, lorenz_points, top_share
from src.bvna.config import (
    BVNA_ADDON,
    BVNA_AUDIT,
    BVNA_CODES,
    BVNA_LEGACY,
    BVNA_PRIMARY,
    BVNA_RAW,
    COMPARATORS,
    COMPARISON_ORDER,
    DESERT_THRESHOLD,
    EXPECTED_TOKENS,
    FACILITY_PROVIDER_TYPES,
    LATEST,
    RUCA_URBAN_MAX,
    SPECIALTY_BUCKETS,
    YEARS,
)
from src.constants import PROCESSED_DIR, RAW_DIR, RATE_PER, STATE_ABBRS

LOGGER: Final = logging.getLogger(__name__)
ALL_CODES: Final[tuple[str, ...]] = BVNA_CODES + tuple(COMPARATORS)
PROV_COLUMNS: Final[list[str]] = [
    "Rndrng_NPI", "Rndrng_Prvdr_State_Abrvtn", "Rndrng_Prvdr_RUCA",
    "Rndrng_Prvdr_Type", "HCPCS_Cd", "HCPCS_Desc", "Place_Of_Srvc",
    "Tot_Benes", "Tot_Srvcs",
]


# ------------------------------------------------------------------ loading
def load_provider_rows() -> pd.DataFrame:
    """BVNA rows from the API cache plus comparator rows from the PNS cache."""
    frames: list[pd.DataFrame] = []
    for year in YEARS:
        api = pd.DataFrame(json.load(gzip.open(BVNA_RAW / f"bvna_prov_svc_{year}.json.gz")))
        api = api[PROV_COLUMNS].assign(year=year)
        stream = pd.read_csv(RAW_DIR / f"prov_svc_{year}_studycodes.csv.gz", dtype=str)
        stream = stream.loc[stream["HCPCS_Cd"].isin(COMPARATORS), PROV_COLUMNS].assign(year=year)
        frames += [api, stream]
    rows = pd.concat(frames, ignore_index=True)
    rows["Tot_Srvcs"] = pd.to_numeric(rows["Tot_Srvcs"], errors="raise")
    rows["Tot_Benes"] = pd.to_numeric(rows["Tot_Benes"], errors="raise")
    rows["ruca"] = pd.to_numeric(rows["Rndrng_Prvdr_RUCA"], errors="coerce")
    rows["is_facility"] = rows["Rndrng_Prvdr_Type"].isin(FACILITY_PROVIDER_TYPES)
    return rows


def load_geography(years: tuple[int, ...]) -> pd.DataFrame:
    """National and state rows for every study code from the geography files."""
    wanted = set(ALL_CODES) | {BVNA_LEGACY}
    frames: list[pd.DataFrame] = []
    for year in years:
        frame = pd.read_csv(RAW_DIR / f"geo_svc_{year}.csv.gz", dtype=str,
                            usecols=["Rndrng_Prvdr_Geo_Lvl", "Rndrng_Prvdr_Geo_Desc",
                                     "HCPCS_Cd", "HCPCS_Desc", "Place_Of_Srvc",
                                     "Tot_Rndrng_Prvdrs", "Tot_Benes", "Tot_Srvcs"])
        frame = frame.loc[frame["HCPCS_Cd"].isin(wanted)].assign(year=year)
        frames.append(frame)
    geo = pd.concat(frames, ignore_index=True)
    for column in ("Tot_Rndrng_Prvdrs", "Tot_Benes", "Tot_Srvcs"):
        geo[column] = pd.to_numeric(geo[column], errors="raise")
    return geo


def state_name_to_abbr() -> dict[str, str]:
    from src.clean import STATE_NAME_BY_ABBR
    return {name: abbr for abbr, name in STATE_NAME_BY_ABBR.items()}


# ----------------------------------------------------------------- checks
def verify_descriptors(rows: pd.DataFrame, geo: pd.DataFrame) -> list[dict]:
    """Confirm 64628/64629 by their own descriptors in both CMS files."""
    table: list[dict] = []
    for code, tokens in EXPECTED_TOKENS.items():
        descriptors = set(rows.loc[rows["HCPCS_Cd"] == code, "HCPCS_Desc"]) | \
            set(geo.loc[geo["HCPCS_Cd"] == code, "HCPCS_Desc"])
        missing = sorted({t for d in descriptors for t in tokens if t not in d.lower()})
        years = sorted(set(geo.loc[geo["HCPCS_Cd"] == code, "year"]))
        table.append({"code": code, "descriptor": max(descriptors, key=len) if descriptors else "",
                      "years": years, "status": "FAIL" if missing or not descriptors else "PASS",
                      "missing_tokens": missing})
        if missing or not descriptors:
            raise ValueError(f"Descriptor check failed for {code}: {missing or 'absent'}")
    return table


# ---------------------------------------------------------------- analyses
def national(geo: pd.DataFrame) -> pd.DataFrame:
    """National services, beneficiaries and provider entries per code-year."""
    nat = geo.loc[geo["Rndrng_Prvdr_Geo_Lvl"] == "National"]
    out = nat.groupby(["year", "HCPCS_Cd"], as_index=False).agg(
        services=("Tot_Srvcs", "sum"), benes=("Tot_Benes", "sum"),
        provider_entries_sum=("Tot_Rndrng_Prvdrs", "sum"),
        provider_entries_max=("Tot_Rndrng_Prvdrs", "max"),
    )
    facility = nat.loc[nat["Place_Of_Srvc"] == "F"].groupby(["year", "HCPCS_Cd"])["Tot_Srvcs"].sum()
    out["facility_services"] = out.set_index(["year", "HCPCS_Cd"]).index.map(facility).fillna(0)
    out["pct_facility"] = out["facility_services"] / out["services"] * 100
    return out


def growth(nat: pd.DataFrame, denominators: pd.DataFrame) -> dict:
    """Rates per 100,000 FFS beneficiaries and the 64629:64628 ratio."""
    ffs = denominators.groupby("year")["ffs_benes"].sum()
    frame = nat.copy()
    frame["per_100k"] = frame.apply(lambda r: r["services"] / ffs[r["year"]] * RATE_PER, axis=1)
    by_year: dict[int, dict] = {}
    for year in YEARS:
        block = frame.loc[frame["year"] == year].set_index("HCPCS_Cd")
        primary = float(block.loc[BVNA_PRIMARY, "services"])
        addon = float(block.loc[BVNA_ADDON, "services"]) if BVNA_ADDON in block.index else 0.0
        by_year[year] = {
            "services_64628": primary,
            "services_64629": addon,
            "per_100k_64628": float(block.loc[BVNA_PRIMARY, "per_100k"]),
            "per_100k_64629": float(block.loc[BVNA_ADDON, "per_100k"]) if addon else 0.0,
            "addon_ratio": addon / primary if primary else float("nan"),
            "benes_64628": float(block.loc[BVNA_PRIMARY, "benes"]),
            "ffs_benes": float(ffs[year]),
        }
    first, last = by_year[YEARS[0]], by_year[YEARS[-1]]
    comparator_growth = {}
    for code in COMPARISON_ORDER:
        series = frame.loc[frame["HCPCS_Cd"] == code].set_index("year")["per_100k"]
        comparator_growth[code] = {
            "per_100k": {int(y): float(v) for y, v in series.items() if y in YEARS},
            "pct_change": float((series[YEARS[-1]] / series[YEARS[0]] - 1) * 100),
        }
    return {
        "by_year": by_year,
        "fold_change_64628": last["services_64628"] / first["services_64628"],
        "pct_change_rate_64628": (last["per_100k_64628"] / first["per_100k_64628"] - 1) * 100,
        "comparators": comparator_growth,
    }


def growth_robustness(rows: pd.DataFrame) -> dict:
    """Growth counted from clinician claims only, which cannot double-count a
    case the way the geography total can when a surgery centre also bills it."""
    out: dict[int, dict] = {}
    for year in YEARS:
        block = rows.loc[(rows["HCPCS_Cd"] == BVNA_PRIMARY) & (rows["year"] == year)]
        facility = float(block.loc[block["is_facility"], "Tot_Srvcs"].sum())
        clinician = float(block.loc[~block["is_facility"], "Tot_Srvcs"].sum())
        out[year] = {"clinician_services": clinician,
                     "facility_share_pct": facility / (facility + clinician) * 100}
    out_fold = out[YEARS[-1]]["clinician_services"] / out[YEARS[0]]["clinician_services"]
    return {"by_year": out, "clinician_fold_change": out_fold}


def legacy_code(geo: pd.DataFrame) -> dict:
    """Pre-2022 BVNA billing under C9752 (facility-only HCPCS Level II)."""
    legacy = load_geography((2019, 2020, 2021, 2022))
    nat = legacy.loc[(legacy["Rndrng_Prvdr_Geo_Lvl"] == "National")
                     & (legacy["HCPCS_Cd"] == BVNA_LEGACY)]
    by_year = nat.groupby("year")["Tot_Srvcs"].sum()
    desc = nat["HCPCS_Desc"].iloc[0] if len(nat) else ""
    return {"code": BVNA_LEGACY, "descriptor": desc,
            "services_by_year": {int(y): float(v) for y, v in by_year.items()},
            "years_present": sorted(int(y) for y in by_year.index)}


def concentration(rows: pd.DataFrame, nat: pd.DataFrame, code: str, year: int) -> dict:
    """Clinician-only concentration among visible billers, plus coverage."""
    block = rows.loc[(rows["HCPCS_Cd"] == code) & (rows["year"] == year)]
    clinicians = block.loc[~block["is_facility"]]
    per_npi = clinicians.groupby("Rndrng_NPI")["Tot_Srvcs"].sum().to_numpy(float)
    nat_row = nat.loc[(nat["HCPCS_Cd"] == code) & (nat["year"] == year)].iloc[0]
    low, high = bootstrap_gini_ci(per_npi)
    x, y = lorenz_points(per_npi)
    return {
        "code": code, "year": year,
        "visible_clinicians": int(per_npi.size),
        "visible_facility_npis": int(block.loc[block["is_facility"], "Rndrng_NPI"].nunique()),
        "visible_services_all": float(block["Tot_Srvcs"].sum()),
        "visible_services_clinicians": float(per_npi.sum()),
        "national_services": float(nat_row["services"]),
        "share_visible_pct": float(block["Tot_Srvcs"].sum() / nat_row["services"] * 100),
        "national_provider_entries_low": int(nat_row["provider_entries_max"]),
        "national_provider_entries_high": int(nat_row["provider_entries_sum"]),
        "gini": gini(per_npi), "gini_ci_low": low, "gini_ci_high": high,
        "top10_share_pct": top_share(per_npi) * 100,
        "median_services_per_clinician": float(np.median(per_npi)),
        "lorenz_x": x.tolist(), "lorenz_y": y.tolist(),
    }


def deserts(geo: pd.DataFrame, denominators: pd.DataFrame,
            rows: pd.DataFrame) -> list[dict]:
    """BVNA access deserts, bracketed by two views of the same question.

    GEOGRAPHY view (lower bound on deserts): the geography file counts
    low-volume providers, but it drops any state row under 11 beneficiaries
    (verified: minimum on any state row is exactly 11). A state with no row
    therefore had fewer than 11 Medicare beneficiaries receive BVNA - possibly
    zero, possibly a handful. Provider entries are summed across facility and
    office rows, an upper bound on distinct providers.

    PROVIDER-FILE view (upper bound on deserts): states with no provider of any
    kind visible above the provider-level floor.
    """
    names = state_name_to_abbr()
    state = geo.loc[(geo["Rndrng_Prvdr_Geo_Lvl"] == "State") & (geo["HCPCS_Cd"] == BVNA_PRIMARY)].copy()
    state["state"] = state["Rndrng_Prvdr_Geo_Desc"].map(lambda d: names.get(d, d))
    out: list[dict] = []
    for year in YEARS:
        counts = (state.loc[state["year"] == year].groupby("state")["Tot_Rndrng_Prvdrs"].sum())
        den = denominators.loc[denominators["year"] == year].set_index("state")["ffs_benes"]
        den = den.loc[den.index.isin(STATE_ABBRS)]
        providers = pd.Series({s: float(counts.get(s, 0)) for s in den.index})
        zero = providers.loc[providers == 0]
        sparse = providers.loc[providers < DESERT_THRESHOLD]
        visible = rows.loc[(rows["HCPCS_Cd"] == BVNA_PRIMARY) & (rows["year"] == year)]
        visible_counts = visible.groupby("Rndrng_Prvdr_State_Abrvtn")["Rndrng_NPI"].nunique()
        visible_zero = [s for s in den.index if visible_counts.get(s, 0) == 0]
        visible_sparse = [s for s in den.index if visible_counts.get(s, 0) < DESERT_THRESHOLD]
        out.append({
            "year": year,
            "provider_view_states_zero": len(visible_zero),
            "provider_view_states_sparse": len(visible_sparse),
            "provider_view_pct_benes_sparse": float(den[visible_sparse].sum() / den.sum() * 100),
            "provider_view_benes_sparse": int(den[visible_sparse].sum()),
            "states_zero": int(len(zero)),
            "states_sparse": int(len(sparse)),
            "pct_benes_zero": float(den[zero.index].sum() / den.sum() * 100),
            "pct_benes_sparse": float(den[sparse.index].sum() / den.sum() * 100),
            "benes_sparse": int(den[sparse.index].sum()),
            "zero_states": sorted(zero.index.tolist()),
        })
    return out


def specialty_mix(rows: pd.DataFrame, code: str, year: int) -> dict:
    """Share of visible clinician services and clinicians by requested specialty."""
    block = rows.loc[(rows["HCPCS_Cd"] == code) & (rows["year"] == year) & ~rows["is_facility"]]
    lookup = {t: bucket for bucket, types in SPECIALTY_BUCKETS.items() for t in types}
    bucket = block["Rndrng_Prvdr_Type"].map(lambda t: lookup.get(t, "Other"))
    services = block.groupby(bucket)["Tot_Srvcs"].sum()
    clinicians = block.groupby(bucket)["Rndrng_NPI"].nunique()
    order = list(SPECIALTY_BUCKETS) + ["Other"]
    total = services.sum()
    other_types = (block.loc[bucket == "Other"].groupby("Rndrng_Prvdr_Type")["Tot_Srvcs"]
                   .sum().sort_values(ascending=False))
    return {
        "code": code, "year": year,
        "services_pct": {b: float(services.get(b, 0) / total * 100) for b in order},
        "clinicians": {b: int(clinicians.get(b, 0)) for b in order},
        "other_types": {k: float(v) for k, v in other_types.head(5).items()},
    }


def rurality(rows: pd.DataFrame, code: str, year: int) -> dict:
    """Share of visible clinician services from providers outside metro areas."""
    block = rows.loc[(rows["HCPCS_Cd"] == code) & (rows["year"] == year) & ~rows["is_facility"]]
    known = block.dropna(subset=["ruca"])
    rural = known.loc[known["ruca"] > RUCA_URBAN_MAX]
    return {
        "code": code, "year": year,
        "pct_services_nonmetro": float(rural["Tot_Srvcs"].sum() / known["Tot_Srvcs"].sum() * 100),
        "nonmetro_clinicians": int(rural["Rndrng_NPI"].nunique()),
        "clinicians_with_ruca": int(known["Rndrng_NPI"].nunique()),
    }


def medicare_advantage(year: int) -> dict:
    """Medicare Advantage share by state - the population these files cannot see."""
    with gzip.open(RAW_DIR / "geo_variation_national_state_county.csv.gz", "rt",
                   encoding="utf-8", errors="replace") as handle:
        frame = pd.read_csv(handle, low_memory=False,
                            usecols=["YEAR", "BENE_GEO_LVL", "BENE_GEO_DESC",
                                     "BENE_AGE_LVL", "MA_PRTCPTN_RATE"])
    frame = frame.loc[(frame["YEAR"] == year) & (frame["BENE_AGE_LVL"] == "All")]
    nat = frame.loc[frame["BENE_GEO_LVL"] == "National", "MA_PRTCPTN_RATE"]
    states = frame.loc[(frame["BENE_GEO_LVL"] == "State")
                       & frame["BENE_GEO_DESC"].isin(STATE_ABBRS)]
    states = states.assign(ma=pd.to_numeric(states["MA_PRTCPTN_RATE"]) * 100).sort_values("ma")
    return {
        "year": year,
        "national_pct": float(pd.to_numeric(nat).iloc[0]) * 100,
        "highest": [(s, float(v)) for s, v in states[["BENE_GEO_DESC", "ma"]].tail(3).iloc[::-1].values],
        "lowest": [(s, float(v)) for s, v in states[["BENE_GEO_DESC", "ma"]].head(3).values],
        "states_over_half": int((states["ma"] > 50).sum()),
    }


def run() -> dict:
    rows = load_provider_rows()
    geo = load_geography(YEARS)
    denominators = pd.read_parquet(PROCESSED_DIR / "denominators.parquet")
    nat = national(geo)

    results = {
        "years": list(YEARS), "latest": LATEST,
        "descriptors": verify_descriptors(rows, geo),
        "legacy": legacy_code(geo),
        "growth": growth(nat, denominators),
        "growth_robustness": growth_robustness(rows),
        "concentration": {c: concentration(rows, nat, c, LATEST) for c in COMPARISON_ORDER},
        "deserts": deserts(geo, denominators, rows),
        "specialty": {c: specialty_mix(rows, c, LATEST) for c in ("64628", "64635")},
        "rurality": {c: rurality(rows, c, LATEST) for c in COMPARISON_ORDER},
        "setting": {c: float(nat.loc[(nat["HCPCS_Cd"] == c) & (nat["year"] == LATEST),
                                     "pct_facility"].iloc[0]) for c in COMPARISON_ORDER},
        "medicare_advantage": medicare_advantage(LATEST),
    }
    BVNA_AUDIT.mkdir(parents=True, exist_ok=True)
    (BVNA_AUDIT / "results.json").write_text(json.dumps(results, indent=1, default=str))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = run()
    g = r["growth"]
    print("DESCRIPTORS:", [(d["code"], d["status"], d["years"]) for d in r["descriptors"]])
    print("LEGACY:", r["legacy"]["code"], r["legacy"]["services_by_year"])
    print("\nGROWTH (geography file, unsuppressed):")
    for y, v in g["by_year"].items():
        print(f"  {y}: 64628 {v['services_64628']:>7,.0f} svc ({v['per_100k_64628']:.1f}/100k) | "
              f"64629 {v['services_64629']:>6,.0f} | add-on ratio {v['addon_ratio']:.3f}")
    print(f"  64628 rate change {YEARS[0]}->{YEARS[-1]}: {g['pct_change_rate_64628']:+.0f}%")
    for c, v in g["comparators"].items(): print(f"    {c} rate change: {v['pct_change']:+.1f}%")
    print("\nCONCENTRATION (clinicians only, visible in provider file):")
    for c, v in r["concentration"].items():
        print(f"  {c}: visible clinicians {v['visible_clinicians']:>5,} (+{v['visible_facility_npis']} ASCs) | "
              f"share visible {v['share_visible_pct']:5.1f}% | national entries {v['national_provider_entries_low']:,}-{v['national_provider_entries_high']:,} | "
              f"Gini {v['gini']:.3f} [{v['gini_ci_low']:.3f},{v['gini_ci_high']:.3f}] | top10 {v['top10_share_pct']:.1f}% | median svc {v['median_services_per_clinician']:.0f}")
    print("\nDESERTS:")
    for d in r["deserts"]:
        print(f"  {d['year']}: zero={d['states_zero']} sparse(<3)={d['states_sparse']} "
              f"%benes zero={d['pct_benes_zero']:.1f} %benes sparse={d['pct_benes_sparse']:.1f}  zero states={d['zero_states']}")
    print("\nSPECIALTY (BVNA, % visible clinician services):", {k: round(v,1) for k,v in r["specialty"]["64628"]["services_pct"].items()})
    print("  other types:", r["specialty"]["64628"]["other_types"])
    print("SPECIALTY (RFA 64635):", {k: round(v,1) for k,v in r["specialty"]["64635"]["services_pct"].items()})
    print("\nSETTING % facility:", {k: round(v,1) for k,v in r["setting"].items()})
    print("RURALITY % non-metro services:", {k: round(v["pct_services_nonmetro"],1) for k,v in r["rurality"].items()})
    print("\nMEDICARE ADVANTAGE:", r["medicare_advantage"])
