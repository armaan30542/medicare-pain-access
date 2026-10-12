# CITATION_AUDIT.md

Verification pass over SOURCES.md sections A, B, and D.
**Method:** every record resolved through the NCBI E-utilities `efetch` API
(`db=pubmed&retmode=xml`) on **2026-08-25**. Raw XML for each record is cached in
`audit/pm_<PMID>.xml` so any claim below can be re-checked without re-querying.
(PubMed's HTML pages sit behind a cookie interstitial and cannot be scraped; the
API is the authoritative route and is what I used.)

---

## ⚠️ FLAGS — read before the meeting

**1. Do NOT say "each 10-day insurance delay cut the odds of relief by 89%."**
The published abstract of Odonkor 2026 (PMID 41148054) reads: *each 10-day delay
reduced the odds of ≥50% and ≥80% relief "by 89% and ≥80%, respectively."* The
second figure is a percentage-threshold symbol where a magnitude should be — the
sentence is internally inconsistent **as published**. Every other number in that
abstract verifies cleanly. Say the response rates, which are solid, and if the
delay effect comes up, say **"insurance delay independently predicted worse
response"** without attaching a percentage. This is his own paper; a garbled
quote-back would be worse than saying nothing.

**2. The MAUDE PNS safety paper is Cooper, not McCormick.**
SOURCES.md lists it as "McCormick ZL et al." McCormick is the second-to-last
author. First author is **Cooper AN**. If you call it "McCormick's paper" in front
of a neuromodulation physician who reads Neuromodulation, that is a small but
avoidable tell. Say **"Cooper and McCormick's MAUDE analysis."**

**3. Two of Dr. Chow's own papers are cited with the wrong year** in SOURCES.md
(both are off by one — an epub-vs-issue-date confusion). Corrected below. These
are papers he wrote; the year should be right.

**Everything I plan to say out loud about his 60-day PNS paper verifies.**
n=121, Dec 2023–Dec 2024, single center, 66.9% / 28.9% at 60 days,
78.5% / 44.6% at 6 months, 62.5% of 60-day non-responders reaching ≥50% by
6 months — all confirmed verbatim against the abstract.

---

## Section A — Dr. Chow's work

| citation_key | claim_checked | source_url | status | correction_if_any |
|---|---|---|---|---|
| `odonkor2026pns` | Full citation: Pain Med. 2026;27(5):560-573; DOI 10.1093/pm/pnaf151; authors Odonkor CA, Hirani S, Bohacek S, Pokuri S, Chow RM, Abd-Elsayed A | https://pubmed.ncbi.nlm.nih.gov/41148054/ | **PASS** | Precise issue date is 2026 May 1. Author list, order, journal, volume, issue, pages, DOI all exact. |
| `odonkor2026pns` | n=121 adults, temporary PNS, Dec 1 2023 – Dec 1 2024, single center | same | **PASS** | Abstract: prospective single-center observational cohort, 121 adult patients with chronic pain. |
| `odonkor2026pns` | 60-day: 66.9% ≥50%, 28.9% ≥80% | same | **PASS** | Verbatim in abstract. |
| `odonkor2026pns` | 6-month: 78.5% ≥50%, 44.6% ≥80% | same | **PASS** | Verbatim in abstract. |
| `odonkor2026pns` | 62.5% of 60-day non-responders reached ≥50% by 6 months | same | **PASS** | Abstract also gives 45.3% reaching ≥80% — a second usable number. |
| `odonkor2026pns` | "Insurance delay and high baseline disability predicted worse outcomes" | same | **PASS** *(with flag 1)* | Direction verified. The *magnitude* sentence is corrupt as published — do not quote it. |
| `odonkor2026nomogram` | Neuromodulation 2026; DOI 10.1016/j.neurom.2025.11.007; Odonkor C, Siddique M, Yeung J, Vu P, Johar S, Chow R, Patel N | https://pubmed.ncbi.nlm.nih.gov/41504677/ | **PASS → upgrade [S] to [V]** | Full initials: Odonkor CA, Siddique MU, Yeung J, Vu PD, Johar S, Chow RM, Patel N. Online ahead of print — no volume/issue/pages assigned yet. Adds usable numbers: n=110, multisite, 12-month ≥50% outcome, clinical nomogram AUC 0.91, psychosocial-enhanced AUC 0.97. |
| `chow2025smoking` | Pain Pract. 2025 Nov;25(8):e70083; DOI 10.1111/papr.70083; Chow R, Lans Z, Cohen SP, Lin HM, Zhao J, Rajput K | https://pubmed.ncbi.nlm.nih.gov/40977634/ | **PASS** | Month, volume, issue, pages, DOI, author order all exact. |
| `chow2025smoking` | SMD POD0 0.46 (0.26-0.66), POD1 0.32 (0.17-0.46), POD2 0.38 (0.24-0.52); higher opioid requirements | same | **PASS** | All three CIs verbatim. Opioid SMDs additionally: POD0 0.62 (0.43-0.80), POD1 0.49 (0.36-0.62), POD2 0.70 (0.56-0.84). Five studies in the pain-score meta-analysis. |
| `basharat2025chatgpt` | Interv Pain Med. 2025;4:100636; PMID 40978326; 12-author list ending Chow R | https://pubmed.ncbi.nlm.nih.gov/40978326/ | **CORRECTED** | Add issue: **2025;4(3):100636**. Author list order confirmed exactly as in SOURCES.md (Odonkor's initials are CA). |
| `rajput2025catastrophizing` | Reg Anesth Pain Med. 2025; DOI 10.1136/rapm-2025-107047; Rajput K, Fujita-Howie B, Zhao X, Lin H, Chow R | https://pubmed.ncbi.nlm.nih.gov/40819919/ | **PASS → upgrade [S] to [V]** | Full initials Fujita-Howie BA, Lin HM. Online ahead of print; no volume/issue/pages. **No abstract is indexed in PubMed** — do not attribute any number to this paper. |
| `rajput2024relief` | Reg Anesth Pain Med. **2024**;50:489-494 | https://pubmed.ncbi.nlm.nih.gov/38744446/ | **CORRECTED** | Year is **2025**, not 2024: *Reg Anesth Pain Med. 2025 Jun 10;50(6):489-494.* (Epub 2024 was the online-first date.) Authors confirmed: Rajput K, Howie BA, Danesh JA, Zhao X, Lin HM, Yanez D, Chow R. n=128 enrolled. |
| `chow2024steroid` | Pain Practice. **2024**;25:e13410 | https://pubmed.ncbi.nlm.nih.gov/39305041/ | **CORRECTED** | Year is **2025**, not 2024: *Pain Pract. 2025 Jan;25(1):e13410* (epub 2024 Sep 20). Authors confirmed: Chow R, Ng J, Wood M, Yanez D, He Z, Rajput K. n=311. **Directly relevant to this project: that study identified its cohort by CPT code 62323 — the same code I use as my "basic procedure" comparator.** |
| `chow2023pnsreview` | Curr Pain Headache Rep. 2023;27:321-327; Chow R, Lee R, Rajput K | https://pubmed.ncbi.nlm.nih.gov/37523121/ | **CORRECTED** | Add issue: **2023;27(9):321-327**. Full initials Chow RM, Lee RY, Rajput K. |
| `aggarwal2021maude` | INCOMPLETE in SOURCES.md — "Real world adverse events of interspinous spacers using MAUDE database", Aggarwal N, Chow R | https://pubmed.ncbi.nlm.nih.gov/33866770/ | **COMPLETED — keep it in the deck** | Full citation: **Aggarwal N, Chow R. "Real world adverse events of interspinous spacers using Manufacturer and User Facility Device Experience data." Anesth Pain Med (Seoul). 2021;16(2):177-183. doi:10.17085/apm.20093. PMID 33866770.** Note the real title ends *"…Experience data,"* not *"…Experience (MAUDE) database."* Method was a **disproportionality analysis** on X-Stop, Vertiflex, and Coflex; significant signals for fracture, migration, and pain/worsening symptoms. This confirms the premise you wanted it for: **he has already published a study built entirely on a free federal public dataset.** |

## Section B — Prior art

| citation_key | claim_checked | source_url | status | correction_if_any |
|---|---|---|---|---|
| `day2025scs` | "SCS utilization trends and predictors of unsuccessful trial-to-implant conversion," NASSJ 2025, PMID 40548099 | https://pubmed.ncbi.nlm.nih.gov/40548099/ | **CORRECTED (incomplete → complete)** | SOURCES.md gave no authors. Full: **Day W, Maloy GC, Winter AD, Chapman KB, Seddio AE, Doshi RH, Ratnasamy PP, Varthi AG, Fourman MS, Grauer JN. N Am Spine Soc J. 2025;22:100616.** pii S2666-5484(25)00036-8 confirmed. Note this is a **Yale orthopaedics group (Grauer lab)** — worth knowing before you walk in. |
| `day2025scs` | Conversion 63.4% (2010) → 73.3% (2021) | same | **PASS** | Verbatim. |
| `day2025scs` | OR: age 0.97/decade, male 0.93, Medicaid 0.78, Medicare 0.85, Northeast 0.63, West 0.82, South 0.85 | same | **PASS** | All seven verbatim. Reference categories confirmed: commercial insurance and Midwest region. |
| `day2025scs` | SCS trialing 17.9 → 22.9 per 100,000 covered lives | same | **PASS** | Verbatim. Adds: n=265,756 trials, 67% overall conversion. |
| `day2025scs` | Uses PearlDiver Mariner (proprietary) | same | **PASS** | Abstract states 2010–2022 PearlDiver Mariner. SOURCES.md implied 2010–2021; the **database window is 2010–2022**, the conversion-rate series runs to 2021. |
| `huang2015scs` | MarketScan 2000-2009; commercial 43% vs 37%; North Central vs Northeast OR 1.48 (1.31-1.66) | https://pubmed.ncbi.nlm.nih.gov/24930992/ | **CORRECTED (incomplete → complete)** | Numbers all verbatim. Missing citation now filled: **Huang KT, Martin J, Marky A, Chagoya G, Hatef J, Hazzard MA, Thomas SM, Lokhnygina Y, Lad SP. Neuromodulation. 2015;18(2):133-139. doi:10.1111/ner.12199.** Adds: n=21,672 trials, 41.4% overall conversion. |
| `murphy2017volume` | "Volume-Outcome Effect," high-volume implanters convert better, PMID 27696607 | https://pubmed.ncbi.nlm.nih.gov/27696607/ | **CORRECTED (incomplete → complete)** | **Murphy KR, Han JL, Hussaini SM, Yang S, Parente B, Xie J, Lad SP. Neuromodulation. 2017;20(3):256-262. doi:10.1111/ner.12526.** Truven MarketScan 2007-2012. n=17,850 trials by 3,028 providers; 64.7% conversion; high-volume (>25) vs low-volume (3-8) 65.9% vs 63.3%, p=0.029; multivariate OR 1.12 (1.02-1.22). **This is your strongest supporting citation for why concentration matters clinically.** |
| `cooper2025maude` | "McCormick ZL et al., Adverse Events Associated With PNS: MAUDE," 2025, PMID 40178466 | https://pubmed.ncbi.nlm.nih.gov/40178466/ | **CORRECTED — wrong first author** | First author is **Cooper AN**, not McCormick. Full: **Cooper AN, Sen H, Kanjanapanang N, Saad K, Wahl G, Young C, Essman M, Fogarty AE, Burnham T, Conger AM, McCormick ZL, Glinka Przybysz A. Neuromodulation. 2025 Jun;28(4):619-626.** (epub 2025 Apr 3). Article ID confirmed. |
| `cooper2025maude` | CY2023 only; infection, lead migration, skin erosion most common | same | **PASS** | Exact figures: **594 unique MDRs**, five FDA-approved PNS devices, infection **22.7%**, migration **14.7%**, skin erosion **9.4%**; Jan 1–Dec 31 2023. |
| *"the only major PNS public-data paper; no one has done access or concentration for PNS"* | the novelty premise itself | see NOVELTY_CHECK.md | **PASS — independently re-tested** | Confirmed by 11 PubMed queries. `"peripheral nerve stimulation" AND Medicare` returns **4 records** in all of PubMed, none of them an access or distribution study. |

## Section D — HCUP NASS access requirements

See `DATA_PROVENANCE.md` for the verification of the HCUP DUA / training /
purchase / degree-seeking-enrollment language, captured with its access date.

---

## Status summary

| Status | Count |
|---|---|
| PASS | 13 |
| CORRECTED | 8 |
| UNVERIFIABLE | 0 |

Every `[S]` entry in SOURCES.md sections A and B has been resolved to `[V]` or
corrected. No citation had to be dropped — including the Aggarwal/Chow MAUDE
paper, which is now complete and is worth keeping precisely because it shows he
already publishes off free federal data.
