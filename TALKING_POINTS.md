# TALKING POINTS

Every number is tagged **MY RESULT** (computed by this repo) or **CITED**
(published, PMID given inline, verified in `CITATION_AUDIT.md`).
Data accessed 2026-08-25. Most recent data year 2024.

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
out that in 2024, **268 providers in the entire Medicare
fee-for-service program billed PNS** - against **7,346** who billed a lumbar
epidural."*

---

## FIGURE 1 - PNS growth

**What it shows.** PNS volume per 100,000 fee-for-service beneficiaries against
SCS trials and lumbar epidurals, 2017-2024.

**Say these numbers:**
- PNS reached **41 services per 100,000 FFS beneficiaries in 2024**, from **2.7 at its 2018 trough** — a **16-fold** rise. *(MY RESULT)*
- Lumbar epidural volume **fell 13%** from 2019 to 2024, 2537 to 2213 per 100,000. *(MY RESULT)*
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
same universe of interventional pain providers, 2024.

**Say these numbers:**
- **The top 10% of providers deliver 100% of all PNS volume, versus 49% of all epidural volume.** *(MY RESULT)*
- **Gini 0.98 for PNS [0.982-0.986] versus 0.68 for epidurals [0.676-0.690]**, 2,000-resample bootstrap, non-overlapping. *(MY RESULT)*
- **268 PNS providers versus 7,346 epidural providers — a 27-fold difference.** *(MY RESULT)*

**The limitation, phrased for a physician:** *"CMS deletes any provider-procedure
row with 10 or fewer beneficiaries. So every low-volume
PNS provider is invisible to me — **47% of the PNS providers I
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
- **14 states had zero PNS providers in 2024.** *(MY RESULT)*
- **24% of FFS beneficiaries — 6,722,156 people — live in a state with fewer than 3 PNS providers.** *(MY RESULT)*
- Deserts peaked at **42 states** and have fallen every year since. *(MY RESULT)*

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
- General pain provider density: **IRR 1.108** in Model A, **1.089** in Model B — it barely moves and stays significant. *(MY RESULT)*
- Neuromodulation-capable density: **IRR 1.129**, p = 0.005. *(MY RESULT)*
- **Pseudo R² is only 0.022** — over 97% of the variation in state PNS volume is unexplained by provider supply of either kind. *(MY RESULT)*

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
- Income: **Pearson r = 0.013, p = 0.929** — a **null result**. *(MY RESULT)*
- Dual-eligible: **Spearman ρ = -0.252, p = 0.074** — right direction, not significant. *(MY RESULT)*
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
- **168 SCS papers versus 44 PNS papers — about 4 to 1.** *(MY RESULT, reproducible query)*
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

2. **The 10-beneficiary suppression floor.** CMS
   excludes every provider-code row with 10 or fewer
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
