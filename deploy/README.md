# Deployment options and security boundary

Local development runs your server over **stdio** (how Claude Desktop / Claude
Code launch it). To share it with an agent platform, deploy it to a host that
serves it over **streamable-HTTP**, then register it.

This repository contains deployment examples, but **no hosted deployment is
approved by this prototype**. Use local stdio by default. Hosted deployment
requires an independently approved, authenticated ingress and review of the
target agency's security requirements.

The examples cover:

| Target | Kits | Transport | When to use |
|---|---|---|---|
| **IBM watsonx Orchestrate** | [`ibm/`](ibm/) — 3 kits | stdio (local) **or** streamable-HTTP (Code Engine) | You're evaluating/agent-building in watsonx Orchestrate |
| **Databricks** | [`databricks/`](databricks/) | streamable-HTTP (Databricks Apps) | You're deploying alongside a Databricks workspace |

## HTTP startup is fail-closed

The server uses `src/fisheries_mcp/` and the public SQLite snapshot. Local stdio
and loopback HTTP are the supported prototype modes. The entry point selects:

- a platform port (`DATABRICKS_APP_PORT` or `PORT`) → **HTTP** only when
  `MCP_TRUSTED_HTTP_INGRESS=true`;
- `MCP_TRANSPORT=streamable-http` → HTTP on `MCP_HOST:MCP_PORT`;
- otherwise → **stdio**.

The server rejects platform ports and non-loopback binds by default. The
`MCP_TRUSTED_HTTP_INGRESS` setting is only an explicit operator assertion: it
does not add authentication or prove that the platform protects the endpoint.
Never enable it until the platform's authenticated ingress is verified and
direct unauthenticated access is blocked. An application login page or OAuth
redirect alone is not a complete MCP authorization test.

## IBM (three options, lowest → highest overhead)

See [`ibm/README.md`](ibm/README.md) for the full chooser. In short:

1. **[`ibm/local-mcp-toolkit/`](ibm/local-mcp-toolkit/)** — ship the code; run it
   over stdio **inside** Orchestrate. No HTTP, no container, no registry.
   **Lowest overhead — recommended for first-timers.**
2. **[`ibm/code-engine-git-build/`](ibm/code-engine-git-build/)** — Code Engine
   builds from your public Git repo and pushes to your Container Registry.
   Needs ICR authority.
3. **[`ibm/prebuilt-image/`](ibm/prebuilt-image/)** — deploy a prebuilt public
   image to Code Engine (or build from Git). Lowest cloud authority.

## Databricks

See [`databricks/README.md`](databricks/README.md). Deploy as a Databricks App:
the kit syncs your repo to the workspace and runs `databricks apps deploy`. The
server configuration explicitly acknowledges Databricks OAuth ingress. Verify
the route rejects unauthenticated access and cannot bypass that boundary before
deploying.

## cloud.gov (bonus)

Not a full kit, but the repo root includes a `manifest.yaml` for cloud.gov
(Cloud Foundry). Deploy with `cf push` after `cf login`/`cf target`. See the
comments in `manifest.yaml`.

---

## Security status

The MCP application has no built-in authentication or dataset authorization.
The Databricks kit documents a platform OAuth boundary that must be verified
from the deployed environment. The IBM Code Engine examples do not establish an
authenticated ingress and must not be used as public endpoints. None of these
examples demonstrates production readiness or agency authorization. See
[`SECURITY.md`](../SECURITY.md) for implemented controls and deployment gates.
Never commit secrets; deployment `.env` files are ignored and should contain
only non-secret coordinates.
