"""Every statistic that appears in a figure or in RESULTS.md.

No figure code lives here and no statistic is computed inside figures.py, so
that every number can be recomputed and tested independently of plotting.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Final, Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from src.constants import (
    ADVANCED_CODES,
    BASIC_CODES,
    BOOTSTRAP_RESAMPLES,
    CI_LEVEL,
    DESERT_PROVIDER_THRESHOLD,
    INDEX_BASE_YEAR,
    NEUROMOD_CODES_STRICT,
    PNS_CODE,
    RANDOM_SEED,
    RATE_PER,
    TOP_SHARE_QUANTILE,
    YEARS,
)

LOGGER: Final = logging.getLogger(__name__)

INDEX_BASE_VALUE: Final[float] = 100.0
FIGURE1_CODES: Final[tuple[str, ...]] = ("64555", "63650", "62323")
BASIC_COMPARATOR: Final[str] = "62323"
ALPHA_FLOOR: Final[float] = 1e-6


# ------------------------------------------------------------------ Gini
def gini(values: Sequence[float] | np.ndarray) -> float:
    """Gini coefficient of a non-negative distribution.

    0.0 for a perfectly uniform distribution, approaching 1.0 as all mass
    concentrates on a single unit. Uses the ordered-rank formulation, which is
    exact for finite samples rather than an area approximation.
    """
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        raise ValueError("Gini is undefined for an empty distribution.")
    if np.any(array < 0):
        raise ValueError("Gini requires non-negative values.")
    total = array.sum()
    if total == 0:
        raise ValueError("Gini is undefined when every value is zero.")
    ordered = np.sort(array)
    n = ordered.size
    index = np.arange(1, n + 1)
    return float((2.0 * np.sum(index * ordered)) / (n * total) - (n + 1.0) / n)


def lorenz_points(values: Sequence[float] | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative provider share (x) and cumulative volume share (y), low to high."""
    ordered = np.sort(np.asarray(values, dtype=float))
    cumulative = np.cumsum(ordered)
    x = np.concatenate(([0.0], np.arange(1, ordered.size + 1) / ordered.size))
    y = np.concatenate(([0.0], cumulative / cumulative[-1]))
    return x, y


def top_share(values: Sequence[float] | np.ndarray,
              quantile: float = TOP_SHARE_QUANTILE) -> float:
    """Share of total volume delivered by providers above `quantile` of the rank."""
    ordered = np.sort(np.asarray(values, dtype=float))
    cut = int(np.floor(quantile * ordered.size))
    return float(ordered[cut:].sum() / ordered.sum())


def bootstrap_gini_ci(
    values: Sequence[float] | np.ndarray,
    resamples: int = BOOTSTRAP_RESAMPLES,
    level: float = CI_LEVEL,
    seed: int = RANDOM_SEED,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the Gini coefficient. Deterministic given `seed`."""
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    draws = np.empty(resamples, dtype=float)
    for i in range(resamples):
        sample = rng.choice(array, size=array.size, replace=True)
        draws[i] = gini(sample) if sample.sum() > 0 else np.nan
    draws = draws[~np.isnan(draws)]
    tail = (1.0 - level) / 2.0
    return float(np.quantile(draws, tail)), float(np.quantile(draws, 1.0 - tail))


# ------------------------------------------------------------- Figure 1
def growth_index(national: pd.DataFrame,
                 codes: Sequence[str] = FIGURE1_CODES) -> pd.DataFrame:
    """Services per 100k FFS beneficiaries, indexed to INDEX_BASE_YEAR = 100."""
    subset = national.loc[national["hcpcs_code"].isin(codes)].copy()
    base = (
        subset.loc[subset["year"] == INDEX_BASE_YEAR]
        .set_index("hcpcs_code")["services_per_100k"]
    )
    missing = set(codes) - set(base.index)
    if missing:
        raise ValueError(f"No {INDEX_BASE_YEAR} baseline for codes {missing}.")
    subset["index_value"] = subset.apply(
        lambda row: row["services_per_100k"] / base[row["hcpcs_code"]] * INDEX_BASE_VALUE,
        axis=1,
    )
    return subset.sort_values(["hcpcs_code", "year"]).reset_index(drop=True)


def inflection_year(indexed: pd.DataFrame, code: str = PNS_CODE) -> int:
    """The year the series turns - its minimum, after which growth is sustained.

    Defined as the argmin of the rate rather than the largest year-over-year
    jump. For 64555 the largest jump lands in the final year, which describes
    the steepest segment, not the point at which the trend reverses. The turning
    point is the honest reading of "the year PNS inflects".
    """
    series = (
        indexed.loc[indexed["hcpcs_code"] == code]
        .sort_values("year")
        .set_index("year")["index_value"]
    )
    return int(series.idxmin())


# ------------------------------------------------------------- Figure 2
@dataclass(frozen=True)
class ConcentrationResult:
    """Everything Figure 2 and its caption need for one HCPCS code."""

    code: str
    year: int
    n_providers: int
    total_services: float
    gini: float
    gini_ci_low: float
    gini_ci_high: float
    top_decile_share: float
    lorenz_x: list[float] = field(repr=False, default_factory=list)
    lorenz_y: list[float] = field(repr=False, default_factory=list)


def concentration(collapsed: pd.DataFrame, code: str, year: int) -> ConcentrationResult:
    """Gini, bootstrap CI, Lorenz curve and top-decile share for one code-year."""
    values = (
        collapsed.loc[(collapsed["hcpcs_code"] == code) & (collapsed["year"] == year),
                      "total_services"]
        .to_numpy(dtype=float)
    )
    if values.size == 0:
        raise ValueError(f"No providers billed {code} in {year}.")
    low, high = bootstrap_gini_ci(values)
    x, y = lorenz_points(values)
    return ConcentrationResult(
        code=code,
        year=year,
        n_providers=int(values.size),
        total_services=float(values.sum()),
        gini=gini(values),
        gini_ci_low=low,
        gini_ci_high=high,
        top_decile_share=top_share(values),
        lorenz_x=x.tolist(),
        lorenz_y=y.tolist(),
    )


def concentration_common_base(
    collapsed: pd.DataFrame, code: str, year: int
) -> ConcentrationResult:
    """Concentration of one code's volume across the WHOLE provider universe.

    `concentration()` ranks only the providers who billed the code, which is
    truncation-sensitive: the suppression floor removes proportionally far more
    of a low-volume code's tail than a high-volume code's, mechanically pushing
    a rare procedure's Gini DOWN. Ranking instead over the common denominator of
    every provider who billed any study code that year - assigning zero to those
    who did not bill this particular code - removes that asymmetry and is the
    comparison that actually tests a two-tier delivery claim.
    """
    block = collapsed.loc[collapsed["year"] == year]
    base = block["npi"].unique()
    volume = (
        block.loc[block["hcpcs_code"] == code]
        .groupby("npi")["total_services"].sum()
        .reindex(base, fill_value=0.0)
        .to_numpy(dtype=float)
    )
    if volume.sum() == 0:
        raise ValueError(f"No volume for {code} in {year}.")
    low, high = bootstrap_gini_ci(volume)
    x, y = lorenz_points(volume)
    return ConcentrationResult(
        code=code,
        year=year,
        n_providers=int(volume.size),
        total_services=float(volume.sum()),
        gini=gini(volume),
        gini_ci_low=low,
        gini_ci_high=high,
        top_decile_share=top_share(volume),
        lorenz_x=x.tolist(),
        lorenz_y=y.tolist(),
    )


# ------------------------------------------------------------- Figure 3
def access_deserts(panel: pd.DataFrame) -> pd.DataFrame:
    """Per year: states with zero PNS providers, and share of FFS lives at risk."""
    rows: list[dict[str, object]] = []
    for year, block in panel.groupby("year"):
        total_ffs = block["ffs_benes"].sum()
        zero = block.loc[block["pns_providers"] == 0]
        sparse = block.loc[block["pns_providers"] < DESERT_PROVIDER_THRESHOLD]
        rows.append(
            {
                "year": int(year),
                "states_zero_pns": int(len(zero)),
                "states_sparse_pns": int(len(sparse)),
                "pct_benes_zero_pns": float(zero["ffs_benes"].sum() / total_ffs * 100),
                "pct_benes_sparse_pns": float(sparse["ffs_benes"].sum() / total_ffs * 100),
                "benes_sparse_pns": int(sparse["ffs_benes"].sum()),
                "zero_state_list": ", ".join(sorted(zero["state"])),
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


# ------------------------------------------------------------- Figure 4
@dataclass(frozen=True)
class ModelResult:
    """One negative binomial fit, ready for a forest plot."""

    name: str
    terms: dict[str, dict[str, float]]
    n_obs: int
    n_clusters: int
    pseudo_r2: float
    alpha: float
    pearson_dispersion: float
    llf: float


def _fit_negbin(
    panel: pd.DataFrame, predictors: Sequence[str], name: str
) -> ModelResult:
    """NB2 with a log FFS-beneficiary offset, year fixed effects, state-clustered SE.

    The dispersion parameter alpha is estimated by NB2 maximum likelihood, then
    the model is refitted as a GLM at that alpha so that a cluster-robust
    covariance can be applied. Reported alpha > 0 is the overdispersion evidence.
    """
    data = panel.copy()
    year_dummies = pd.get_dummies(data["year"].astype(int), prefix="yr", drop_first=True)
    design = pd.concat([data[list(predictors)], year_dummies.astype(float)], axis=1)
    design = sm.add_constant(design, has_constant="add")
    endog = data["pns_services"].astype(float)
    offset = np.log(data["ffs_benes"].astype(float))

    nb2 = sm.NegativeBinomial(endog, design, loglike_method="nb2", offset=offset)
    alpha = float(max(nb2.fit(disp=0, maxiter=200).params.get("alpha", ALPHA_FLOOR),
                      ALPHA_FLOOR))

    glm = sm.GLM(
        endog, design, family=sm.families.NegativeBinomial(alpha=alpha), offset=offset
    )
    fit = glm.fit(cov_type="cluster", cov_kwds={"groups": data["state"].to_numpy()})

    null = sm.GLM(
        endog,
        np.ones((len(endog), 1)),
        family=sm.families.NegativeBinomial(alpha=alpha),
        offset=offset,
    ).fit()
    pseudo_r2 = float(1.0 - fit.llf / null.llf)

    conf = fit.conf_int(alpha=1.0 - CI_LEVEL)
    terms = {
        term: {
            "irr": float(np.exp(fit.params[term])),
            "irr_low": float(np.exp(conf.loc[term, 0])),
            "irr_high": float(np.exp(conf.loc[term, 1])),
            "coef": float(fit.params[term]),
            "p_value": float(fit.pvalues[term]),
        }
        for term in predictors
    }
    return ModelResult(
        name=name,
        terms=terms,
        n_obs=int(fit.nobs),
        n_clusters=int(data["state"].nunique()),
        pseudo_r2=pseudo_r2,
        alpha=alpha,
        pearson_dispersion=float(fit.pearson_chi2 / fit.df_resid),
        llf=float(fit.llf),
    )


def supply_models(panel: pd.DataFrame) -> dict[str, ModelResult]:
    """Model A (general pain supply only) and Model B (adds neuromodulation supply)."""
    return {
        "A": _fit_negbin(panel, ["basic_density_per_100k"], "Model A"),
        "B": _fit_negbin(
            panel, ["basic_density_per_100k", "neuromod_density_per_100k"], "Model B"
        ),
    }


# ------------------------------------------------------------- Figure 5
@dataclass(frozen=True)
class GradientResult:
    """Advanced-to-basic ratio regressed on one state-level covariate."""

    covariate: str
    year: int
    n_states: int
    pearson_r: float
    pearson_p: float
    spearman_rho: float
    spearman_p: float
    slope: float
    intercept: float
    table: pd.DataFrame = field(repr=False, default_factory=pd.DataFrame)


def equity_gradient(
    panel: pd.DataFrame,
    collapsed: pd.DataFrame,
    income: pd.DataFrame,
    year: int,
    covariate: str,
) -> GradientResult:
    """Correlate the advanced-to-basic ratio with income or dual-eligible share.

    The ratio is 64555 services divided by 62323 services in the state. States
    with no 62323 volume are dropped (the ratio is undefined), not zero-filled.
    """
    block = panel.loc[panel["year"] == year].merge(income, on="state", how="left")
    comparator = (
        collapsed.loc[(collapsed["year"] == year)
                      & (collapsed["hcpcs_code"] == BASIC_COMPARATOR)]
        .groupby("state", as_index=False)
        .agg(comparator_services=("total_services", "sum"))
    )
    block = block.merge(comparator, on="state", how="left")
    block["comparator_services"] = block["comparator_services"].fillna(0)
    block = block.loc[block["comparator_services"] > 0].copy()
    block["advanced_to_basic"] = (
        block["pns_services"] / block["comparator_services"] * 1000.0
    )

    usable = block.dropna(subset=[covariate, "advanced_to_basic"])
    x = usable[covariate].to_numpy(dtype=float)
    y = usable["advanced_to_basic"].to_numpy(dtype=float)
    pearson = stats.pearsonr(x, y)
    spearman = stats.spearmanr(x, y)
    fit = sm.OLS(y, sm.add_constant(x)).fit()

    return GradientResult(
        covariate=covariate,
        year=year,
        n_states=int(len(usable)),
        pearson_r=float(pearson.statistic),
        pearson_p=float(pearson.pvalue),
        spearman_rho=float(spearman.statistic),
        spearman_p=float(spearman.pvalue),
        slope=float(fit.params[1]),
        intercept=float(fit.params[0]),
        table=usable[["state", covariate, "advanced_to_basic", "pns_services",
                      "comparator_services", "ffs_benes"]].reset_index(drop=True),
    )


# ------------------------------------------------------------ suppression
def suppression_footprint(collapsed: pd.DataFrame, year: int) -> dict[str, float]:
    """Describe how close observed providers sit to the suppression floor.

    Every surviving row has more than 10 beneficiaries by construction. The
    share of providers sitting just above the floor indicates how much of the
    true distribution is missing below it.
    """
    block = collapsed.loc[collapsed["year"] == year]
    out: dict[str, float] = {}
    for code in (PNS_CODE, BASIC_COMPARATOR):
        values = block.loc[block["hcpcs_code"] == code, "total_benes"].to_numpy(float)
        out[f"{code}_min_benes"] = float(values.min())
        out[f"{code}_median_benes"] = float(np.median(values))
        out[f"{code}_pct_at_11_to_15"] = float(
            np.mean((values >= 11) & (values <= 15)) * 100
        )
    return out


def run(tables: dict[str, pd.DataFrame], literature: dict) -> dict:
    """Compute every result. Returns a JSON-serialisable dict."""
    collapsed = tables["prov_svc_study"]
    panel = tables["state_year_panel"]
    national = tables["national_by_code"]
    income = tables["income"]
    latest = int(max(YEARS))

    indexed = growth_index(national)
    pns_conc = concentration(collapsed, PNS_CODE, latest)
    basic_conc = concentration(collapsed, BASIC_COMPARATOR, latest)
    pns_conc_base = concentration_common_base(collapsed, PNS_CODE, latest)
    basic_conc_base = concentration_common_base(collapsed, BASIC_COMPARATOR, latest)
    deserts = access_deserts(panel)
    models = supply_models(panel)
    income_gradient = equity_gradient(panel, collapsed, income, latest, "median_hh_income")
    dual_gradient = equity_gradient(panel, collapsed, income, latest, "dual_pct")

    # Sensitivity: neuromodulation capability excluding 64590, which the CMS
    # descriptor shows also covers gastric neurostimulator generators.
    strict = (
        collapsed.loc[collapsed["hcpcs_code"].isin(NEUROMOD_CODES_STRICT)]
        .groupby(["state", "year"], as_index=False)
        .agg(neuromod_providers_strict=("npi", "nunique"))
    )
    strict_panel = panel.merge(strict, on=["state", "year"], how="left")
    strict_panel["neuromod_providers_strict"] = (
        strict_panel["neuromod_providers_strict"].fillna(0)
    )
    strict_panel["neuromod_density_per_100k"] = (
        strict_panel["neuromod_providers_strict"] / strict_panel["ffs_benes"] * 100_000
    )
    model_b_strict = _fit_negbin(
        strict_panel, ["basic_density_per_100k", "neuromod_density_per_100k"],
        "Model B (strict)",
    )

    results = {
        "latest_year": latest,
        "years": list(YEARS),
        "hcpcs_verification": tables["hcpcs_verification"].to_dict("records"),
        "national_by_code": national.to_dict("records"),
        "growth_index": indexed.to_dict("records"),
        "pns_inflection_year": inflection_year(indexed),
        "concentration_billers_only": {
            PNS_CODE: pns_conc.__dict__,
            BASIC_COMPARATOR: basic_conc.__dict__,
        },
        "concentration_common_base": {
            PNS_CODE: pns_conc_base.__dict__,
            BASIC_COMPARATOR: basic_conc_base.__dict__,
        },
        "deserts": deserts.to_dict("records"),
        "models": {k: v.__dict__ for k, v in models.items()},
        "model_b_strict": model_b_strict.__dict__,
        "gradients": {
            "income": {k: v for k, v in income_gradient.__dict__.items() if k != "table"},
            "dual": {k: v for k, v in dual_gradient.__dict__.items() if k != "table"},
        },
        "suppression_footprint": suppression_footprint(collapsed, latest),
        "literature": literature,
    }
    return {
        "results": results,
        "objects": {
            "indexed": indexed,
            "pns_conc": pns_conc,
            "basic_conc": basic_conc,
            "pns_conc_base": pns_conc_base,
            "basic_conc_base": basic_conc_base,
            "deserts": deserts,
            "models": models,
            "income_gradient": income_gradient,
            "dual_gradient": dual_gradient,
        },
    }
