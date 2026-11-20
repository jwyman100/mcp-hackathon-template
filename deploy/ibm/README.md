# IBM watsonx Orchestrate — Deployment Kits

Three self-contained kits get your MCP server into **watsonx Orchestrate**,
ordered from lowest to highest infrastructure overhead. Pick one.

| Kit | Transport / where it runs | Infra needed | Best for |
|---|---|---|---|
| **[`local-mcp-toolkit/`](local-mcp-toolkit/)** | **stdio, inside Orchestrate** | **None** (ADK + repo) | Novices; fastest path; no cloud account plumbing |
| **[`code-engine-git-build/`](code-engine-git-build/)** | streamable-HTTP on IBM Code Engine (built from your Git repo) | Code Engine + IBM Container Registry | The "point Code Engine at your repo and go" flow |
| **[`prebuilt-image/`](prebuilt-image/)** | streamable-HTTP on IBM Code Engine (prebuilt public image) | Code Engine + a public image (e.g. GHCR) | Lowest cloud authority; no ICR access needed |

## Which should I use?

- **Just want it working with the least setup?** → `local-mcp-toolkit/`. It reuses
  your server code unchanged and runs it over stdio inside Orchestrate — no HTTP,
  no container, no registry.
- **Want a real hosted HTTP endpoint and your account has Container Registry
  authority?** → `code-engine-git-build/`. Code Engine builds from your public
  repo and pushes to your ICR namespace.
- **Your account lacks registry authority, or you already have a public image?**
  → `prebuilt-image/`. Deploys a prebuilt public image directly (e.g. from GHCR).
  No ICR access required.

All three end the same way: **register the server in Orchestrate → build an agent
that uses its tools**. The two Code Engine kits produce a public `/mcp` URL you
register as a *remote* toolkit; the local kit ships the code and runs it as a
*local* toolkit.

## Prerequisites common to all kits

- A watsonx Orchestrate SaaS instance (URL + API key from the wxO service page in
  IBM Cloud).
- The Orchestrate ADK for scripted registration:
  `pip install --upgrade ibm-watsonx-orchestrate` (Python 3.11–3.14).
- For the Code Engine kits: the IBM Cloud CLI + `code-engine` plugin, and a paid
  (or trial-upgraded) account — the free "Lite" tier cannot create Code Engine
  projects.

Each kit's `README.md` has the full runbook, a `.env.example` (no secrets), and
idempotent scripts.

> **Security note:** the MCP application has no built-in authentication. The
> Code Engine kits do not establish an authenticated ingress and are not
> approved as public endpoints. The server refuses platform-injected ports
> unless `MCP_TRUSTED_HTTP_INGRESS=true` is explicitly supplied; that setting
> is an operator assertion, not an authentication mechanism. Use the local
> stdio kit for this prototype. Do not enable the setting for Code Engine
> without a separately verified, approved authenticated ingress.
