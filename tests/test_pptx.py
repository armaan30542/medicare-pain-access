"""Tests for deck.pptx: structure, plain-language contract, and legibility."""
from __future__ import annotations

import pytest

pptx = pytest.importorskip("pptx")
from pptx import Presentation  # noqa: E402

from src.build_pptx import (  # noqa: E402
    BANNED_TERMS,
    FIGURE_STEMS,
    MAX_SENTENCES,
    MAX_WORDS,
    MISSING,
    PPTX_PATH,
    banned_used,
    estimate_overflow,
    sentence_count,
    word_count,
)

PICTURE_SHAPE_TYPE = 13
FIGURE_SLIDE_NUMBERS = range(3, 3 + len(FIGURE_STEMS))


@pytest.fixture(scope="module")
def slides():
    if not PPTX_PATH.exists():
        pytest.skip("deck.pptx not built. Run `python run.py`.")
    return list(Presentation(str(PPTX_PATH)).slides)


def _texts(slide) -> list[str]:
    return [s.text_frame.text.strip() for s in slide.shapes
            if s.has_text_frame and s.text_frame.text.strip()]


def _explanation(slide) -> str:
    box = next(s for s in slide.shapes
               if s.has_text_frame and "WHAT THIS MEANS" in s.text_frame.text)
    return box.text_frame.text.split("\n", 1)[1].strip()


def test_slide_count_and_widescreen(slides) -> None:
    assert len(slides) == 5 + len(FIGURE_STEMS) == 11
    prs = Presentation(str(PPTX_PATH))
    assert round(prs.slide_width / prs.slide_height, 2) == round(16 / 9, 2)


def test_no_slide_is_empty(slides) -> None:
    for index, slide in enumerate(slides, start=1):
        pictures = [s for s in slide.shapes if s.shape_type == PICTURE_SHAPE_TYPE]
        assert _texts(slide) or pictures, f"slide {index} is empty"


def test_no_missing_placeholders(slides) -> None:
    for index, slide in enumerate(slides, start=1):
        for text in _texts(slide):
            assert MISSING not in text, f"slide {index} has an unresolved field"


def test_every_figure_slide_has_exactly_one_image(slides) -> None:
    for number in FIGURE_SLIDE_NUMBERS:
        pictures = [s for s in slides[number - 1].shapes
                    if s.shape_type == PICTURE_SHAPE_TYPE]
        assert len(pictures) == 1, f"slide {number} has {len(pictures)} images"


def test_figures_are_not_stretched(slides) -> None:
    """Rendered aspect ratio must match the source PNG's."""
    from PIL import Image

    from src.constants import FIGURES_DIR

    for number, stem in zip(FIGURE_SLIDE_NUMBERS, FIGURE_STEMS):
        picture = next(s for s in slides[number - 1].shapes
                       if s.shape_type == PICTURE_SHAPE_TYPE)
        with Image.open(FIGURES_DIR / f"{stem}.png") as image:
            source = image.size[0] / image.size[1]
        assert picture.width / picture.height == pytest.approx(source, rel=0.01)


def test_every_figure_slide_has_speaker_notes(slides) -> None:
    for number in FIGURE_SLIDE_NUMBERS:
        slide = slides[number - 1]
        assert slide.has_notes_slide
        notes = slide.notes_slide.notes_text_frame.text
        assert "SAY:" in notes and "LIKELY QUESTION:" in notes and "ANSWER:" in notes


def test_explanations_obey_the_plain_language_contract(slides) -> None:
    for number in FIGURE_SLIDE_NUMBERS:
        text = _explanation(slides[number - 1])
        assert text, f"slide {number} has an empty explanation"
        assert sentence_count(text) <= MAX_SENTENCES, (number, text)
        assert word_count(text) <= MAX_WORDS, (number, word_count(text))
        assert banned_used(text) == [], (number, banned_used(text))


def test_explanations_are_not_copied_from_results_md(slides) -> None:
    """The box text must be freshly written, not lifted out of RESULTS.md."""
    from src.constants import PROJECT_ROOT

    results = PROJECT_ROOT / "RESULTS.md"
    body = results.read_text(encoding="utf-8")
    for number in FIGURE_SLIDE_NUMBERS:
        for sentence in _explanation(slides[number - 1]).split(". "):
            trimmed = sentence.strip().rstrip(".")
            if len(trimmed) > 30:
                assert trimmed not in body, f"slide {number} copies RESULTS.md"


def test_no_text_box_overflows(slides) -> None:
    for index, slide in enumerate(slides, start=1):
        for shape in slide.shapes:
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue
            overflows, needed, available = estimate_overflow(shape)
            assert not overflows, (
                f"slide {index}: {needed:.2f}in needed vs {available:.2f}in"
            )


def test_font_sizes_meet_the_floor(slides) -> None:
    """Body >= 20pt, explanation >= 18pt; references and slide numbers exempt."""
    reference_slide = len(slides)
    for index, slide in enumerate(slides, start=1):
        if index == reference_slide:
            continue
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            is_box = "WHAT THIS MEANS" in shape.text_frame.text
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if not run.font.size or not run.text.strip():
                        continue
                    size = run.font.size.pt
                    if run.text.strip().isdigit() and size < 14:
                        continue          # slide number
                    floor = 14 if is_box else 18
                    assert size >= floor, (index, run.text[:30], size)


def test_title_slide_has_no_slide_number(slides) -> None:
    assert not any(t.strip().isdigit() for t in _texts(slides[0]))
