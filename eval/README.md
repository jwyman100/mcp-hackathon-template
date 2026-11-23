# Evaluation: what is measured and what is not

## 1. Overview and objectives

Measure numerical correctness, scope handling, and real MCP transport behavior.
The prototype's contribution is domain-aware access to public fisheries data.
Do not interpret scripted tool success as measured agent reasoning or MCP lift.

## 2. Testing methodology

`tests` constructs invented CSV records and exercises the importer, query layer,
typed requests, MCP resource/prompt discovery, and actual stdio calls. Cases
include zeros versus missing/unknown measurements, duplicate keys/aliases,
invalid scope, orphan rows, read-only opening, and atomic import failure.

`run.py` reads the **original public ZIP**, independently filters CSV rows and
aggregates with `Decimal`, and compares those answers with a separate server
process reached through MCP stdio. It does not call application query helpers.
Counts/identifiers compare exactly; numeric values use relative tolerance
`1e-10` and absolute tolerance `1e-8`. Tool responses are checked against their
advertised JSON schemas.

Run from the repository root with the pinned public archive:

```powershell
uv run python eval\run.py --archive C:\path\to\public-survey.zip --output C:\path\to\new-scripted-results.json
```

`questions.json` contains 12 versioned, rubric-bearing questions adapted from
the internal suite's *methodology*, not its private database or expected answers.
`benchmark.json` records the fixed public scope, adaptation rules, protocol, and
the preserved pre-change baseline. Eight questions are development cases and
four are a prospective holdout. The holdout is frozen in-repository, not blind.
Each scripted request is repeated three times; this is 36 trials, not 36
independent questions. Select a split explicitly and write a separate result:

```powershell
uv run python eval\run.py --archive C:\path\to\public-survey.zip --split development --output C:\path\to\new-development.json
uv run python eval\run.py --archive C:\path\to\public-survey.zip --split holdout --output C:\path\to\new-holdout.json
uv run python eval\run.py --archive C:\path\to\public-survey.zip --split all --output C:\path\to\new-all.json
```

The report contains arguments, complete public results, errors, environment,
source/question hashes, the evaluated database and server-source hashes,
selected split, and measured durations. The default split is `all`. A new
`--output` path is required; an existing result is preserved unless the
operator explicitly supplies `--overwrite`. A failing check gives a nonzero exit
status.

The separate [`submission/demo.py`](../submission/demo.py) scripted MCP example
can also write a public-only evidence receipt with the exact request/result
sequence, public archive identity, SQLite hash, server source hashes and
limitations. Replay is deterministic for the same snapshot and code and fails
on a source, server or result mismatch:

```powershell
uv run python submission\demo.py --receipt submission\candidate-v7\demo-receipt.json
uv run python submission\demo.py --replay submission\candidate-v7\demo-receipt.json
```

The receipt is not a model trace, scientific review, or security audit. It
proves which local public inputs and scripted MCP outputs were captured; it
does not prove an inference is scientifically valid. See the provisional
[scientific schema contract](../submission/schema-contract.md) for the proposed
expert-review workflow; the contract example is not expert-approved.

The candidate change for suite v2 tightens MCP input schemas and descriptions
for this fixed five-year/two-species snapshot, makes the exactly-two-species
comparison requirement explicit, and exposes supported/unsupported analysis
scope in the data-dictionary resource. The pre-change `results\scripted.json`
is preserved as the direct-call baseline. These scripted checks validate the
contract and data path only; they cannot establish that an LLM selects the
improved schemas or writes better answers.

Recorded comparison: baseline **36/36** scripted trials; candidate **36/36**
(development **24/24**, prospective holdout **12/12**). The archived baseline
used the same call requests and public source hash. This shows no regression in
the deterministic MCP/data path, not an agent hill-climb win.

After the panel review, the revised server accepted exact returned species
labels, added interpretation caveats and a curated report-context tool. The
[post-review scripted result](results/candidate-v3-judged.json) is separate
from the historical baseline and v2 artifacts. Additional direct tests exercise
both published-label handoffs and the context cards. Candidate-v7 agent runs
are now available below; they do not establish matched before/after improvement.

The candidate-v7 source-review metadata clarification was rerun as
[candidate-v7-scripted.json](results/candidate-v7-scripted.json). It passed
36/36 deterministic trials against the independent public-CSV reference. This
is evidence for the scripted contract/data path only; it does not grade
scientific interpretation.

## 3. Performance metrics

See the [historical baseline](results/scripted.json) and
[post-review result](results/candidate-v3-judged.json). `passed / trial_count`
measures scripted conformance, including correctly rejected invalid requests.

**Historical agent evidence:** A supplied three-repeat set covers NOAA
A01/B01/C01 and eight of the frozen questions, including Q10. It does not cover
every question from Q01-Q09: Q04 and Q06 were omitted. Its 76 successful tool
payloads matched the pinned public-CSV reference, but model configuration and
evaluated database-file identity remain unconfirmed. See the
[public evidence appendix](../submission/public-evaluation-appendix.md) and
[repeat-trial review](published_reference/repeated-trials-review.md).

Three repeats per source-assisted NOAA case show persistent, distinct
weaknesses: A01 repeats the prompt's wrong page locator; B01 repeatedly
recovers from a species-label error but overstates the meaning of reduced
stratum counts; C01 retrieves correct totals but overstates unit/method
certainty. Q02 repeats the same name-resolution error; Q08 safely refuses
without calling MCP; Q10's answers overstate what an empty result proves about
survey effort. The complete payloads for all C01 calls are now available and
independently verified. Prior proposed B01/C01 trial-FAIL ratings remain
assistant review judgments, not MLflow grades or expert findings.

Answers vary in wording across the three trials per case while successful
payloads are stable. This is a small observed sample, not a statistical
repeatability estimate. The supplied records omit the model configuration and
database-file checksum. Do not claim a controlled stability comparison,
confidence interval, or overall pass rate.

**Not established:** overall agent accuracy, human time savings, agent baseline
improvement, Databricks performance, production concurrency, or robustness
against arbitrary attacks.

### Agent evaluation and hill climbing

For Databricks, the [importable notebook builder](../deploy/databricks/README.md)
packages the public snapshot and a bounded, model-selected MCP tool loop. It
records actual model/tool traces in MLflow and provides independent references
for manual analyst assessment, separate from scientific approval. Model calls
are disabled by default. Local
runner checks alone are not evidence of live model access or evaluation.
The appendix distinguishes the later shared model answers from scripted results.

Use the development split to identify one failure mode and change only one
factor (tool schema, description, or prompt) per iteration. Compare baseline and
candidate with the same model/version/settings, fixed public snapshot, and
development-question hash. Repeat agent trials and preserve tool traces and
answers; score question-level criteria rather than treating a passing tool call
as an agent success. Have a domain reviewer assess independent reference answers
and scientific claims. Run the frozen holdout only after selecting the candidate.
Because its questions are repository-visible, this holdout is confirmation, not
a blind generalization test.

The four holdout concepts cover scientific-name resolution, snapshot no-match,
current-data refusal, and unsupported population-trend inference. Do not tune on
their outputs. For a stronger later test, prepare a second independently
reviewed question set from the same public source and keep it outside tuning.

The [supplementary NOAA cases](published_reference/README.md) are separate from
the frozen suite and baseline. Historical A01/B01/C01 are source-assisted; C01
tests reconciliation limits, not full representative-haul reproduction. The
original full comparison remains
[unresolved](published_reference/benchmark-c-feasibility.md).

**Candidate-v7 agent evidence:** The sanitized
[run manifest](results/candidate-v7-agent-evaluation.json) covers all 12
repository-visible questions plus A02, D01 and C01, with three repeats each
(45 total trials). All completed; 82 of 84 tool calls succeeded, with two
malformed Q06 search calls recovering. Requested numerical tool payloads were
consistent with the packaged independent references in the cases reviewed.
Final answers still show interpretation errors: unsupported causation in D01,
confusion of absent catch rows with measured zero in Q10:2, and an incorrect
lowest-weight statement in Q12:3. A02 and D01 are now actual candidate-v7 runs;
D01 demonstrates selection of a curated context card, not live report
discovery. Later informal subject-matter input on one NOAA-D01:2 excerpt
highlighted the need to examine where sampling occurred. It did not resolve
the claim or review the full answer; the [manifest](results/candidate-v7-agent-evaluation.json)
records its scope and limits. All trial reviews remain `UNVERIFIED`; there is
no expert scientific approval or matched before/after model comparison.

**Hardened runtime:** The separate
[scripted run](results/candidate-v7-hardened-scripted.json) passed 36/36
checks against the independently calculated public-CSV reference using
FastMCP 3.4.11. It exercised the hardened runtime with direct MCP calls, not
the model-selected agent. The historical 45-trial agent evidence used
FastMCP 2.14.7 and does not evaluate the upgraded runtime. A separate
[current-runtime agent run](results/hardened-agent-evaluation.json) has since
completed 45 MCP trials, with 80 recorded calls and no reported tool errors.
In six partially reviewed answers, the AI linked lower catches to reduced
sampling, relevant context that the catch totals alone cannot quantify. The
other 37 trials were not fully reviewed. This is not an overall accuracy
score; scientific review remains `UNVERIFIED`. The manifest preserves the
original review findings.

Score each trial on tool/argument correctness, numerical correctness,
provenance, required caveats, and appropriate refusal/clarification. The
checked-in candidate-v7 manifest summarizes reviewed case observations; the
raw model traces remain separate and contain workspace-specific metadata that
must be reviewed before external sharing. Keep `UNVERIFIED` unless an
independent domain expert has reviewed the relevant full trial and its
scientific claims; a consultation on one excerpt does not suffice. GSA requires
evaluation setup and results; its public page specifies no numerical pass
threshold.

The upstream template recommends a Phoenix/LangChain/LLM-judge harness.
This project instead uses a bounded model-selected MCP loop, MLflow traces,
independent CSV references and explicit manual dimensions. This is a documented
implementation choice, not a claim that an automated judge or Phoenix experiment
was run.

The notebook now offers a separate `no_tools` arm: the same model, questions,
options and shared dictionary, but no tools or numerical-data access. This
measures access plus tooling, **not** MCP against an equally informed interface.
A comparison with direct SQL or file access would need a separate experiment;
no generic SQL interface belongs in the submission tools. The completed
comparison supplied the requested snapshot result in 24/24 MCP trials and
0/24 no-tool trials for eight questions repeated three times. This is result
presence, not an overall accuracy score; the no-tool arm lacked the underlying
records and had different access instructions.

### Answer assessment, separate from scientific approval

Use `review_answers.py` on downloaded **same-run** `answers.json` and
`configuration.json`. Preserve these files unchanged. Run locally:

```powershell
uv run python eval\review_answers.py template --answers C:\evidence\answers.json --configuration C:\evidence\configuration.json --output C:\evidence\analyst-review.json
```

The new JSON starts with every dimension `UNVERIFIED`. Edit only verdicts and
evidence notes, consulting `independent_reference.json`, the question's rubric,
the original answer and tool traces. Do not grade the tool output alone.

| Dimension | What to check |
| --- | --- |
| `numerical_fidelity` | All requested available numbers are supplied correctly, with the requested year/species/stratum scope. Extra factual claims count too. |
| `missing_vs_zero` | Missing records/measurements remain unknown, never measured zero. No selected station record does not prove no survey effort. |
| `ranking` | Every lowest/highest/comparison claim agrees with the actual series, including unasked supporting claims. |
| `provenance` | The answer retains source identity, snapshot dates and unspecified weight units; report counts are not silently substituted for snapshot counts. |
| `causal_claims` | Survey disruption is context, not proof that it caused lower catch. Counts alone do not establish effort, spatial representativeness or abundance. |
| `scope` | The answer respects the fixed snapshot and distinguishes answer, clarification and supported refusal. |
| `tool_use` | The agent selected suitable tools/arguments and used their results. An appropriate unsupported-task refusal need not call a tool. |

Use `PASS`, `FAIL`, `UNVERIFIED`, or `NOT_APPLICABLE`. Every verdict except
`UNVERIFIED` requires a note pointing to the answer/trace/reference evidence.
`NOT_APPLICABLE` means the dimension is genuinely irrelevant, not merely
unchecked. For example, a name-only request with no ranking claim may have
ranking marked not applicable. Unrequested causal/ranking claims still count.
For the no-tool arm, tool use is not applicable. A refusal to provide an
available requested number fails numerical fidelity even if honestly worded;
an unsupported task can correctly be refused in either arm.

```powershell
uv run python eval\review_answers.py summarize --answers C:\evidence\answers.json --configuration C:\evidence\configuration.json --reviews C:\evidence\analyst-review.json --output C:\evidence\analyst-summary.json
```

The summary binds reviews to file hashes, rejects duplicate/missing trial IDs,
reports dimension counts and all-exported-repeat consistency, and never
overwrites existing output files. A demonstrated error makes the trial FAIL;
unreviewed dimensions prevent PASS. All-not-applicable is not a pass.
The denominator is the supplied completed trials, not all planned attempts:
report failures/omissions separately and never pool different arms or builds.
Three repeats do not establish a population accuracy rate.

These are **analyst assessments**, including any AI-assisted assessment, not
independent scientific validation. The tool always leaves scientific review
UNVERIFIED. Specialist approval requires a separately documented review of the
relevant full answer; the earlier one-excerpt feedback remains limited input.
Do not publish raw workspace exports or reviewer identities with the summary.

## 4. Security considerations

The runtime has no network/data connector and opens SQLite read-only.
Preparation downloads only one operator-owned HTTPS URL, rejects redirects,
bounds input sizes, and verifies a pinned hash. CSV members are streamed without
extracting paths. Tool values are bound SQL parameters. Internal data and
credentials are absent from the design; provenance identifies public versus
synthetic fixtures.

HTTP lacks built-in caller authentication and is loopback-only by default.
Platform-provided ports and non-loopback binds fail closed unless
`MCP_TRUSTED_HTTP_INGRESS=true` is explicitly supplied; that setting does not
authenticate callers. Private cloud use requires a separately approved and
verified authenticated ingress. The repository contains public results only,
but model/MLflow traces may contain full prompts and tool results; protect them
with the workspace's access and retention controls and review before sharing.
This is not a security audit; do not treat parser checks, MCP hints, or a small
test set as a complete authorization or prompt-injection defense.

## 5. Lessons learned and recommendations

- The published catch file includes combined species labels. Historical B01 showed that
  returning such a label does not guarantee the analysis tool will accept it:
  the agent recovered by using the separate common-name field. The revised
  interface accepts an exact returned label; direct checks cover the fix.
- Some out-of-scope taxa have duplicate catch keys; the focused importer fails
  on duplicate selected keys rather than guessing deduplication semantics.
- Station comments contain non-UTF-8 bytes. The reviewed archive uses explicit
  Latin-1 decoding; comments/locations are not imported.
- Missing measurements differ from missing records and measured zero.
- Unit and sampling limitations must survive into the final agent answer.
  Tool-returned caveats alone do not prove that behavior.
- A01 also exposed an evaluator-authored page citation error. Evaluation
  artifacts need scrutiny alongside the server and model.
- A controlled post-change agent evaluation could test whether the repaired
  handoff and narrower interpretation guidance change model behavior. Neither
  agent improvement nor repeated-run stability improvement is established.
