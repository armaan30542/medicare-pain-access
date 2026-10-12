"""Guards that keep `python run.py` byte-for-byte reproducible."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.constants import PROJECT_ROOT

FIGURE_DIRS = (PROJECT_ROOT / "figures", PROJECT_ROOT / "bvna" / "figures")


def _svgs() -> list[Path]:
    found = [p for d in FIGURE_DIRS if d.exists() for p in d.glob("*.svg")]
    if not found:
        pytest.skip("no figures built yet")
    return found


def test_svgs_carry_no_render_timestamp() -> None:
    """A timestamp would make every rebuild differ from the committed figures."""
    for svg in _svgs():
        assert "<dc:date>" not in svg.read_text(), svg.name


def test_no_hardcoded_contact_email_in_code() -> None:
    for path in (PROJECT_ROOT / "src").rglob("*.py"):
        assert "@gmail.com" not in path.read_text(), path.name


def test_access_date_is_not_the_wall_clock() -> None:
    """Footnote access dates must come from the download ledger."""
    run = (PROJECT_ROOT / "run.py").read_text()
    assert "_accessed_date()" in run
    assert "accessed = date.today()" not in run
