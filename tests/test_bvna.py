"""Tests for the BVNA analysis and deck."""
from __future__ import annotations

import gzip
import json

import pytest

from src.bvna.config import BVNA_AUDIT, BVNA_CODES, BVNA_FIGURES, BVNA_RAW, YEARS

RESULTS = BVNA_AUDIT / "results.json"


@pytest.fixture(scope="module")
def results() -> dict:
    if not RESULTS.exists():
        pytest.skip("BVNA not built. Run `python run_bvna.py`.")
    return json.loads(RESULTS.read_text())


def test_api_pull_contains_only_bvna_codes() -> None:
    """Guards against the API silently ignoring the HCPCS filter."""
    for year in YEARS:
        path = BVNA_RAW / f"bvna_prov_svc_{year}.json.gz"
        if not path.exists():
            pytest.skip("BVNA raw rows not cached")
        rows = json.load(gzip.open(path))
        assert rows, f"{year} pull is empty"
        assert {r["HCPCS_Cd"] for r in rows} <= set(BVNA_CODES)


def test_descriptors_verified(results) -> None:
    assert [d["status"] for d in results["descriptors"]] == ["PASS", "PASS"]
    for d in results["descriptors"]:
        assert "basivertebral" in d["descriptor"].lower()


def test_legacy_code_precedes_cpt_codes(results) -> None:
    years = results["legacy"]["years_present"]
    assert results["legacy"]["code"] == "C9752"
    assert years and max(years) < 2022


def test_shares_and_rates_are_valid(results) -> None:
    for code, c in results["concentration"].items():
        assert 0 < c["share_visible_pct"] <= 100, code
        assert 0 <= c["gini"] <= 1, code
        assert c["gini_ci_low"] <= c["gini"] <= c["gini_ci_high"], code
        assert c["visible_clinicians"] > 0, code
    for year, g in results["growth"]["by_year"].items():
        assert g["per_100k_64628"] > 0 and g["addon_ratio"] > 0, year


def test_surgery_centres_excluded_from_clinician_counts(results) -> None:
    for code, c in results["concentration"].items():
        assert c["visible_services_clinicians"] <= c["visible_services_all"], code


def test_desert_bracket_is_ordered(results) -> None:
    """Geography view must never find more deserts than the provider-file view."""
    for d in results["deserts"]:
        assert d["states_zero"] <= d["provider_view_states_sparse"], d["year"]


def test_figures_exist() -> None:
    for stem in ("figure1", "figure2", "figure3", "figure4", "figure5"):
        assert (BVNA_FIGURES / f"{stem}.png").exists(), stem


def test_deck_has_no_missing_and_obeys_contract() -> None:
    pptx = pytest.importorskip("pptx")
    from src.build_pptx import MISSING, banned_used, sentence_count, word_count, MAX_WORDS
    from src.bvna.deck import DECK_PATH

    if not DECK_PATH.exists():
        pytest.skip("deck not built")
    prs = pptx.Presentation(str(DECK_PATH))
    for index, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if shape.has_text_frame:
                assert MISSING not in shape.text_frame.text, index
                if "WHAT THIS MEANS" in shape.text_frame.text:
                    body = shape.text_frame.text.split("\n", 1)[1]
                    assert sentence_count(body) <= 3 and word_count(body) <= MAX_WORDS
                    assert banned_used(body) == []
