# Optional Databricks experiment (not deployed)

The local SQLite server is the complete reproducible core. A Databricks account
does not automatically imply Apps, compute, catalog, model, or client permissions.
Recorded model answers and limited trace reviews are available; see the
[public evidence appendix](../../submission/public-evaluation-appendix.md).
No Databricks Apps deployment, overall agent pass or cloud performance result
is claimed.

### Download evidence without copying the trace viewer

Open the MLflow experiment run whose ID section 6 prints, then its **Artifacts**
tab. Download `answers.json`, `configuration.json`, and `agent_context.json`.
The answers artifact includes completed trials' full messages and tool results;
the run's `trials/` directory contains the individual JSON files. Download files
rather than copying the expandable preview, which may show collapsed fields.
No model rerun is needed.

If execution stopped before writing `answers.json`, use the individual completed
trial files and any `*-failure.json` entries under `trials/`. A failure artifact
records the exception type, not necessarily the partial conversation. Include
`scientific_review.json` if it exists, keeping unreviewed dimensions unverified.
Keep raw artifacts private and review them before publishing public-only excerpts.

## Gates before using the workspace

Confirm account/cloud/edition, available compute, permitted sandbox use,
code-release/upload permission, intended OAuth client, cost expectations, and
who will stop/delete resources. Do not put tokens or internal data in this repo.
Only the public snapshot and approved code may be uploaded.

## Notebook evaluation

### Step-by-step: current hardened-source run

Use the newly generated notebook, not a previous import. These are manual
workspace actions; do not use **Run all**. Nothing below deploys an App or
connects to internal Oracle. The notebook installs a separate pinned dependency
stack, not the container lockfile.

1. Confirm the public-code upload, sandbox compute, model and cost permissions.
   Use existing approved Python 3.11+ compute with subprocess support. Do not
   create a new cluster merely to follow these instructions.
2. In **Workspace**, open your working folder, choose **Import**, and upload
   the supplied `fisheries-hardened-comparison.ipynb`. Attach the approved compute.
3. Run section **1**'s `%pip` cell, wait for success, then run its
   `dbutils.library.restartPython()` cell. If dependency resolution fails, retain
   the error rather than upgrading packages ad hoc.
4. Run section **2** to unpack/check the public bundle. Save the printed
   confirmation; a hash mismatch is a stop condition.
5. Run section **3** to list model endpoints. This does not call a model.
   Confirm your approved endpoint is available; listing is not query permission.
6. Run section **4** with `ENABLE_MODEL_CALLS=False`, `EVALUATION_ARM="mcp"`,
   `SPLIT="smoke"`, `REPEATS=1`. The comparison notebook uses the earlier
   `databricks-claude-opus-4-8` and `MODEL_OPTIONS={"max_tokens": 4000}`.
   Preserve those if available/approved; otherwise record the new configuration
   and do not claim an exact historical comparison. Temperature was not recorded
   previously. Leave `EXPERIMENT_PATH=""` unless your administrator supplies an
   experiment path you can write to.
7. Run section **5**. Expect five tools, public provenance and a successful cod
   name handoff. No model usage occurs. Do not proceed if this fails.
8. For one paid/credit-consuming smoke trial, change only
   `ENABLE_MODEL_CALLS=True` in section **4**, rerun that configuration cell,
   then run section **6**. Inspect the answer and tool trace; execution completion
   is not correctness. Check `configuration.json` records FastMCP 3.4.11.
9. If smoke works, freeze source, model, options and prompts. For each row below,
   edit `SPLIT` and `REPEATS`, rerun section **4**, then **6**, and export the
   artifacts before moving to the next row. Do not rerun installation/unpacking
   between batches or tune the candidate between them.

   | SPLIT | REPEATS | Trials |
   | --- | ---: | ---: |
   | `development` | 3 | 24 |
   | `holdout` | 3 | 12 |
   | `published_reference_corrected` | 3 | 3 |
   | `published_report_context` | 3 | 3 |
   | `published_c_preflight` | 3 | 3 |

10. For each printed MLflow run ID, open **Experiments > run > Artifacts**.
    Download `answers.json`, `configuration.json`, `agent_context.json`,
    `independent_reference.json` and the `trials/` records to a separate folder
    named for that arm/split/run. Retain failed run artifacts too. Section **7**
    identifies the current run; it does not assign scientific approval.
11. Optional additional comparison: after approving its extra model usage,
    select `EVALUATION_ARM="no_tools"`, `SPLIT="smoke"`, `REPEATS=1`. Rerun
    sections **4** and **6**. If it works, use `development`/3 for 24 baseline
    trials and compare with the same 24 MCP trials. Do not change model/options
    or provide gold answers. This is a development-set access-plus-tooling
    comparison, not blind evaluation or MCP versus equally informed SQL.
    The baseline retains dictionary context but cannot query the snapshot.
12. Set `ENABLE_MODEL_CALLS=False` and rerun section **4** when finished.
    Stop/detach compute according to sandbox policy. Bring the downloaded
    artifacts back for review; keep workspace identifiers and raw traces private.
    Use the [local answer-review commands](../../eval/README.md#answer-assessment-separate-from-scientific-approval)
    to record analyst findings separately from scientific approval.

The primary run is **45 trials plus one smoke**. The optional baseline adds
**24 trials plus one smoke**. These request limits are not a dollar budget.
If any batch fails, keep the failed run, stop, and diagnose before retrying;
do not quietly replace failed evidence with a later success.

### Importable model-driven notebook

`build_eval_notebook.py` creates a single `.ipynb` with an allowlisted copy of the
public server, SQLite snapshot, questions, and independently calculated CSV
reference answers. It does not include `.env`, MCP connection configuration,
internal data, or the rest of the repository. Review agency upload permissions
before importing even this public-only package.

```powershell
uv run python deploy\databricks\build_eval_notebook.py --archive C:\path\to\public-survey.zip --output C:\path\to\fisheries-databricks-eval.ipynb
```

In Databricks, choose **Workspace > your folder > Import**, import the notebook,
attach approved Python 3.11+ compute, and run its cells one at a time. It includes
notebook-scoped dependency installation, automatic notebook authentication,
endpoint discovery, a no-model MCP check, a gated one-question agent run, and
MLflow traces/artifacts. No Genie, Apps, SQL warehouse, new cluster, or public
deployment is created by the notebook. Workspace-specific experiment or
trace-storage permissions may still be needed.

Set `ENDPOINT` to an approved chat endpoint with tool calling. Leave model calls
disabled until the MCP check passes; then enable only the smoke run. Subsequently
select development/3 for 24 trials and, after freezing the candidate, holdout/3
for 12 confirmation trials. Every trial has fresh conversation state and bounded
requests; errors stop the run. Limits are not a dollar budget.

The model receives only the question, common MCP dictionary context and discovered
tools, never expected answers or scripted arguments. `eval/databricks_agent.py`
implements the bounded model-selected tool loop. MLflow records actual model
and MCP calls. The notebook supplies independent references for **manual analyst
assessment**, not an automatic LLM judge. Scientific review stays `UNVERIFIED`
even when an analyst marks an answer PASS; separate specialist review is needed.
Execution success is not scientific correctness.

This experiment uses only the fixed public snapshot. It does not connect to
internal Oracle data or implement/test the planned enterprise SSO,
per-tool/data authorization, guardrails, or auditability. The separate schema
contract example is provisional, not expert-approved; identity verification
alone is not dataset authorization.

For the supplementary NOAA published-reference comparison, select
`SPLIT = "published_reference"` and keep `REPEATS = 1`. It compares the
2025 MCP station-record count with the published representative/non-representative
breakdown. The relevant report facts are stated in that historical question;
the packaged evaluator reference is not sent to the model. The current server
also offers manually curated 2023/2025 report context, not live report
retrieval. See [the question and source notes](../../eval/published_reference/README.md).

The updated notebook also supports `SPLIT = "published_context"` for the
separate B01 question on the 2023 survey disruption; use `REPEATS = 1` and
retain your approved working model options. `SPLIT = "published_c_preflight"`
selects C01, a separate test of 2025 catch retrieval and the limits of
representative-haul reconciliation. Neither case reruns A01 or requires a new
server capability. C01 is not a full report-total reconciliation, and no
independent scientific review was performed. A01's original prompt has a
citation erratum: its Overview is on physical PDF page 3, not 1; the completed
trial's prompt is preserved. The revised notebook also offers
`published_reference_corrected` (A02) and
`published_report_context` (D01). Both were included in the historical
candidate-v7 run and in the later
[hardened-runtime run](../../eval/results/hardened-agent-evaluation.json). D01
asks for context without providing the facts in the prompt, but can only test
the curated card, not live report discovery.

### Rerun on the hardened runtime

Generate a **fresh** notebook from the current source; an older notebook embeds
its earlier server. Confirm upload, compute, model and cost permissions first.
Use `--candidate-v7-config` when building to populate the recorded endpoint and
model options; confirm the endpoint `databricks-claude-opus-4-8` is approved
and `MODEL_OPTIONS` contains `{"max_tokens": 4000}`. Keep the recorded limits
of six model rounds, eight tool calls and 180 seconds.
The earlier temperature was not recorded, so omitting it does not create an
exactly controlled comparison. Confirm FastMCP 3.4.11 in the run configuration.
The notebook installs its dependencies separately from the container lockfile;
the run identifies its recorded package versions but is not a lock-identical
container evaluation.
Keep calls disabled until the no-model check passes, then run one smoke trial.
Run `development` and `holdout` with three repeats each; run
`published_reference_corrected`, `published_report_context`, and
`published_c_preflight` with three repeats each. That is 45 trials in addition
to the smoke trial. Preserve configuration, answers, traces and failures for
each split; compare answers and interpretation as well as execution. Scientific
reviews stay UNVERIFIED until appropriately reviewed.

The pinned notebook stack is in `requirements-eval.txt`. The loop can be tested
offline with the existing test suite, but a new workspace still requires a
smoke run to check installation, endpoint permissions, model response and
MLflow storage. Generating a notebook does not itself run an experiment.

### Independent numerical check

In an approved notebook, read the exact NOAA public archive (hash in
`data\README.md`). Independently select audited spring records for 2021-2025,
cod/haddock codes 073/074, join catch to unique stations by ID, and aggregate
expanded weight/number and coverage. Use the public metadata for semantics,
not the application query functions as the reference implementation.

Compare annual results with `eval\results\scripted.json`, retaining null versus
zero distinctions and documenting numeric tolerance. Export public-only results
and run metadata. Do not call that evidence of MCP/client integration by itself.

## Optional Apps experiment

The inherited `app.yaml` points to `fisheries_mcp.app`; the app command
explicitly acknowledges the Databricks OAuth ingress, then the server reads
`DATABRICKS_APP_PORT`, enables stateless Streamable HTTP, and serves `/mcp`.
The repository includes `data\spring.sqlite`; verify it is included in the
deployment and use an explicit `FISHERIES_DATABASE` if the runtime cwd differs.

After the gates are satisfied, use the inherited deployment script or the
Databricks Apps UI in an approved sandbox. Neither has been run for this
submission. The script can create cloud resources and upload source; reviewing
this document is not permission to run it.

The app command sets `MCP_TRUSTED_HTTP_INGRESS=true` to acknowledge the
Databricks OAuth ingress. The server does not validate OAuth tokens itself.
Before deploying, confirm authorized access, rejection of unauthorized access,
and that no direct route bypasses the platform boundary. Also verify MCP
initialization, tool discovery, and real tool calls. A health response or login
redirect alone is not an MCP test. Use **OAuth**, not a PAT: current official
documentation does not support PATs for MCP servers hosted on Apps.

Hosting a SQLite file behind Apps OAuth does not demonstrate Unity Catalog
row-level governance or per-user source-system authorization. Do not add a second data
backend just for hosting. The account and authenticated client determine whether
this demonstration is practical; retain the local path if they are unavailable.

Official guidance:

- https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp
- https://docs.databricks.com/aws/en/agents/mcp-tools/authentication-networking

No public endpoint is part of the hackathon plan. Authentication alone does not
establish that a platform is an approved government sandbox.
