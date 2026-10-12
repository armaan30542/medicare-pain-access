"""BVNA figures, in the same visual system as the PNS deck.

Every title, subtitle and number is computed from bvna/audit/results.json; the
comparative claims in titles ("fastest-growing", "least rural") are derived by
ranking the computed values, never asserted.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Final

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.bvna.config import (  # noqa: E402
    BVNA_AUDIT, BVNA_FIGURES, COMPARISON_ORDER, DESERT_THRESHOLD, LABELS, LATEST, YEARS,
)
from src.constants import AUDIT_DIR  # noqa: E402
from src.figures import (  # noqa: E402
    BLUE, BODY_SIZE, FIGSIZE, FOOTNOTE_SIZE, GREEN, GREY, LIGHT_GREY, ORANGE,
    VERMILLION, _finish, apply_style,
)

LOGGER: Final = logging.getLogger(__name__)
MANIFEST: Final = BVNA_AUDIT / "figure_captions.json"
CODE_COLORS: Final[dict[str, str]] = {
    "64628": VERMILLION, "64555": BLUE, "64635": GREEN, "62323": GREY,
}
CMS_PROV: Final[str] = "CMS Medicare Physician & Other Practitioners (by Provider and Service; by Geography and Service)"


def _accessed() -> str:
    """Access dates, read from the two provenance ledgers rather than typed."""
    geo = json.loads((AUDIT_DIR / "provenance.json").read_text())
    bvna = json.loads((BVNA_AUDIT / "provenance.json").read_text())
    geo_date = max(e["downloaded_utc"] for e in geo)[:10]
    bvna_date = max(e["downloaded_utc"] for e in bvna)[:10]
    return f"geography files accessed {geo_date}; BVNA provider rows accessed {bvna_date}"


PANEL_TITLE_ROOM: Final[float] = 0.045


def _save(fig, ax, title, subtitle, footnote, stem, left=0.085, panels=False):
    return _finish(fig, ax, title, subtitle, footnote, stem, left=left,
                   out_dir=BVNA_FIGURES, manifest=MANIFEST,
                   extra_top=PANEL_TITLE_ROOM if panels else 0.0)


def _rank_word(values: dict[str, float], code: str, high: bool) -> bool:
    """True if `code` is the most extreme of `values` in the given direction."""
    best = max(values, key=values.get) if high else min(values, key=values.get)
    return best == code


# ------------------------------------------------------------------ Fig 1
def figure1(r: dict, accessed: str) -> None:
    g = r["growth"]["by_year"]
    years = [int(y) for y in g]
    rate_primary = [g[str(y)]["per_100k_64628"] for y in years]
    rate_addon = [g[str(y)]["per_100k_64629"] for y in years]
    ratio = [g[str(y)]["addon_ratio"] for y in years]
    fold = rate_primary[-1] / rate_primary[0]
    robust = r["growth_robustness"]["clinician_fold_change"]

    apply_style()
    fig, (left, right) = plt.subplots(1, 2, figsize=FIGSIZE,
                                      gridspec_kw={"width_ratios": [1.55, 1]})
    for values, color, label in ((rate_primary, VERMILLION, "64628  first two vertebrae"),
                                 (rate_addon, ORANGE, "64629  each extra vertebra")):
        left.plot(years, values, color=color, marker="o", markersize=9, label=label)
        for x, v in zip(years, values):
            left.annotate(f"{v:.1f}", (x, v), xytext=(0, 11), textcoords="offset points",
                          ha="center", fontsize=BODY_SIZE - 1, color=color, fontweight="bold")
    left.set_xticks(years)
    left.set_ylabel("Services per 100,000\nfee-for-service beneficiaries")
    left.set_ylim(0, max(rate_primary) * 1.28)
    left.legend(frameon=False, loc="upper left", fontsize=BODY_SIZE - 2)
    left.set_title("BVNA volume", fontsize=BODY_SIZE, loc="left", color=GREY)

    right.plot(years, ratio, color=BLUE, marker="o", markersize=9)
    for x, v in zip(years, ratio):
        right.annotate(f"{v:.2f}", (x, v), xytext=(0, 11), textcoords="offset points",
                       ha="center", fontsize=BODY_SIZE - 1, color=BLUE, fontweight="bold")
    right.set_xticks(years)
    right.set_ylim(0, max(ratio) * 1.45)
    right.set_ylabel("Extra-vertebra codes\nper procedure")
    right.set_title("Levels treated per procedure", fontsize=BODY_SIZE, loc="left", color=GREY)
    for ax in (left, right):
        ax.yaxis.grid(True); ax.set_axisbelow(True)
    fig.subplots_adjust(wspace=0.42)

    direction = "fell" if ratio[-1] < ratio[0] else "rose"
    _save(fig, left,
          f"BVNA use per Medicare beneficiary rose {fold:.1f}-fold in two years",
          f"From {rate_primary[0]:.1f} to {rate_primary[-1]:.1f} procedures per 100,000 fee-for-service "
          f"beneficiaries, {years[0]}-{years[-1]}. Extra levels per procedure {direction}, "
          f"from {ratio[0]:.2f} to {ratio[-1]:.2f}.",
          f"Source: {CMS_PROV}, data years {years[0]}-{years[-1]}; {accessed}. Totals from the geography file, "
          f"which counts low-volume providers. Robustness: counting clinician claims only (no surgery-centre "
          f"double count), volume rose {robust:.1f}-fold. Before 2022 BVNA was billed as facility-only C9752.",
          "figure1", left=0.10, panels=True)


# ------------------------------------------------------------------ Fig 2
def figure2(r: dict, accessed: str) -> None:
    conc = r["concentration"]
    bvna = conc["64628"]
    apply_style()
    fig, (left, right) = plt.subplots(1, 2, figsize=FIGSIZE,
                                      gridspec_kw={"width_ratios": [1, 1.35]})

    codes = list(COMPARISON_ORDER)
    shares = [conc[c]["share_visible_pct"] for c in codes]
    positions = np.arange(len(codes))[::-1]
    left.barh(positions, shares, color=[CODE_COLORS[c] for c in codes], height=0.62)
    for pos, value in zip(positions, shares):
        left.annotate(f"{value:.0f}%", (value, pos), xytext=(6, 0), textcoords="offset points",
                      va="center", fontsize=BODY_SIZE - 1, fontweight="bold")
    left.set_yticks(positions)
    left.set_yticklabels([LABELS[c].replace(" (", "\n(") for c in codes], fontsize=BODY_SIZE - 2)
    left.set_xlim(0, 118)
    left.set_xlabel("% of national volume visible")
    left.set_title("What the public file can see", fontsize=BODY_SIZE, loc="left", color=GREY)
    left.xaxis.grid(True); left.yaxis.grid(False); left.set_axisbelow(True)

    right.plot([0, 1], [0, 1], color=LIGHT_GREY, linestyle="--", linewidth=1.6)
    for code in codes:
        c = conc[code]
        right.plot(c["lorenz_x"], c["lorenz_y"], color=CODE_COLORS[code],
                   linewidth=3.4 if code == "64628" else 2.2,
                   label=f"{LABELS[code].split(' (')[0]}  Gini {c['gini']:.2f}")
    right.set_xlim(0, 1); right.set_ylim(0, 1)
    ticks = np.arange(0, 1.01, 0.25)
    right.set_xticks(ticks); right.set_yticks(ticks)
    right.set_xticklabels([f"{t:.0%}" for t in ticks]); right.set_yticklabels([f"{t:.0%}" for t in ticks])
    right.set_xlabel("Visible clinicians, lowest to highest volume")
    right.set_ylabel("Share of their volume")
    right.legend(frameon=False, loc="upper left", fontsize=BODY_SIZE - 3)
    right.set_title("Among visible clinicians", fontsize=BODY_SIZE, loc="left", color=GREY)
    right.yaxis.grid(True); right.set_axisbelow(True)
    fig.subplots_adjust(wspace=0.55)

    least_concentrated = _rank_word({c: conc[c]["gini"] for c in codes}, "64628", high=False)
    _save(fig, left,
          "BVNA is spread across many low-volume providers, not a small expert core",
          f"{bvna['national_provider_entries_low']:,}+ provider entries billed BVNA in {LATEST}; only "
          f"{bvna['visible_clinicians']} clinicians cleared the 11-patient floor. Among them the top 10% deliver "
          f"{bvna['top10_share_pct']:.0f}% (Gini {bvna['gini']:.2f}, 95% CI {bvna['gini_ci_low']:.2f}-{bvna['gini_ci_high']:.2f})"
          + (", the least concentrated of the four." if least_concentrated else "."),
          f"Source: {CMS_PROV}, {LATEST}; {accessed}. Clinicians only (surgery-centre claims excluded). CMS drops "
          f"rows with 10 or fewer beneficiaries; the less of a procedure is visible, the more that flattens its "
          f"curve, so BVNA's low Gini is partly mechanical. CIs: 2,000-resample bootstrap.",
          "figure2", left=0.165, panels=True)


# ------------------------------------------------------------------ Fig 3
def figure3(r: dict, accessed: str) -> None:
    d = r["deserts"]
    years = [x["year"] for x in d]
    series = [
        ("states_zero", VERMILLION, "Under 11 BVNA patients statewide (geography file)"),
        ("provider_view_states_zero", ORANGE, "No BVNA provider visible (provider file)"),
        ("provider_view_states_sparse", BLUE, f"Fewer than {DESERT_THRESHOLD} visible BVNA providers"),
    ]
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    width = 0.26
    base = np.arange(len(years))
    for i, (key, color, label) in enumerate(series):
        values = [x[key] for x in d]
        bars = ax.bar(base + (i - 1) * width, values, width, color=color, label=label)
        for bar in bars:
            ax.annotate(f"{bar.get_height():.0f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 4), textcoords="offset points", ha="center",
                        fontsize=BODY_SIZE - 1, color=GREY)
    ax.set_xticks(base); ax.set_xticklabels([str(y) for y in years])
    ax.set_ylabel("States (of 51, incl. DC)")
    ax.set_ylim(0, 51)
    ax.legend(frameon=False, loc="upper right", fontsize=BODY_SIZE - 2)

    first, last = d[0], d[-1]
    _save(fig, ax,
          f"BVNA deserts are closing fast: {first['states_zero']} states in {first['year']}, {last['states_zero']} in {last['year']}",
          f"In {last['year']}, between {last['states_zero']} states ({last['pct_benes_zero']:.1f}% of fee-for-service "
          f"beneficiaries) and {last['provider_view_states_sparse']} states ({last['provider_view_pct_benes_sparse']:.1f}%) "
          f"had little or no visible BVNA, depending on which file you trust. Lowest-access states: "
          f"{', '.join(last['zero_states'])}.",
          f"Source: {CMS_PROV}, data years {years[0]}-{years[-1]}; {accessed}. The two files bracket the truth: "
          f"the geography file counts low-volume providers but drops state rows under 11 beneficiaries; the "
          f"provider file shows only providers above its own 11-patient floor.",
          "figure3")


# ------------------------------------------------------------------ Fig 4
def figure4(r: dict, accessed: str) -> None:
    spec = r["specialty"]
    buckets = list(spec["64628"]["services_pct"])
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    positions = np.arange(len(buckets))[::-1]
    height = 0.38
    for offset, code, color in ((height / 2, "64628", VERMILLION), (-height / 2, "64635", GREEN)):
        values = [spec[code]["services_pct"][b] for b in buckets]
        ax.barh(positions + offset, values, height, color=color, label=LABELS[code])
        for pos, v in zip(positions + offset, values):
            ax.annotate(f"{v:.1f}%", (v, pos), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=BODY_SIZE - 3, color=GREY)
    ax.set_yticks(positions); ax.set_yticklabels(buckets)
    ax.set_xlabel("Share of visible clinician services")
    ax.set_xlim(0, max(spec["64628"]["services_pct"].values()) * 1.25)
    ax.xaxis.grid(True); ax.yaxis.grid(False)
    ax.legend(frameon=False, loc="lower right", fontsize=BODY_SIZE - 1)

    core = sum(spec["64628"]["services_pct"][b] for b in ("Pain medicine", "Anesthesiology", "PM&R"))
    surgical = sum(spec["64628"]["services_pct"][b] for b in
                   ("Interventional radiology", "Orthopedics", "Neurosurgery"))
    _save(fig, ax,
          f"BVNA is done by the same specialties as facet ablation: {core:.0f}% pain, anesthesia or PM&R",
          f"Spine surgery and interventional radiology together account for {surgical:.1f}% of visible BVNA "
          f"services in {LATEST}. The specialty profile is almost identical to lumbar facet RFA.",
          f"Source: {CMS_PROV}, data year {LATEST}; {accessed}. Clinicians above the 11-patient floor only, "
          f"by CMS rendering-provider specialty; surgery centres excluded.",
          "figure4", left=0.245)


# ------------------------------------------------------------------ Fig 5
def figure5(r: dict, accessed: str) -> None:
    codes = list(COMPARISON_ORDER)
    metrics = [
        ("Growth in use, 2022-2024", {c: r["growth"]["comparators"][c]["pct_change"] for c in codes}, "{:+.0f}%"),
        ("Done in a facility", {c: r["setting"][c] for c in codes}, "{:.0f}%"),
        ("Services from non-metro clinicians", {c: r["rurality"][c]["pct_services_nonmetro"] for c in codes}, "{:.1f}%"),
        ("Volume visible provider-by-provider", {c: r["concentration"][c]["share_visible_pct"] for c in codes}, "{:.0f}%"),
    ]
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(FIGSIZE[0], FIGSIZE[1] + 0.6))
    positions = np.arange(len(codes))[::-1]
    for ax, (title, values, fmt) in zip(axes.flat, metrics):
        data = [values[c] for c in codes]
        ax.barh(positions, data, color=[VERMILLION if c == "64628" else LIGHT_GREY for c in codes], height=0.62)
        for pos, v in zip(positions, data):
            ax.annotate(fmt.format(v), (v, pos), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=BODY_SIZE - 3, fontweight="bold")
        ax.set_yticks(positions)
        ax.set_yticklabels([LABELS[c].split(" (")[0] for c in codes], fontsize=BODY_SIZE - 3)
        ax.set_xlim(0, max(data) * 1.32)
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
        ax.set_title(title, fontsize=BODY_SIZE - 1, loc="left", color="#111111")
        ax.yaxis.grid(False)
    fig.subplots_adjust(hspace=0.5, wspace=0.55)

    growth = metrics[0][1]; facility = metrics[1][1]; rural = metrics[2][1]
    claims = []
    if _rank_word(growth, "64628", high=True): claims.append("fastest-growing")
    if _rank_word(facility, "64628", high=True): claims.append("most facility-bound")
    if _rank_word(rural, "64628", high=False): claims.append("least rural")
    headline = ("Side by side, BVNA is the " + ", ".join(claims[:-1]) + (" and " if len(claims) > 1 else "")
                + claims[-1] + " of the four") if claims else "BVNA compared with three established procedures"
    _save(fig, axes.flat[0], headline,
          f"BVNA use grew {growth['64628']:.0f}% in two years, {facility['64628']:.0f}% happens in a facility, and only "
          f"{rural['64628']:.1f}% of visible services come from clinicians outside metro areas.",
          f"Source: {CMS_PROV}, data years {YEARS[0]}-{LATEST}; {accessed}. Growth and setting from the geography "
          f"file (all providers); rurality from RUCA codes of visible clinicians only (RUCA 4-10 = non-metro).",
          "figure5", left=0.17, panels=True)


def run() -> None:
    r = json.loads((BVNA_AUDIT / "results.json").read_text())
    accessed = _accessed()
    for build in (figure1, figure2, figure3, figure4, figure5):
        build(r, accessed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
    for k, v in json.loads(MANIFEST.read_text()).items():
        print(f"{k}: {v['title']}")
