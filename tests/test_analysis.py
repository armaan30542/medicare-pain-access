"""Tests for the statistics and the data contract.

Run with: pytest -q
The data-dependent tests skip cleanly if data/processed is not built yet, so the
pure-maths tests can run in any checkout.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.analysis import bootstrap_gini_ci, gini, lorenz_points, top_share
from src.constants import (
    ALL_CODES,
    CODE_EXPECTATIONS,
    PROCESSED_DIR,
    SUPPRESSION_BENE_THRESHOLD,
)

TABLES = ("hcpcs_verification", "prov_svc_study", "denominators",
          "income", "state_year_panel", "national_by_code")


@pytest.fixture(scope="module")
def tables() -> dict[str, pd.DataFrame]:
    missing = [t for t in TABLES if not (PROCESSED_DIR / f"{t}.parquet").exists()]
    if missing:
        pytest.skip(f"processed tables not built: {missing}. Run `python run.py`.")
    return {t: pd.read_parquet(PROCESSED_DIR / f"{t}.parquet") for t in TABLES}


# --------------------------------------------------------------- Gini maths
def test_gini_is_zero_for_a_uniform_distribution() -> None:
    for n in (2, 10, 500):
        assert gini(np.full(n, 7.0)) == pytest.approx(0.0, abs=1e-12)


def test_gini_approaches_one_for_a_maximally_skewed_distribution() -> None:
    # All volume on a single unit: the theoretical maximum for n units is
    # (n-1)/n, which tends to 1 as n grows.
    for n in (100, 10_000):
        values = np.zeros(n)
        values[0] = 1.0
        assert gini(values) == pytest.approx((n - 1) / n, abs=1e-9)
    assert gini(np.concatenate(([1.0], np.zeros(999_999)))) > 0.999


def test_gini_is_scale_invariant() -> None:
    values = np.array([1.0, 2.0, 3.0, 40.0])
    assert gini(values) == pytest.approx(gini(values * 1000.0))


def test_gini_rejects_degenerate_input() -> None:
    with pytest.raises(ValueError):
        gini([])
    with pytest.raises(ValueError):
        gini([0.0, 0.0])
    with pytest.raises(ValueError):
        gini([-1.0, 2.0])


def test_lorenz_curve_is_monotonic_and_anchored() -> None:
    x, y = lorenz_points([5.0, 1.0, 3.0, 11.0])
    assert x[0] == 0.0 and y[0] == 0.0
    assert x[-1] == pytest.approx(1.0) and y[-1] == pytest.approx(1.0)
    assert np.all(np.diff(y) >= -1e-12)
    assert np.all(y <= x + 1e-12)  # Lorenz curve never rises above equality


def test_top_share_bounds() -> None:
    assert top_share(np.full(100, 1.0)) == pytest.approx(0.10)
    concentrated = np.zeros(100)
    concentrated[-1] = 1.0
    assert top_share(concentrated) == pytest.approx(1.0)


def test_bootstrap_ci_is_deterministic_and_brackets_the_estimate() -> None:
    rng = np.random.default_rng(0)
    values = rng.gamma(shape=1.5, scale=10.0, size=400)
    first = bootstrap_gini_ci(values, resamples=200)
    second = bootstrap_gini_ci(values, resamples=200)
    assert first == second, "bootstrap must be reproducible for a fixed seed"
    low, high = first
    assert low < gini(values) < high
    assert 0.0 <= low < high <= 1.0


# ------------------------------------------------------------ data contract
def test_every_hcpcs_description_matches_expectation(tables) -> None:
    verification = tables["hcpcs_verification"]
    assert set(verification["hcpcs_code"]) == set(ALL_CODES)
    failures = verification.loc[verification["status"] != "PASS"]
    assert failures.empty, f"descriptor mismatch:\n{failures}"
    for row in verification.itertuples():
        description = row.hcpcs_desc_from_file.lower()
        for token in CODE_EXPECTATIONS[row.hcpcs_code]:
            assert token.lower() in description, (row.hcpcs_code, token)


def test_rates_are_non_negative(tables) -> None:
    national = tables["national_by_code"]
    assert (national["services_per_100k"] >= 0).all()
    assert (national["total_services"] >= 0).all()
    assert (national["n_providers"] >= 0).all()
    panel = tables["state_year_panel"]
    for column in ("pns_per_100k", "basic_density_per_100k",
                   "neuromod_density_per_100k", "ffs_benes"):
        assert (panel[column] >= 0).all(), column


def test_no_nans_in_final_tables(tables) -> None:
    for name in ("state_year_panel", "national_by_code", "income", "denominators"):
        frame = tables[name]
        assert not frame.isna().any().any(), (
            f"{name} contains NaN:\n{frame.isna().sum()[frame.isna().sum() > 0]}"
        )


def test_suppression_floor_is_present_in_the_delivered_data(tables) -> None:
    """CMS documents a >10-beneficiary floor. Confirm it empirically."""
    minimum = tables["prov_svc_study"]["total_benes"].min()
    assert minimum > SUPPRESSION_BENE_THRESHOLD, (
        f"minimum Tot_Benes was {minimum}; the documented floor implies > "
        f"{SUPPRESSION_BENE_THRESHOLD}"
    )
    assert minimum == SUPPRESSION_BENE_THRESHOLD + 1


def test_panel_is_balanced_and_denominators_are_positive(tables) -> None:
    panel = tables["state_year_panel"]
    assert len(panel) == panel["state"].nunique() * panel["year"].nunique()
    assert panel["state"].nunique() == 51        # 50 states + DC
    assert (panel["ffs_benes"] > 0).all()
    assert panel["dual_pct"].between(0, 100).all()


def test_provider_counts_never_exceed_service_counts(tables) -> None:
    panel = tables["state_year_panel"]
    billing = panel.loc[panel["pns_services"] > 0]
    assert (billing["pns_providers"] <= billing["pns_services"]).all()


def test_income_covers_every_state_once(tables) -> None:
    income = tables["income"]
    assert len(income) == 51
    assert income["state"].is_unique
    assert income["median_hh_income"].between(20_000, 200_000).all()
