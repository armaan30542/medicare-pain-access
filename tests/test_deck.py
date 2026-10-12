"""Tests for deck.html: self-contained, complete, and print-ready."""
from __future__ import annotations

import re

import pytest

from src.build_deck import ALLOWED_LINK_HOSTS, FIGURE_ORDER, MISSING_TEXT, verify
from src.constants import PROJECT_ROOT

DECK = PROJECT_ROOT / "deck.html"
NOTES = PROJECT_ROOT / "deck_notes.md"


@pytest.fixture(scope="module")
def deck() -> str:
    if not DECK.exists():
        pytest.skip("deck.html not built. Run `python run.py`.")
    return DECK.read_text(encoding="utf-8")


def test_deck_and_notes_exist(deck: str) -> None:
    assert NOTES.exists(), "deck_notes.md was not written"
    assert len(deck) > 100_000


def test_no_missing_placeholders(deck: str) -> None:
    """A red hole on screen is better than a wrong number - but zero is better."""
    assert MISSING_TEXT not in deck, (
        "deck.html contains unresolved fields; check the build warnings"
    )


def test_self_contained(deck: str) -> None:
    assert verify(deck) == []


def test_every_figure_is_inlined(deck: str) -> None:
    """Each figure appears twice: once inline, once in its lightbox."""
    assert deck.count("data:image/png;base64,") == len(FIGURE_ORDER) * 2
    for stem in FIGURE_ORDER:
        assert f'id="{stem}"' in deck
        assert f'id="zoom-{stem}"' in deck


def test_no_external_subresources(deck: str) -> None:
    for value in re.findall(r'\bsrc\s*=\s*"([^"]*)"', deck):
        assert value.startswith("data:"), f"external src: {value[:60]}"
    for tag in ("<script", "<iframe", "<link ", "@import"):
        assert tag not in deck.lower()


def test_outbound_links_are_references_only(deck: str) -> None:
    hosts = {
        re.sub(r"^https?://", "", v).split("/")[0]
        for v in re.findall(r'\bhref\s*=\s*"(https?://[^"]*)"', deck)
    }
    assert hosts <= set(ALLOWED_LINK_HOSTS), f"unexpected link hosts: {hosts}"


def test_has_print_stylesheet_and_all_sections(deck: str) -> None:
    assert "@media print" in deck
    for slug in ("one-liner", "why", "findings", "novelty",
                 "limitations", "methods", "provenance", "references"):
        assert f'id="{slug}"' in deck


def test_lightbox_is_css_only(deck: str) -> None:
    assert ".lightbox:target" in deck
    assert "onclick" not in deck.lower()
