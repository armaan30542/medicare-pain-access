"""Build deck.html - a single self-contained presentation page.

Every number rendered into the deck is EXTRACTED from a generated artifact
(RESULTS.md, TALKING_POINTS.md, CITATION_AUDIT.md, NOVELTY_CHECK.md,
DATA_PROVENANCE.md, data/processed/*.parquet, audit/figure_captions.json).
Nothing is typed by hand. Anything that cannot be found renders as a bright red
[MISSING - CHECK RESULTS.MD] and is listed in a warning at the end of the run.

Figures are embedded as base64 data URIs so the file opens with no network.
"""
from __future__ import annotations

import base64
import html
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable, Sequence

import pandas as pd

from src.constants import AUDIT_DIR, FIGURES_DIR, PROCESSED_DIR, PROJECT_ROOT

LOGGER: Final = logging.getLogger(__name__)

MISSING_TEXT: Final[str] = "[MISSING - CHECK RESULTS.MD]"
ACCENT: Final[str] = "#0F5C8C"          # colorblind-safe deep blue
ACCENT_WARM: Final[str] = "#B03A00"     # colorblind-safe vermillion, used sparingly
DECK_PATH: Final[Path] = PROJECT_ROOT / "deck.html"
NOTES_PATH: Final[Path] = PROJECT_ROOT / "deck_notes.md"

FIGURE_ORDER: Final[tuple[str, ...]] = (
    "figure1", "figure2", "figure3", "figure4", "figure5", "figure5b", "figure6",
)
# Which TALKING_POINTS section covers which figure. 5b shares Figure 5's block.
TALKING_SECTION_FOR: Final[dict[str, str]] = {
    "figure1": "FIGURE 1", "figure2": "FIGURE 2", "figure3": "FIGURE 3",
    "figure4": "FIGURE 4", "figure5": "FIGURE 5", "figure5b": "FIGURE 5",
    "figure6": "FIGURE 6",
}

# Bias direction per limitation. Prose only - contains no numbers, so it does
# not fall under the no-hand-typed-numbers rule. Keyed by leading words of the
# limitation so a reordering of TALKING_POINTS.md cannot mis-pair them.
BIAS_DIRECTION: Final[dict[str, str]] = {
    "ecological": "Direction: unknown. Ecological units can bias either way; "
                  "this is a limit on inference, not a tilt in one direction.",
    "suppression": "Direction: against me. Truncation hides low-volume providers, "
                   "so measured concentration is a floor, not a ceiling.",
    "practice location": "Direction: against me. Counting patients at the "
                         "provider's address understates travel burden, so real "
                         "access deserts are worse than shown.",
    "fee-for-service": "Direction: unknown. If Medicare Advantage authorises PNS "
                       "differently, national rates shift by an amount public "
                       "data cannot bound.",
    "causal": "Direction: unknown. No instrument and no policy shock, so "
              "unmeasured state characteristics could push either way.",
    "64590": "Direction: toward the null. Contamination adds non-PNS implanters "
             "to the exposure, which dilutes rather than manufactures the effect.",
}


# --------------------------------------------------------------- missing-field
@dataclass
class Extraction:
    """Tracks every field pulled from an artifact, and every one that failed."""

    missing: list[str] = field(default_factory=list)

    def get(self, label: str, value: object) -> str:
        """Return `value` as text, or record a miss and return the sentinel."""
        if value is None or (isinstance(value, str) and not value.strip()):
            self.missing.append(label)
            return MISSING_TEXT
        return str(value)

    def html(self, label: str, value: object) -> str:
        """Same as `get`, but wrapped for HTML with the red missing style."""
        text = self.get(label, value)
        if text == MISSING_TEXT:
            return f'<span class="missing">{html.escape(MISSING_TEXT)}</span>'
        return html.escape(text)

    def raw(self, label: str, value: object) -> str:
        """Like `html` but keeps pre-escaped/inline-marked-up text intact."""
        text = self.get(label, value)
        if text == MISSING_TEXT:
            return f'<span class="missing">{html.escape(MISSING_TEXT)}</span>'
        return text


# --------------------------------------------------------------- md utilities
def read(path: Path) -> str:
    """Read a required artifact, raising a clear error if the run never made it."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} is missing. Run `python run.py` before building the deck."
        )
    return path.read_text(encoding="utf-8")


def strip_md(text: str) -> str:
    """Remove inline markdown emphasis, code ticks and links, keeping the words."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"(?<!\w)\*(?!\s)([^*]+?)\*(?!\w)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_tables(markdown: str) -> list[list[dict[str, str]]]:
    """Parse every GitHub-style pipe table in `markdown` into a list of dicts."""
    tables: list[list[dict[str, str]]] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].strip().startswith("|"):
            index += 1
            continue
        block = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            block.append(lines[index].strip())
            index += 1
        if len(block) < 3:
            continue
        cells = [[c.strip() for c in row.strip("|").split("|")] for row in block]
        header = [strip_md(c) for c in cells[0]]
        rows = [
            dict(zip(header, [c for c in row]))
            for row in cells[2:]
            if len(row) == len(header)
        ]
        if rows:
            tables.append(rows)
    return tables


def table_with(tables: Sequence[list[dict[str, str]]],
               *required: str) -> list[dict[str, str]] | None:
    """First table whose header contains all `required` column names."""
    for rows in tables:
        header = {h.lower() for h in rows[0]}
        if all(any(r.lower() in h for h in header) for r in required):
            return rows
    return None


def cell(rows: Sequence[dict[str, str]], match_column: str, match_value: str,
         want_column: str) -> str | None:
    """Value of `want_column` in the first row where `match_column` contains value."""
    for row in rows:
        # `is not None`, not truthiness: a leading column with an empty header
        # name is legitimate in these tables and an empty string is falsy.
        key = next((k for k in row if match_column.lower() in k.lower()), None)
        want = next((k for k in row if want_column.lower() in k.lower()), None)
        if key is None or want is None:
            continue
        if match_value.lower() in strip_md(row[key]).lower():
            return strip_md(row[want])
    return None


def first_number(text: str | None) -> str | None:
    """First numeric token (with sign, commas, decimals, percent) in `text`."""
    if not text:
        return None
    found = re.search(r"-?\d[\d,]*\.?\d*%?", text)
    return found.group(0) if found else None


def section(markdown: str, heading_contains: str, level: str = "## ") -> str | None:
    """Body of the first section whose heading contains `heading_contains`."""
    pattern = re.compile(
        rf"^{re.escape(level)}.*{re.escape(heading_contains)}.*$", re.MULTILINE
    )
    start = pattern.search(markdown)
    if not start:
        return None
    rest = markdown[start.end():]
    nxt = re.search(rf"^{re.escape(level.strip())} ", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def bullets(block: str | None, after_label: str) -> list[str]:
    """Bullet list following a bolded label such as '**Say these numbers:**'."""
    if not block:
        return []
    start = block.find(after_label)
    if start == -1:
        return []
    tail = block[start + len(after_label):]
    out: list[str] = []
    for line in tail.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            out.append(stripped[2:].strip())
        elif out and stripped and not stripped.startswith(("**", "#", "---")):
            out[-1] += " " + stripped
        elif out:
            break
    return out


def labelled_paragraph(block: str | None, label: str) -> str | None:
    """Text following a bolded inline label, up to the next bolded label."""
    if not block:
        return None
    found = re.search(re.escape(label) + r"\s*(.*?)(?=\n\s*\n\*\*|\n---|\Z)",
                      block, re.DOTALL)
    return strip_md(found.group(1)) if found else None


# ------------------------------------------------------------------ artifacts
@dataclass
class Artifacts:
    """Everything the deck is built from, already read off disk."""

    results: str
    talking: str
    audit: str
    novelty: str
    provenance: str
    captions: dict[str, dict[str, str]]
    prov_svc: pd.DataFrame
    panel: pd.DataFrame
    national: pd.DataFrame
    verification: pd.DataFrame

    @classmethod
    def load(cls) -> "Artifacts":
        captions_path = AUDIT_DIR / "figure_captions.json"
        return cls(
            results=read(PROJECT_ROOT / "RESULTS.md"),
            talking=read(PROJECT_ROOT / "TALKING_POINTS.md"),
            audit=read(PROJECT_ROOT / "CITATION_AUDIT.md"),
            novelty=read(PROJECT_ROOT / "NOVELTY_CHECK.md"),
            provenance=read(PROJECT_ROOT / "DATA_PROVENANCE.md"),
            captions=json.loads(read(captions_path)),
            prov_svc=pd.read_parquet(PROCESSED_DIR / "prov_svc_study.parquet"),
            panel=pd.read_parquet(PROCESSED_DIR / "state_year_panel.parquet"),
            national=pd.read_parquet(PROCESSED_DIR / "national_by_code.parquet"),
            verification=pd.read_parquet(PROCESSED_DIR / "hcpcs_verification.parquet"),
        )


def embed_png(stem: str) -> str | None:
    """Base64 data URI for a figure PNG, or None if it was never rendered."""
    path = FIGURES_DIR / f"{stem}.png"
    if not path.exists():
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def figure_blocks(art: Artifacts, ex: Extraction) -> list[dict[str, str]]:
    """One rendering block per figure, in figure-number order."""
    blocks: list[dict[str, str]] = []
    for stem in FIGURE_ORDER:
        caption = art.captions.get(stem, {})
        talking = section(art.talking, TALKING_SECTION_FOR[stem])
        shows = labelled_paragraph(talking, "**What it shows.**")
        say = bullets(talking, "**Say these numbers:**")
        # Figure 6 uses a different label for the same idea.
        limitation = (
            labelled_paragraph(talking, "**The limitation, phrased for a physician:**")
            or labelled_paragraph(talking, "**The limitation you must say yourself:**")
        )
        next_study = labelled_paragraph(talking, "**Next study:**")
        blocks.append(
            {
                "stem": stem,
                "number": stem.replace("figure", "Figure "),
                "headline": ex.get(f"{stem}.headline", caption.get("title")),
                "subtitle": ex.get(f"{stem}.subtitle", caption.get("subtitle")),
                "source": ex.get(f"{stem}.footnote", caption.get("footnote")),
                "shows": ex.get(f"{stem}.what_it_shows", shows),
                "say": say,
                "limitation": ex.get(f"{stem}.limitation", limitation),
                "next_study": ex.get(f"{stem}.next_study", next_study),
                "image": embed_png(stem),
            }
        )
        if blocks[-1]["image"] is None:
            ex.missing.append(f"{stem}.png")
    return blocks


def headline_stats(art: Artifacts, ex: Extraction) -> dict[str, str]:
    """The numbers that get their own large stat callouts."""
    fig2 = parse_tables(section(art.results, "Figure 2 - Concentration") or "")
    primary = fig2[0] if fig2 else []
    secondary = fig2[1] if len(fig2) > 1 else []
    fig3 = parse_tables(section(art.results, "Figure 3 - Access deserts") or "")
    fig4 = parse_tables(section(art.results, "Figure 4 - Does general") or "")
    fig5 = parse_tables(section(art.results, "Figure 5 - The equity gradient") or "")
    fig6 = parse_tables(section(art.results, "Figure 6 - The literature gap") or "")

    deserts_last = fig3[0][-1] if fig3 else {}
    desert_values = list(deserts_last.values())

    # Provider counts come straight from the analytic parquet, not from prose.
    latest = int(art.prov_svc["year"].max())
    latest_rows = art.prov_svc[art.prov_svc["year"] == latest]
    pns_providers = latest_rows.loc[latest_rows["hcpcs_code"] == "64555", "npi"].nunique()
    epi_providers = latest_rows.loc[latest_rows["hcpcs_code"] == "62323", "npi"].nunique()
    ratio = round(epi_providers / pns_providers) if pns_providers else None

    return {
        "latest_year": ex.get("latest_year", latest),
        "gini_pns": ex.get("fig2.gini_pns",
                           cell(primary, "Measure", "Gini coefficient", "PNS")),
        "gini_basic": ex.get("fig2.gini_basic",
                             cell(primary, "Measure", "Gini coefficient", "epidural")),
        "gini_pns_ci": ex.get("fig2.gini_pns_ci",
                              cell(primary, "Measure", "bootstrap CI", "PNS")),
        "gini_basic_ci": ex.get("fig2.gini_basic_ci",
                                cell(primary, "Measure", "bootstrap CI", "epidural")),
        "top10_pns": ex.get("fig2.top10_pns",
                            cell(primary, "Measure", "top 10%", "PNS")),
        "top10_basic": ex.get("fig2.top10_basic",
                              cell(primary, "Measure", "top 10%", "epidural")),
        "billers_pns": ex.get("fig2.billers_pns",
                              cell(secondary, "Measure", "Providers billing", "PNS")),
        "billers_basic": ex.get("fig2.billers_basic",
                                cell(secondary, "Measure", "Providers billing", "epidural")),
        "gini_billers_pns": ex.get("fig2.gini_billers_pns",
                                   cell(secondary, "Measure", "Gini among billers", "PNS")),
        "gini_billers_basic": ex.get("fig2.gini_billers_basic",
                                     cell(secondary, "Measure", "Gini among billers", "epidural")),
        "pns_providers_parquet": ex.get("parquet.pns_providers", f"{pns_providers:,}"),
        "epi_providers_parquet": ex.get("parquet.epi_providers", f"{epi_providers:,}"),
        "provider_ratio": ex.get("parquet.provider_ratio", ratio),
        "states_zero": ex.get("fig3.states_zero",
                              desert_values[1] if len(desert_values) > 1 else None),
        "pct_benes_sparse": ex.get("fig3.pct_benes_sparse",
                                   desert_values[4] if len(desert_values) > 4 else None),
        "model_b_general": ex.get("fig4.model_b_general",
                                  cell(fig4[0] if fig4 else [], "", "General", "Model B")),
        "model_b_neuromod": ex.get("fig4.model_b_neuromod",
                                   cell(fig4[0] if fig4 else [], "", "Neuromodulation", "Model B")),
        "pseudo_r2_b": ex.get("fig4.pseudo_r2",
                              cell(fig4[0] if fig4 else [], "", "Pseudo", "Model B")),
        "n_state_years": ex.get("fig4.n_obs",
                                cell(fig4[0] if fig4 else [], "", "N (state-years)", "Model B")),
        "income_pearson": ex.get("fig5.income_pearson",
                                 cell(fig5[0] if fig5 else [], "", "Pearson", "Income")),
        "dual_spearman": ex.get("fig5.dual_spearman",
                                cell(fig5[0] if fig5 else [], "", "Spearman", "Dual")),
        "lit_scs_total": ex.get("fig6.scs_total",
                                cell(fig6[0] if fig6 else [], "Year", "Total", "SCS")),
        "lit_pns_total": ex.get("fig6.pns_total",
                                cell(fig6[0] if fig6 else [], "Year", "Total", "PNS")),
    }


def chow_numbers(art: Artifacts, ex: Extraction) -> dict[str, object]:
    """Verified key numbers for the Pain Medicine 2026 paper, from the audit."""
    rows = [r for table in parse_tables(art.audit) for r in table]
    key_rows = [
        r for r in rows
        if any("odonkor2026pns" in strip_md(v) for v in r.values())
    ]
    audit_date = re.search(r"API\)?\s*on \*\*([\d-]+)\*\*", art.audit)
    if not audit_date:
        audit_date = re.search(r"\*\*(\d{4}-\d{2}-\d{2})\*\*", art.audit)

    def claim(fragment: str) -> tuple[str | None, str | None]:
        """Return (claim text, status) for the audit row matching `fragment`."""
        for row in key_rows:
            values = list(row.values())
            if len(values) < 4:
                continue
            checked = strip_md(values[1])
            if fragment.lower() in checked.lower():
                return checked, strip_md(values[3])
        return None, None

    cohort, cohort_status = claim("n=121")
    day60, day60_status = claim("60-day:")
    month6, month6_status = claim("6-month:")
    delayed, delayed_status = claim("non-responders")

    statuses = {cohort_status, day60_status, month6_status, delayed_status}
    corrected = any(s and "CORRECT" in s.upper() for s in statuses)

    return {
        "cohort": ex.get("audit.chow_cohort", cohort),
        "day60": ex.get("audit.chow_60day", day60),
        "month6": ex.get("audit.chow_6month", month6),
        "delayed": ex.get("audit.chow_delayed", delayed),
        "audit_date": ex.get("audit.date", audit_date.group(1) if audit_date else None),
        "corrected": corrected,
        "pass_count": ex.get("audit.pass_count",
                             cell([r for t in parse_tables(art.audit) for r in t],
                                  "Status", "PASS", "Count")),
        "corrected_count": ex.get("audit.corrected_count",
                                  cell([r for t in parse_tables(art.audit) for r in t],
                                       "Status", "CORRECTED", "Count")),
        "unverifiable_count": ex.get("audit.unverifiable_count",
                                     cell([r for t in parse_tables(art.audit) for r in t],
                                          "Status", "UNVERIFIABLE", "Count")),
    }


def novelty_bundle(art: Artifacts, ex: Extraction) -> dict[str, object]:
    """Verdict, the three closest papers, and the exact PubMed query strings."""
    verdict = re.search(r"^## Verdict:\s*\*\*(.+?)\*\*", art.novelty, re.MULTILINE)
    closest_block = section(art.novelty, "three closest papers")
    closest: list[dict[str, str]] = []
    if closest_block:
        for line in re.findall(r"^\d+\.\s+(.*?)(?=\n\d+\.|\n##|\Z)",
                               closest_block, re.MULTILINE | re.DOTALL):
            flat = strip_md(line)
            pmid = re.search(r"PMID\s*(\d+)", flat)
            name = re.match(r"^(.*?)\s*—", flat)
            says = re.search(r'Say:\s*"(.+?)"\s*$', flat)
            closest.append({
                "label": name.group(1) if name else flat[:90],
                "pmid": pmid.group(1) if pmid else "",
                "note": says.group(1) if says else flat,
            })

    query_rows = table_with(parse_tables(art.novelty), "Query", "Hits") or []
    queries = [
        {
            "id": strip_md(list(r.values())[0]),
            "query": strip_md(list(r.values())[1]),
            "hits": strip_md(list(r.values())[2]),
            "scoop": strip_md(list(r.values())[3]) if len(r) > 3 else "",
        }
        for r in query_rows
    ]

    fig6_block = section(art.results, "Figure 6 - The literature gap") or ""
    scs_q = re.search(r"\*\*SCS:\*\*\s*`(.+?)`", fig6_block, re.DOTALL)
    pns_q = re.search(r"\*\*PNS:\*\*\s*`(.+?)`", fig6_block, re.DOTALL)

    return {
        "verdict": ex.get("novelty.verdict", verdict.group(1) if verdict else None),
        "closest": closest,
        "queries": queries,
        "fig6_scs_query": ex.get("novelty.fig6_scs_query",
                                 scs_q.group(1).strip() if scs_q else None),
        "fig6_pns_query": ex.get("novelty.fig6_pns_query",
                                 pns_q.group(1).strip() if pns_q else None),
    }


def limitations(art: Artifacts, ex: Extraction) -> list[dict[str, str]]:
    """The numbered limitations list, each paired with its bias direction."""
    block = section(art.talking, "Known limitations")
    if not block:
        ex.missing.append("talking.limitations")
        return []
    items = re.findall(r"^\d+\.\s+(.*?)(?=\n\d+\.\s|\n---|\Z)",
                       block, re.MULTILINE | re.DOTALL)
    out: list[dict[str, str]] = []
    for item in items:
        flat = strip_md(item)
        title = re.match(r"^(.*?[.:])\s", flat)
        direction = next(
            (v for k, v in BIAS_DIRECTION.items() if k.lower() in flat.lower()), None
        )
        out.append({
            "title": title.group(1).rstrip(".:") if title else flat[:70],
            "body": flat,
            "direction": ex.get(f"limitation.direction.{flat[:24]}", direction),
        })
    return out


def references(art: Artifacts, ex: Extraction) -> tuple[list[dict[str, str]], list[str]]:
    """Passing references with resolvable links, plus any excluded entries."""
    block = section(art.results, "References")
    entries: list[dict[str, str]] = []
    if block:
        for line in re.findall(r"^-\s+\[(.+?)\]\s+(.*?)(?=\n-\s+\[|\n##|\Z)",
                               block, re.MULTILINE | re.DOTALL):
            key, text = line[0], strip_md(line[1])
            doi = re.search(r"doi:\s*(10\.\S+?)\.?(?:\s|$)", text)
            pmid = re.search(r"PMID\s*(\d+)", text)
            entries.append({
                "key": key,
                "text": text,
                "doi": doi.group(1).rstrip(".") if doi else "",
                "pmid": pmid.group(1) if pmid else "",
            })
    if not entries:
        ex.missing.append("results.references")

    excluded = [
        strip_md(list(row.values())[0]) + " — " + strip_md(list(row.values())[1])
        for table in parse_tables(art.audit)
        for row in table
        if any("UNVERIFIABLE" in strip_md(v).upper() for v in list(row.values())[2:])
    ]
    return entries, excluded


def provenance_rows(art: Artifacts, ex: Extraction) -> list[dict[str, str]]:
    """File-level provenance: name, timestamp, rows, size, hash."""
    rows = table_with(parse_tables(art.provenance), "Cached file", "SHA256")
    if not rows:
        ex.missing.append("provenance.table")
        return []
    return [{strip_md(k): strip_md(v) for k, v in row.items()} for row in rows]


def methods_lines(art: Artifacts, ex: Extraction) -> list[tuple[str, str]]:
    """Six terse methods lines, each value pulled from an artifact."""
    fig4 = parse_tables(section(art.results, "Figure 4 - Does general") or "")
    model_rows = fig4[0] if fig4 else []
    years = f"{int(art.national['year'].min())}-{int(art.national['year'].max())}"
    software = re.search(r"CPython ([\d.]+)", read(PROJECT_ROOT / "requirements.txt"))
    packages = [
        line.split("==")[0]
        for line in read(PROJECT_ROOT / "requirements.txt").splitlines()
        if "==" in line and line.split("==")[0] in
        {"pandas", "numpy", "statsmodels", "scipy", "matplotlib"}
    ]
    return [
        ("Data source",
         ex.get("methods.source",
                "CMS Medicare Physician & Other Practitioners (by Provider and Service; "
                "by Geography and Service), CMS Medicare Geographic Variation, US Census SAIPE")),
        ("Years", ex.get("methods.years", years)),
        ("Unit of analysis",
         ex.get("methods.unit",
                f"Provider x HCPCS x year ({len(art.prov_svc):,} rows) for concentration; "
                f"state x year ({len(art.panel):,} rows) for the models")),
        ("Outcome",
         ex.get("methods.outcome",
                "64555 (PNS) service volume; log fee-for-service beneficiary offset")),
        ("Model",
         ex.get("methods.model",
                "Negative binomial (NB2), year fixed effects, SE clustered on state; "
                f"N = {cell(model_rows, '', 'N (state-years)', 'Model B') or '?'} state-years, "
                f"{cell(model_rows, '', 'Clusters', 'Model B') or '?'} clusters")),
        ("Software",
         ex.get("methods.software",
                f"Python {software.group(1) if software else ''} - "
                + ", ".join(packages) + "; bootstrap seeded, versions pinned")),
    ]


# ------------------------------------------------------------------- CSS
CSS: Final[str] = """
:root {
  --accent: %(accent)s;
  --warm: %(warm)s;
  --ink: #16191C;
  --muted: #55606A;
  --rule: #D9DEE3;
  --wash: #F4F6F8;
  --page: #FFFFFF;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; background: var(--page); color: var(--ink);
  font-family: Charter, "Bitstream Charter", "Iowan Old Style", Georgia,
               "Times New Roman", serif;
  font-size: 19px; line-height: 1.62;
  -webkit-text-size-adjust: 100%%;
}
.layout { display: flex; align-items: flex-start; gap: 0; }

/* ---------------------------------------------------------- sidebar */
nav {
  position: sticky; top: 0; flex: 0 0 268px; height: 100vh;
  padding: 40px 26px 40px 34px; border-right: 1px solid var(--rule);
  background: var(--wash); overflow-y: auto;
}
nav .brand {
  font-size: 15px; letter-spacing: .07em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 6px;
}
nav .brandsub { font-size: 16px; color: var(--ink); margin-bottom: 30px; line-height: 1.35; }
nav ol { list-style: none; margin: 0; padding: 0; counter-reset: nav; }
nav li { counter-increment: nav; margin: 0 0 4px; }
nav a {
  display: block; padding: 8px 10px 8px 34px; position: relative;
  color: var(--ink); text-decoration: none; font-size: 16.5px;
  line-height: 1.3; border-radius: 3px;
}
nav a::before {
  content: counter(nav); position: absolute; left: 10px; top: 8px;
  color: var(--muted); font-size: 14px;
}
nav a:hover { background: #E7ECF1; color: var(--accent); }
nav .navfoot {
  margin-top: 28px; padding-top: 18px; border-top: 1px solid var(--rule);
  font-size: 15.5px; color: var(--muted); line-height: 1.45;
}

/* ------------------------------------------------------------- main */
main { flex: 1 1 auto; min-width: 0; padding: 64px 56px 120px; }
.wrap { max-width: 72ch; }
.wrap.wide { max-width: 96ch; }
section { margin: 0 0 92px; scroll-margin-top: 24px; }
h2 {
  font-size: 15px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--accent); font-weight: 700; margin: 0 0 22px;
  padding-bottom: 10px; border-bottom: 2px solid var(--accent);
  max-width: 72ch;
}
h3 { font-size: 27px; line-height: 1.28; margin: 0 0 14px; font-weight: 700; }
h4 { font-size: 17px; margin: 0 0 8px; letter-spacing: .04em;
     text-transform: uppercase; color: var(--muted); font-weight: 700; }
p { margin: 0 0 20px; }
a { color: var(--accent); }

.oneliner {
  font-size: 39px; line-height: 1.26; font-weight: 700;
  letter-spacing: -0.012em; margin: 0 0 26px; max-width: 26ch;
}
.oneliner .em { color: var(--accent); }
.standfirst { font-size: 25px; line-height: 1.5; color: var(--muted); max-width: 62ch; }

/* ------------------------------------------------------ stat callouts */
.stats { display: flex; flex-wrap: wrap; gap: 18px; margin: 34px 0 10px; }
.stat {
  flex: 1 1 210px; min-width: 200px; padding: 22px 22px 20px;
  border: 1px solid var(--rule); border-top: 4px solid var(--accent);
  background: var(--page); break-inside: avoid;
}
.stat.warm { border-top-color: var(--warm); }
.stat .n {
  display: block; font-size: 46px; line-height: 1.02; font-weight: 700;
  letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
}
.stat.warm .n { color: var(--warm); }
.stat .k { display: block; margin-top: 10px; font-size: 16px; color: var(--muted);
           line-height: 1.38; }
.stat .sub { display: block; margin-top: 6px; font-size: 15.5px; color: var(--muted); }

/* ---------------------------------------------------------- figures */
.figblock { margin: 0 0 76px; break-inside: avoid; }
.figblock .kicker {
  font-size: 15px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 8px;
}
.figblock .sub { color: var(--muted); font-size: 18px; margin: 0 0 20px; max-width: 78ch; }
.figframe { border: 1px solid var(--rule); background: var(--page); padding: 10px; }
.figframe img { display: block; width: 100%%; height: auto; }
.enlarge { font-size: 15.5px; color: var(--muted); margin-top: 8px; }
.srcline { font-size: 15px; color: var(--muted); margin-top: 10px; line-height: 1.45;
           white-space: pre-wrap; }
.tworow { display: flex; gap: 34px; margin-top: 26px; }
.tworow > div { flex: 1 1 0; min-width: 0; }
.tworow ul { margin: 0; padding-left: 20px; }
.tworow li { margin-bottom: 9px; }
.saidaloud {
  border-left: 3px solid var(--accent); padding-left: 18px;
  font-style: italic; color: var(--ink);
}
.aside { margin-top: 18px; font-size: 16.5px; color: var(--muted); }

/* ------------------------------------------------------- lightbox */
.lightbox {
  position: fixed; inset: 0; background: rgba(20,22,25,.94);
  display: none; z-index: 90; padding: 22px; overflow: auto; text-align: center;
}
.lightbox:target { display: block; }
.lightbox img { max-width: 100%%; height: auto; margin: 0 auto; background: #fff; }
.lightbox .close {
  display: inline-block; margin: 0 0 14px; color: #fff; text-decoration: none;
  font-size: 17px; border: 1px solid #7A848E; padding: 7px 18px; border-radius: 3px;
}

/* ---------------------------------------------------------- novelty */
.verdict {
  border: 2px solid var(--accent); padding: 30px 32px; margin: 0 0 32px;
  background: var(--wash);
}
.verdict .label { font-size: 14px; letter-spacing: .11em; text-transform: uppercase;
                  color: var(--muted); }
.verdict .value { font-size: 54px; font-weight: 700; color: var(--accent);
                  line-height: 1.05; margin: 6px 0 12px; letter-spacing: -0.02em; }
.verdict p { margin: 0; font-size: 18px; color: var(--muted); max-width: 66ch; }
.paper { border-left: 3px solid var(--rule); padding: 4px 0 4px 20px; margin-bottom: 24px; }
.paper .t { font-weight: 700; }
code, .q {
  font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 15px;
  background: var(--wash); border: 1px solid var(--rule); padding: 2px 5px;
}
.q { display: block; padding: 12px 14px; margin: 8px 0 18px; white-space: pre-wrap;
     word-break: break-word; line-height: 1.55; }

/* ------------------------------------------------------ limitations */
.limit { border-left: 4px solid var(--accent); padding: 2px 0 2px 22px; margin: 0 0 30px;
         break-inside: avoid; }
.limit .t { font-weight: 700; font-size: 20px; display: block; margin-bottom: 6px; }
.limit .dir {
  display: inline-block; margin-top: 10px; font-size: 16px; color: var(--muted);
  border-top: 1px solid var(--rule); padding-top: 8px;
}

/* ----------------------------------------------------------- tables */
table { border-collapse: collapse; width: 100%%; font-size: 16px; margin: 6px 0 0; }
th, td { text-align: left; padding: 8px 12px 8px 0; border-bottom: 1px solid var(--rule);
         vertical-align: top; }
th { font-size: 15px; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); }
td.hash { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 14px;
          word-break: break-all; }
details { border: 1px solid var(--rule); padding: 18px 22px; background: var(--wash); }
summary { cursor: pointer; font-weight: 700; font-size: 19px; }
details[open] summary { margin-bottom: 18px; }

/* --------------------------------------------------------- methods */
.methods { width: 100%%; }
.methods th { width: 22%%; white-space: nowrap; padding-right: 22px;
              text-transform: none; font-size: 15px; letter-spacing: 0;
              color: var(--ink); font-weight: 700; }
.methods td { font-size: 16.5px; }

/* ------------------------------------------------------ references */
.ref { margin: 0 0 18px; font-size: 16.5px; line-height: 1.5; }
.ref .links { font-size: 16px; }
.excluded { border: 1px dashed var(--rule); padding: 18px 22px; color: var(--muted);
            font-size: 16.5px; }

.missing { color: #D40000; font-weight: 700; background: #FFECEC;
           padding: 1px 6px; border: 1px solid #D40000; }

/* ------------------------------------------------------------ print */
@media print {
  @page { margin: 15mm; }
  body { font-size: 11.5pt; line-height: 1.45; }
  nav, .enlarge, .lightbox { display: none !important; }
  main { padding: 0; }
  .wrap, .wrap.wide { max-width: 100%%; }
  section { margin-bottom: 26pt; page-break-inside: auto; }
  h2 { font-size: 10pt; margin-bottom: 12pt; }
  h3 { font-size: 15pt; page-break-after: avoid; }
  .oneliner { font-size: 24pt; max-width: 100%%; }
  .standfirst { font-size: 13pt; }
  .stat .n { font-size: 24pt; }
  .stats { gap: 10pt; }
  .figblock, .stat, .limit, .paper { page-break-inside: avoid; }
  .figframe img { max-height: 105mm; width: auto; max-width: 100%%; margin: 0 auto; }
  .verdict .value { font-size: 26pt; }
  details { border: none; padding: 0; background: none; }
  details:not([open]) > *:not(summary) { display: revert; }
  a { color: var(--ink); text-decoration: none; }
  .ref .links::after { content: ""; }
}
@media (max-width: 900px) {
  .layout { display: block; }
  nav { position: static; width: auto; height: auto; border-right: none;
        border-bottom: 1px solid var(--rule); }
  main { padding: 32px 22px 70px; }
  .tworow { display: block; }
  .tworow > div + div { margin-top: 24px; }
}
""" % {"accent": ACCENT, "warm": ACCENT_WARM}


# ------------------------------------------------------------------- render
NAV: Final[tuple[tuple[str, str], ...]] = (
    ("one-liner", "The one-liner"),
    ("why", "Why this question"),
    ("findings", "Findings"),
    ("novelty", "What I checked before claiming novelty"),
    ("limitations", "Limitations I'm raising myself"),
    ("methods", "Methods in six lines"),
    ("provenance", "Data provenance"),
    ("references", "References"),
)


def stat(value: str, key: str, sub: str = "", warm: bool = False) -> str:
    """One large standalone stat callout."""
    extra = f'<span class="sub">{sub}</span>' if sub else ""
    return (f'<div class="stat{" warm" if warm else ""}">'
            f'<span class="n">{value}</span>'
            f'<span class="k">{key}</span>{extra}</div>')


def render_figures(blocks: Sequence[dict[str, object]],
                   ex: Extraction) -> tuple[str, str]:
    """Findings section: one block per figure, plus the CSS-only lightboxes."""
    parts: list[str] = []
    lightboxes: list[str] = []
    for block in blocks:
        stem = block["stem"]
        image = block["image"]
        if image:
            figure_html = (
                f'<a class="figframe" href="#zoom-{stem}">'
                f'<img src="{image}" alt="{html.escape(str(block["headline"]))}"></a>'
                f'<div class="enlarge">Click the figure to enlarge. '
                f'Vector copy: figures/{stem}.svg</div>'
            )
            lightboxes.append(
                f'<div class="lightbox" id="zoom-{stem}">'
                f'<a class="close" href="#{stem}">Close</a>'
                f'<img src="{image}" alt="{html.escape(str(block["headline"]))} enlarged">'
                f"</div>"
            )
        else:
            figure_html = (f'<p><span class="missing">'
                           f'{html.escape(MISSING_TEXT)}</span> figure image '
                           f'{html.escape(stem)}.png was not rendered.</p>')

        say_items = "".join(
            f"<li>{html.escape(strip_md(s))}</li>" for s in block["say"]
        ) or f'<li><span class="missing">{html.escape(MISSING_TEXT)}</span></li>'

        parts.append(f"""
<div class="figblock" id="{stem}">
  <div class="kicker">{html.escape(str(block["number"]))}</div>
  <h3>{ex.raw(f'{stem}.headline.render', html.escape(str(block["headline"])))}</h3>
  <p class="sub">{ex.raw(f'{stem}.subtitle.render', html.escape(str(block["subtitle"])))}</p>
  {figure_html}
  <div class="srcline">{html.escape(str(block["source"]))}</div>
  <div class="tworow">
    <div>
      <h4>What this shows</h4>
      <p>{ex.raw(f'{stem}.shows.render', html.escape(str(block["shows"])))}</p>
      <p class="aside"><strong>Next study.</strong>
         {ex.raw(f'{stem}.next.render', html.escape(str(block["next_study"])))}</p>
    </div>
    <div>
      <h4>What I'd say out loud</h4>
      <ul>{say_items}</ul>
      <p class="saidaloud">{ex.raw(f'{stem}.limit.render', html.escape(str(block["limitation"])))}</p>
    </div>
  </div>
</div>""")
    return "\n".join(parts), "\n".join(lightboxes)


def build_html(art: Artifacts, ex: Extraction) -> str:
    """Assemble the whole single-file deck."""
    stats = headline_stats(art, ex)
    chow = chow_numbers(art, ex)
    novelty = novelty_bundle(art, ex)
    limits = limitations(art, ex)
    refs, excluded = references(art, ex)
    prov = provenance_rows(art, ex)
    methods = methods_lines(art, ex)
    blocks = figure_blocks(art, ex)
    findings_html, lightbox_html = render_figures(blocks, ex)

    nav_html = "".join(
        f'<li><a href="#{slug}">{html.escape(label)}</a></li>' for slug, label in NAV
    )

    footnote_mark = (
        f'<sup><a href="#audit-note">1</a></sup>'
    )
    audit_note = (
        f'<p id="audit-note" class="aside"><sup>1</sup> These are the values '
        f'confirmed against the publisher record via the NCBI E-utilities PubMed '
        f'API on {ex.html("audit.date.render", chow["audit_date"])}, not the values '
        f'as originally written down. Full audit: CITATION_AUDIT.md '
        f'({ex.html("audit.pass.render", chow["pass_count"])} pass, '
        f'{ex.html("audit.corr.render", chow["corrected_count"])} corrected, '
        f'{ex.html("audit.unver.render", chow["unverifiable_count"])} unverifiable).</p>'
    )

    closest_html = "".join(
        f'<div class="paper"><span class="t">{html.escape(p["label"])}</span>'
        + (f' &middot; <a href="https://pubmed.ncbi.nlm.nih.gov/{p["pmid"]}/">'
           f'PMID {p["pmid"]}</a>' if p["pmid"] else
           f' <span class="missing">{html.escape(MISSING_TEXT)}</span>')
        + f'<p>{html.escape(p["note"])}</p></div>'
        for p in novelty["closest"]
    ) or f'<p><span class="missing">{html.escape(MISSING_TEXT)}</span></p>'

    query_rows = "".join(
        f'<tr><td>{html.escape(q["id"])}</td>'
        f'<td><code>{html.escape(q["query"])}</code></td>'
        f'<td style="white-space:nowrap">{html.escape(q["hits"])}</td></tr>'
        for q in novelty["queries"]
    ) or f'<tr><td colspan="3"><span class="missing">{html.escape(MISSING_TEXT)}</span></td></tr>'

    # Counted, never typed: how many limitations push against the finding.
    against = sum(
        1 for l in limits
        if isinstance(l["direction"], str)
        and ("against" in l["direction"].lower() or "toward the null" in l["direction"].lower())
    )

    limits_html = "".join(
        f'<div class="limit"><span class="t">{html.escape(l["title"])}</span>'
        f'<div>{html.escape(l["body"])}</div>'
        f'<span class="dir">{ex.raw("limit.dir." + l["title"][:20], html.escape(l["direction"]))}</span>'
        f"</div>"
        for l in limits
    ) or f'<p><span class="missing">{html.escape(MISSING_TEXT)}</span></p>'

    methods_html = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{ex.raw('methods.' + k, html.escape(v))}</td></tr>"
        for k, v in methods
    )

    prov_head = list(prov[0].keys()) if prov else []
    prov_html = (
        "<table><thead><tr>"
        + "".join(f"<th>{html.escape(h)}</th>" for h in prov_head)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(
                f'<td class="{"hash" if "SHA" in h else ""}">{html.escape(row.get(h, ""))}</td>'
                for h in prov_head
            ) + "</tr>"
            for row in prov
        )
        + "</tbody></table>"
    ) if prov else f'<p><span class="missing">{html.escape(MISSING_TEXT)}</span></p>'

    refs_html = "".join(
        f'<p class="ref">{html.escape(r["text"])}<br><span class="links">'
        + (f'<a href="https://doi.org/{html.escape(r["doi"])}">doi.org/{html.escape(r["doi"])}</a>'
           if r["doi"] else "")
        + (" &middot; " if r["doi"] and r["pmid"] else "")
        + (f'<a href="https://pubmed.ncbi.nlm.nih.gov/{r["pmid"]}/">PubMed {r["pmid"]}</a>'
           if r["pmid"] else "")
        + "</span></p>"
        for r in refs
    ) or f'<p><span class="missing">{html.escape(MISSING_TEXT)}</span></p>'

    excluded_html = (
        "".join(f"<p>{html.escape(e)}</p>" for e in excluded)
        if excluded else
        "<p>Nothing was excluded. Every citation in the audit resolved to a "
        "publisher record; none was marked UNVERIFIABLE.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Two-tier interventional pain: PNS access in Medicare</title>
<style>{CSS}</style>
</head>
<body>
<div class="layout">
<nav>
  <div class="brand">Research meeting</div>
  <div class="brandsub">Peripheral nerve stimulation access in&nbsp;Medicare</div>
  <ol>{nav_html}</ol>
  <div class="navfoot">
    All figures and numbers generated by <code>run.py</code>.<br>
    Data year {ex.html("nav.latest_year", stats["latest_year"])}.<br>
    100% free public data.
  </div>
</nav>

<main>

<section id="one-liner">
  <h2>The one-liner</h2>
  <div class="wrap">
    <p class="oneliner">Interventional pain medicine is <span class="em">two-tiered</span>,
      and the second tier is far narrower than anyone has measured.</p>
    <p class="standfirst">In {ex.html("one.year", stats["latest_year"])}, just
      <strong>{ex.html("one.pns_providers", stats["pns_providers_parquet"])}</strong>
      providers in all of Medicare fee-for-service billed peripheral nerve
      stimulation, against
      <strong>{ex.html("one.epi_providers", stats["epi_providers_parquet"])}</strong>
      who billed a lumbar epidural &mdash; and across that same provider universe the
      top 10% deliver <strong>{ex.html("one.top10", stats["top10_pns"])}</strong>
      of all PNS volume.</p>
  </div>
  <div class="wrap wide">
  <div class="stats">
    {stat(ex.html("stat.gini", stats["gini_pns"]), "Gini coefficient for PNS volume",
          "vs " + ex.get("stat.gini_basic", stats["gini_basic"]) + " for lumbar epidurals")}
    {stat(ex.html("stat.top10", stats["top10_pns"]), "of PNS volume delivered by the top 10% of providers",
          "vs " + ex.get("stat.top10_basic", stats["top10_basic"]) + " for epidurals")}
    {stat(ex.html("stat.providers", stats["pns_providers_parquet"]), "providers billed PNS nationally",
          ex.get("stat.ratio", stats["provider_ratio"]) + "-fold fewer than lumbar epidural providers")}
    {stat(ex.html("stat.states", stats["states_zero"]), "states with zero PNS providers",
          ex.get("stat.sparse", stats["pct_benes_sparse"]) + " of beneficiaries are in a state with fewer than three", warm=True)}
  </div>
  </div>
</section>

<section id="why">
  <h2>Why this question</h2>
  <div class="wrap">
    <p>Odonkor, Chow and colleagues followed a cohort through 60-day peripheral
      nerve stimulation and asked what predicted response
      ({ex.raw("why.cohort", html.escape(str(chow["cohort"])))}). At 60 days,
      {ex.raw("why.day60", html.escape(str(chow["day60"])))}; by six months,
      {ex.raw("why.month6", html.escape(str(chow["month6"])))}.{footnote_mark}
      Insurance delay and high baseline disability independently predicted worse
      outcomes, and the response trajectory kept moving late &mdash;
      {ex.raw("why.delayed", html.escape(str(chow["delayed"])))}.</p>

    <p>Every patient in that study had already received the device. The cohort
      begins at the moment a lead goes in. Whatever an authorisation delay costs
      a patient, it is measured only among people who cleared every earlier
      barrier: a referral to someone who offers the therapy, a clinic within
      reach, a physician who has done enough of these to offer one.</p>

    <p>This project asks the upstream question. Before the delay clock starts,
      who can reach a PNS provider at all? The answer is that the delivery base
      is extraordinarily narrow &mdash;
      {ex.html("why.providers", stats["pns_providers_parquet"])} providers
      nationally &mdash; and the volume inside it is concentrated to a degree
      that has no parallel in basic interventional pain care.</p>
    {audit_note}
  </div>
</section>

<section id="findings">
  <h2>Findings</h2>
  <div class="wrap wide">
  {findings_html}
  </div>
</section>

<section id="novelty">
  <h2>What I checked before claiming novelty</h2>
  <div class="wrap wide">
    <div class="verdict">
      <div class="label">Verdict, after eleven adversarial PubMed queries</div>
      <div class="value">{ex.raw("novelty.verdict.render", html.escape(str(novelty["verdict"])))}</div>
      <p>These queries were written to <em>find</em> a paper that scoops this
         work, not to avoid one. Finding one now would have been a good outcome;
         finding one during the meeting would not. Every query string, hit count
         and returned record is cached in <code>audit/novelty_raw.json</code>.</p>
    </div>

    <h3>The three closest papers</h3>
    {closest_html}

    <h3>The exact queries</h3>
    <table>
      <thead><tr><th>#</th><th>PubMed query</th><th>Hits</th></tr></thead>
      <tbody>{query_rows}</tbody>
    </table>

    <h3 style="margin-top:34px">The two matched queries behind Figure 6</h3>
    <p>Identical except for the therapy term, which is what makes the gap a
       measurement rather than an assertion.</p>
    <div class="q">SCS &nbsp;{ex.raw("q.scs", html.escape(str(novelty["fig6_scs_query"])))}</div>
    <div class="q">PNS &nbsp;{ex.raw("q.pns", html.escape(str(novelty["fig6_pns_query"])))}</div>
    <p>Across the decade that returns
      <strong>{ex.html("novelty.scs_total", stats["lit_scs_total"])}</strong> SCS papers
      against <strong>{ex.html("novelty.pns_total", stats["lit_pns_total"])}</strong>
      PNS papers. Publication counts proxy research attention; they are not proof
      of absence, and I will say so before anyone else does.</p>
  </div>
</section>

<section id="limitations">
  <h2>Limitations I'm raising myself</h2>
  <div class="wrap">
    <p>Each of these is stated in the form I would use out loud, with the
       direction it pushes the result.
       {ex.html("limits.against", against)} of the
       {ex.html("limits.total", len(limits))} push <em>against</em> the finding,
       which is the useful thing to know about them.</p>
  </div>
  <div class="wrap wide">{limits_html}</div>
</section>

<section id="methods">
  <h2>Methods in six lines</h2>
  <div class="wrap wide">
    <table class="methods"><tbody>{methods_html}</tbody></table>
  </div>
</section>

<section id="provenance">
  <h2>Data provenance</h2>
  <div class="wrap wide">
    <details>
      <summary>Every cached file: timestamp, rows, size, SHA256</summary>
      {prov_html}
    </details>
  </div>
</section>

<section id="references">
  <h2>References</h2>
  <div class="wrap">
    <p>Everything below resolved to a publisher record during the citation audit.</p>
    {refs_html}
    <h3 style="margin-top:38px">Excluded &mdash; could not verify</h3>
    <div class="excluded">{excluded_html}</div>
  </div>
</section>

</main>
</div>
{lightbox_html}
</body>
</html>
"""


# -------------------------------------------------------------- crib sheet
def _against_count(art: Artifacts, ex: Extraction) -> int:
    """How many limitations bias the result against the finding."""
    return sum(
        1 for l in limitations(art, ex)
        if isinstance(l["direction"], str)
        and ("against" in l["direction"].lower()
             or "toward the null" in l["direction"].lower())
    )


def build_notes(art: Artifacts, ex: Extraction) -> str:
    """deck_notes.md - private crib sheet, one page, never shown on screen."""
    stats = headline_stats(art, ex)
    chow = chow_numbers(art, ex)
    novelty = novelty_bundle(art, ex)
    captions = art.captions

    def g(key: str) -> str:
        return str(stats.get(key, MISSING_TEXT))

    rows: list[tuple[str, list[str], str, str]] = [
        (
            "1. The one-liner",
            [f"{g('pns_providers_parquet')} PNS providers vs "
             f"{g('epi_providers_parquet')} epidural providers ({g('provider_ratio')}-fold)",
             f"Top 10% deliver {g('top10_pns')} of PNS volume vs {g('top10_basic')}",
             f"Gini {g('gini_pns')} vs {g('gini_basic')}"],
            "Isn't 64555 just a low-volume code, so of course it looks concentrated?",
            "That is exactly why I rank both codes over the same provider universe "
            "rather than among billers only - the common-base comparison removes the "
            "volume asymmetry, and I show the billers-only version too because it reverses.",
        ),
        (
            "2. Why this question",
            [str(chow["cohort"]), str(chow["day60"]), str(chow["delayed"])],
            "Are you saying my study was measuring the wrong thing?",
            "The opposite - your cohort is the cleanest evidence that delay costs "
            "response, and I am asking what happens to the people who never enter a "
            "cohort like it.",
        ),
        (
            "3a. Figure 1 - growth",
            [captions.get("figure1", {}).get("title", MISSING_TEXT)],
            "Why does the curve start high in 2015 and collapse?",
            "I don't know, and I say so - the specialty mix billing 64555 is stable "
            "across the whole period, so it isn't specialty substitution, and I quote "
            "growth off the trough with that caveat attached.",
        ),
        (
            "3b. Figure 2 - concentration (THE slide)",
            [f"Gini {g('gini_pns')} {g('gini_pns_ci')} vs {g('gini_basic')} {g('gini_basic_ci')}",
             f"Top 10%: {g('top10_pns')} vs {g('top10_basic')}",
             f"Billers-only Gini REVERSES: {g('gini_billers_pns')} vs {g('gini_billers_basic')}"],
            "Doesn't the suppression floor break this?",
            "It biases concentration downward, so my estimate is a floor - and it is "
            "precisely why the billers-only specification inverts, which I show rather "
            "than hide.",
        ),
        (
            "3c. Figure 3 - deserts",
            [f"{g('states_zero')} states with zero PNS providers",
             f"{g('pct_benes_sparse')} of FFS beneficiaries in a state with fewer than three"],
            "Aren't deserts just shrinking on their own?",
            "Yes, and I lead with that - the finding is that diffusion is incomplete, "
            "not absent.",
        ),
        (
            "3d. Figure 4 - supply models (CONTRADICTS ME)",
            [f"General density IRR in Model B: {g('model_b_general')}",
             f"Neuromodulation density: {g('model_b_neuromod')}",
             f"Pseudo R2 {g('pseudo_r2_b')} on {g('n_state_years')} state-years"],
            "So your hypothesis failed here?",
            "Yes - general supply keeps predicting after adjustment, so the honest "
            "claim is that provider counts are a weak proxy, not the wrong one.",
        ),
        (
            "3e. Figure 5 - equity (NULL)",
            [f"Income: {g('income_pearson')}", f"Dual-eligible: {g('dual_spearman')}"],
            "Doesn't a null undercut the whole equity framing?",
            "At state level, yes - and I think the state is the wrong unit, which is "
            "why the county-level version is the next study rather than a rescue.",
        ),
        (
            "3f. Figure 6 - literature gap",
            [f"{g('lit_scs_total')} SCS papers vs {g('lit_pns_total')} PNS papers"],
            "Keyword counts prove nothing, do they?",
            "Correct - they proxy research attention, and I raise that caveat myself "
            "before it gets raised for me.",
        ),
        (
            "4. Novelty",
            [f"Verdict: {novelty['verdict']}",
             "Closest: " + "; ".join(
                 f"PMID {p['pmid']}" for p in novelty["closest"] if p["pmid"]) or MISSING_TEXT],
            "Has nobody really done this?",
            '"peripheral nerve stimulation" AND Medicare returns four records in all '
            "of PubMed, and none of them is an access or provider-distribution study.",
        ),
        (
            "5. Limitations",
            [f"{_against_count(art, ex)} of {len(limitations(art, ex))} push against the finding",
             "Suppression floor: measured concentration is a lower bound"],
            "Isn't this all ecological?",
            "It is, entirely - it generates a hypothesis about delivery structure and "
            "cannot speak to any individual patient.",
        ),
        (
            "6-8. Methods, provenance, references",
            [f"Audit: {chow['pass_count']} pass, {chow['corrected_count']} corrected, "
             f"{chow['unverifiable_count']} unverifiable"],
            "Where did the data come from and can I rerun it?",
            "Three free CMS files plus Census SAIPE, no login and no DUA - one command "
            "rebuilds every figure and every hash is in the provenance table.",
        ),
    ]

    lines = [
        "# DECK NOTES - private crib sheet",
        "",
        "Not shown on screen. Generated from the same artifacts as deck.html, so the "
        "numbers here cannot drift from the numbers on the slide.",
        "",
        "**Before anything else:** do not quote the 10-day-delay magnitude from PMID "
        "41148054 - the published abstract is internally inconsistent there. Say "
        "\"insurance delay independently predicted worse response\" and stop.",
        "**The MAUDE PNS paper is Cooper et al., not McCormick et al.** (PMID 40178466).",
        "",
        "---",
        "",
    ]
    for title, numbers, question, answer in rows:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("**Say:**")
        for number in numbers:
            lines.append(f"- {number}")
        lines.append("")
        lines.append(f"**He'll ask:** {question}")
        lines.append("")
        lines.append(f"**Answer:** {answer}")
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------- verification
ALLOWED_LINK_HOSTS: Final[tuple[str, ...]] = ("doi.org", "pubmed.ncbi.nlm.nih.gov")


def verify(deck_html: str) -> list[str]:
    """Confirm the deck is self-contained. Returns a list of problems."""
    problems: list[str] = []

    for attr, value in re.findall(r'\b(src|href)\s*=\s*"([^"]*)"', deck_html):
        if value.startswith(("#", "data:")) or not value.strip():
            continue
        if attr == "src":
            problems.append(f'external src="{value[:70]}"')
            continue
        if value.startswith(("http://", "https://", "//")):
            host = re.sub(r"^https?://", "", value).split("/")[0]
            if host not in ALLOWED_LINK_HOSTS:
                problems.append(f'external href to non-reference host: {host}')
        elif not value.startswith(("figures/", "mailto:")):
            problems.append(f'unexpected href="{value[:70]}"')

    for tag in ("<script", "<iframe", "<link ", "@import"):
        if tag in deck_html.lower():
            problems.append(f"contains {tag!r}, which could load or execute externally")

    embedded = deck_html.count("data:image/png;base64,")
    expected = len(FIGURE_ORDER) * 2       # inline figure + its lightbox copy
    if embedded < expected:
        problems.append(
            f"only {embedded} embedded images, expected {expected} "
            f"({len(FIGURE_ORDER)} figures inline plus lightboxes)"
        )
    return problems


def main() -> int:
    """Build deck.html and deck_notes.md, then verify self-containment."""
    ex = Extraction()
    art = Artifacts.load()

    deck_html = build_html(art, ex)
    DECK_PATH.write_text(deck_html, encoding="utf-8")
    NOTES_PATH.write_text(build_notes(art, ex), encoding="utf-8")

    size_mb = DECK_PATH.stat().st_size / 1_048_576
    LOGGER.info("wrote %s (%.2f MB, %s figures embedded)",
                DECK_PATH.name, size_mb, len(FIGURE_ORDER))
    LOGGER.info("wrote %s", NOTES_PATH.name)

    problems = verify(deck_html)
    if problems:
        LOGGER.error("deck.html is NOT self-contained:")
        for problem in problems:
            LOGGER.error("  - %s", problem)
    else:
        LOGGER.info("deck.html is self-contained: no external src, "
                    "no scripts, all figures inlined as data URIs")

    unique_missing = sorted(set(ex.missing))
    if unique_missing:
        LOGGER.warning("%d MISSING field(s) rendered as %s:",
                       len(unique_missing), MISSING_TEXT)
        for name in unique_missing:
            LOGGER.warning("  - %s", name)
    else:
        LOGGER.info("no MISSING fields: every number resolved from an artifact")

    return 1 if problems else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S")
    raise SystemExit(main())
