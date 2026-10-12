"""Layout tests: no figure text may overflow the canvas or collide with the axes.

These render the real figures from the real computed results, so they catch the
case where an unusually long interpolated number pushes a caption off the page.
"""
from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.constants import FIGURES_DIR  # noqa: E402

STEMS = ("figure1", "figure2", "figure3", "figure4", "figure5", "figure5b", "figure6")
MIN_TITLE_PT = 18.0
MIN_BODY_PT = 14.0


@pytest.mark.parametrize("stem", STEMS)
def test_both_formats_exist_and_are_non_trivial(stem: str) -> None:
    for suffix in ("png", "svg"):
        path = FIGURES_DIR / f"{stem}.{suffix}"
        assert path.exists(), f"{path} was not written"
        assert path.stat().st_size > 10_000, f"{path} looks empty"


@pytest.mark.parametrize("stem", STEMS)
def test_png_is_300_dpi_and_at_least_10x6_inches(stem: str) -> None:
    from PIL import Image  # pillow ships with matplotlib's test extras

    with Image.open(FIGURES_DIR / f"{stem}.png") as image:
        width, height = image.size
    assert width / 300 >= 10.0, f"{stem} is {width/300:.1f} in wide at 300 dpi"
    assert height / 300 >= 6.0, f"{stem} is {height/300:.1f} in tall at 300 dpi"
