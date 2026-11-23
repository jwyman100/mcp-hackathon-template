# Evidence-aware Fisheries MCP

This prototype helps an AI assistant find and understand **public NOAA
fisheries data**. It is read-only and runs locally; it does not access a
private database.

The fixed snapshot covers Atlantic cod and haddock in spring 2021-2025. It is
not a live feed or an official stock assessment.

## Try the demo first

Install [uv](https://docs.astral.sh/uv/) if needed. From the repository root,
install the project dependencies:

```text
uv sync --locked --group dev
```

Run the scripted demo:

**Windows PowerShell**

```powershell
uv run python submission\demo.py
```

**macOS or Linux**

```bash
uv run python submission/demo.py
```

This calls the real MCP server using public data. The calls are scripted, not
selected by an AI; it needs no model, Oracle access, API key, or network access.

## Connect an MCP client

The server uses MCP over stdio; it is not a chat interface. Follow
[QUICKSTART.md](QUICKSTART.md) to connect a compatible MCP client. The client
starts the server with `uv run fisheries-mcp`. Queries run offline and are
read-only.

The included `data\spring.sqlite` is a public-only snapshot. To rebuild it
from the checksum-pinned NOAA archive, run `uv run fisheries-prepare --download`.

## What makes it useful

For example: **"Compare cod and haddock catch from 2021 to 2025, and check
the survey coverage."**

| Tool | Goal |
| --- | --- |
| `search_species` | Find published common/scientific names in this snapshot |
| `get_spring_catch_summary` | Retrieve one species' catch and sampling context |
| `compare_spring_catch` | Compare distinct species with identical scope |
| `get_spring_survey_coverage` | Inspect station coverage independently of catch |
| `get_spring_report_context` | Read a curated, cited NOAA context card for 2023 or 2025 |

The report cards are curated summaries, not live report retrieval. The server
also provides a data dictionary and a comparison prompt. It does not expose
arbitrary SQL.

## Important limits

- Catch totals are **not population estimates** and are not standardized for
  survey effort.
- No catch record means unknown, not measured zero. Station records are not
  automatically valid hauls.
- NOAA's linked metadata does not specify the weight unit. Do not assume one.
- Survey changes make comparisons harder; they do not prove why catch changed.
- A scientist has not approved the answers.

## What we tested

- **Scripted checks:** 36 of 36 passed against independently calculated NOAA
  CSV values. These test the tools, not the AI's reasoning.
- **AI trials:** 45 MCP trials completed. All 80 recorded tool calls returned
  without errors.
- **Data access:** For eight questions tried three times each, the AI supplied
  the requested result in 24 of 24 MCP trials and 0 of 24 no-tool trials. The
  no-tool version did not have the underlying records.
- **Answer review:** In six reviewed answers, the AI linked lower catches to
  reduced sampling—useful context, though the catch totals cannot tell how much
  that explains. The review was partial and AI-assisted; 37 trials were not
  fully reviewed. Overall accuracy and scientific approval remain
  **UNVERIFIED**.

The comparison tests data access, not an MCP advantage over equally informed SQL
or files. It is not an overall accuracy score.

## Submission materials

- [Reference slides without a recording](submission/release/repository/fisheries-deck.pptx)
- [Evaluation document](submission/release/repository/fisheries-evaluation.docx)
- [Video slide template](submission/release/repository/fisheries-video-deck.pptx)
- [Short video script](submission/VIDEO.md)
- [Current evaluation details](eval/results/hardened-agent-evaluation.json)
- [Technical evidence and rubric map](submission/README.md)

The finished recording and edited decks are separate from these templates.

The earlier agent results and their limitations are preserved separately in the
[candidate-v7 manifest](eval/results/candidate-v7-agent-evaluation.json).

```powershell
uv run pytest tests -q
uv run ruff check .
uv run ruff format --check .
```

See [evaluation details](eval/README.md), the
[Databricks runbook](deploy/databricks/README.md) and
[CONTRIBUTING.md](CONTRIBUTING.md) for technical reproduction.

## Structure

`src\fisheries_mcp` contains the thin app, models, read-only data layer, public
importer, and one file per tool. `tests` uses invented records, not restricted
data. `eval` computes reference answers independently of application queries.
`data` contains only the selected official public extract.

## Source and attribution

- [NOAA Spring Bottom Trawl Survey metadata and downloads](https://www.fisheries.noaa.gov/inport/item/22561)
- [Catch field metadata](https://www.fisheries.noaa.gov/inport/item/33608)
- [Station field metadata](https://www.fisheries.noaa.gov/inport/item/33610)

Acknowledgement: NOAA/NMFS/NEFSC. This independent prototype is not an official
NOAA or Department of Commerce assessment or endorsement. See
[SECURITY.md](SECURITY.md) and the [MIT license](LICENSE).
