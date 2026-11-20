# Run and connect locally

Use Python 3.11+ and [uv](https://docs.astral.sh/uv/). No Oracle, cloud account,
API key, model subscription, or internal network connection is required to run
the server. An agent/chat client requires its own approved model access.

From the repository root:

```powershell
uv sync --locked --group dev
uv run fisheries-mcp
```

The command communicates MCP over stdio. It does not show a chatbot. Stop it
before having a client launch another instance if testing the same configuration.

## Connect an MCP client

Use the client's local/stdio server configuration:

```json
{
  "mcpServers": {
    "fisheries": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\this-repository", "run", "fisheries-mcp"],
      "env": {
        "FISHERIES_DATABASE": "C:\\path\\to\\this-repository\\data\\spring.sqlite"
      }
    }
  }
}
```

Replace the paths with your checkout; do not paste credentials. Clients differ
in config wrappers (for example VS Code uses `servers`). The process command,
arguments, and environment are the same. Verify that five tools are discovered.
The catch tools accept the exact published label returned by `search_species`,
as well as the exact common or scientific name.

To see a scripted search-to-summary-to-context workflow without a model, run:

```powershell
uv run python submission\demo.py --receipt submission\candidate-v7\demo-receipt.json
uv run python submission\demo.py --replay submission\candidate-v7\demo-receipt.json
```

It invokes the real MCP server, but the calls are chosen by the script rather
than by an AI agent. With an already-installed Windows virtual environment,
`.\.venv\Scripts\python.exe submission\demo.py --receipt submission\candidate-v7\demo-receipt.json`
also works if `uv` is not on PATH. The receipt contains public requests and
results plus source/database/server hashes. Replay fails if the data, code or
tool outputs differ; it is not scientific approval or a security audit.

Try:

> Compare Atlantic cod and haddock for the public spring 2021-2025 snapshot.
> Include sampling coverage, complete matched years, source, and limitations.

Then:

> Do these totals prove the cod population declined?

The correct answer must distinguish catch totals from abundance estimates.
The server supplies caveats; whether an agent retains them must be evaluated.
`get_spring_report_context` supplies offline, manually curated NOAA cards for
2023 and 2025, not live report search. For 2023, NOAA's 70 sampled trawl
stations and the snapshot's 77 selected station records are distinct counts.
Source-check metadata is not scientific approval: the cards are marked
`not_reviewed`. The proposed, non-approved
[schema contract](submission/schema-contract.md) illustrates future expert
collaboration. Oracle access, SSO, per-tool authorization, guardrails and
auditability are planned enterprise work, not capabilities of this public
prototype; identity alone does not grant data access.

## Rebuild the snapshot

```powershell
uv run fisheries-prepare --download
# Or, with the exact official ZIP downloaded from the NOAA metadata record:
uv run fisheries-prepare --archive C:\path\to\public-survey.zip
```

The importer verifies SHA-256, selected fields and joins, and duplicate keys,
then atomically replaces the database. A changed upstream archive fails the pin;
review changes before updating code. Do not substitute an internal export.
After preparation, the server requires no network access.

## Optional loopback HTTP

```powershell
$env:MCP_TRANSPORT = "streamable-http"
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8000"
uv run fisheries-mcp
```

Connect at `http://127.0.0.1:8000/mcp`. HTTP has **no application
authentication** and is restricted to loopback by default. `GET /health`
reports a missing/invalid snapshot as HTTP 503. Platform-provided ports and
non-loopback binds fail closed unless `MCP_TRUSTED_HTTP_INGRESS=true` is set.
That setting is only an operator assertion; it does not add authentication.
Do not expose this process publicly or enable the setting without verifying an
approved authenticated ingress and blocking direct unauthenticated access.

Unset the environment variables before returning to stdio. `FISHERIES_DATABASE`
can select another operator-prepared file, but no MCP argument can change it.
The submitted snapshot's provenance states its exact scope and source.

## Common failures

- Missing database: run the importer from the repository root or set the
  absolute `FISHERIES_DATABASE` path.
- Checksum mismatch: the public file changed; stop and review it. Do not remove
  verification to make the demo work.
- Unknown species: call `search_species`; only cod and haddock are included.
- Out-of-range year: this snapshot covers 2021-2025; it is not live.
- `uv` unavailable after pip installation: use `python -m uv` for the documented
  commands or add the installation's Scripts directory to PATH.
