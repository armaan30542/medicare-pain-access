# NOVELTY_CHECK.md

**Question tested:** has anyone published a geographic-access or provider-concentration
analysis of **peripheral nerve stimulation (PNS)**?

**Method.** NCBI E-utilities `esearch`/`esummary`/`efetch` against PubMed, run
2026-08-25, from `audit/novelty_search.py`. Every query string, hit count, and
returned record is cached verbatim in `audit/novelty_raw.json` so this is
re-runnable and auditable. I ran the six queries specified in the brief plus five
additional adversarial queries designed to *find* a scoop, not to avoid one.

## Verdict: **NOVEL**

No indexed paper performs provider-level concentration (Gini/Lorenz), state-level
access-desert, or income/dual-eligibility gradient analysis for PNS. The specific
combination — CPT 64555, provider-level Medicare Part B public-use files, and a
concentration/equity framing — returns zero hits.

Two of my five figures are **partially anticipated in their trend component only**
(details below). Three are, as far as PubMed indexes, unprecedented.

## Queries run and hit counts

| # | Query | Hits | Anything that scoops me? |
|---|---|---|---|
| Q1 | `"peripheral nerve stimulation"[Title] AND (Medicare OR access OR disparities OR utilization OR geographic)` | 125 | No. One relevant: a micro-IPG cost/utilization study (39757932). Rest are clinical/technical. |
| Q2 | `"64555"` | 18 | No. 17 of 18 are unrelated (analytical chemistry, materials science — the string matches sample IDs). The one relevant hit is 35077894, discussed below. |
| Q3 | `(neuromodulation) AND ("geographic variation" OR county OR "access to care") AND Medicare` | 24 | No. Dominated by pharmacotherapy geographic-variation papers. |
| Q4 | `("spinal cord stimulation" OR "peripheral nerve stimulation") AND ("Medicare Provider Utilization" OR "Physician and Other Practitioners")` | 6 | No. Surveys and social-media analyses, not claims-file analyses. |
| Q5 | `(Gini OR Lorenz OR concentration) AND (Medicare) AND (pain OR neuromodulation)` | 45 | No. Zero apply Gini/Lorenz to a pain procedure. |
| Q6 | `"interventional pain" AND (disparities OR "access") AND (rural OR income)` | 11 | No. Closest are two Iowa/critical-access-hospital papers (31151339, 31077934). |
| Q7 | `"peripheral nerve stimulation" AND (provider OR physician) AND (concentration OR volume OR supply OR density)` | 137 | No. "Concentration" hits are drug/anesthetic concentration, not provider concentration. |
| Q8 | `"peripheral nerve stimulation" AND Medicare` | **4** | No. Two are industry cost-savings analyses; one is SCS MRI lead-shielding; one is from 2004. |
| Q9 | `("peripheral nerve stimulation") AND (trends OR utilization OR "practice patterns") AND (national OR Medicare OR database)` | 38 | No. Clinical trials, reviews, MAUDE safety. |
| Q10 | `Manchikanti[au] AND Medicare AND utilization AND (neuromodulation OR "spinal cord stimulation")` | 2 | Partially — 34323431, see below. |
| Q11 | `("spinal cord stimulation" OR neuromodulation) AND Medicare AND (provider OR physician) AND (distribution OR concentration OR workforce OR density)` | 15 | No. |

**The number that matters: `"peripheral nerve stimulation" AND Medicare` returns 4 papers in all of PubMed.**
None of the four is an access, geography, or provider-distribution study.

## Every relevant paper found

**Directly on PNS**
- **40178466** — Cooper AN, Sen H, Kanjanapanang N, … McCormick ZL, Glinka Przybysz A.
  *Adverse Events Associated With Peripheral Nerve Stimulation: An Analysis of the MAUDE Data base.*
  Neuromodulation 2025;28(4):619-626. 594 MDRs, CY2023. **Safety, not access.**
  (Note: SOURCES.md attributes this to McCormick as first author — it is Cooper. See CITATION_AUDIT.md.)
- **39396358** — Karri J, Sivanesan E, Gulati A, et al. *PNS for Pain Management: A Survey of Clinical Practice Patterns.* Neuromodulation 2025;28(2):348-361. n=94 physician survey. Self-reported practice variation — **not measured delivery, no denominator, no geography.**
- **39589685 / 38980601** — Industry-sponsored cost-savings analyses of 60-day PNS. Cost, not access.
- **39757932** — Real-world healthcare utilization/costs of PNS with a micro-IPG system. Device-registry framing.
- **37523121** — Chow RM, Lee RY, Rajput K. *PNS for Pain Management: A Review.* Narrative review.

**On SCS (the therapy that *has* been studied this way)**
- **34323431** — Manchikanti L, et al. *Spinal Cord Stimulation Trends of Utilization and Expenditures in FFS Medicare Population from 2009 to 2018.* Pain Physician 2021. **Closest on data source.** FFS Medicare Part B, national/state utilization. SCS only; no provider-level file, no concentration measure, no equity gradient.
- **40548099** — Day W, Maloy GC, Winter AD, … Grauer JN. *SCS utilization trends and predictors of unsuccessful trial-to-implant conversion.* N Am Spine Soc J 2025;22:100616. PearlDiver Mariner, **proprietary**.
- **24930992** — Huang KT, et al. Neuromodulation 2015;18(2):133-139. MarketScan, **proprietary**.
- **27696607** — Murphy KR, et al. *The Volume-Outcome Effect.* Neuromodulation 2017;20(3):256-262. MarketScan. **Supports my concentration premise** (high-volume implanters convert better) but is SCS and proprietary.
- **35690511** — Clinical longevity of 106,462 SCS devices in Medicare. Device survival, not access.

**Methodologically closest, different procedure**
- **33337542** — Torabi SJ, Kasle DA, Savoca EL, Gottschalk CH, Manes RP. *Characterizing the providers of and reimbursement for chronic migraine chemodenervation among the Medicare population.* Headache 2021;61(2):373-384. **Uses the exact file I use** (Medicare Provider Utilization and Payment Data) to characterize who delivers one specific procedure. No Gini, no geography, no equity gradient — and not a pain-procedure/neuromodulation comparison.
- **31151339** — Pearson ACS, Dexter F. *Distribution and Diversity of Interventional Pain Procedures Among Hospitals in the State of Iowa.* Pain Physician 2019;22(3):E157-E170. **Closest on concept** — explicitly asks whether few proceduralists do most procedures. One state, hospital facilities, 2012-2017, not PNS.
- **31077934** — Elhakim M, Dexter F, Pearson ACS. *US critical access hospitals' listings of pain medicine physicians…* J Clin Anesth 2019;58:52-54. Rural interventional pain availability via **website listings**, n=110 sampled hospitals.
- **35077894** — Nguyen B, Parikh P, Singh R, Patel N, Noland SS. *Trends in Peripheral Nerve Surgery: Workforce, Reimbursement, and Procedural Rates.* World Neurosurg 2022;160:e180-e188. Medicare Provider Utilization Database, 2012-2019, peripheral nerve **surgery** workforce by specialty. **This is the single closest "workforce + 64555-adjacent + Medicare public file" paper.** It is about surgical decompression/repair volume by specialty, not neuromodulation access, no concentration statistic, no geography, no equity.
- **41628203** — Manchikanti L, et al. *Updated Analysis of Declining Utilization Rate of 13% Epidural Procedures … 2019 to 2024.* Pain Physician 2026;29(1):1-16. **Directly relevant to my Figure 1 basic-procedure line** and gives me an external validation target: epidural utilization declined ~13% 2019→2024 in traditional Medicare.

## Which of my figures survive

| Figure | Status | Reasoning |
|---|---|---|
| **1 — PNS growth vs SCS vs epidural** | **Partially anticipated** | The *epidural* line replicates Manchikanti (41628203) and the *SCS* line overlaps Manchikanti (34323431). The **PNS line is new** — no published national FFS Medicare trend for 64555 exists. **Pivot:** stop presenting Fig 1 as a discovery. Present it as *calibration* — "my epidural series reproduces the published 13% decline, which is how you know the pipeline is right; now look at the PNS line nobody has plotted." That converts a redundancy into a credibility asset. |
| **2 — Lorenz/Gini, 64555 vs 62323** | **NOVEL** | Zero hits applying Gini/Lorenz to any Medicare pain procedure (Q5, n=45). Pearson & Dexter asked the question in Iowa; nobody has answered it nationally, and nobody at all for PNS. **This is the strongest slide.** |
| **3 — Access deserts** | **NOVEL** | No state-level PNS provider-count analysis exists. |
| **4 — Density does not predict access** | **NOVEL** | No published model regresses PNS volume on pain-provider supply. |
| **5 — Equity gradient (income, dual-eligible)** | **NOVEL for PNS** | Income/insurance gradients exist for SCS *conversion* (40548099: Medicaid OR 0.78, Medicare OR 0.85) but never for PNS and never as an advanced-to-basic ratio. |
| **6 — Literature gap** | **NOVEL by construction** | It measures the gap the other five exploit. |

## The three closest papers — be ready to name these on the call

1. **Manchikanti 2021, Pain Physician (PMID 34323431)** — "SCS Trends of Utilization and Expenditures in FFS Medicare, 2009-2018." *Say:* "That's the closest thing to my data source, and it stops at SCS and stops at utilization. It never opens the provider-level file."
2. **Torabi 2021, Headache (PMID 33337542)** — migraine chemodenervation provider characterization. *Say:* "That paper proves the method works — provider-level Medicare public files can characterize who actually delivers a procedure. I'm applying an established method to a procedure nobody has applied it to."
3. **Pearson & Dexter 2019, Pain Physician (PMID 31151339)** — Iowa interventional pain distribution. *Say:* "They asked my exact question — do a few proceduralists do most of the work — but in one state, on hospital facility data. I'm asking it nationally, at the provider level, for the newest therapy in the field."

## Honest caveats on this novelty check

- PubMed only. I did not systematically search Embase or Scopus (no free API), and my medRxiv coverage is limited to what PubMed indexes. A preprint could exist.
- Absence from a keyword index is weak evidence of absence. Industry white papers, HEOR posters, and abstracts presented at NANS/ASRA would not appear here.
- I searched in English only.
