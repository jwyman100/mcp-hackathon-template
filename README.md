# Evidence-aware Fisheries MCP

A GSA hackathon **Dataset Access Server** prototype that turns a public NOAA
spring survey snapshot into reproducible, scientifically qualified answers.
It resolves species names, summarizes expanded catch, aligns comparisons,
reports sampling coverage, and supplies selected published-survey context
without requiring an internal database account.

**Scope:** Atlantic cod and haddock, spring 2021-2025. The public archive's
extraction date is June 25, 2026. This is not a live feed, a full species catalog, an official
stock assessment, or a publicly deployed service.

## Quick start

Install [uv](https://docs.astral.sh/uv/), then from the repository root:

```powershell
uv sync --locked --group dev
uv run fisheries-mcp
```

The included `data\spring.sqlite` is a compact public-only snapshot. To regenerate
it from the checksum-pinned official archive:

```powershell
uv run fisheries-prepare --download
```

The first command above starts a **stdio MCP server**, not a chat interface. Add
it to an MCP-capable client using [QUICKSTART.md](QUICKSTART.md). Runtime queries
are offline and read-only. Missing/incompatible data causes an explicit error;
there is no fallback to synthetic data or an internal server.

For a reproducible demonstration without a model:

```powershell
uv run python submission\demo.py
```

This script calls the real MCP server over stdio; its calls are scripted, not
selected by an agent. If the Windows virtual environment is already installed
but `uv` is not on PATH, run `.\.venv\Scripts\python.exe submission\demo.py`.

## What makes it useful

Ask: **"Compare Atlantic cod and haddock spring catch for 2021-2025. Check coverage
before interpreting the difference."**

The server provides the same years and strata for both species, annual catch
completeness, station/cruise/stratum counts, public provenance, and interpretation
limits. It rejects aliases of the same species as a two-species comparison.

| Tool | Goal |
| --- | --- |
| `search_species` | Find published common/scientific names in this snapshot |
| `get_spring_catch_summary` | Retrieve one species' catch and sampling context |
| `compare_spring_catch` | Compare distinct species with identical scope |
| `get_spring_survey_coverage` | Inspect station coverage independently of catch |
| `get_spring_report_context` | Read a curated, cited NOAA context card for 2023 or 2025 |

The catch tools accept exact common names, scientific names, and published labels
returned by search. Every tool has a typed `request` object. Survey years default
to 2021-2025 and strata to `00000`-`99999` (all snapshot strata). The report cards are manually curated and limited to the two named years; their
source-check date is distinct from scientific approval, and their review status
is `not_reviewed`. They do not fetch or search current reports. Report figures
are separate from snapshot records. The resource `fisheries://dictionary`
explains source fields and provenance; the `responsible_comparison` prompt
provides a reproducible starting question. There is no arbitrary SQL tool.

## Scientific limits are part of the result

- Expanded catch totals are **not population abundance indices**. No area
  weighting, vessel calibration, effort standardization, or haul/gear validity
  filtering is applied.
- No catch record means unknown, not measured zero. Unknown measurements make
  that annual total null; known subtotals are labeled separately.
- `EXPCATCHNUM` is an expanded number of individuals and can be fractional.
- The linked public field metadata does **not specify the unit of EXPCATCHWT**.
  Responses say "source units"; this does not prove which units are excluded.
- Coverage counts station records. A matched year means complete catch
  measurements for the requested species, not equal effort between years.
- No selected station records do not prove that no survey effort occurred;
  counts of strata do not measure the geographic area covered.
- Out-of-snapshot years are rejected rather than presented as missing data.

## Evidence and deliverables

Start with the [claim-to-artifact map](submission/README.md#rubric-evidence),
[presentation](submission/release/fisheries-deck.pptx) and
[evaluation document](submission/release/fisheries-evaluation.docx).
The [step-by-step Databricks runbook](deploy/databricks/README.md#step-by-step-current-hardened-source-run)
prepares the current-runtime agent rerun and optional no-tool comparison;
these new experiments have not yet been executed.

[Evaluation documentation](eval/README.md) explains independent raw-CSV
reconciliation, synthetic edge-case tests, the 12-question benchmark, results,
and limitations. [Historical scripted results](eval/results/scripted.json) and
the [post-review scripted run](eval/results/candidate-v3-judged.json) and
[candidate-v7 scripted run](eval/results/candidate-v7-scripted.json), plus the
[hardened-runtime scripted run](eval/results/candidate-v7-hardened-scripted.json),
distinguish transport/tool correctness from model-selected tool use.
The hardened-runtime run passed 36/36 scripted checks against the public CSV
reference; it is not an agent score.
The [public evidence appendix](submission/public-evaluation-appendix.md) records
numerical agreement alongside recovered tool errors, unsupported model claims,
and an evaluator citation error. The historical 33-trial set remains separate
from the candidate-v7 agent run. The sanitized
[candidate-v7 run manifest](eval/results/candidate-v7-agent-evaluation.json)
records 45 model-selected trials across 15 questions: all completed, 82 of 84
MCP calls succeeded, and the two malformed calls recovered. Reviewed numerical
tool outputs agreed with supplied references in the requested cases, while
answer-level interpretation errors remain. All trial scientific-review statuses
are `UNVERIFIED`. Later, limited subject-matter input addressed one historical
NOAA-D01:2 excerpt and identified a need to examine spatial sampling; it did
not approve the answer. No independent CSV reprocessing of this bundle, full
scientific review, perfect score, or controlled before/after result is claimed.

```powershell
uv run pytest tests -q
uv run ruff check .
uv run ruff format --check .
```

The [submission guide](submission/README.md) contains the demo narrative,
rubric-to-evidence mapping, deck/document generation, and remaining release
gates. The [provisional schema contract](submission/schema-contract.md) explains
the proposed scientist-review lifecycle; the demo's optional JSON receipt
records reproducible public tool calls and can be replayed locally. Neither is
scientific approval. The optional [Databricks experiment](deploy/databricks/README.md) is not
required to reproduce the local server and has not been deployed.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the code-path map, scientific
invariants, evidence lifecycle and clean-checkout validation steps.

## Structure

`src\fisheries_mcp` contains the thin app, models, read-only data layer, public
importer, and one file per tool. `tests` uses invented records, not restricted
data. `eval` computes reference answers independently of application queries.
`data` contains only the selected official public extract.

## Source and attribution

- [NOAA Spring Bottom Trawl Survey metadata and downloads](https://www.fisheries.noaa.gov/inport/item/22561)
- [Catch field metadata](https://www.fisheries.noaa.gov/inport/item/33608)
- [Station field metadata](https://www.fisheries.noaa.gov/inport/item/33610)

Read the source metadata and use constraints before making inferences.
Acknowledgement: NOAA/NMFS/NEFSC. This independently implemented prototype is not
official NOAA or Department of Commerce communication or endorsement. It uses
only the published extract, not internal survey data or an internal MCP endpoint.
Code is provided under the inherited [MIT license](LICENSE); see
[SECURITY.md](SECURITY.md) for reporting and deployment boundaries.
