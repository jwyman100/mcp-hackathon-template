# Repeated trial evidence review

These are historical trials of the earlier server. The revised server accepts
exact returned species labels and adds caveats plus curated NOAA context.
The findings below describe the original trials, not the later
[candidate-v7](../results/candidate-v7-agent-evaluation.json) or
[hardened-runtime](../results/hardened-agent-evaluation.json) agent runs.

## Trial set and verification

The supplied folder contains 33 completed trial records: three each for NOAA
A01, B01 and C01; and three each for Q01, Q02, Q03, Q05, Q07, Q08, Q09 and
Q10. This is the eight-question development subset, including Q10, not Q01-Q09 as a
contiguous range. Q04 and Q06 were not included; neither were holdout Q11/Q12.
Raw trial JSON is not copied into this repository.

Each record reports `execution_status = completed` and
`scientific_review = UNVERIFIED`. The received files do not include a companion
`configuration.json`, MLflow run ID, or notebook bundle manifest. The model
endpoint/options, exact bundle, and byte identity of the evaluated SQLite
database therefore remain unverified. Tool responses report the expected NOAA
archive SHA-256; that metadata claim is not a hash of the database file.

Using `eval/run.py`'s independent raw-CSV `Reference` implementation against
the locally pinned archive (SHA-256
`f273e8bbb56dcf8360e7df065b94f8dabaa3f2ea89111807951dea77c3eb65fd`), all 76
successful tool-result payloads were independently checked for source hash,
scope, coverage, species identity, annual catch values and matched years where
applicable. All matched the reference. This verifies the returned payloads for
these requests; it does not verify the full model answer or evaluated database
identity.

Across 82 total tool calls, six calls returned a species-name error: one in
each Q02 and B01 repeat. Each was followed by a successful retry using the
common name. Q08 made no MCP tool calls in any of its three runs; those answers
refused a false two-species comparison based on the provided context but did
not exercise the comparison tool's rejection path. The scripted MCP benchmark
tests that server behavior separately.

## Per-case run summary

| Case | Runs | Successful payloads | Recovered tool errors |
|---|---:|---:|---:|
| NOAA-A01 | 3 | 3 | 0 |
| NOAA-B01 | 3 | 9 | 3 |
| NOAA-C01 preflight | 3 | 18 | 0 |
| Q01 | 3 | 7 | 0 |
| Q02 | 3 | 6 | 3 |
| Q03 | 3 | 9 | 0 |
| Q05 | 3 | 3 | 0 |
| Q07 | 3 | 9 | 0 |
| Q08 | 3 | 0 | 0 |
| Q09 | 3 | 3 | 0 |
| Q10 | 3 | 9 | 0 |
| **Total** | **33** | **76** | **6** |

The 33 answers produced two or three distinct text variants per case. The
successful tool payloads were stable within each case. Q01 varied by one
additional species-search call in one repeat; Q10 added explicit year bounds
to one repeat. These three-run observations do not support a confidence
interval, statistical significance, a general model-stability claim, or a
pass rate.

## Findings by case

- **A01:** All three runs retrieve the same correct 2025 count and preserve the
  aggregate-versus-representative-haul caveat. All three repeat the question's
  incorrect “PDF p. 1” locator. The Overview is on physical PDF page 3. The
  report is linked in these new answers; the page error originates in the
  benchmark question and is an evaluator error, not an incorrect count.
- **B01:** Each run repeats the combined published-label rejection, then
  recovers using the common name. The tool outputs match the reference, and
  the answers report the correct catch and coverage values. All three answers
  nevertheless infer geographic coverage from the number of sampled strata
  (including “84% of the normal stratum footprint”) and overstate how much
  coverage or daytime sampling explains the catch differences. Thirteen of 82
  sampled strata is a count, not a measured percentage of area. NOAA's warning
  that further evaluation is needed does not quantify the separate effects.
- **C01 preflight:** All 18 successful payloads, including complete comparison
  results, match the reference; the prior pasted trace's collapsed catch
  fields are not an issue in these JSON files. All answers appropriately
  decline to reproduce the representative-haul table, but continue to make
  unsupported categorical claims about what units are excluded and whether
  expansion methods differ. Unknown units do not prove the values are not
  pounds or kilograms; unknown field correspondence does not prove a
  methodology difference.
- **Q01:** All requested catch and coverage payloads match. One answer performs
  an additional search; the other two do not. This does not change the results.
- **Q02:** All three runs hit the same species-name error and recover on retry.
  Returned measurements and coverage match. This repeats the same tool-guidance
  friction observed in B01.
- **Q03:** All three runs return correct inclusive stratum/year results,
  retaining leading-zero stratum codes. Answers differ in formatting and
  whether they separately tabulate coverage.
- **Q05:** All three searches return the expected snapshot species identity and
  scope caveat.
- **Q07:** All three comparison payloads match; answers identify all five
  years as complete for selected catch measurements. This is not matched
  survey effort or proof of abundance comparability.
- **Q08:** All three answers correctly identify Atlantic cod and *Gadus
  morhua* as aliases and refuse the requested false comparison. They make no
  tool call, so the model result alone does not demonstrate server-side
  duplicate-species rejection.
- **Q09:** All three coverage payloads match and answers distinguish station
  records from valid-haul counts.
- **Q10:** All three payloads correctly show no selected station/catch records
  for stratum 99999. The answers go further and say there were “no tows” or a
  “complete absence of survey effort.” Those claims are not established by an
  empty snapshot result; the code may be unused, out of scope, or unsampled.
  Some answer text acknowledges this ambiguity, making the stronger claim
  internally inconsistent.

## Scoring and release boundary

This review reports tool-payload agreement and recurring answer limitations;
it does not assign an overall PASS/FAIL rate or change `scientific_review`.
B01/C01's earlier proposed trial-FAIL recommendations remain assistant
evidence judgments, not independent scientific review or MLflow grades.
Independent scientific review was not performed. Keep the original runs and
the distinction between correct data retrieval and unsupported interpretation
visible in the submission.
