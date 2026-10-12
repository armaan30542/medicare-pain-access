# Medicare access to new interventional pain procedures

Two studies, one pipeline, built entirely on **free, public, no-login data**:

| Study | Question | Procedure codes | Data years |
|---|---|---|---|
| **PNS** | Who delivers peripheral nerve stimulation, and how concentrated is it? | 64555 vs 63650, 63685, 64590, 62323, 64483, 64635 | 2015-2024 |
| **BVNA** | Where is basivertebral nerve ablation delivered, by whom, and who has no access? | 64628, 64629 (C9752 before 2022) | 2022-2024 |

## One command

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

That downloads every raw CMS file it needs, verifies the procedure codes
against the files' own descriptions, and rebuilds **every number, table, figure
and slide** for both studies. Nothing is typed by hand: every statistic in the
documents and decks is read from computed artifacts, and anything missing
renders as a red `[MISSING]` instead of a guess.

**Requirements:** Python 3.12+ (the pinned numpy and scipy require it).

**First run downloads about 31 GB.** The CMS provider-level files are about
3 GB per year and must be streamed in full; the pipeline keeps only the rows
for the study codes (a few MB). Expect hours on a fast connection. Every later
run reads the local cache and finishes in seconds. Nothing is ever downloaded
twice.

To set the contact address NCBI asks API callers to provide (only used if a
literature cache is deleted and must be refetched):

```bash
export NCBI_EMAIL="you@example.com"
```

If a download fails, `run.py` prints the exact URL and target filename to fetch
by hand, then exits without touching partial data.

## What gets built

| Output | What it is |
|---|---|
| `RESULTS.md` | Every PNS number, formatted to read aloud |
| `figures/` | PNS figures 1-6, PNG (300 dpi) and SVG |
| `deck.html`, `deck.pptx` | PNS presentation (not committed; rebuilt each run) |
| `bvna/figures/` | BVNA figures 1-5 |
| `bvna/FIRST_DELIVERABLE_NOTE.md` | BVNA growth, concentration and surprises |
| `bvna/deck_bvna.pptx` | BVNA presentation (not committed; rebuilt each run) |
| `audit/results.json`, `bvna/audit/results.json` | Every computed statistic, machine-readable |
| `DATA_PROVENANCE.md`, `*/audit/provenance.json` | URL, timestamp, row count and SHA256 for every download |

`python3 run_bvna.py` rebuilds only the BVNA study (after one full run).

## Data sources

All discovered at runtime from the CMS catalog at <https://data.cms.gov/data.json>.

- **CMS Medicare Physician & Other Practitioners**, by Provider and Service and by
  Geography and Service.
- **CMS Medicare Geographic Variation** by National, State & County: fee-for-service
  denominators, dual-eligible share, Medicare Advantage share.
- **US Census SAIPE**: state median household income. (The ACS API now requires a
  key for every request; SAIPE needs none.)
- **NCBI PubMed E-utilities**: literature counts. Results are cached in
  `audit/novelty_raw.json` and `bvna/audit/novelty_raw.json` and committed, because
  PubMed grows daily and re-querying would silently change the counts.

## Method notes that matter

**The 11-beneficiary floor.** The provider-level file drops every provider-code
row with 10 or fewer beneficiaries. The test suite confirms the floor
empirically: the minimum on any surviving row is exactly 11.

**The geography file sees what the provider file cannot.** It totals all
providers, including those below the floor, so it is the source for growth
rates and state-level counts. Every concentration result is reported alongside
the share of national volume the provider file can actually see.

**Surgery centres double-count procedures.** When a case is done in an ambulatory
surgery centre, the physician and the centre both bill it. Clinician-only
analyses exclude facility provider types.

## A correction to the PNS study

The PNS concentration figures were computed only from the provider-level file,
before the geography-file comparison above existed. That comparison later showed
the provider file captures well under half of national PNS volume, and that a
large share of the "providers" it lists are surgery centres. As a result, the
PNS provider count and the top-10% share in `RESULTS.md` and the PNS decks are
**overstated**. The BVNA study uses the corrected method, and its deck opens with
this correction (slide 3). The PNS write-up has not yet been regenerated with
the corrected method.

## Tests

```bash
python3 -m pytest -q
```

Covers the Gini maths, HCPCS descriptor verification, the suppression floor,
rates and panels, figure dimensions, both decks' structure and plain-language
contract, and a guard that fails if the CMS API ever ignores the HCPCS filter.
Data-dependent tests skip cleanly until `run.py` has been run once.

## Layout

```
run.py                one command: both studies, end to end
run_bvna.py           BVNA only
src/                  PNS pipeline: download, clean, analysis, figures, report, decks
src/bvna/             BVNA pipeline: fetch, analyze, figures, literature, deck
tests/                pytest suite
CITATION_AUDIT.md     every cited claim checked against PubMed
NOVELTY_CHECK.md      adversarial search for prior work (PNS)
```
