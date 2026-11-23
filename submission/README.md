# Submission guide and technical evidence

## Start here

- [Reference slides without a recording](release/repository/fisheries-deck.pptx) and
  [evaluation document](release/repository/fisheries-evaluation.docx).
- [Video slide template](release/repository/fisheries-video-deck.pptx) and
  [short recording steps](VIDEO.md).
- [Current AI evaluation](../eval/results/hardened-agent-evaluation.json):
  45 MCP trials completed, with 80 tool calls and no reported tool errors.
  The checked numerical outputs matched separate calculations from NOAA's
  original files. In six reviewed answers, the AI linked lower catches to
  reduced sampling, useful context that the catch totals cannot quantify.
  The partial AI-assisted review did not fully review 37 other trials.

The included command-line demo is scripted. The recording deck can be used
with a separate live demo; the finished recording and edited decks are separate
from the repository templates. The AI trials are separate from both examples.
None establishes scientific approval. The sections below provide technical detail.

## Narrative

**Problem:** Fisheries scientists face schema discovery, query-building and
repeated clarification before they can interpret survey data. Even a fluent
answer can mistake catch totals for abundance, unknown values for zeros, or
sparse coverage for a population trend.

**Solution:** Five read-only MCP tools expose a public snapshot with species
identity, consistent filters, coverage, measurement completeness, and
source/interpretation metadata, plus curated context for two NOAA reports.
Explicit schemas describe the fixed year/species
scope; the data-dictionary resource distinguishes supported from unsupported
analyses. The server does not require internal network access.

**Mission:** The NEFSC mission is to provide scientific information and tools
for productive, sustainable, healthy marine ecosystems and coastal communities.
This project illustrates a way to make scientific data easier to access and
interpret. Reduced researcher effort is an intended benefit, not a measured
outcome. This independent public-data prototype is not an official NOAA
assessment or endorsement.

## Official requirements and template alignment

Checked against the current
[GSA event instructions](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon?gsaredirect=hackathon)
(page updated November 4, 2026) and
[GSA-TTS/mcp-hackathon-template](https://github.com/GSA-TTS/mcp-hackathon-template)
at revision `f39249f1768309e3ef8b31742390a4f3a656b5f3`.

| Requirement | This submission |
| --- | --- |
| Dataset Access Server track; already-public government data | Read-only NOAA public spring-survey snapshot; no non-public data dependency |
| Complete documented GitHub repository | Root README, typed server, importer, tests, evaluation sources and preserved results; publication remains a release gate |
| Deck: problem, solution, technical decisions, functionality demo | Candidate-v7 presentation, including a public-data receipt and scientist-centered enterprise roadmap |
| Evaluation: methodology, performance, security, lessons/recommendations | Current evaluation document and public evidence appendix |
| Technical quality and own evaluation/reliability evidence | Independent CSV reference, real MCP calls, model answers and explicit failure analysis |
| Innovation, mission alignment, presentation | Domain-aware research access with coverage, identity and uncertainty retained |
| Sandbox prototypes will not be publicly deployed | Local/approved-sandbox use only; no public runtime endpoint |

The upstream FastMCP, Pydantic, thin-app, per-tool module, resource and prompt
patterns are retained. Offline SQLite deliberately replaces a live API client;
bounded results do not require pagination. The template's suggested
Phoenix/LangChain/LLM-judge path is replaced by a bounded model-selected MCP
loop, MLflow traces and analyst-review dimensions. We do not claim to have run
Phoenix or automated judging. The current no-tool baseline is a limited
data-access comparison, not a comparison with an equally informed interface.

The official templates were downloaded again for this candidate:

- Deck: `https://www.gsa.gov/system/files/MCP-hackathon-sample-deck.pptx`;
  SHA-256 `58c2c2356fd474c32c919a1ad7cff1183edf2619e2f7961397d1f9296af6e246`.
- Evaluation document: `https://www.gsa.gov/system/files/MCP-hackathon-sample-evaluation-document.docx`;
  SHA-256 `53104f7b8ee10f51f74977cde87b88e558aebd387b77f5ff2d91228dc9a8e62f`.

## Demo sequence

Run `uv run python submission\demo.py` from the repository root. With an
already-installed Windows virtual environment, use
`.\.venv\Scripts\python.exe submission\demo.py` if `uv` is not on PATH.
To create a receipt, add `--receipt C:\path\to\new-demo-receipt.json`; the
script refuses to overwrite an existing file. The scripted client calls the
real MCP server over stdio:

1. Search for cod and pass the exact returned label into a catch summary.
2. Show 2022 and 2023 expanded catch, station records and sampled strata.
3. Retrieve the curated, cited 2023 NOAA disruption card and distinguish its
   70 sampled trawl stations from the snapshot's 77 station records.
4. Hand the result to a scientist for interpretation; neither stratum counts
   nor the catch totals establish geographic area or a population trend.
5. Replay the saved evidence with
   `uv run python submission\demo.py --replay submission\release\demo-receipt.json`.
   Replay checks the SQLite database and source hashes and each tool result,
   including its public provenance; it does not re-download the public archive.
   A mismatch fails explicitly.

The demo's central distinction is **observation versus explanation**. Lower
catch and fewer station records are observed; NOAA's shortened-survey report
provides context, not proof of what caused the catch difference. End with a
specific handoff: which locations and sampling conditions are comparable,
and what analysis would support that comparison? This is presenter-written
guidance, not a newly observed agent answer or an expert-approved conclusion.

The receipt contains the exact question, scripted mode, requests/results,
public source identity, database/server hashes and interpretation limits. It
contains public data only. It is not a security audit or scientific approval.
This is a **scripted demonstration, not an agent-selected workflow**. The report
card is manually curated and does not search the web. If presenting an actual
model trace instead, use the historical run evidence and its limitations.

The original `candidate-v7` receipt is retained as historical evidence. It
does not replay against the later hardened server because its source hashes
differ. The `release` receipt was freshly generated and
replayed against the hardened server; it does not change the historical agent
run.

## Scientific schema collaboration

[`schema-contract.md`](schema-contract.md) gives one explicitly provisional
example of the definitions a scientist and data steward would confirm before a
tool is trusted for research use. It separates source checks from scientific
approval and lays out a proposed lifecycle from draft contract through expert
review, versioned implementation, regression evaluation and re-review.
The example is not expert-approved, and no scientific preflight approval gate
is implemented.

The prototype has no built-in HTTP authentication or dataset authorization.
Platform-provided ports and non-loopback binds fail closed unless an operator
explicitly acknowledges an independently verified authenticated ingress.
The container uses pinned image digests, the dependency lock, a non-root
runtime user, and read-only snapshot permissions; CI is configured for a
dependency audit, secret scan, dependency review, and read-only container smoke
test. The container was built and checked locally; see
[`container-verification.json`](container-verification.json). The GitHub
workflow passed on the fork's merged commit; it has not verified this later
documentation revision or the destination repository. These are prototype
safeguards, not enterprise authorization or a security certification.

The historical candidate-v7 agent run used FastMCP 2.14.7. The current locked
runtime uses FastMCP 3.4.11 after the dependency audit; those historical trials
do not evaluate the hardened runtime. The future enterprise
architecture—authorized Oracle connectivity, SSO, per-tool/data
authorization, guardrails and tamper-resistant auditability—is **planned only**.
SSO verifies identity; it does not itself authorize a person to access a
dataset. No FISMA authorization, zero-trust certification or production
readiness is claimed.

## Evaluation and hill-climbing evidence

The v2 evaluation adapts the internal scientific-suite methodology to 12
public-snapshot questions with explicit criteria, a development/holdout split,
and scope-adjusted pass conditions. One documented candidate change tightens
tool schemas and scope descriptions. Baseline and candidate both passed 36/36
scripted MCP trials (candidate: development 24/24; prospective holdout 12/12)
against the independent CSV reference. This verifies deterministic contract/data
behavior, not agent/model quality or an agent hill-climb win. The holdout is
prospective, visible, and not blind.

After the panel review, a [separate v3 scripted run](../eval/results/candidate-v3-judged.json)
again checks those 12 cases three times. The revised server accepts exact
published labels, with direct search-to-summary regression tests, and adds
explicit limits for no-record, stratum-count and unknown-unit interpretations.
It also exposes curated 2023/2025 NOAA context cards. **No model rerun was
performed at that stage**. Candidate-v7 has since been evaluated with the
model-selected trials summarized below. No matched before/after model comparison
is claimed. Original A01 remains unchanged. The scripted result records the
evaluated database and server-source hashes.

The candidate-v7 source-review metadata clarification was rerun separately
with the independent CSV reference:
[candidate-v7-scripted.json](../eval/results/candidate-v7-scripted.json)
passed 36/36 deterministic checks. It is not a model grade or evidence of
scientific approval.

After the security and dependency changes, a separate
[hardened-runtime scripted run](../eval/results/candidate-v7-hardened-scripted.json)
also passed 36/36 direct MCP checks against the independent public-CSV reference
using FastMCP 3.4.11. This scripted result is not an agent run. A separate
[current-runtime agent evaluation](../eval/results/hardened-agent-evaluation.json)
has since been completed.

### Current-runtime AI evaluation

The new Databricks run completed 45 MCP trials, plus 36 no-tool trials and
two smoke trials. All 80 recorded non-smoke MCP calls returned without a tool
error. Checked coverage and catch payloads matched the independently
recomputed NOAA CSV references.

For eight questions repeated three times, the MCP arm supplied the requested
snapshot result in 24/24 trials; the no-tool arm supplied it in 0/24. The
no-tool arm had the same dictionary but no underlying records and different
access instructions. This measures access and result presence, not overall
accuracy or an advantage over equally informed SQL or files.

A partial AI-assisted review flagged six answers that linked lower catches to
reduced sampling. That is relevant context, but the catch totals alone cannot
measure how much sampling explains. The other 37 MCP trials were not fully
reviewed; this is not an overall accuracy score or a scientific verdict.
The [sanitized manifest](../eval/results/hardened-agent-evaluation.json)
records case IDs, excerpts, file hashes and limits. Raw exports are excluded
because they may contain workspace identifiers and prompts.

One shared development agent run produced answers for eight questions. The
[public evidence appendix](public-evaluation-appendix.md) compares six questions'
reported numerical values with independently recalculated public-CSV values.
These checks do not constitute an overall pass; snapshot identity, development
tool traces, and full scientific review remain unverified.

Three repeats are now available for NOAA A01/B01/C01 and eight development
questions, including Q10. This is not a contiguous Q01-Q09 set: Q04 and Q06 were not
run. All 76 successful tool payloads across the 33 trials match the independent
public-CSV reference. The answers still vary in wording and expose recurring
issues: B01's geographic overreach, C01's unsupported unit/method claims, the
repeated species-name tool error, and Q10's unsupported "no tows" conclusion.
Q08 refuses safely but makes no MCP call. A01 repeats the benchmark's wrong
PDF page locator.

These are observed differences in a three-repeat sample, not a statistical
stability estimate. B01/C01 proposed FAIL reviews remain assistant judgments,
not MLflow grades; no independent scientific review was performed. The trial
files omit model configuration and an evaluated database checksum. See the
appendix and [detailed repeat-trial review](../eval/published_reference/repeated-trials-review.md).

The candidate-v7 model-selected run is recorded in the sanitized
[agent-evaluation manifest](../eval/results/candidate-v7-agent-evaluation.json).
It covers the 12 frozen questions and A02, D01 and C01, with three repeats each
(45 trials total). All completed. Of 84 recorded MCP calls, 82 succeeded and
two malformed Q06 search calls recovered. The recorded model endpoint, request
options, code, question and database identities are consistent across batches;
temperature is not recorded. Requested numerical tool payloads in the reviewed
cases agreed with the packaged independent references, but the final answers
still include unsupported causal explanations, a missing-versus-zero error and
an incorrect lowest-weight claim. A02 and D01 are now run cases; D01 demonstrates
discovery of the curated context card, not live report retrieval.

All 45 scientific-review fields remain `UNVERIFIED`. The run is not an expert
review, an overall accuracy score, a blind test, or evidence of before/after
improvement. The run manifest is the structured source used by the document
generator; account-specific MLflow exports are not included in the repository.

### Limited subject-matter input

The participant sought informal feedback on a shortened excerpt from historical
NOAA-D01:2, asking whether survey disruption directly explains the lower 2023
figures. A survey-data subject-matter contact was unsure, highlighted where
sampling occurred and the patchiness of cod catches, and recommended survey
and cod-population specialists. A developer familiar with the data answered
no but offered an uncertain explanation about why the survey was shortened.
An attached form indicated unable to assess and recommended cod-population
specialists; it may or may not be from either person in the text exchanges.

This feedback is limited to one excerpt, not the full answer or trial suite.
It did not verify the numerical results, establish causation, or provide
scientific approval. Names and direct quotations are omitted; obtain permission
before publicly identifying or quoting a reviewer. See the manifest's
`targeted_feedback` record for the anonymized details.

## Rubric evidence

| Claim / criterion | Exact artifact | What it does not establish |
| --- | --- | --- |
| Readability and agent-oriented design | [Maintainer map](../CONTRIBUTING.md), [typed contracts](../src/fisheries_mcp/models.py), [five tool modules](../src/fisheries_mcp/tools/) | User comprehension or agent accuracy |
| Current runtime: 36/36 scripted checks | [Hardened scripted results](../eval/results/candidate-v7-hardened-scripted.json), [independent CSV evaluator](../eval/run.py) | Model-selected tool use or scientific approval |
| Historical agent: 45 completed trials, 82/84 successful calls | [Run manifest and per-case findings](../eval/results/candidate-v7-agent-evaluation.json) | Overall answer accuracy; this used FastMCP 2.14.7, not the current 3.4.11 runtime |
| Public evidence is replayable | [Current receipt](release/demo-receipt.json), [replay implementation](receipt.py) | A live model run, new source download or expert review |
| Local container operated with runtime restrictions | [Container record and input hashes](container-verification.json), [MCP smoke verifier](container_mcp_smoke.py) | A passing GitHub Actions run or production authorization |
| CI on the fork | [Successful CI run](https://github.com/jwyman100/mcp-hackathon-template/actions/runs/45185569653), [workflow](../.github/workflows/ci.yml) | This later documentation revision or a destination-repository run |
| Interpretation problems remain visible | [Public appendix](public-evaluation-appendix.md), [candidate-v7 findings](../eval/results/candidate-v7-agent-evaluation.json) | That caveats prevented every unsupported answer |
| Targeted subject-matter input received | `targeted_feedback` in the [historical manifest](../eval/results/candidate-v7-agent-evaluation.json) | Review of the full answer, numerical validation or causal approval |
| Current agent run and data-access comparison | [Current manifest](../eval/results/hardened-agent-evaluation.json), [review protocol](../eval/README.md#answer-assessment-separate-from-scientific-approval) | Overall answer accuracy, scientific approval, or an MCP advantage over an equally informed interface |
| Scientific schema-review lifecycle proposed | [Provisional contract](schema-contract.md) | An implemented or expert-approved approval gate |
| Mission and presentation | [Scripted demo](demo.py), current deck and evaluation listed below | Measured researcher time savings or agency endorsement |

No official numerical grading weights or vendor-platform bonus were found.
The optional Databricks experiment is not a substitute for correctness evidence.

## Generate the submission documents

The generator adapts the official GSA sample templates, removes their example
claims/images, and inserts this project's results. Download the templates from
the [GSA event page](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon?gsaredirect=hackathon),
then run:

```powershell
uv sync --locked --group dev --extra presentation
uv run python submission\demo.py --receipt C:\path\to\new-demo-receipt.json
uv run python submission\build_documents.py --deck-template C:\path\to\sample.pptx --evaluation-template C:\path\to\sample.docx --results eval\results\candidate-v7-hardened-scripted.json --receipt C:\path\to\new-demo-receipt.json --agent-evaluation eval\results\candidate-v7-agent-evaluation.json --output-dir C:\path\to\new-output-directory
```

The generator creates the [reference deck](release/repository/fisheries-deck.pptx),
the [six-slide recording template](release/repository/fisheries-video-deck.pptx),
and the [evaluation document](release/repository/fisheries-evaluation.docx).
The templates do not include the recorded demo. They summarize the current
evaluation and its limits; the candidate-v7 agent run remains separate
historical evidence. The schema contract and receipt/replay details are in this
guide and the linked technical files.

The earlier `candidate-v7-sme-feedback` receipt is preserved for historical
container/server provenance. The current demo adds a clearer interpretation
handoff, so that earlier receipt intentionally fails the demo-source hash check.
Use the `release` receipt to replay the current code.

The configured CI container smoke test connects to `/mcp`, discovers tools,
resolves cod and checks the 2022-2023 public catch results in addition to
checking `/health`. Those container checks were also performed locally.
The fork's CI passed on the merged commit; this later documentation revision
and any destination-repository CI run have not yet been verified.
Earlier local binary
drafts, including candidate-v5, and Office lock files are ignored, not deleted;
do not include them in the release. They contain superseded claims or scope
language. Preserve archived
scripted result JSON as historical evidence, including its scripted-only
`agent_evaluation` status.

## Outstanding before final submission

- Confirm the submission process and cutoff time. The public GSA page lists
  November 23, without a specific time or submission link.
- Confirm any required agency code-release/upload permission.
- Disclose the limited one-excerpt consultation and that a full independent
  scientific review was not performed. Do not claim weight units, official
  abundance or representative-haul equivalence.
- Keep all candidate-v7 scientific review statuses `UNVERIFIED` until a
  fisheries expert reviews the relevant claims.
- Keep SSO, per-tool authorization, guardrails and auditability clearly labeled
  as future enterprise work; do not imply identity alone authorizes data access.
- Keep all 33 historical trial records unverified until each applicable rubric
  dimension has been reviewed. Do not rewrite their saved status or answers.
- Use [the maintainer guide](../CONTRIBUTING.md) for the code map, evaluation
  evidence lifecycle and clean-checkout test procedure.
- Review the materials and add any required team details.
- Use approved Databricks access and bounded model calls; do not deploy a public
  runtime. Plenty of available credits is not a reason to run an unbounded loop.

The project has been pushed to the fork, but the participant controls the
destination push and final submission. No public runtime deployment is claimed.
Internal-project improvement notes are stored outside this repository.
