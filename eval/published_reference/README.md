# NOAA published-reference benchmarks

These are supplementary, separately selected single-question scenarios. Three
repeats each of historical A01/B01/C01 are present in the supplied trial files.
The later candidate-v7 run includes three repeats each of A02, D01 and C01.
None modifies the frozen 12-question suite or its scripted baseline.

## A01: station records versus representative hauls

The question gives the model a citable fact from NOAA's 2025 survey report and
requires it to retrieve the corresponding year-specific count from the public
MCP server. It evaluates tool use, arithmetic, provenance, and the distinction
between a station-record count and representative/valid hauls. It does **not**
test report discovery: the public report and its relevant counts are stated in
the question. The server then had no report-context tool; the current server's
curated cards are not live report retrieval.

The independently checked NOAA report Overview (physical PDF page 3) says 370
representative and 25 non-representative stations. The downloaded PDF matched
NOAA Repository's published SHA-512. The public source archive is pinned by
SHA-256 in `data/README.md`. The local MCP server returned 395 station records
for 2025, one cruise, and 82 sampled strata; `eval/run.py`'s independent raw
CSV reference agreed.

The totals match arithmetically, but do not claim record-by-record identity.
The MCP's station records have not been independently reconciled against the
report's representative/non-representative classification. The coverage tool
does not filter by haul/gear validity. The source report also has inconsistent
planned-station wording later in the Results section; this case avoids
completion percentages.

**Citation erratum:** the original A01 question incorrectly says PDF page 1.
Its text remains unchanged to preserve the completed trial's question identity.
Use physical PDF page 3 when citing the Overview. The figures are unchanged.
This is an evaluator-authored citation error, not an agent-generated error.

The [A01 trace review](a01-review.json) describes the earlier supplied answer.
In the newer three-repeat set, each answer links the report and repeats the
prompt's incorrect page-1 locator; the Overview is on physical PDF page 3.
Counts, the aggregate distinction and coverage tool payloads are consistent.
This remains source-assisted evidence, not independent report discovery.
Provenance does not establish the evaluated database's byte identity.

## B01: interpret the 2023 disruption

[B01](benchmark-b.json) supplies NOAA's documented operational context and asks
the agent to retrieve cod catch and station/stratum coverage for 2022-2024.
It tests interpretation across different sampling conditions, not web retrieval.
The historical source-assisted design follows A01 and did not test a
report-context tool.
Independent numerical references are computed from the pinned CSV archive.

The question distinguishes 70 sampled trawl stations in NOAA's summary from 77
snapshot station records. Neither their difference nor missing station data
licenses inventing seven invalid hauls. The reference also requires geographic
and daytime-sampling caveats, source attribution, and unspecified weight units.

An [answer-and-trace review](b01-review.md) reproduces the numbers and confirms
the requested tool results, but identifies unsupported scientific claims. The
agent recovered from an error when the catch tool rejected a combined species
label returned by search. No companion run configuration was supplied, independent scientific review
was not performed, and no MLflow review was changed.

## C01: representative-haul reconciliation preflight

[C01](benchmark-c.json) asks for the original representative-haul comparison,
but also requests the available 2025 all-snapshot cod/haddock totals and
coverage. It tests whether the agent retrieves those values and clearly
explains why the available tools cannot complete the requested comparison.
The question supplies the report's table scope and units, not its catch totals.
Evaluator-only references cover the all-snapshot values, not the unresolved
representative-haul comparison.

This is an explicitly limited **preflight**, not the selected full
reconciliation and not proof that the report's catch totals were reproduced.
No independent scientific review was performed. The [feasibility
findings](benchmark-c-feasibility.md) retain the unresolved table omissions,
weight units and numerical differences.

The [C01 answer-and-trace review](c01-review.md) describes the earlier
single-trial evidence. The newer repeated JSON trials contain all call payloads:
all 18 successful results across three repeats match the independent CSV
reference. Answers still overstate what is known about units and methodology.
The run configuration and evaluated database-file identity remain unverified.
No MLflow assessment was changed.

## A02 and D01: candidate-v7 follow-up

[A02](benchmark-a02.json) corrects the A01 prompt's locator to physical PDF
page 3 without changing the historical A01 question. [D01](benchmark-d.json)
asks the model to retrieve 2023 cod and survey coverage and use the new
`get_spring_report_context` card without placing the report facts in the
question. The card contains manually curated, cited facts for 2023 and 2025;
it does not fetch reports or demonstrate live source discovery. Both cases
were subsequently run three times in the
[candidate-v7 agent evaluation](../results/candidate-v7-agent-evaluation.json);
their scientific-review statuses remain `UNVERIFIED`. Later informal feedback
on one D01 excerpt did not approve the full answer.

The [repeated-trial review](repeated-trials-review.md) includes all supplied
cases, per-case call outcomes, independent payload checks,
and repeated answer-quality limitations. All `scientific_review` fields remain
`UNVERIFIED`; there is no overall agent pass rate or independent scientific
approval.

## Run A, B or C01 separately

Build the standard public-only Databricks notebook using the pinned NOAA ZIP,
then select `SPLIT = "published_reference"` for A01 or
`SPLIT = "published_context"` for B01, or `SPLIT = "published_c_preflight"`
for C01, with `REPEATS = 1`. The independent answer card is packaged for
manual review but is never passed to the agent. Run only after checking
endpoint permissions and being ready for model usage. The existing notebook
keeps model calls disabled by default.

Score `NOAA-A01:1`, `NOAA-B01:1` or `NOAA-C01:1` across facts, tool use,
provenance, caveats, and scope. Use `None` for unreviewed dimensions and
disclose that independent scientific review was not performed. An individual
trial can fail with some dimensions unreviewed; execution success or a single
trial result is not an overall scientific pass.

For B01 in the new notebook, run setup sections 1-3, retain your working endpoint
and model options in section 4, set `SPLIT = "published_context"`, and run section
5's no-model MCP check. When ready, enable model calls in section 4 and execute
that configuration cell again, then run section 6 once. Sections are headings,
not literal cell numbers. Section 6 replaces in-memory RESULTS and RUN_ID;
retain the earlier A01 MLflow run and exports rather than overwriting its review.
Export the new answer, trace and configuration before reviewing section 7.

For C01, import a freshly built notebook and run setup sections 1-3. In section
4, retain the endpoint and model options that worked for B01, set
`SPLIT = "published_c_preflight"` and `REPEATS = 1`, and keep model calls
disabled until section 5's MCP check succeeds. Then set
`ENABLE_MODEL_CALLS = True`, rerun the configuration cell, and run section 6
once. Export the answer, tool trace and configuration; this creates a separate
run and does not alter the earlier A01 or B01 runs.

For prospective A02 or D01, use the revised notebook and select respectively
`SPLIT = "published_reference_corrected"` or
`SPLIT = "published_report_context"`. Keep model calls disabled until the
no-model checks succeed. Save new runs separately; do not rewrite historical
answers or review fields.
