# DECK NOTES - private crib sheet

Not shown on screen. Generated from the same artifacts as deck.html, so the numbers here cannot drift from the numbers on the slide.

**Before anything else:** do not quote the 10-day-delay magnitude from PMID 41148054 - the published abstract is internally inconsistent there. Say "insurance delay independently predicted worse response" and stop.
**The MAUDE PNS paper is Cooper et al., not McCormick et al.** (PMID 40178466).

---

## 1. The one-liner

**Say:**
- 268 PNS providers vs 7,346 epidural providers (27-fold)
- Top 10% deliver 100.0% of PNS volume vs 49.0%
- Gini 0.984 vs 0.683

**He'll ask:** Isn't 64555 just a low-volume code, so of course it looks concentrated?

**Answer:** That is exactly why I rank both codes over the same provider universe rather than among billers only - the common-base comparison removes the volume asymmetry, and I show the billers-only version too because it reverses.

## 2. Why this question

**Say:**
- n=121 adults, temporary PNS, Dec 1 2023 – Dec 1 2024, single center
- 60-day: 66.9% ≥50%, 28.9% ≥80%
- 62.5% of 60-day non-responders reached ≥50% by 6 months

**He'll ask:** Are you saying my study was measuring the wrong thing?

**Answer:** The opposite - your cohort is the cleanest evidence that delay costs response, and I am asking what happens to the people who never enter a cohort like it.

## 3a. Figure 1 - growth

**Say:**
- PNS volume has risen 16-fold since its 2018 trough

**He'll ask:** Why does the curve start high in 2015 and collapse?

**Answer:** I don't know, and I say so - the specialty mix billing 64555 is stable across the whole period, so it isn't specialty substitution, and I quote growth off the trough with that caveat attached.

## 3b. Figure 2 - concentration (THE slide)

**Say:**
- Gini 0.984 [0.982, 0.986] vs 0.683 [0.676, 0.690]
- Top 10%: 100.0% vs 49.0%
- Billers-only Gini REVERSES: 0.332 [0.291, 0.369] vs 0.513 [0.505, 0.521]

**He'll ask:** Doesn't the suppression floor break this?

**Answer:** It biases concentration downward, so my estimate is a floor - and it is precisely why the billers-only specification inverts, which I show rather than hide.

## 3c. Figure 3 - deserts

**Say:**
- 14 states with zero PNS providers
- 24.3% of FFS beneficiaries in a state with fewer than three

**He'll ask:** Aren't deserts just shrinking on their own?

**Answer:** Yes, and I lead with that - the finding is that diffusion is incomplete, not absent.

## 3d. Figure 4 - supply models (CONTRADICTS ME)

**Say:**
- General density IRR in Model B: IRR 1.089 [1.028, 1.153], p = 0.004
- Neuromodulation density: IRR 1.129 [1.037, 1.229], p = 0.005
- Pseudo R2 0.022 on 510 state-years

**He'll ask:** So your hypothesis failed here?

**Answer:** Yes - general supply keeps predicting after adjustment, so the honest claim is that provider counts are a weak proxy, not the wrong one.

## 3e. Figure 5 - equity (NULL)

**Say:**
- Income: 0.013 (p = 0.929)
- Dual-eligible: -0.252 (p = 0.074)

**He'll ask:** Doesn't a null undercut the whole equity framing?

**Answer:** At state level, yes - and I think the state is the wrong unit, which is why the county-level version is the next study rather than a rescue.

## 3f. Figure 6 - literature gap

**Say:**
- 168 SCS papers vs 44 PNS papers

**He'll ask:** Keyword counts prove nothing, do they?

**Answer:** Correct - they proxy research attention, and I raise that caveat myself before it gets raised for me.

## 4. Novelty

**Say:**
- Verdict: NOVEL
- Closest: PMID 34323431; PMID 33337542; PMID 31151339

**He'll ask:** Has nobody really done this?

**Answer:** "peripheral nerve stimulation" AND Medicare returns four records in all of PubMed, and none of them is an access or provider-distribution study.

## 5. Limitations

**Say:**
- 3 of 6 push against the finding
- Suppression floor: measured concentration is a lower bound

**He'll ask:** Isn't this all ecological?

**Answer:** It is, entirely - it generates a hypothesis about delivery structure and cannot speak to any individual patient.

## 6-8. Methods, provenance, references

**Say:**
- Audit: 13 pass, 8 corrected, 0 unverifiable

**He'll ask:** Where did the data come from and can I rerun it?

**Answer:** Three free CMS files plus Census SAIPE, no login and no DUA - one command rebuilds every figure and every hash is in the provenance table.
