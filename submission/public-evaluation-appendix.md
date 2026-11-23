# Public-data evaluation evidence

**Version boundary:** The agent trials below used the earlier four-tool
server. Since those trials, the server accepts exact returned species labels,
adds explicit interpretation caveats, and exposes manually curated 2023/2025
NOAA context cards. At the time of this earlier review, no post-change model
trials or independent scientific review had been performed. A separate later
[candidate-v7 run](../eval/results/candidate-v7-agent-evaluation.json) has
since been evaluated. A separate later [hardened-runtime agent run](../eval/results/hardened-agent-evaluation.json)
is also available. The original answers, errors and `UNVERIFIED` statuses
remain unchanged.

## Scope and method

One shared development run produced answers for eight questions. The reported
numerical outputs for Q01, Q02, Q03, Q07, Q09 and Q10 were compared with an
independent raw-CSV calculation, separate from the server's SQLite query path.
No numerical discrepancies were found in the fields shown below. This is a
numerical consistency check, not an overall agent pass or scientific validation.

Public source: https://storage.googleapis.com/nmfs_odp_nefsc/PARR/PEMAD/ESB/22561/22561_NEFSCSpringFisheriesIndependentBottomTrawlData.zip

Metadata: https://www.fisheries.noaa.gov/inport/item/22561

Checked archive SHA-256: `f273e8bbb56dcf8360e7df065b94f8dabaa3f2ea89111807951dea77c3eb65fd`

The reference calculation selects spring cruises in metadata years 2021-2025,
purpose code 10 and cruise status 10; selects stations in those cruises with
station status 10; and selects Atlantic cod (`073`) or haddock (`074`) catch
records with catch status 10, matching selected stations by ID. The default is
all published station strata. Q03 restricts station strata to `01130`-`01150`,
inclusive; Q10 selects `99999`. No valid-haul or gear-condition filtering,
effort standardization, stratum-area weighting, or vessel calibration is applied.

The `Reference` implementation in `eval/run.py` independently reads the
original CSVs and sums measurements using `Decimal`; it does not use the
server's SQLite query helpers. Counts are exact; floating comparisons use
relative tolerance `1e-10` and absolute tolerance `1e-8`. The answers compared
below were supplied as text; the development run's full traces have not been
reviewed. A matching archive checksum alone does not establish byte-for-byte
identity of the snapshot actually used in that run with the intended snapshot,
or prove that it was built from this archive.

## Q01 and Q09: cod and annual coverage

Each entry is **reported / recalculated**. Weight is in source units, which the
linked public metadata does not specify. Q01 also reported no unknown cod
weight or number measurements; the recalculation found zero for both each year.
Q09 reported the same three coverage columns.

| Year | Expanded weight | Expanded number | Cod catch records | Station records | Cruises | Sampled strata |
|---|---|---|---|---|---|---|
| 2021 | 430.626 / 430.626 | 547 / 547 | 65 / 65 | 332 / 332 | 1 / 1 | 71 / 71 |
| 2022 | 609.780 / 609.780 | 584 / 584 | 65 / 65 | 378 / 378 | 1 / 1 | 82 / 82 |
| 2023 | 416.396 / 416.396 | 284 / 284 | 24 / 24 | 77 / 77 | 1 / 1 | 13 / 13 |
| 2024 | 486.661 / 486.661 | 323 / 323 | 56 / 56 | 388 / 388 | 1 / 1 | 82 / 82 |
| 2025 | 404.150 / 404.150 | 367 / 367 | 54 / 54 | 395 / 395 | 1 / 1 | 82 / 82 |

## Q02: haddock catch and missing measurements

Each entry is **reported / recalculated**.

| Year | Expanded weight | Expanded number | Unknown weights | Unknown numbers |
|---|---|---|---|---|
| 2021 | 5146.850 / 5146.850 | 11324 / 11324 | 0 / 0 | 0 / 0 |
| 2022 | 2859.398 / 2859.398 | 10682 / 10682 | 0 / 0 | 0 / 0 |
| 2023 | 3900.607 / 3900.607 | 7779 / 7779 | 0 / 0 | 0 / 0 |
| 2024 | 2132.807 / 2132.807 | 3425 / 3425 | 0 / 0 | 0 / 0 |
| 2025 | 2231.485 / 2231.485 | 3646 / 3646 | 0 / 0 | 0 / 0 |

## Q03: cod in strata 01130-01150

Each entry is **reported / recalculated**. `null` means no selected cod catch
records, not an observed zero catch.

| Year | Expanded weight | Expanded number | Cod catch records |
|---|---|---|---|
| 2021 | 0.001 / 0.001 | 1 / 1 | 1 / 1 |
| 2022 | 1.060 / 1.060 | 1 / 1 | 1 / 1 |
| 2023 | 1.499 / 1.499 | 1 / 1 | 1 / 1 |
| 2024 | 0.226 / 0.226 | 1 / 1 | 1 / 1 |
| 2025 | null / null | null / null | 0 / 0 |

## Q07: shared-scope comparison

The reported cod values and station counts match the Q01/Q09 table; the
reported haddock values match Q02. The reported and recalculated complete
measurement years for both species are **2021, 2022, 2023, 2024 and 2025**.
These are complete measurements in the selected catch records, not matched
survey effort or abundance estimates.

## Q10: no records in stratum 99999

For **each** year 2021-2025, the reported / recalculated values are: station
records **0 / 0**, cod catch records **0 / 0**, expanded weight **null / null**
and expanded number **null / null**. No records do not establish measured zero
catch or biological absence.

## Supplementary NOAA cases: agreement and discrepancies

These are separate source-assisted questions, not extra independent questions
in the frozen 12-question suite. Report context is supplied in their prompts;
they do not test autonomous report retrieval. The attached trial folder contains
three repeats per NOAA case and three repeats each for Q01/Q02/Q03/Q05/Q07/Q08/
Q09/Q10. That is 33 completed trials, not a contiguous Q01-Q09 run: Q04 and Q06
were not included. Individual trial review fields remain `UNVERIFIED`;
independent scientific approval was not performed.

The trial files contain 82 calls: 76 successful tool payloads and six
species-name errors, each recovered by a retry. All 76 successful payloads
were independently compared with the pinned raw-CSV reference, including the
previously collapsed C01 catch results; all matched. This establishes
request-level data agreement, not a full answer PASS or evaluated-database
identity. Q08 made no calls in any repeat, so its refusal did not exercise the
MCP server's duplicate-species rejection.

| Case | Runs | Successful payloads / errors | Observed outcome |
|---|---:|---:|---|
| A01 | 3 | 3 / 0 | All counts and scope caveats correct; all repeat the benchmark's wrong PDF page 1 locator (Overview is physical page 3). The new answers link the report. |
| B01 | 3 | 9 / 3 | Correct data and recovery every run; all overstate what 13 of 82 strata establishes about geographic area and/or why catch changed. |
| C01 preflight | 3 | 18 / 0 | Full payloads match; all decline full-haul reconciliation, but continue to overstate unit or expansion-method certainty. |
| Q01/Q02/Q03/Q05/Q07/Q08/Q09/Q10 | 24 | 46 / 3 | All successful payloads match; recurring Q02 name errors, no-call Q08 refusal and Q10 no-records overclaim are noted below. |

Text varied in every case (two or three distinct answer variants),
while successful data payloads were stable. The files do not establish a
statistical stability estimate or pass rate.

### Discrepancies and their owners

- **Evaluator, A01:** the question cited PDF page 1, but the report Overview
  is on physical PDF page 3. All three new answers repeat the wrong locator
  while providing the report link. Counts and aggregate reasoning are correct.
  The page error originates in the benchmark prompt, not the model.
- **Tool interface, B01:** search returned a combined published species label
  that the catch tool rejected. The error instructed the agent to use an exact
  returned name. Retrying with the separate common name succeeded. The current
  summary description at the time specified common/scientific names, but the
  returned fields and error guidance still created avoidable friction.
- **Interpretation, B01:** all three answers convert the count of sampled
  strata into a statement about missing geographic area/footprint; some also
  treat reduced coverage as the expected or dominant explanation for catch
  differences. Neither stratum counts nor the supplied report quantify the
  area or cause of the catch changes. The report's 70 sampled trawl stations
  and the snapshot's 77 station records are different measures; their
  difference is not proof of seven invalid hauls.
- **Interpretation, C01:** unspecified units do not exclude pounds or
  kilograms. Unknown field correspondence does not establish different
  expansion methods. The tools lack individual haul rows, but can return
  annual aggregates for a supplied stratum range.
- **Interpretation, Q10:** all three answers report no selected records for
  stratum 99999, but assert there were “no tows” or a “complete absence of
  survey effort.” An empty selected snapshot does not establish whether the
  code is unused, out of scope or unsampled. Some prose acknowledges that
  ambiguity, making the stronger claim internally inconsistent.
- **Tool use, Q08:** all three answers correctly identify Atlantic cod and
  *Gadus morhua* as the same species and refuse a false comparison, but do so
  without calling the tool. The scripted MCP suite separately exercises its
  duplicate-species error.
- **Tool interface, Q02/B01:** in all six runs, search returns a combined
  published label that the then-current summary tool rejected. The agent recovered with the
  common name each time; repeated recovery does not remove the interface
  friction.
- **Full report reconciliation:** 370 representative-station entries versus
  364 catch-table rows, unit correspondence and rounded-value differences
  remain unresolved. C01 preflight does not reproduce those representative-haul
  totals and does not establish equivalence between sources.

The three-run results demonstrate **observed textual variation**, not
repeat-run reliability: each case produced two or three distinct answer texts,
but the underlying successful tool payloads were stable. B01's geographic
overreach and C01's unsupported unit/method claims recurred. No statistical
stability estimate, confidence interval, significance test, model-to-model
comparison or overall answer-quality pass rate is claimed. The exact model
options and bundle/snapshot file identity cannot be verified because the
companion configuration artifacts were not included.

B01/C01's earlier proposed trial-FAIL recommendations remain assistant
evidence judgments, not independent scientific review or MLflow grades. No
trial review status was changed.

See the [repeat-run evidence review](../eval/published_reference/repeated-trials-review.md)
for per-question coverage, independent payload checks and limits. Retain the
original trial answers and distinguish these findings from the earlier
single-trial reviews.

Review records: `eval/published_reference/a01-review.json`,
`eval/published_reference/b01-review.md`,
`eval/published_reference/c01-review.md`, and
`eval/published_reference/repeated-trials-review.md`.

NOAA 2025 report (A01/C01): https://repository.library.noaa.gov/view/noaa/72382

NOAA 2023 summary (B01): https://www.fisheries.noaa.gov/new-england-mid-atlantic/ecosystems/2023-northeast-spring-bottom-trawl-survey-summary

## Remaining limitations

- Q05 describes search within the selected snapshot, not the full species
  catalog. Q08's model answers did not invoke the MCP server, although the
  separate scripted test covers its same-species rejection.
- The source hash in tool provenance matches the pinned archive, and successful
  payloads match its independent calculations. The exact SQLite database file,
  notebook bundle and model options used in the run remain unconfirmed because
  the companion configuration artifacts were not supplied.
- This earlier trial set has not received a full independent scientific
  review. Later targeted feedback concerned only one excerpt from a separate
  candidate-v7 trial; it did not approve these answers. The overall evaluation
  remains **UNVERIFIED**. These checks do not establish population abundance,
  stock status, equivalence to another source, or generalization beyond the
  checked questions.
- In the selected snapshot, 2023 had fewer station records and sampled strata
  than the other years. Station records are not validated tows or standardized
  effort, and expanded catch totals are not abundance or biomass indices.
