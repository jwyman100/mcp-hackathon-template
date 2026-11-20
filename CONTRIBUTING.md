# Maintainer guide

This guide maps common changes to the smallest relevant part of the repository.
The project is a public-data prototype; changes must not introduce internal
records, credentials, or unsupported scientific claims.

Evidence receipts hash exact file bytes. `.gitattributes` disables automatic
line-ending conversion for those source/container inputs so Windows and Linux
checkouts can replay the same evidence. Do not mass-normalize those files:
intentional source or formatting changes require a new receipt, while historical
receipts stay unchanged.

## Follow a request through the server

1. `src/fisheries_mcp/app.py` constructs the FastMCP server and registers the
   tools, resource, and prompt.
2. `src/fisheries_mcp/tools/<tool>.py` defines one MCP tool and delegates work.
3. `src/fisheries_mcp/models.py` owns typed request/result contracts and shared
   interpretation language.
4. `src/fisheries_mcp/data.py` runs parameterized, read-only SQLite queries.
5. `data/spring.sqlite` is built from the pinned public archive by
   `src/fisheries_mcp/prepare.py`; do not hand-edit the database.

Keep the layers narrow: tool functions validate through the request models and
call `SurveyStore`; the store owns query and scope behavior; the models define
the public contract. Add tests at the layer where behavior changes and retain
stdio integration tests for MCP-visible behavior.

## Common changes

| Change | Start here | Also verify |
|---|---|---|
| Add or change an MCP tool | `src/fisheries_mcp/tools/`, `models.py`, and `app.py` | Tool registration, JSON schema, successful and invalid MCP requests, and documented scope |
| Change a query or scope rule | `data.py` and `models.py` | Independent reference in `eval/run.py`; missing, zero, empty and boundary cases |
| Change source fields or import behavior | `prepare.py` and `data/README.md` | Synthetic importer fixtures, pinned archive identity and atomic failure behavior |
| Add a benchmark question | `eval/questions.json` and `eval/run.py` references | Stable answer, explicit rubric, development vs. confirmation classification |
| Review model-selected trials | `eval/review_answers.py` and `eval/README.md` | Preserve hash-bound answers/configuration; distinguish analyst judgments from scientific approval; never rewrite historical results |
| Change submission documents | `submission/build_documents.py` and source evaluation data | Regenerate from the documented templates and inspect rendered output |

## Scientific and data invariants

- The bundled snapshot is public, fixed to Atlantic cod and haddock for spring
  2021-2025, and is not a full survey catalog or live service.
- Expanded catch weight units are unspecified in the linked public metadata.
  Never label them as pounds or kilograms without authoritative evidence.
- Missing catch rows or measurements are not measured zero. A station record is
  not necessarily a valid or representative haul.
- Station and sampled-stratum counts are not standardized effort or geographic
  area. Catch totals do not establish population trends or their cause.
- Curated NOAA context cards are source-checked statements, not live retrieval
  or scientific approval. Their `scientific_review_status` is not reviewed.
- SSO, per-tool/data authorization, guardrails and enterprise auditability are
  planned, not implemented in the public prototype.
- Platform-provided ports and non-loopback HTTP binds fail closed unless
  `MCP_TRUSTED_HTTP_INGRESS=true`; this is an operator assertion, not auth.
- Keep runtime logs allowlisted and sanitized. Do not log prompts, tool inputs,
  query strings, results, credentials, or internal identifiers.
- Do not rewrite archived answers or review statuses to make a run appear
  successful. Separate tool-payload agreement from final-answer interpretation.

## Reproduce the local checks

From a clean checkout, install the locked development and document dependencies,
then run the checks used by CI:

```powershell
uv sync --locked --group dev --extra presentation
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/ -v
```

CI additionally runs the documented model-free MCP demo, writes a receipt to a
temporary path, and replays it. This verifies MCP startup, the public snapshot,
and deterministic receipt behavior without model access.
It also runs dependency and secret checks, reviews dependency changes on pull
requests, and builds the pinned non-root container with a read-only runtime
smoke test. The trusted-ingress container check verifies basic startup only; it
does not verify authentication or authorize a hosted deployment.

To run those demo steps locally on PowerShell:

```powershell
$receipt = Join-Path $env:TEMP "fisheries-demo-receipt.json"
uv run python submission\demo.py --receipt $receipt
uv run python submission\demo.py --replay $receipt
Remove-Item -LiteralPath $receipt
```

The demo refuses to overwrite an existing receipt. Choose a new temporary path
if the file already exists. The receipt is public-data evidence, not scientific
approval or a security audit.

## Evaluation evidence lifecycle

`eval/results/candidate-v7-agent-evaluation.json` is the sanitized, structured
summary used by the submission document generator. It records run configuration,
case scope, observed findings, limited post-run feedback, and unverified review
status. Keep it separate
from the raw model traces and account-specific MLflow artifacts. Do not copy
workspace identifiers or credentials into the repository.

The checked-in case observations summarize an evaluator review; they are not a
substitute for expert scientific review. If the evidence changes, update this
manifest and regenerate the deck/evaluation document from their source
templates. Verify that every run has three trials per case, all cases remain
UNVERIFIED unless the relevant full trial is reviewed by a domain expert, and
historical and candidate-v7 runs are not conflated. One excerpt consultation
does not validate the rest of a trial or the suite; do not identify or quote
reviewers without permission.

The repository-visible `holdout` questions are confirmation cases, not a blind
test. The recorded candidate-v7 model settings do not include temperature.
Do not claim a controlled before/after improvement without matched model,
question, prompt, and snapshot settings.
