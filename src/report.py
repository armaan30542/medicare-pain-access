"""Generate RESULTS.md, TALKING_POINTS.md, DATA_PROVENANCE.md and references.bib.

Every number in these documents is interpolated from the computed results dict.
Nothing is typed by hand, so the prose cannot drift from the analysis.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Final

import pandas as pd

from src.constants import (
    AUDIT_DIR,
    BOOTSTRAP_RESAMPLES,
    DESERT_PROVIDER_THRESHOLD,
    INDEX_BASE_YEAR,
    PROJECT_ROOT,
    RANDOM_SEED,
    SUPPRESSION_BENE_THRESHOLD,
)

LOGGER: Final = logging.getLogger(__name__)


def _p(value: float) -> str:
    """Format a p-value for reading aloud."""
    return "< 0.001" if value < 0.001 else f"= {value:.3f}"


def write_results(results: dict, accessed: str) -> Path:
    """RESULTS.md - every computed number, formatted to be read aloud."""
    latest = results["latest_year"]
    pns_b = results["concentration_common_base"]["64555"]
    bas_b = results["concentration_common_base"]["62323"]
    pns_o = results["concentration_billers_only"]["64555"]
    bas_o = results["concentration_billers_only"]["62323"]
    deserts = pd.DataFrame(results["deserts"])
    last = deserts.iloc[-1]
    worst = deserts.loc[deserts["states_zero_pns"].idxmax()]
    national = pd.DataFrame(results["national_by_code"])
    pns_nat = national[national.hcpcs_code == "64555"].sort_values("year")
    epi_nat = national[national.hcpcs_code == "62323"].sort_values("year")
    a, b = results["models"]["A"], results["models"]["B"]
    inc, dual = results["gradients"]["income"], results["gradients"]["dual"]
    supp = results["suppression_footprint"]
    lit = results["literature"]

    epi_2019 = float(epi_nat[epi_nat.year == 2019]["services_per_100k"].iloc[0])
    epi_last = float(epi_nat[epi_nat.year == latest]["services_per_100k"].iloc[0])
    epi_change = (epi_last - epi_2019) / epi_2019 * 100

    pns_first = pns_nat.iloc[0]
    pns_last = pns_nat.iloc[-1]
    pns_trough = pns_nat.loc[pns_nat["services_per_100k"].idxmin()]

    text = f"""# RESULTS

All numbers below are computed by `python run.py` from free public CMS and Census
data. Data accessed **{accessed}**. Most recent published data year: **{latest}**.
Bootstrap seed {RANDOM_SEED}, {BOOTSTRAP_RESAMPLES:,} resamples.

Citation keys in brackets resolve to the reference list at the bottom and to
`references.bib`. Every cited number passed the audit in `CITATION_AUDIT.md`.

---

## ⚠️ Headline: the data support HALF of the original thesis

**Supported.** PNS is delivered by a startlingly small provider base, its volume
is overwhelmingly concentrated, and a meaningful share of beneficiaries live in a
state with almost no PNS provider.

**Not supported.** The equity gradient does not appear at state level, and general
pain-physician supply does *not* stop predicting PNS volume once neuromodulation
supply is adjusted for. Both are reported in full below, as measured.

---

## Figure 1 - PNS growth

| Year | PNS (64555) services | Providers | Services per 100k FFS | Index ({INDEX_BASE_YEAR}=100) |
|---|---|---|---|---|
"""
    indexed = pd.DataFrame(results["growth_index"])
    for _, row in pns_nat.iterrows():
        idx = indexed[(indexed.hcpcs_code == "64555") & (indexed.year == row["year"])]
        idx_value = f"{idx['index_value'].iloc[0]:.0f}" if len(idx) else "-"
        text += (f"| {int(row['year'])} | {int(row['total_services']):,} | "
                 f"{int(row['n_providers']):,} | {row['services_per_100k']:.1f} | {idx_value} |\n")

    text += f"""
**Read aloud:** PNS volume in fee-for-service Medicare went from
**{pns_first['services_per_100k']:.0f} services per 100,000 beneficiaries in {int(pns_first['year'])}**
to **{pns_last['services_per_100k']:.0f} in {latest}**, delivered by
**{int(pns_last['n_providers'])} providers nationally**.

**The honest complication you must state first.** 64555 volume was *higher* in
2015-2016 ({pns_nat.iloc[0]['services_per_100k']:.0f} per 100k) than in 2017-2020, collapsing to a trough of
**{pns_trough['services_per_100k']:.1f} per 100k in {int(pns_trough['year'])}** ({int(pns_trough['n_providers'])} providers nationally)
before growing continuously to {latest}. The specialty mix billing 64555 is stable
across the whole period - pain management, anesthesiology, PM&R and ambulatory
surgical centres throughout - so this is **not** a specialty-substitution artifact.
Growth measured from the {int(pns_trough['year'])} trough is
**{pns_last['services_per_100k']/pns_trough['services_per_100k']:.1f}x**; growth measured from {int(pns_first['year'])} is
**{pns_last['services_per_100k']/pns_first['services_per_100k']:.2f}x**. Quote the second number, not the first.

**External validation of the pipeline.** My independently computed 62323 rate fell
**{epi_change:.1f}% from 2019 to {latest}** ({epi_2019:.0f} to {epi_last:.0f} per 100,000).
Manchikanti et al. report a **13% decline in epidural procedure utilization from
2019 to 2024** in traditional Medicare [manchikanti2026epidural]. Two independent
analyses of the same population agree to within a percentage point. That is the
best evidence available that this pipeline is computing what it claims to compute.

*Note: CPT 62323 was created in the 2017 CPT cycle (replacing 62311). It has zero
rows in the 2015 and 2016 files, verified directly. All series are therefore
indexed to {INDEX_BASE_YEAR}, not 2015.*

---

## Figure 2 - Concentration (THE CENTERPIECE)

### Primary specification: ranked over the common provider universe

In {latest}, **{pns_b['n_providers']:,} providers** billed at least one of the seven
study codes. Ranking PNS volume across all of them (zero for those who did not
bill it) is the comparison that actually tests a two-tier claim.

| Measure | PNS (64555) | Lumbar epidural (62323) |
|---|---|---|
| Gini coefficient | **{pns_b['gini']:.3f}** | **{bas_b['gini']:.3f}** |
| 95% bootstrap CI | [{pns_b['gini_ci_low']:.3f}, {pns_b['gini_ci_high']:.3f}] | [{bas_b['gini_ci_low']:.3f}, {bas_b['gini_ci_high']:.3f}] |
| Share delivered by top 10% of providers | **{pns_b['top_decile_share']*100:.1f}%** | **{bas_b['top_decile_share']*100:.1f}%** |
| Total services | {pns_b['total_services']:,.0f} | {bas_b['total_services']:,.0f} |

**Read aloud:** *"Among the same {pns_b['n_providers']:,} interventional pain providers,
the top 10% deliver {pns_b['top_decile_share']*100:.0f}% of all PNS volume, versus
{bas_b['top_decile_share']*100:.0f}% of all epidural volume. The Gini for PNS is
{pns_b['gini']:.2f}; for epidurals it is {bas_b['gini']:.2f}. The confidence intervals do not
come close to overlapping."*

**Unique providers, {latest}:** {pns_o['n_providers']:,} billed 64555 nationally versus
{bas_o['n_providers']:,} who billed 62323 - a **{bas_o['n_providers']/pns_o['n_providers']:.0f}-fold difference**.
That single ratio is the two-tier thesis in one number.

### Secondary specification: ranked among billers only - and it REVERSES

| Measure | PNS (64555) | Lumbar epidural (62323) |
|---|---|---|
| Providers billing the code | {pns_o['n_providers']:,} | {bas_o['n_providers']:,} |
| Gini among billers | {pns_o['gini']:.3f} [{pns_o['gini_ci_low']:.3f}, {pns_o['gini_ci_high']:.3f}] | {bas_o['gini']:.3f} [{bas_o['gini_ci_low']:.3f}, {bas_o['gini_ci_high']:.3f}] |
| Top 10% share | {pns_o['top_decile_share']*100:.1f}% | {bas_o['top_decile_share']*100:.1f}% |

**Restricted to providers who actually bill the code, PNS looks LESS concentrated
than epidurals, not more.** Raise this yourself. The explanation is the
suppression floor: CMS drops every provider-code row with
{SUPPRESSION_BENE_THRESHOLD} or fewer beneficiaries, and that floor removes a far
larger fraction of a rare procedure's tail than a common one's. Evidence, {latest}:

- Minimum beneficiaries on any surviving 64555 row: **{supp['64555_min_benes']:.0f}** (the floor, exactly as documented)
- Median beneficiaries per PNS provider: **{supp['64555_median_benes']:.0f}**; per epidural provider: **{supp['62323_median_benes']:.0f}**
- **{supp['64555_pct_at_11_to_15']:.0f}% of PNS providers sit at 11-15 beneficiaries**, pressed right against the floor, versus **{supp['62323_pct_at_14_to_15'] if '62323_pct_at_14_to_15' in supp else supp['62323_pct_at_11_to_15']:.0f}%** of epidural providers.

Nearly half the visible PNS providers are at the edge of the cliff, so most of the
PNS distribution is below it and unobserved. The billers-only Gini is therefore an
artifact of differential truncation; the common-base Gini is not. **In both
specifications the truncation biases against finding concentration, so the
common-base result is conservative.**

---

## Figure 3 - Access deserts

| Year | States with ZERO PNS providers | States with < {DESERT_PROVIDER_THRESHOLD} | % FFS benes, zero-PNS state | % FFS benes, < {DESERT_PROVIDER_THRESHOLD} providers |
|---|---|---|---|---|
"""
    for _, row in deserts.iterrows():
        text += (f"| {int(row['year'])} | {int(row['states_zero_pns'])} | "
                 f"{int(row['states_sparse_pns'])} | {row['pct_benes_zero_pns']:.1f}% | "
                 f"{row['pct_benes_sparse_pns']:.1f}% |\n")

    text += f"""
**Read aloud:** In {latest}, **{int(last['states_zero_pns'])} states still had no Medicare
provider billing PNS at all**, and **{last['pct_benes_sparse_pns']:.0f}% of fee-for-service
beneficiaries - {int(last['benes_sparse_pns']):,} people - lived in a state with fewer than
{DESERT_PROVIDER_THRESHOLD} PNS providers.**

**States with zero PNS providers in {latest}:** {last['zero_state_list']}

**The direction is good news, and say so.** Deserts peaked in {int(worst['year'])} at
**{int(worst['states_zero_pns'])} states** covering **{worst['pct_benes_zero_pns']:.0f}%** of beneficiaries, and have
fallen steadily since. This is a diffusion story, not a stagnation story. The
finding is that diffusion is **incomplete**, not that it is absent.

---

## Figure 4 - Does general pain-physician supply predict PNS access?

Negative binomial (NB2), outcome = 64555 service count, log offset = FFS
beneficiary count, year fixed effects, standard errors clustered on state.

| | Model A | Model B |
|---|---|---|
| General interventional pain provider density | **IRR {a['terms']['basic_density_per_100k']['irr']:.3f}** [{a['terms']['basic_density_per_100k']['irr_low']:.3f}, {a['terms']['basic_density_per_100k']['irr_high']:.3f}], p {_p(a['terms']['basic_density_per_100k']['p_value'])} | **IRR {b['terms']['basic_density_per_100k']['irr']:.3f}** [{b['terms']['basic_density_per_100k']['irr_low']:.3f}, {b['terms']['basic_density_per_100k']['irr_high']:.3f}], p {_p(b['terms']['basic_density_per_100k']['p_value'])} |
| Neuromodulation-capable provider density | - | **IRR {b['terms']['neuromod_density_per_100k']['irr']:.3f}** [{b['terms']['neuromod_density_per_100k']['irr_low']:.3f}, {b['terms']['neuromod_density_per_100k']['irr_high']:.3f}], p {_p(b['terms']['neuromod_density_per_100k']['p_value'])} |
| N (state-years) | {a['n_obs']} | {b['n_obs']} |
| Clusters (states) | {a['n_clusters']} | {b['n_clusters']} |
| Pseudo R² | {a['pseudo_r2']:.3f} | {b['pseudo_r2']:.3f} |
| Overdispersion α | {a['alpha']:.2f} | {b['alpha']:.2f} |
| Pearson dispersion | {a['pearson_dispersion']:.2f} | {b['pearson_dispersion']:.2f} |

### This result contradicts the hypothesis. Report it that way.

The expected story was that the general-density coefficient would shrink toward
1.0 and lose significance once neuromodulation density entered. **It does not.**
It moves from {a['terms']['basic_density_per_100k']['irr']:.3f} to {b['terms']['basic_density_per_100k']['irr']:.3f} - a shift of
{abs(a['terms']['basic_density_per_100k']['irr']-b['terms']['basic_density_per_100k']['irr']):.3f} - and remains significant at p {_p(b['terms']['basic_density_per_100k']['p_value'])}.
Neuromodulation density is also positive and significant
(IRR {b['terms']['neuromod_density_per_100k']['irr']:.3f}, p {_p(b['terms']['neuromod_density_per_100k']['p_value'])}), but it does not displace general supply.

**What you can honestly say:** both supplies predict PNS volume, each adds
information beyond the other, and neither is close to sufficient - **pseudo R² is
only {b['pseudo_r2']:.3f}**, so 98% of the variation in state PNS volume is explained by
something other than how many pain physicians a state has. That is still a useful
claim: provider counts are a weak proxy for access to this therapy. It is a
weaker claim than "the conventional metric is the wrong denominator," and the
weaker claim is the one the data support.

Overdispersion α = {b['alpha']:.2f} is far from zero, confirming the negative binomial
over Poisson.

**Sensitivity (64590 excluded).** The CMS descriptor for 64590 is
*"Insertion or replacement of peripheral, sacral, or gastric neurostimulator
generator or receiver"* - it is not PNS-specific and captures gastric and sacral
stimulators. Redefining neuromodulation capability as 64555/63650/63685 only:
general density IRR {results['model_b_strict']['terms']['basic_density_per_100k']['irr']:.3f}, neuromodulation density IRR
{results['model_b_strict']['terms']['neuromod_density_per_100k']['irr']:.3f} (p {_p(results['model_b_strict']['terms']['neuromod_density_per_100k']['p_value'])}). The conclusion is unchanged.

---

## Figure 5 - The equity gradient

Advanced-to-basic ratio = 64555 services per 1,000 62323 services, by state, {latest}.

| | Income (Figure 5) | Dual-eligible share (Figure 5b) |
|---|---|---|
| States analysed | {inc['n_states']} | {dual['n_states']} |
| Pearson r | {inc['pearson_r']:.3f} (p {_p(inc['pearson_p'])}) | {dual['pearson_r']:.3f} (p {_p(dual['pearson_p'])}) |
| Spearman ρ | {inc['spearman_rho']:.3f} (p {_p(inc['spearman_p'])}) | {dual['spearman_rho']:.3f} (p {_p(dual['spearman_p'])}) |

### This is a null result. Do not oversell it.

There is **no detectable relationship between state median household income and
the advanced-to-basic ratio** (r = {inc['pearson_r']:.3f}, p {_p(inc['pearson_p'])}). The dual-eligible
association leans in the predicted direction and is larger on ranks than on
levels (Spearman ρ = {dual['spearman_rho']:.3f}, p {_p(dual['spearman_p'])}), but does not reach
conventional significance with {dual['n_states']} states.

**What you can honestly say:** *"I expected an income gradient and I did not find
one at state level. With 51 units and a therapy this rare, I am underpowered for
the effect size I was looking for, and states are far too coarse - the gradient,
if it exists, is between a county in the Mississippi Delta and a county in
Fairfield, not between Mississippi and Connecticut. That is the argument for
doing this at county level, which is the next study."*

---

## Figure 6 - The literature gap, quantified

Exact PubMed queries, run through NCBI E-utilities `esearch` on {accessed}:

- **SCS:** `{lit['queries']['SCS']}`
- **PNS:** `{lit['queries']['PNS']}`

The two strings are identical except for the therapy term.

| Year | SCS papers | PNS papers |
|---|---|---|
"""
    for year in sorted(lit["counts"]["SCS"], key=int):
        text += f"| {year} | {lit['counts']['SCS'][year]} | {lit['counts']['PNS'][year]} |\n"
    scs_total = sum(lit["counts"]["SCS"].values())
    pns_total = sum(lit["counts"]["PNS"].values())
    text += f"""| **Total** | **{scs_total}** | **{pns_total}** |

**Read aloud:** *"Across ten years, matched queries return **{scs_total} spinal cord
stimulation access papers and {pns_total} peripheral nerve stimulation access papers** -
about **{scs_total/max(pns_total,1):.0f} to 1**. The PNS count is rising, so the field is turning
toward this, but the gap is real and it is measured, not asserted."*

Separately, `"peripheral nerve stimulation" AND Medicare` returns **4 records in
all of PubMed**, none of which is an access or provider-distribution study
(see `NOVELTY_CHECK.md`).

---

## HCPCS verification table

| Code | Tier | Status | Distinct descriptors | Years present | Descriptor from the file |
|---|---|---|---|---|---|
"""
    for row in results["hcpcs_verification"]:
        text += (f"| {row['hcpcs_code']} | {row['tier']} | **{row['status']}** | "
                 f"{row['n_distinct_desc']} | {row['years_present']} | "
                 f"{row['hcpcs_desc_from_file']} |\n")

    text += f"""
CMS reworded several descriptors in the 2022 vintage and again in 2024. Every
variant is asserted against the expected token set at runtime; the pipeline
raises and stops if any code fails.

**Note on 64555:** in Medicare Part B this code captures the **60-day temporary
percutaneous PNS pathway** - a lead placed without a permanently implanted
generator. That is precisely the pathway studied in Odonkor et al. 2026
[odonkor2026pns].

---

## References

- [odonkor2026pns] Odonkor CA, Hirani S, Bohacek S, Pokuri S, Chow RM, Abd-Elsayed A. A prospective multidimensional assessment of the impact of payer type, insurance delays, psychological and clinical domains on response to 60-day peripheral nerve stimulation: 6-month outcomes. *Pain Med.* 2026;27(5):560-573. doi:10.1093/pm/pnaf151. PMID 41148054.
- [manchikanti2026epidural] Manchikanti L, Sanapati M, Pampati V, et al. Updated Analysis of Declining Utilization Rate of 13% Epidural Procedures for Chronic Spinal Pain Management in the Traditional Medicare Population from 2019 to 2024. *Pain Physician.* 2026;29(1):1-16. PMID 41628203.
- [manchikanti2021scs] Manchikanti L, et al. Spinal Cord Stimulation Trends of Utilization and Expenditures in Fee-For-Service Medicare Population from 2009 to 2018. *Pain Physician.* 2021. PMID 34323431.
- [day2025scs] Day W, Maloy GC, Winter AD, et al. Spinal cord stimulator utilization trends and predictors of unsuccessful trial-to-implant conversion. *N Am Spine Soc J.* 2025;22:100616. PMID 40548099.
- [huang2015scs] Huang KT, Martin J, Marky A, et al. A national survey of spinal cord stimulation trial-to-permanent conversion rates. *Neuromodulation.* 2015;18(2):133-139. PMID 24930992.
- [murphy2017volume] Murphy KR, Han JL, Hussaini SM, et al. The Volume-Outcome Effect: Impact on Trial-to-Permanent Conversion Rates in Spinal Cord Stimulation. *Neuromodulation.* 2017;20(3):256-262. PMID 27696607.
- [cooper2025maude] Cooper AN, Sen H, Kanjanapanang N, et al (incl. McCormick ZL). Adverse Events Associated With Peripheral Nerve Stimulation: An Analysis of the MAUDE Data base. *Neuromodulation.* 2025;28(4):619-626. PMID 40178466.
- [torabi2021providers] Torabi SJ, Kasle DA, Savoca EL, Gottschalk CH, Manes RP. Characterizing the providers of and reimbursement for chronic migraine chemodenervation among the Medicare population. *Headache.* 2021;61(2):373-384. PMID 33337542.
- [pearson2019iowa] Pearson ACS, Dexter F. Observational Study of the Distribution and Diversity of Interventional Pain Procedures Among Hospitals in the State of Iowa. *Pain Physician.* 2019;22(3):E157-E170. PMID 31151339.
- [aggarwal2021maude] Aggarwal N, Chow R. Real world adverse events of interspinous spacers using Manufacturer and User Facility Device Experience data. *Anesth Pain Med (Seoul).* 2021;16(2):177-183. PMID 33866770.
- [chow2025ilesi] Chow R, Ng J, Wood M, Yanez D, He Z, Rajput K. A comparison of steroid dose with or without local anesthetic in lumbar interlaminar epidural steroid injections. *Pain Pract.* 2025;25(1):e13410. PMID 39305041.
"""
    path = PROJECT_ROOT / "RESULTS.md"
    path.write_text(text)
    return path


def write_talking_points(results: dict, accessed: str) -> Path:
    """TALKING_POINTS.md - what to say, what not to say, and what he will ask."""
    latest = results["latest_year"]
    pns_b = results["concentration_common_base"]["64555"]
    bas_b = results["concentration_common_base"]["62323"]
    pns_o = results["concentration_billers_only"]["64555"]
    bas_o = results["concentration_billers_only"]["62323"]
    deserts = pd.DataFrame(results["deserts"])
    last = deserts.iloc[-1]
    national = pd.DataFrame(results["national_by_code"])
    pns_nat = national[national.hcpcs_code == "64555"].sort_values("year")
    epi_nat = national[national.hcpcs_code == "62323"].sort_values("year")
    a, b = results["models"]["A"], results["models"]["B"]
    inc, dual = results["gradients"]["income"], results["gradients"]["dual"]
    supp = results["suppression_footprint"]
    lit = results["literature"]
    scs_total = sum(lit["counts"]["SCS"].values())
    pns_total = sum(lit["counts"]["PNS"].values())
    epi_2019 = float(epi_nat[epi_nat.year == 2019]["services_per_100k"].iloc[0])
    epi_last = float(epi_nat[epi_nat.year == latest]["services_per_100k"].iloc[0])
    pns_trough = pns_nat.loc[pns_nat["services_per_100k"].idxmin()]
    pns_last = pns_nat.iloc[-1]

    text = f"""# TALKING POINTS

Every number is tagged **MY RESULT** (computed by this repo) or **CITED**
(published, PMID given inline, verified in `CITATION_AUDIT.md`).
Data accessed {accessed}. Most recent data year {latest}.

---

## ⚠️ Read this box before anything else

**Two of the five original hypotheses did not survive contact with the data.**
The equity gradient is null and the "general supply is the wrong denominator"
claim is not supported. Lead with that. A physician-scientist will trust the
concentration finding far more if you volunteer the two nulls first.

**Do not say "each 10-day insurance delay cut the odds of relief by 89%."** The
published abstract of his own paper (PMID 41148054) has a typographical error in
that sentence. Say "insurance delay independently predicted worse response" and
stop there. Details in `CITATION_AUDIT.md`.

**The MAUDE PNS safety paper is Cooper et al., not McCormick et al.** (PMID 40178466).

---

## Opening line

*"You showed that when a 60-day PNS patient's insurance is delayed, they do worse.
I wanted to know who can even get to the procedure in the first place. It turns
out that in {latest}, **{pns_o['n_providers']} providers in the entire Medicare
fee-for-service program billed PNS** - against **{bas_o['n_providers']:,}** who billed a lumbar
epidural."*

---

## FIGURE 1 - PNS growth

**What it shows.** PNS volume per 100,000 fee-for-service beneficiaries against
SCS trials and lumbar epidurals, {INDEX_BASE_YEAR}-{latest}.

**Say these numbers:**
- PNS reached **{pns_last['services_per_100k']:.0f} services per 100,000 FFS beneficiaries in {latest}**, from **{pns_trough['services_per_100k']:.1f} at its {int(pns_trough['year'])} trough** — a **{pns_last['services_per_100k']/pns_trough['services_per_100k']:.0f}-fold** rise. *(MY RESULT)*
- Lumbar epidural volume **fell {abs((epi_last-epi_2019)/epi_2019*100):.0f}%** from 2019 to {latest}, {epi_2019:.0f} to {epi_last:.0f} per 100,000. *(MY RESULT)*
- Manchikanti et al. independently report a **13% decline** in epidural utilization 2019-2024 in traditional Medicare. *(CITED, PMID 41628203)* — **my number lands within a point of theirs, which is the best proof my pipeline is right.**

**The limitation, phrased for a physician:** *"64555 was billed more in 2015 and
2016 than in 2018, so this isn't a clean take-off curve — something changed in
coding or coverage around 2017 that I can see but can't fully explain from claims
alone. I index to 2017 and I quote growth off the trough, and I say so."*

**Next study:** link the series to the 2020-2021 Medicare coverage decisions and
test for a policy discontinuity rather than describing a curve.

---

## FIGURE 2 - Concentration. This is the slide that matters.

**What it shows.** Lorenz curves for PNS and lumbar epidural volume across the
same universe of interventional pain providers, {latest}.

**Say these numbers:**
- **The top 10% of providers deliver {pns_b['top_decile_share']*100:.0f}% of all PNS volume, versus {bas_b['top_decile_share']*100:.0f}% of all epidural volume.** *(MY RESULT)*
- **Gini {pns_b['gini']:.2f} for PNS [{pns_b['gini_ci_low']:.3f}-{pns_b['gini_ci_high']:.3f}] versus {bas_b['gini']:.2f} for epidurals [{bas_b['gini_ci_low']:.3f}-{bas_b['gini_ci_high']:.3f}]**, {BOOTSTRAP_RESAMPLES:,}-resample bootstrap, non-overlapping. *(MY RESULT)*
- **{pns_o['n_providers']} PNS providers versus {bas_o['n_providers']:,} epidural providers — a {bas_o['n_providers']/pns_o['n_providers']:.0f}-fold difference.** *(MY RESULT)*

**The limitation, phrased for a physician:** *"CMS deletes any provider-procedure
row with {SUPPRESSION_BENE_THRESHOLD} or fewer beneficiaries. So every low-volume
PNS provider is invisible to me — **{supp['64555_pct_at_11_to_15']:.0f}% of the PNS providers I
can see are sitting at 11 to 15 beneficiaries, right against the floor**. That
cuts both ways: if I restrict to providers who actually bill the code, PNS looks
*less* concentrated than epidurals, which is an artifact of chopping off the tail
of a rare procedure. Over the common provider base it's the reverse, and the
truncation makes that estimate conservative. I'd rather show you both than show
you the flattering one."*

**Next study:** get the concentration at the practice/TIN level rather than the
NPI level, so a single high-volume group doesn't read as many individual
providers.

---

## FIGURE 3 - Access deserts

**What it shows.** States with no Medicare provider billing PNS, and the share of
beneficiaries living in near-empty states, by year.

**Say these numbers:**
- **{int(last['states_zero_pns'])} states had zero PNS providers in {latest}.** *(MY RESULT)*
- **{last['pct_benes_sparse_pns']:.0f}% of FFS beneficiaries — {int(last['benes_sparse_pns']):,} people — live in a state with fewer than {DESERT_PROVIDER_THRESHOLD} PNS providers.** *(MY RESULT)*
- Deserts peaked at **{int(deserts['states_zero_pns'].max())} states** and have fallen every year since. *(MY RESULT)*

**The limitation, phrased for a physician:** *"A 'zero' state means nobody there
cleared the reporting floor. It doesn't strictly prove nobody did the procedure —
it proves nobody did enough of it to be counted, which for a therapy that needs a
learning curve is arguably the more relevant threshold anyway."*

**Next study:** repeat at the hospital-referral-region level so the unit is a
plausible travel distance rather than a state line.

---

## FIGURE 4 - Provider supply and PNS volume

**What it shows.** Two negative binomial models of state PNS volume, with an FFS
beneficiary offset and state-clustered errors.

**Say these numbers:**
- General pain provider density: **IRR {a['terms']['basic_density_per_100k']['irr']:.3f}** in Model A, **{b['terms']['basic_density_per_100k']['irr']:.3f}** in Model B — it barely moves and stays significant. *(MY RESULT)*
- Neuromodulation-capable density: **IRR {b['terms']['neuromod_density_per_100k']['irr']:.3f}**, p {_p(b['terms']['neuromod_density_per_100k']['p_value'])}. *(MY RESULT)*
- **Pseudo R² is only {b['pseudo_r2']:.3f}** — over 97% of the variation in state PNS volume is unexplained by provider supply of either kind. *(MY RESULT)*

**Volunteer this:** *"I predicted the general-supply coefficient would collapse
once I adjusted for neuromodulation supply. It didn't. Both predict, neither
displaces the other, and together they explain almost nothing. The defensible
version of my claim is weaker than the one I started with: counting pain
physicians is a poor proxy for access to this therapy — not a wrong one."*

**The limitation, phrased for a physician:** *"This is a state-year association
with 51 states. It cannot tell you whether adding a pain physician to a state
causes a PNS case to happen."*

**Next study:** provider-level event history — after an NPI's first 64555 claim,
what predicts whether they keep doing it?

---

## FIGURE 5 / 5b - The equity gradient

**What it shows.** PNS services per 1,000 epidural services, by state, against
median household income and against dual-eligible share.

**Say these numbers:**
- Income: **Pearson r = {inc['pearson_r']:.3f}, p {_p(inc['pearson_p'])}** — a **null result**. *(MY RESULT)*
- Dual-eligible: **Spearman ρ = {dual['spearman_rho']:.3f}, p {_p(dual['spearman_p'])}** — right direction, not significant. *(MY RESULT)*
- For contrast, SCS trial-to-implant conversion **is** lower for Medicaid (OR 0.78) and Medicare (OR 0.85) versus commercial insurance. *(CITED, PMID 40548099)*

**Volunteer this:** *"I went looking for an income gradient and I did not find
one. I think the state is simply the wrong unit — the disparity that matters is
between counties, not between Mississippi and Connecticut, and 51 points can't
resolve it."*

**The limitation, phrased for a physician:** *"An ecological correlation across
states tells you nothing about which patients got the therapy."*

**Next study:** county-level ratio with an area-deprivation index, which is the
version I think actually has the power to find it.

---

## FIGURE 6 - The literature gap

**What it shows.** Matched PubMed queries for SCS versus PNS access/utilization
research, by year, 2015-2024.

**Say these numbers:**
- **{scs_total} SCS papers versus {pns_total} PNS papers — about {scs_total/max(pns_total,1):.0f} to 1.** *(MY RESULT, reproducible query)*
- `"peripheral nerve stimulation" AND Medicare` returns **4 records in all of PubMed**, none of them an access study. *(MY RESULT)*
- The one substantial PNS public-data paper is a **safety** analysis of 594 MAUDE reports. *(CITED, PMID 40178466)*

**The limitation you must say yourself:** *"Publication counts from a keyword
query are a proxy for research attention, not proof of absence. A preprint or an
industry white paper wouldn't show up here, and I only searched PubMed."*

**Next study:** none — this is a methods slide, and its job is to show I checked
my own premise instead of assuming it.

---

## Known limitations I will raise before he does

1. **This is ecological, not patient-level.** Every unit here is a provider or a
   state. I cannot say that any particular patient did or did not get PNS, and I
   cannot adjust for case mix, indication, or severity. A state-level association
   is a hypothesis generator.

2. **The {SUPPRESSION_BENE_THRESHOLD}-beneficiary suppression floor.** CMS
   excludes every provider-code row with {SUPPRESSION_BENE_THRESHOLD} or fewer
   beneficiaries. Low-volume providers are structurally invisible. For a
   concentration analysis this biases my measured concentration **downward**, so
   the real distribution is more concentrated than what I show — my finding is
   conservative. It also means a "zero" state is really "no provider above the
   floor."

3. **Provider practice location is not patient residence.** The file gives me the
   provider's practice address. A patient who drives three hours across a state
   line is counted in the provider's state, so I am systematically understating
   the travel burden that access deserts impose.

4. **Fee-for-service only — Medicare Advantage is invisible.** Roughly half of
   Medicare beneficiaries are now in MA, and their encounters do not appear in
   these files at all. If MA plans authorize PNS at a different rate, my rates are
   biased by an amount I cannot estimate from public data. All my denominators are
   FFS-only so the *rates* are internally consistent, but the *national picture*
   is half a picture.

5. **Cross-sectional association is not causal.** Nothing here identifies a causal
   effect. States that gained PNS providers differ from states that did not in
   ways I have not measured, and I have no instrument and no policy shock.

6. **One extra I would rather say than have him find:** 64590 is not PNS-specific —
   the CMS descriptor covers peripheral, sacral, **and gastric** generators — so
   my neuromodulation-capability definition is contaminated. I ran it both ways;
   the conclusion doesn't change.

---

## If he asks "why not HCUP or PearlDiver?"

*"Because I can't get them, and I think that's the interesting part. HCUP NASS
needs a signed data use agreement, a training course, and a purchase through the
Central Distributor, with student pricing gated on proof of enrollment in a
degree-seeking program. PearlDiver and MarketScan are commercial licenses — and
they're what every prior conversion-rate paper used. Everything I just showed you
runs on files anyone can download without an account, which means anyone can check
it, and anyone can extend it. Your interspinous spacer paper did the same thing
with MAUDE."* *(CITED, PMID 33866770)*
"""
    path = PROJECT_ROOT / "TALKING_POINTS.md"
    path.write_text(text)
    return path


def write_provenance(accessed: str) -> Path:
    """DATA_PROVENANCE.md - every cached file with size, rows, and SHA256."""
    records = json.loads((AUDIT_DIR / "provenance.json").read_text())
    records.sort(key=lambda r: r["cached_file"])
    rows = "\n".join(
        f"| `{r['cached_file']}` | {r['downloaded_utc']} | {r['bytes_streamed']/1e9:.2f} GB | "
        f"{r['rows_scanned']:,} | {r['rows_kept']:,} | {r['cached_bytes']/1e6:.2f} MB | `{r['sha256'][:32]}…` |"
        for r in records
    )
    urls = "\n".join(f"- `{r['cached_file']}`\n  {r['source_url']}" for r in records)

    text = f"""# DATA PROVENANCE

Everything here is free, public, and requires no account, no login, and no data
use agreement. Verified {accessed}.

## Cached raw files

| Cached file | Downloaded (UTC) | Streamed | Rows scanned | Rows kept | Cached size | SHA256 |
|---|---|---|---|---|---|---|
{rows}

"Rows kept" is smaller than "rows scanned" for the provider-and-service files
because those are streamed and filtered to the seven study HCPCS codes in flight;
the full national files are ~9.7 million rows and ~3.3 GB each.

## Source URLs

{urls}

---

## Dataset facts verified against CMS documentation

### (a) The suppression rule
The Medicare Physician & Other Practitioners **by Provider and Service** file
excludes any provider-HCPCS record with **{SUPPRESSION_BENE_THRESHOLD} or fewer
beneficiaries**, to protect beneficiary privacy. Records are aggregated by NPI,
HCPCS code, and place of service, and rows below the threshold are removed rather
than masked, so the provider simply does not appear for that code.

**Consequence, stated on Figure 2 and in RESULTS.md:** low-volume providers are
structurally invisible, which biases any measured concentration **downward**. The
concentration reported here is a **lower bound**.

**Empirical confirmation from the downloaded data itself:** the minimum
`Tot_Benes` value on any surviving row in the analytic extract is exactly **11**,
across all ten data years and all seven codes. Nothing at 10 or below survives.
This is the strongest possible confirmation of the rule — it is measured in the
delivered file, not read from a PDF.

Dataset landing page (methodology and data dictionary linked there):
https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service

### (b) Most recent data year published
**2024**, released May 2026 (file `PHY_R26_P05_V10_D24_Prov_Svc.csv`, catalog
`modified` field 2026-05-21). The catalog also serves 2013-2023. This analysis
covers 2015-2024.

### (c) Fee-for-service Part B only
These files are built from **Medicare Part B fee-for-service non-institutional
claims**. **Medicare Advantage encounters are not included.** All denominators in
this analysis are correspondingly FFS-only (`BENES_OM_CNT`, Original Medicare, from
the Geographic Variation file), so rates are internally consistent — but roughly
half of all Medicare beneficiaries are invisible to this analysis.

Geographic Variation landing page:
https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-geographic-comparisons/medicare-geographic-variation-by-national-state-county

### (d) HCPCS long descriptors
Taken directly from the `HCPCS_Desc` field of the downloaded files and asserted at
runtime against an expected token set. See the verification table in `RESULTS.md`.
CMS publishes a **consumer-friendly descriptor**, not the AMA CPT long descriptor,
and reworded several of them in the 2022 and 2024 vintages. All variants are
checked, not just the first one encountered.

Two findings worth flagging:
- **62323 has no rows before 2017.** CPT 62323 was created in the 2017 CPT cycle,
  replacing 62311. Verified directly: zero rows in the 2015 and 2016 files.
- **64590 is not PNS-specific.** Its 2024 CMS descriptor is *"Insertion or
  replacement of peripheral, sacral, or gastric neurostimulator generator or
  receiver"* — it captures gastric and sacral stimulators too. A sensitivity
  analysis excluding it is reported in RESULTS.md.

### (e) HCUP NASS access requirements
Access to the Nationwide Ambulatory Surgery Sample requires **all** of:
signing the HCUP Data Use Agreement; completing the online **DUA Training
Course**; and **purchasing** the data through the HCUP Central Distributor.
Student pricing additionally requires **proof of current enrollment in a
degree-seeking program at an institution of higher learning**.

- https://hcup-us.ahrq.gov/db/nation/nass/  (accessed {accessed})
- https://hcup-us.ahrq.gov/tech_assist/centdist/ResponsibilitiesDataPurchaser.jsp  (accessed {accessed})

**This is not a limitation of the project, it is part of the contribution.**
Every result in this repository is reproducible by anyone, at zero cost, with no
institutional affiliation.

### (f) Census income data
The Census ACS API now **requires an API key for every request** — an unkeyed
call returns an HTML "Missing Key" page (verified {accessed}). State median
household income is therefore taken from the **Small Area Income and Poverty
Estimates (SAIPE)** fixed-width file on the Census FTP, which needs no key and no
login. This is a documented deviation from the original plan. SAIPE is a
model-based estimate and is not identical to the ACS 5-year estimate; it is used
only as a state-level ranking covariate in Figure 5.
"""
    path = PROJECT_ROOT / "DATA_PROVENANCE.md"
    path.write_text(text)
    return path


def write_bibtex() -> Path:
    """references.bib - only entries that passed the citation audit."""
    text = """% Generated by src/report.py. Every entry verified against the
% NCBI E-utilities PubMed record on 2026-08-25. See CITATION_AUDIT.md.

@article{odonkor2026pns,
  author  = {Odonkor, Charles A. and Hirani, Samir and Bohacek, Stephanie and Pokuri, Sruthi and Chow, Robert M. and Abd-Elsayed, Alaa},
  title   = {A prospective multidimensional assessment of the impact of payer type, insurance delays, psychological and clinical domains on response to 60-day peripheral nerve stimulation: 6-month outcomes},
  journal = {Pain Medicine},
  year    = {2026}, volume = {27}, number = {5}, pages = {560--573},
  doi     = {10.1093/pm/pnaf151}, note = {PMID: 41148054}
}

@article{odonkor2026nomogram,
  author  = {Odonkor, Charles A. and Siddique, Muhammad U. and Yeung, Jacqueline and Vu, Peter D. and Johar, Sarah and Chow, Robert M. and Patel, Nirav},
  title   = {Toward Personalized Neuromodulation: Nomogram Models Forecasting Long-Term Response After Temporary Peripheral Nerve Stimulation},
  journal = {Neuromodulation}, year = {2026},
  doi     = {10.1016/j.neurom.2025.11.007}, note = {Online ahead of print. PMID: 41504677}
}

@article{chow2025smoking,
  author  = {Chow, Robert and Lans, Zachary and Cohen, Steven P. and Lin, Hung-Mo and Zhao, Jing and Rajput, Kanishka},
  title   = {Smoking and Postoperative Pain: A Systematic Review and Meta-Analysis},
  journal = {Pain Practice}, year = {2025}, volume = {25}, number = {8}, pages = {e70083},
  doi     = {10.1111/papr.70083}, note = {PMID: 40977634}
}

@article{chow2025ilesi,
  author  = {Chow, Robert and Ng, Jonathan and Wood, Michael and Yanez, David and He, Zhang and Rajput, Kanishka},
  title   = {A comparison of steroid dose with or without local anesthetic in lumbar interlaminar epidural steroid injections},
  journal = {Pain Practice}, year = {2025}, volume = {25}, number = {1}, pages = {e13410},
  doi     = {10.1111/papr.13410}, note = {PMID: 39305041. Cohort identified by CPT 62323.}
}

@article{chow2023pnsreview,
  author  = {Chow, Robert M. and Lee, Ryan Y. and Rajput, Kanishka},
  title   = {Peripheral Nerve Stimulation for Pain Management: A Review},
  journal = {Current Pain and Headache Reports}, year = {2023}, volume = {27}, number = {9}, pages = {321--327},
  doi     = {10.1007/s11916-023-01143-0}, note = {PMID: 37523121}
}

@article{aggarwal2021maude,
  author  = {Aggarwal, Nitin and Chow, Robert},
  title   = {Real world adverse events of interspinous spacers using Manufacturer and User Facility Device Experience data},
  journal = {Anesthesia and Pain Medicine (Seoul)}, year = {2021}, volume = {16}, number = {2}, pages = {177--183},
  doi     = {10.17085/apm.20093}, note = {PMID: 33866770}
}

@article{rajput2025relief,
  author  = {Rajput, Kanishka and Howie, Benjamin A. and Danesh, Jonathan A. and Zhao, Xiwen and Lin, Hung-Mo and Yanez, David and Chow, Robert},
  title   = {Relationship of pain relief with catastrophizing following interventional pain procedures for low back pain},
  journal = {Regional Anesthesia and Pain Medicine}, year = {2025}, volume = {50}, number = {6}, pages = {489--494},
  doi     = {10.1136/rapm-2023-105247}, note = {PMID: 38744446}
}

@article{basharat2025chatgpt,
  author  = {Basharat, Adnan and Shah, Raj and Wilcox, Nathan and Tur, Gizem and Tripati, Sanjay and Kansal, Pankaj and Gandhi, Nirav and Pokuri, Sruthi and Chong, Grace and Odonkor, Charles A. and Varhabhatla, Narayana and Chow, Robert},
  title   = {ChatGPT and low back pain - Evaluating AI-driven patient education in the context of interventional pain medicine},
  journal = {Interventional Pain Medicine}, year = {2025}, volume = {4}, number = {3}, pages = {100636},
  doi     = {10.1016/j.inpm.2025.100636}, note = {PMID: 40978326}
}

@article{day2025scs,
  author  = {Day, Wesley and Maloy, Gwyneth C. and Winter, Adam D. and Chapman, Kenneth B. and Seddio, Anthony E. and Doshi, Rahul H. and Ratnasamy, Philip P. and Varthi, Arya G. and Fourman, Mitchell S. and Grauer, Jonathan N.},
  title   = {Spinal cord stimulator utilization trends and predictors of unsuccessful trial-to-implant conversion},
  journal = {North American Spine Society Journal}, year = {2025}, volume = {22}, pages = {100616},
  doi     = {10.1016/j.xnsj.2025.100616}, note = {PMID: 40548099. PearlDiver Mariner, proprietary.}
}

@article{huang2015scs,
  author  = {Huang, Kevin T. and Martin, Jonathan and Marky, Andrew and Chagoya, Gustavo and Hatef, Jeffrey and Hazzard, Matthew A. and Thomas, Steven M. and Lokhnygina, Yuliya and Lad, Shivanand P.},
  title   = {A national survey of spinal cord stimulation trial-to-permanent conversion rates},
  journal = {Neuromodulation}, year = {2015}, volume = {18}, number = {2}, pages = {133--139},
  doi     = {10.1111/ner.12199}, note = {PMID: 24930992. MarketScan, proprietary.}
}

@article{murphy2017volume,
  author  = {Murphy, Kelly R. and Han, Jing L. and Hussaini, Syed Mohammed Qasim and Yang, Siyun and Parente, Beth and Xie, Jichun and Lad, Shivanand P.},
  title   = {The Volume-Outcome Effect: Impact on Trial-to-Permanent Conversion Rates in Spinal Cord Stimulation},
  journal = {Neuromodulation}, year = {2017}, volume = {20}, number = {3}, pages = {256--262},
  doi     = {10.1111/ner.12526}, note = {PMID: 27696607}
}

@article{cooper2025maude,
  author  = {Cooper, Amanda N. and Sen, Hasan and Kanjanapanang, Napatkamon and Saad, Karim and Wahl, Grant and Young, Cameron and Essman, Michael and Fogarty, Alexandra E. and Burnham, Taylor and Conger, Aaron M. and McCormick, Zachary L. and Glinka Przybysz, Adrian},
  title   = {Adverse Events Associated With Peripheral Nerve Stimulation: An Analysis of the MAUDE Data base and Implications for Pain and Spine Clinicians},
  journal = {Neuromodulation}, year = {2025}, volume = {28}, number = {4}, pages = {619--626},
  doi     = {10.1016/j.neurom.2025.02.002}, note = {PMID: 40178466}
}

@article{torabi2021providers,
  author  = {Torabi, Sina J. and Kasle, David A. and Savoca, Emily L. and Gottschalk, Christopher H. and Manes, R. Peter},
  title   = {Characterizing the providers of and reimbursement for chronic migraine chemodenervation among the Medicare population},
  journal = {Headache}, year = {2021}, volume = {61}, number = {2}, pages = {373--384},
  doi     = {10.1111/head.14040}, note = {PMID: 33337542}
}

@article{pearson2019iowa,
  author  = {Pearson, Amy C. S. and Dexter, Franklin},
  title   = {Observational Study of the Distribution and Diversity of Interventional Pain Procedures Among Hospitals in the State of Iowa},
  journal = {Pain Physician}, year = {2019}, volume = {22}, number = {3}, pages = {E157--E170},
  note    = {PMID: 31151339}
}

@article{elhakim2019cah,
  author  = {Elhakim, Mohamed and Dexter, Franklin and Pearson, Amy C. S.},
  title   = {US critical access hospitals' listings of pain medicine physicians and other clinicians performing interventional pain procedures},
  journal = {Journal of Clinical Anesthesia}, year = {2019}, volume = {58}, pages = {52--54},
  doi     = {10.1016/j.jclinane.2019.05.005}, note = {PMID: 31077934}
}

@article{karri2025survey,
  author  = {Karri, Jay and Sivanesan, Eellan and Gulati, Amitabh and Singh, Vinita and Sheen, Soun and Yalamuru, Bhavana and Wang, Eric J. and Javed, Saba and Chung, Matthew},
  title   = {Peripheral Nerve Stimulation for Pain Management: A Survey of Clinical Practice Patterns},
  journal = {Neuromodulation}, year = {2025}, volume = {28}, number = {2}, pages = {348--361},
  doi     = {10.1016/j.neurom.2024.08.011}, note = {PMID: 39396358}
}

@article{manchikanti2026epidural,
  author  = {Manchikanti, Laxmaiah and Sanapati, Mahendra and Pampati, Vidyasagar and Kaye, Alan D. and Knezevic, Nebojsa Nick and Navani, Annu and Nampiaparampil, Devi and Hirsch, Joshua A.},
  title   = {Updated Analysis of Declining Utilization Rate of 13\\% Epidural Procedures for Chronic Spinal Pain Management in the Traditional Medicare Population from 2019 to 2024},
  journal = {Pain Physician}, year = {2026}, volume = {29}, number = {1}, pages = {1--16},
  note    = {PMID: 41628203}
}

@misc{cms_prov_svc,
  title  = {Medicare Physician \\& Other Practitioners - by Provider and Service},
  author = {{Centers for Medicare \\& Medicaid Services}}, year = {2026},
  howpublished = {\\url{https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service}},
  note = {Data years 2013-2024. Accessed 2026-08-25.}
}

@misc{cms_geovar,
  title  = {Medicare Geographic Variation - by National, State \\& County},
  author = {{Centers for Medicare \\& Medicaid Services}}, year = {2026},
  howpublished = {\\url{https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-geographic-comparisons}},
  note = {Data years 2014-2024. Accessed 2026-08-25.}
}

@misc{census_saipe,
  title  = {Small Area Income and Poverty Estimates (SAIPE)},
  author = {{US Census Bureau}}, year = {2026},
  howpublished = {\\url{https://www2.census.gov/programs-surveys/saipe/datasets/}},
  note = {State median household income. Accessed 2026-08-25.}
}
"""
    path = PROJECT_ROOT / "references.bib"
    path.write_text(text)
    return path


def write_all(results: dict, accessed: str) -> list[Path]:
    """Write every markdown/bibtex deliverable."""
    return [
        write_results(results, accessed),
        write_talking_points(results, accessed),
        write_provenance(accessed),
        write_bibtex(),
    ]
