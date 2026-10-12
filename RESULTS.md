# RESULTS

All numbers below are computed by `python run.py` from free public CMS and Census
data. Data accessed **2026-08-25**. Most recent published data year: **2024**.
Bootstrap seed 20260825, 2,000 resamples.

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

| Year | PNS (64555) services | Providers | Services per 100k FFS | Index (2017=100) |
|---|---|---|---|---|
| 2015 | 8,959 | 85 | 26.8 | 258 |
| 2016 | 9,454 | 101 | 27.9 | 268 |
| 2017 | 3,497 | 39 | 10.4 | 100 |
| 2018 | 892 | 16 | 2.7 | 26 |
| 2019 | 1,862 | 47 | 5.6 | 54 |
| 2020 | 3,188 | 83 | 9.9 | 95 |
| 2021 | 4,350 | 111 | 14.1 | 136 |
| 2022 | 5,720 | 146 | 19.4 | 186 |
| 2023 | 8,167 | 211 | 28.9 | 277 |
| 2024 | 11,454 | 268 | 41.5 | 398 |

**Read aloud:** PNS volume in fee-for-service Medicare went from
**27 services per 100,000 beneficiaries in 2015**
to **41 in 2024**, delivered by
**268 providers nationally**.

**The honest complication you must state first.** 64555 volume was *higher* in
2015-2016 (27 per 100k) than in 2017-2020, collapsing to a trough of
**2.7 per 100k in 2018** (16 providers nationally)
before growing continuously to 2024. The specialty mix billing 64555 is stable
across the whole period - pain management, anesthesiology, PM&R and ambulatory
surgical centres throughout - so this is **not** a specialty-substitution artifact.
Growth measured from the 2018 trough is
**15.5x**; growth measured from 2015 is
**1.55x**. Quote the second number, not the first.

**External validation of the pipeline.** My independently computed 62323 rate fell
**-12.8% from 2019 to 2024** (2537 to 2213 per 100,000).
Manchikanti et al. report a **13% decline in epidural procedure utilization from
2019 to 2024** in traditional Medicare [manchikanti2026epidural]. Two independent
analyses of the same population agree to within a percentage point. That is the
best evidence available that this pipeline is computing what it claims to compute.

*Note: CPT 62323 was created in the 2017 CPT cycle (replacing 62311). It has zero
rows in the 2015 and 2016 files, verified directly. All series are therefore
indexed to 2017, not 2015.*

---

## Figure 2 - Concentration (THE CENTERPIECE)

### Primary specification: ranked over the common provider universe

In 2024, **11,286 providers** billed at least one of the seven
study codes. Ranking PNS volume across all of them (zero for those who did not
bill it) is the comparison that actually tests a two-tier claim.

| Measure | PNS (64555) | Lumbar epidural (62323) |
|---|---|---|
| Gini coefficient | **0.984** | **0.683** |
| 95% bootstrap CI | [0.982, 0.986] | [0.676, 0.690] |
| Share delivered by top 10% of providers | **100.0%** | **49.0%** |
| Total services | 11,454 | 611,382 |

**Read aloud:** *"Among the same 11,286 interventional pain providers,
the top 10% deliver 100% of all PNS volume, versus
49% of all epidural volume. The Gini for PNS is
0.98; for epidurals it is 0.68. The confidence intervals do not
come close to overlapping."*

**Unique providers, 2024:** 268 billed 64555 nationally versus
7,346 who billed 62323 - a **27-fold difference**.
That single ratio is the two-tier thesis in one number.

### Secondary specification: ranked among billers only - and it REVERSES

| Measure | PNS (64555) | Lumbar epidural (62323) |
|---|---|---|
| Providers billing the code | 268 | 7,346 |
| Gini among billers | 0.332 [0.291, 0.369] | 0.513 [0.505, 0.521] |
| Top 10% share | 27.2% | 38.3% |

**Restricted to providers who actually bill the code, PNS looks LESS concentrated
than epidurals, not more.** Raise this yourself. The explanation is the
suppression floor: CMS drops every provider-code row with
10 or fewer beneficiaries, and that floor removes a far
larger fraction of a rare procedure's tail than a common one's. Evidence, 2024:

- Minimum beneficiaries on any surviving 64555 row: **11** (the floor, exactly as documented)
- Median beneficiaries per PNS provider: **16**; per epidural provider: **39**
- **47% of PNS providers sit at 11-15 beneficiaries**, pressed right against the floor, versus **14%** of epidural providers.

Nearly half the visible PNS providers are at the edge of the cliff, so most of the
PNS distribution is below it and unobserved. The billers-only Gini is therefore an
artifact of differential truncation; the common-base Gini is not. **In both
specifications the truncation biases against finding concentration, so the
common-base result is conservative.**

---

## Figure 3 - Access deserts

| Year | States with ZERO PNS providers | States with < 3 | % FFS benes, zero-PNS state | % FFS benes, < 3 providers |
|---|---|---|---|---|
| 2015 | 33 | 42 | 37.7% | 58.7% |
| 2016 | 30 | 43 | 32.6% | 65.6% |
| 2017 | 36 | 47 | 51.6% | 81.7% |
| 2018 | 42 | 49 | 65.5% | 91.7% |
| 2019 | 31 | 45 | 37.1% | 73.8% |
| 2020 | 31 | 42 | 38.1% | 59.4% |
| 2021 | 21 | 39 | 14.3% | 52.8% |
| 2022 | 22 | 33 | 20.4% | 40.0% |
| 2023 | 16 | 28 | 13.2% | 26.5% |
| 2024 | 14 | 27 | 7.8% | 24.3% |

**Read aloud:** In 2024, **14 states still had no Medicare
provider billing PNS at all**, and **24% of fee-for-service
beneficiaries - 6,722,156 people - lived in a state with fewer than
3 PNS providers.**

**States with zero PNS providers in 2024:** AK, AL, DC, DE, HI, ME, MS, MT, ND, NM, SD, VT, WV, WY

**The direction is good news, and say so.** Deserts peaked in 2018 at
**42 states** covering **65%** of beneficiaries, and have
fallen steadily since. This is a diffusion story, not a stagnation story. The
finding is that diffusion is **incomplete**, not that it is absent.

---

## Figure 4 - Does general pain-physician supply predict PNS access?

Negative binomial (NB2), outcome = 64555 service count, log offset = FFS
beneficiary count, year fixed effects, standard errors clustered on state.

| | Model A | Model B |
|---|---|---|
| General interventional pain provider density | **IRR 1.108** [1.043, 1.177], p < 0.001 | **IRR 1.089** [1.028, 1.153], p = 0.004 |
| Neuromodulation-capable provider density | - | **IRR 1.129** [1.037, 1.229], p = 0.005 |
| N (state-years) | 510 | 510 |
| Clusters (states) | 51 | 51 |
| Pseudo R² | 0.018 | 0.022 |
| Overdispersion α | 6.75 | 6.55 |
| Pearson dispersion | 0.93 | 1.03 |

### This result contradicts the hypothesis. Report it that way.

The expected story was that the general-density coefficient would shrink toward
1.0 and lose significance once neuromodulation density entered. **It does not.**
It moves from 1.108 to 1.089 - a shift of
0.020 - and remains significant at p = 0.004.
Neuromodulation density is also positive and significant
(IRR 1.129, p = 0.005), but it does not displace general supply.

**What you can honestly say:** both supplies predict PNS volume, each adds
information beyond the other, and neither is close to sufficient - **pseudo R² is
only 0.022**, so 98% of the variation in state PNS volume is explained by
something other than how many pain physicians a state has. That is still a useful
claim: provider counts are a weak proxy for access to this therapy. It is a
weaker claim than "the conventional metric is the wrong denominator," and the
weaker claim is the one the data support.

Overdispersion α = 6.55 is far from zero, confirming the negative binomial
over Poisson.

**Sensitivity (64590 excluded).** The CMS descriptor for 64590 is
*"Insertion or replacement of peripheral, sacral, or gastric neurostimulator
generator or receiver"* - it is not PNS-specific and captures gastric and sacral
stimulators. Redefining neuromodulation capability as 64555/63650/63685 only:
general density IRR 1.084, neuromodulation density IRR
1.157 (p = 0.004). The conclusion is unchanged.

---

## Figure 5 - The equity gradient

Advanced-to-basic ratio = 64555 services per 1,000 62323 services, by state, 2024.

| | Income (Figure 5) | Dual-eligible share (Figure 5b) |
|---|---|---|
| States analysed | 51 | 51 |
| Pearson r | 0.013 (p = 0.929) | -0.135 (p = 0.344) |
| Spearman ρ | 0.073 (p = 0.612) | -0.252 (p = 0.074) |

### This is a null result. Do not oversell it.

There is **no detectable relationship between state median household income and
the advanced-to-basic ratio** (r = 0.013, p = 0.929). The dual-eligible
association leans in the predicted direction and is larger on ranks than on
levels (Spearman ρ = -0.252, p = 0.074), but does not reach
conventional significance with 51 states.

**What you can honestly say:** *"I expected an income gradient and I did not find
one at state level. With 51 units and a therapy this rare, I am underpowered for
the effect size I was looking for, and states are far too coarse - the gradient,
if it exists, is between a county in the Mississippi Delta and a county in
Fairfield, not between Mississippi and Connecticut. That is the argument for
doing this at county level, which is the next study."*

---

## Figure 6 - The literature gap, quantified

Exact PubMed queries, run through NCBI E-utilities `esearch` on 2026-08-25:

- **SCS:** `("spinal cord stimulation"[Title/Abstract]) AND (access[Title/Abstract] OR utilization[Title/Abstract] OR disparities[Title/Abstract] OR "geographic variation"[Title/Abstract] OR epidemiology[Title/Abstract])`
- **PNS:** `("peripheral nerve stimulation"[Title/Abstract]) AND (access[Title/Abstract] OR utilization[Title/Abstract] OR disparities[Title/Abstract] OR "geographic variation"[Title/Abstract] OR epidemiology[Title/Abstract])`

The two strings are identical except for the therapy term.

| Year | SCS papers | PNS papers |
|---|---|---|
| 2015 | 8 | 2 |
| 2016 | 10 | 1 |
| 2017 | 18 | 1 |
| 2018 | 13 | 2 |
| 2019 | 9 | 3 |
| 2020 | 14 | 4 |
| 2021 | 23 | 6 |
| 2022 | 17 | 7 |
| 2023 | 29 | 6 |
| 2024 | 27 | 12 |
| **Total** | **168** | **44** |

**Read aloud:** *"Across ten years, matched queries return **168 spinal cord
stimulation access papers and 44 peripheral nerve stimulation access papers** -
about **4 to 1**. The PNS count is rising, so the field is turning
toward this, but the gap is real and it is measured, not asserted."*

Separately, `"peripheral nerve stimulation" AND Medicare` returns **4 records in
all of PubMed**, none of which is an access or provider-distribution study
(see `NOVELTY_CHECK.md`).

---

## HCPCS verification table

| Code | Tier | Status | Distinct descriptors | Years present | Descriptor from the file |
|---|---|---|---|---|---|
| 64555 | ADVANCED | **PASS** | 2 | 2015-2024 | Implantation of peripheral nerve neurostimulator electrodes, accessed through the skin |
| 64590 | ADVANCED | **PASS** | 3 | 2015-2024 | Insertion or replacement of peripheral, sacral, or gastric neurostimulator generator or receiver |
| 63650 | ADVANCED | **PASS** | 2 | 2015-2024 | Implantation of spinal neurostimulator electrodes, accessed through the skin |
| 63685 | ADVANCED | **PASS** | 3 | 2015-2024 | Insertion or replacement of spinal neurostimulator generator or receiver |
| 62323 | BASIC | **PASS** | 2 | 2017-2024 | Injection of substance into spinal canal of lower back or sacrum using imaging guidance |
| 64483 | BASIC | **PASS** | 3 | 2015-2024 | Injections of anesthetic and/or steroid drug into lower or sacral spine nerve root using imaging guidance, single level |
| 64635 | BASIC | **PASS** | 2 | 2015-2024 | Destruction of lower or sacral spinal facet joint nerves using imaging guidance, single facet joint |

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
