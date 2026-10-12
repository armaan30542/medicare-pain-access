"""Presentation-ready figures. Every number comes from src.analysis.

Design contract (applies to all six figures):
  * the title states the FINDING in plain English, not the variable names
  * >= 14pt body text, 18pt titles, >= 10x6 inches, legible at 50% zoom
  * white background, light horizontal gridlines only, no dual axes
  * Okabe-Ito colorblind-safe palette, at most four colors per figure
  * a one-line source footnote naming the dataset, data year, and access date
"""
from __future__ import annotations

import json
import logging
import textwrap
from pathlib import Path
from typing import Final, Sequence

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.analysis import ConcentrationResult, GradientResult, ModelResult  # noqa: E402
from src.constants import (  # noqa: E402
    AUDIT_DIR,
    DESERT_PROVIDER_THRESHOLD,
    FIGURES_DIR,
    INDEX_BASE_YEAR,
)

LOGGER: Final = logging.getLogger(__name__)

# Okabe-Ito, colorblind-safe.
BLUE: Final[str] = "#0072B2"
VERMILLION: Final[str] = "#D55E00"
GREEN: Final[str] = "#009E73"
ORANGE: Final[str] = "#E69F00"
GREY: Final[str] = "#595959"
LIGHT_GREY: Final[str] = "#BBBBBB"

TITLE_SIZE: Final[int] = 19
SUBTITLE_SIZE: Final[int] = 14
# Wrap widths in characters, tuned to the 12-inch canvas at each font size so
# that no line can run off the right edge of the exported image.
TITLE_WRAP: Final[int] = 68
SUBTITLE_WRAP: Final[int] = 96
FOOTNOTE_WRAP: Final[int] = 124
LINE_HEIGHT: Final[float] = 0.030
BODY_SIZE: Final[int] = 15
FOOTNOTE_SIZE: Final[int] = 11
FIGSIZE: Final[tuple[float, float]] = (12.0, 7.0)
DPI: Final[int] = 300

CMS_PROV_SVC: Final[str] = (
    "CMS Medicare Physician & Other Practitioners - by Provider and Service"
)
CMS_GEOVAR: Final[str] = "CMS Medicare Geographic Variation (National/State/County)"

# Every rendered figure records its own headline, subtitle and footnote here so
# that downstream consumers (the deck builder) can quote the figure's own words
# instead of re-deriving them and drifting out of sync with the image.
CAPTION_MANIFEST: Final[Path] = AUDIT_DIR / "figure_captions.json"


def apply_style() -> None:
    """Set global matplotlib defaults. Nothing relies on matplotlib's own sizing."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.size": BODY_SIZE,
            "axes.titlesize": TITLE_SIZE,
            "axes.labelsize": BODY_SIZE,
            "xtick.labelsize": BODY_SIZE,
            "ytick.labelsize": BODY_SIZE,
            "legend.fontsize": BODY_SIZE,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": GREY,
            "axes.linewidth": 1.1,
            "grid.color": "#E4E4E4",
            "grid.linewidth": 0.9,
            "lines.linewidth": 3.0,
            "figure.autolayout": False,
            # Fixed salt so SVG element IDs are identical on every rebuild.
            "svg.hashsalt": "medicare-access-pipeline",
        }
    )


def _wrap(text: str, width: int) -> tuple[str, int]:
    """Hard-wrap text to `width` characters, honouring existing newlines."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    return "\n".join(lines), len(lines)


def _finish(fig: plt.Figure, ax: plt.Axes, title: str, subtitle: str,
            footnote: str, stem: str, left: float = 0.085,
            out_dir: Path | None = None,
            manifest: Path | None = None,
            extra_top: float = 0.0) -> list[Path]:
    """Apply shared chrome and write PNG + SVG.

    Title, subtitle and footnote are wrapped and the axes rectangle is sized
    from the resulting line counts, so no text can overflow the canvas however
    long the interpolated numbers turn out to be.
    """
    title_text, title_lines = _wrap(title, TITLE_WRAP)
    subtitle_text, subtitle_lines = _wrap(subtitle, SUBTITLE_WRAP)
    footnote_text, footnote_lines = _wrap(footnote, FOOTNOTE_WRAP)

    # extra_top reserves room for per-panel titles on multi-panel figures.
    top = 0.930 - LINE_HEIGHT * (1.55 * title_lines + 1.05 * subtitle_lines) - extra_top
    # Reserve room for the x-axis label AND every wrapped footnote line.
    bottom = 0.105 + LINE_HEIGHT * 0.80 * footnote_lines

    ax.set_title("")
    fig.text(0.02, 0.972, title_text, fontsize=TITLE_SIZE, fontweight="bold",
             ha="left", va="top", color="#111111")
    fig.text(0.02, 0.968 - LINE_HEIGHT * 1.55 * title_lines, subtitle_text,
             fontsize=SUBTITLE_SIZE, ha="left", va="top", color=GREY)
    fig.text(0.02, 0.012, footnote_text, fontsize=FOOTNOTE_SIZE, ha="left",
             va="bottom", color=GREY)
    ax.yaxis.grid(True, alpha=0.9)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=0.975)

    _record_caption(stem, title, subtitle, footnote, manifest)

    target_dir = out_dir or FIGURES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for suffix in ("png", "svg"):
        path = target_dir / f"{stem}.{suffix}"
        # No render timestamp, so a rebuild is byte-identical to the original.
        metadata = {"Date": None} if suffix == "svg" else None
        fig.savefig(path, dpi=DPI, format=suffix, metadata=metadata)
        written.append(path)
    plt.close(fig)
    LOGGER.info("wrote %s.png and %s.svg", stem, stem)
    return written


def _record_caption(stem: str, title: str, subtitle: str, footnote: str,
                    path: Path | None = None) -> None:
    """Append this figure's headline/subtitle/footnote to a caption manifest."""
    target = path or CAPTION_MANIFEST
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, str]] = {}
    if target.exists():
        manifest = json.loads(target.read_text())
    manifest[stem] = {"title": title, "subtitle": subtitle, "footnote": footnote}
    target.write_text(json.dumps(manifest, indent=1))


def _source(dataset: str, years: str, accessed: str) -> str:
    return f"Source: {dataset}, data years {years}. Accessed {accessed}. Analysis: 100% free public data, no license required."


# ------------------------------------------------------------------ Fig 1
def figure1(indexed: pd.DataFrame, inflection: int, accessed: str,
            pns_raw: pd.DataFrame) -> list[Path]:
    """PNS growth against SCS trial and lumbar epidural, indexed to 2017."""
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    series = [
        ("64555", "Peripheral nerve stimulation (64555)", VERMILLION),
        ("63650", "Spinal cord stimulation trial (63650)", BLUE),
        ("62323", "Lumbar epidural steroid injection (62323)", GREY),
    ]
    for code, label, color in series:
        block = indexed.loc[indexed["hcpcs_code"] == code].sort_values("year")
        ax.plot(block["year"], block["index_value"], color=color, label=label,
                marker="o", markersize=7, zorder=3)
        last = block.iloc[-1]
        ax.annotate(f"{last['index_value']:.0f}",
                    xy=(last["year"], last["index_value"]),
                    xytext=(8, 0), textcoords="offset points",
                    fontsize=BODY_SIZE, fontweight="bold", color=color,
                    va="center")

    ax.axhline(100, color=LIGHT_GREY, linewidth=1.4, linestyle="--", zorder=1)
    pns = indexed.loc[indexed["hcpcs_code"] == "64555"].set_index("year")
    trough = float(pns.loc[inflection, "index_value"])
    ax.annotate(
        f"{inflection} trough - PNS turns here\nand grows every year after",
        xy=(inflection, trough),
        xytext=(inflection + 0.35, trough + 95),
        fontsize=BODY_SIZE - 1, color=VERMILLION, fontweight="bold",
        arrowprops={"arrowstyle": "->", "color": VERMILLION, "linewidth": 2},
    )
    ax.set_xlabel("")
    ax.set_ylabel(f"Services per 100,000 FFS beneficiaries\n({INDEX_BASE_YEAR} = 100)")
    ax.set_xticks(sorted(indexed["year"].unique()))
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.0, 0.99))

    first = pns_raw.iloc[0]
    last = pns_raw.iloc[-1]
    trough_row = pns_raw.loc[pns_raw["services_per_100k"].idxmin()]
    fold = last["services_per_100k"] / trough_row["services_per_100k"]
    versus_first = (last["services_per_100k"] / first["services_per_100k"] - 1) * 100
    return _finish(
        fig, ax,
        f"PNS volume has risen {fold:.0f}-fold since its {int(trough_row['year'])} trough",
        f"But it is only {versus_first:.0f}% above its {int(first['year'])} level: 64555 billing collapsed between 2016 and {int(trough_row['year'])} "
        f"before growing every year since. Epidural injections declined over the same period.",
        _source(CMS_PROV_SVC + " + " + CMS_GEOVAR, f"{INDEX_BASE_YEAR}-{int(indexed['year'].max())}", accessed)
        + "  CPT 62323 was created in 2017, so all series are indexed to 2017.",
        "figure1",
    )


# ------------------------------------------------------------------ Fig 2
def figure2(pns: ConcentrationResult, basic: ConcentrationResult,
            pns_billers: ConcentrationResult, basic_billers: ConcentrationResult,
            accessed: str) -> list[Path]:
    """Lorenz curves over the common provider universe. The centerpiece."""
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)

    ax.plot([0, 1], [0, 1], color=LIGHT_GREY, linestyle="--", linewidth=1.8,
            label="Line of equality (every provider equal)", zorder=1)
    ax.plot(basic.lorenz_x, basic.lorenz_y, color=GREY, zorder=2,
            label=(f"Lumbar epidural 62323  ·  Gini {basic.gini:.3f} "
                   f"[{basic.gini_ci_low:.3f}-{basic.gini_ci_high:.3f}]"))
    ax.plot(pns.lorenz_x, pns.lorenz_y, color=VERMILLION, zorder=3,
            label=(f"PNS 64555  ·  Gini {pns.gini:.3f} "
                   f"[{pns.gini_ci_low:.3f}-{pns.gini_ci_high:.3f}]"))
    ax.fill_between(pns.lorenz_x, pns.lorenz_y, np.asarray(pns.lorenz_x),
                    color=VERMILLION, alpha=0.07, zorder=0)

    ax.text(
        0.035, 0.955,
        f"The top 10% of providers deliver\n"
        f"{pns.top_decile_share*100:.0f}% of all PNS volume,\n"
        f"versus {basic.top_decile_share*100:.0f}% for epidural injections.",
        transform=ax.transAxes, va="top", ha="left",
        fontsize=BODY_SIZE + 1, fontweight="bold", color="#111111", zorder=5,
        bbox={"boxstyle": "round,pad=0.55", "facecolor": "white",
              "edgecolor": VERMILLION, "linewidth": 1.6},
    )
    ax.axvline(0.90, color=LIGHT_GREY, linewidth=1.2, zorder=1)


    ax.set_xlabel("Cumulative share of providers, ranked lowest to highest volume")
    ax.set_ylabel("Cumulative share of volume")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_xticklabels([f"{v:.0%}" for v in np.arange(0, 1.01, 0.2)])
    ax.set_yticklabels([f"{v:.0%}" for v in np.arange(0, 1.01, 0.2)])
    ax.legend(loc="lower right", fontsize=BODY_SIZE - 1, frameon=True,
              facecolor="white", edgecolor="none", framealpha=0.96)

    footnote = (
        _source(CMS_PROV_SVC, str(pns.year), accessed)
        + f"  Ranked over the common universe of {pns.n_providers:,} providers billing any study code in {pns.year}; "
        + "Gini CIs are 2,000-resample percentile bootstraps.\n"
        + "IMPORTANT: CMS suppresses any provider-code row with 10 or fewer beneficiaries, so low-volume providers are invisible. "
        + "That truncation biases measured concentration DOWNWARD - these estimates are conservative."
    )
    return _finish(
        fig, ax,
        f"The top 10% of providers deliver {pns.top_decile_share*100:.0f}% of all PNS volume",
        f"Gini {pns.gini:.2f} for PNS versus {basic.gini:.2f} for epidurals across the same {pns.n_providers:,} providers. "
        f"Only {pns_billers.n_providers:,} providers billed PNS at all, versus {basic_billers.n_providers:,} for epidurals.",
        footnote, "figure2",
    )


# ------------------------------------------------------------------ Fig 3
def figure3(deserts: pd.DataFrame, accessed: str) -> list[Path]:
    """Access deserts: states with no PNS provider, and the lives inside them."""
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    years = deserts["year"].to_numpy()
    width = 0.4
    positions = np.arange(len(years))

    bars_a = ax.bar(positions - width / 2, deserts["states_zero_pns"], width,
                    color=VERMILLION, label="States with ZERO PNS providers (count, of 51)")
    bars_b = ax.bar(positions + width / 2, deserts["pct_benes_sparse_pns"], width,
                    color=BLUE,
                    label=f"% of FFS beneficiaries in a state with < {DESERT_PROVIDER_THRESHOLD} PNS providers")

    for bars, fmt in ((bars_a, "{:.0f}"), (bars_b, "{:.0f}%")):
        for bar in bars:
            ax.annotate(fmt.format(bar.get_height()),
                        xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 4), textcoords="offset points",
                        ha="center", fontsize=FOOTNOTE_SIZE + 1, color=GREY)

    ax.set_xticks(positions)
    ax.set_xticklabels([str(y) for y in years])
    ax.set_ylabel("States (count)   ·   Beneficiaries (%)")
    ax.set_ylim(0, 112)
    ax.legend(loc="upper left", fontsize=BODY_SIZE - 2, frameon=True,
              facecolor="white", edgecolor="none", framealpha=0.96,
              borderpad=0.7)

    last = deserts.iloc[-1]
    return _finish(
        fig, ax,
        f"{int(last['states_zero_pns'])} states still had no Medicare provider billing PNS in {int(last['year'])}",
        f"Deserts are shrinking fast - but {last['pct_benes_sparse_pns']:.0f}% of fee-for-service beneficiaries "
        f"({int(last['benes_sparse_pns']):,} people) still live in a state with fewer than {DESERT_PROVIDER_THRESHOLD} PNS providers.",
        _source(CMS_PROV_SVC + " + " + CMS_GEOVAR, f"{int(years.min())}-{int(years.max())}", accessed)
        + "  A state counts as zero when no provider clears the 11-beneficiary reporting floor, which is itself an access signal.",
        "figure3",
    )


# ------------------------------------------------------------------ Fig 4
def figure4(models: dict[str, ModelResult], accessed: str, years: str) -> list[Path]:
    """Forest plot of incidence rate ratios from the two negative binomial models."""
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)

    label_map = {
        "basic_density_per_100k": "General pain\nprovider density",
        "neuromod_density_per_100k": "Neuromodulation\nprovider density",
    }
    rows: list[tuple[str, str, dict[str, float], str]] = []
    for key in ("A", "B"):
        model = models[key]
        for term, values in model.terms.items():
            rows.append((f"Model {key}", label_map[term], values,
                         VERMILLION if key == "A" else BLUE))

    positions = np.arange(len(rows))[::-1]
    for pos, (model_name, term_label, values, color) in zip(positions, rows):
        ax.plot([values["irr_low"], values["irr_high"]], [pos, pos],
                color=color, linewidth=3.2, solid_capstyle="round", zorder=2)
        ax.plot(values["irr"], pos, "o", color=color, markersize=13, zorder=3)
        ax.annotate(
            f"IRR {values['irr']:.3f}  [{values['irr_low']:.3f}-{values['irr_high']:.3f}]   p = {values['p_value']:.3f}",
            xy=(values["irr_high"], pos), xytext=(12, 0),
            textcoords="offset points", va="center", fontsize=BODY_SIZE - 1,
            color="#111111",
        )

    ax.axvline(1.0, color=GREY, linestyle="--", linewidth=1.6, zorder=1)
    ax.set_yticks(positions)
    ax.set_yticklabels([f"{m}\n{t}" for m, t, _, _ in rows], fontsize=BODY_SIZE - 1)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.set_xlabel("Incidence rate ratio for PNS (64555) service volume, 95% CI")
    ax.set_xlim(0.95, max(v["irr_high"] for _, _, v, _ in rows) + 0.30)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, alpha=0.9)

    a, b = models["A"], models["B"]
    return _finish(
        fig, ax,
        "General pain-physician supply predicts PNS volume - but only weakly, and it survives adjustment",
        f"Model A: general density IRR {a.terms['basic_density_per_100k']['irr']:.3f}. "
        f"Model B adds neuromodulation-capable density: general density barely moves "
        f"({b.terms['basic_density_per_100k']['irr']:.3f}) and stays significant. "
        f"This does NOT support the hypothesis that general supply is the wrong denominator.",
        _source(CMS_PROV_SVC + " + " + CMS_GEOVAR, years, accessed)
        + f"  Negative binomial, log FFS-beneficiary offset, year fixed effects, SE clustered on state. "
        + f"N = {b.n_obs} state-years, {b.n_clusters} clusters. Pseudo R2: A = {a.pseudo_r2:.3f}, B = {b.pseudo_r2:.3f}. "
        + f"Overdispersion alpha = {b.alpha:.2f} (Poisson would require alpha = 0).",
        "figure4", left=0.175,
    )


# ------------------------------------------------------------------ Fig 5
def _scatter_gradient(result: GradientResult, xlabel: str, title: str,
                      subtitle: str, footnote: str, stem: str,
                      x_formatter) -> list[Path]:
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    table = result.table.copy()
    x = table[result.covariate].to_numpy(dtype=float)
    y = table["advanced_to_basic"].to_numpy(dtype=float)

    ax.scatter(x, y, s=95, color=BLUE, alpha=0.75, zorder=3, edgecolor="white",
               linewidth=1.2)

    grid = np.linspace(x.min(), x.max(), 200)
    predicted = result.intercept + result.slope * grid
    residual = y - (result.intercept + result.slope * x)
    dof = max(len(x) - 2, 1)
    sigma = float(np.sqrt(np.sum(residual ** 2) / dof))
    sxx = float(np.sum((x - x.mean()) ** 2))
    se = sigma * np.sqrt(1.0 / len(x) + (grid - x.mean()) ** 2 / sxx)
    ax.plot(grid, predicted, color=VERMILLION, linewidth=2.8, zorder=4)
    ax.fill_between(grid, predicted - 1.96 * se, predicted + 1.96 * se,
                    color=VERMILLION, alpha=0.14, zorder=2,
                    label="OLS fit with 95% confidence band")

    ranked = table.sort_values("advanced_to_basic")
    for _, row in pd.concat([ranked.head(5), ranked.tail(5)]).iterrows():
        ax.annotate(row["state"], xy=(row[result.covariate], row["advanced_to_basic"]),
                    xytext=(7, 5), textcoords="offset points",
                    fontsize=BODY_SIZE - 2, fontweight="bold", color="#111111")

    ax.set_xlabel(xlabel)
    ax.set_ylabel("PNS services per 1,000 lumbar epidural services")
    ax.xaxis.set_major_formatter(x_formatter)
    ax.legend(frameon=False, loc="upper left", fontsize=BODY_SIZE - 1)
    return _finish(fig, ax, title, subtitle, footnote, stem)


def figure5(result: GradientResult, accessed: str) -> list[Path]:
    """Advanced-to-basic ratio against state median household income."""
    verdict = "no detectable" if result.pearson_p >= 0.05 else "a"
    return _scatter_gradient(
        result,
        "State median household income (SAIPE)",
        f"State income shows {verdict} relationship with PNS access",
        f"Pearson r = {result.pearson_r:.3f} (p = {result.pearson_p:.2f}); "
        f"Spearman rho = {result.spearman_rho:.3f} (p = {result.spearman_p:.2f}); n = {result.n_states} states. "
        f"The expected income gradient is NOT present in these data.",
        _source(CMS_PROV_SVC, str(result.year), accessed)
        + f"  Income: US Census Small Area Income and Poverty Estimates, {result.year}. "
        + "SAIPE replaces the ACS API, which now requires a key for every request.",
        "figure5",
        matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"),
    )


def figure5b(result: GradientResult, accessed: str) -> list[Path]:
    """Sensitivity: dual-eligible share instead of income."""
    verdict = "no detectable" if result.pearson_p >= 0.05 else "a"
    return _scatter_gradient(
        result,
        "Percent of Medicare beneficiaries who are dual-eligible",
        f"Dual-eligible share shows {verdict} linear relationship with PNS access",
        f"Pearson r = {result.pearson_r:.3f} (p = {result.pearson_p:.2f}); "
        f"Spearman rho = {result.spearman_rho:.3f} (p = {result.spearman_p:.2f}); n = {result.n_states} states. "
        f"The rank correlation leans negative but does not reach significance.",
        _source(CMS_PROV_SVC + " + " + CMS_GEOVAR, str(result.year), accessed)
        + "  Dual-eligible share is BENE_DUAL_PCT from the CMS Geographic Variation file.",
        "figure5b",
        matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"),
    )


# ------------------------------------------------------------------ Fig 6
def figure6(counts: dict, queries: dict[str, str], accessed: str) -> list[Path]:
    """Publication counts, SCS vs PNS access/utilization queries, by year."""
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    years = sorted(int(y) for y in counts["SCS"])
    scs = [counts["SCS"][str(y)] if str(y) in counts["SCS"] else counts["SCS"][y] for y in years]
    pns = [counts["PNS"][str(y)] if str(y) in counts["PNS"] else counts["PNS"][y] for y in years]

    positions = np.arange(len(years))
    height = 0.4
    ax.barh(positions + height / 2, scs, height, color=BLUE,
            label="Spinal cord stimulation - access / utilization query")
    ax.barh(positions - height / 2, pns, height, color=VERMILLION,
            label="Peripheral nerve stimulation - access / utilization query")
    for pos, value in zip(positions + height / 2, scs):
        ax.annotate(str(value), xy=(value, pos), xytext=(5, 0),
                    textcoords="offset points", va="center",
                    fontsize=FOOTNOTE_SIZE + 1, color=GREY)
    for pos, value in zip(positions - height / 2, pns):
        ax.annotate(str(value), xy=(value, pos), xytext=(5, 0),
                    textcoords="offset points", va="center",
                    fontsize=FOOTNOTE_SIZE + 1, color=GREY)

    ax.set_yticks(positions)
    ax.set_yticklabels([str(y) for y in years])
    ax.set_xlabel("Indexed PubMed publications")
    ax.invert_yaxis()
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, alpha=0.9)
    ax.set_xlim(0, max(scs) * 1.18)
    ax.legend(loc="upper right", fontsize=BODY_SIZE - 2, frameon=True,
              facecolor="white", edgecolor="none", framealpha=0.96, borderpad=0.7)

    ratio = sum(scs) / max(sum(pns), 1)
    return _finish(
        fig, ax,
        f"Spinal cord stimulation access research outnumbers PNS access research {ratio:.0f} to 1",
        f"Across {years[0]}-{years[-1]}: {sum(scs)} SCS papers versus {sum(pns)} PNS papers on matched access/utilization queries.",
        f"Source: NCBI PubMed E-utilities esearch, accessed {accessed}. Exact queries (identical except the therapy term):\n"
        f'SCS: {queries["SCS"]}\nPNS: {queries["PNS"]}\n'
        "Caveat: publication counts from a keyword query proxy research attention; they are not proof of absence.",
        "figure6",
    )
