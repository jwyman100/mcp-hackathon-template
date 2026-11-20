# Security and deployment policy

This repository is a public-data hackathon prototype, not an authorized
production service or an official NOAA or GSA product. The MCP server does not
implement user authentication, dataset authorization, or a tamper-resistant
audit trail. Do not connect it to internal Oracle data, credentials, or
non-public networks.

## Supported use

- The default transport is local stdio.
- Local HTTP is allowed only on a loopback address.
- A platform-provided port or non-loopback HTTP bind is rejected unless the
  operator explicitly sets `MCP_TRUSTED_HTTP_INGRESS=true`.
- That setting only acknowledges that the operator has verified an approved,
  authenticated ingress and that direct unauthenticated access is blocked. It
  does not add authentication or verify the ingress itself.
- Do not deploy publicly or use an unauthenticated hosted endpoint. Databricks
  Apps or other hosting environments require a separately verified,
  agency-approved authentication and network boundary before enabling the
  setting. IBM Code Engine examples are not approved production deployments.

The security posture is therefore local/demo only. Hosted deployment, agency
authorization, and production readiness have not been established.

## Implemented safeguards

- Runtime SQLite connections use read-only mode and `PRAGMA query_only=ON`.
- Queries are parameterized and request models bound query scope.
- Runtime tools make no outbound requests. The importer uses a fixed official
  source, disables redirects and environment proxies, and verifies a pinned
  archive hash and size bounds.
- The container uses pinned base/build image digests, installs from `uv.lock`,
  runs as a non-root user, and is exercised with a read-only filesystem and
  dropped Linux capabilities in CI.
- CI scans the repository history for secrets and audits locked runtime
  dependencies. Dependabot proposes updates for Python, actions, and container
  images; review and merge those updates deliberately.

Do not add a tool-supplied URL. If a future feature must fetch external URLs,
require exact destination allowlists, connection-time validation of resolved
IPv4/IPv6 addresses, validation at every redirect hop, credential stripping
across origins, and network-level egress controls. A DNS lookup followed by a
normal hostname request is vulnerable to DNS rebinding.

## Logs and data handling

Application error logs use fixed messages and omit tool arguments, query
strings, database rows, upstream response bodies, credentials, and stack traces.
The prototype does not produce authenticated or tamper-resistant audit records.
Do not process PII or sensitive data until retention, access control, and
approved audit storage are designed and authorized.

Treat tool arguments, retrieved content, and agent-to-agent messages as
untrusted. Never place secrets or internal records in issues, logs, receipts,
evaluation artifacts, or this repository.

## Dependency and release operations

Review Dependabot updates and resolve dependency-audit findings before release.
For each release candidate, run CI, inspect the generated container and its
runtime configuration, verify the approved ingress and unauthorized-access
rejection from the deployment boundary, and record the snapshot/image identity.
Update data only through the reviewed importer; retain the prior verified
snapshot and image for rollback.

If a credential or sensitive record is exposed, stop the affected service,
revoke exposed credentials, preserve relevant authorized logs, notify the
responsible maintainer through a private channel, and follow the agency's
incident process. Do not test NOAA or other external systems without written
authorization.

## Vulnerability reporting

Use the repository's private vulnerability reporting feature if it is enabled.
Otherwise, contact the repository maintainer through an available private
channel. Do not publish exploit details, credentials, or sensitive findings in
a public issue.

## Future internal-service requirements

Before any Oracle-backed or internal deployment, separately design and validate
SSO/token verification, per-user and per-tool data authorization, least-privilege
Oracle access, input/output guardrails, privacy-reviewed logging, protected
audit storage, incident response, and agency security authorization. SSO proves
identity; it does not by itself authorize access to a dataset.
