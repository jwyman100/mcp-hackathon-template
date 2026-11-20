# Provisional scientific schema contract

This example shows how the public prototype could turn a dataset field into an
explicit, testable analysis contract. It is an engineering draft, **not an
expert-approved fisheries definition**, an enterprise Oracle schema, or a
production authorization policy.

## Example: annual expanded catch weight

| Contract element | Provisional definition |
| --- | --- |
| Scientific question | What expanded catch weight is recorded for one species in one spring-survey year? |
| Population/survey scope | NOAA NEFSC spring bottom-trawl survey in the public 2021-2025 snapshot |
| Analysis grain | Species and year, after the selected status/purpose filters |
| Input identity | One species resolved from the public labels and code |
| Measure | Sum of published `EXPCATCHWT` values for selected catch rows |
| Unit | Unspecified by the linked public field metadata; retain as “source units” |
| Missingness | No catch rows, unknown measurements, and a measured zero are distinct states |
| Coverage context | Station-record count, cruise count, and sampled-stratum count; these are not effort standardization or geographic area |
| Supported conclusion | The selected rows contain the reported expanded total and coverage counts |
| Unsupported conclusion | Population abundance/trend, a weight-unit conversion, valid-haul equivalence, or geographic-area coverage |
| Evidence and version | Public-source URLs, archive SHA-256, server-source hashes, database SHA-256, and MCP call/result receipt |
| Review state | `not_reviewed`; source verification does not mean scientific approval |

The public source references are NOAA's [spring survey metadata
(InPort 22561)](https://www.fisheries.noaa.gov/inport/item/22561), [catch
fields (InPort 33608)](https://www.fisheries.noaa.gov/inport/item/33608), and
[station fields (InPort 33610)](https://www.fisheries.noaa.gov/inport/item/33610).
The metadata linked for the public snapshot does not establish a unit for
`EXPCATCHWT`. This contract deliberately preserves that unknown rather than
guessing.

## What scientists would decide

For each schema or analysis, domain experts would confirm the intended
population, sampling design, join keys, eligibility filters, aggregation grain,
units, missingness, and valid interpretations. If those semantics cannot be
supported from authoritative sources, the tool should expose the uncertainty
and narrow its answer rather than silently filling the gap.

## Proposed contract lifecycle

1. **Draft:** Data and engineering staff record candidate fields, provenance,
   filters, and unresolved questions.
2. **Expert review:** A relevant scientist confirms or revises the scientific
   meanings, scope, and permitted interpretations.
3. **Versioned implementation:** The accepted contract is versioned alongside
   the tool schema and executable tests.
4. **Regression and release review:** Synthetic edge cases and independent
   source calculations verify the implemented behavior; changes retain a
   receipt tying outputs to the source, database, and server revision.
5. **Re-review on change:** Source, schema, filter, or methodology changes
   return the affected contract to review.

This lifecycle is a proposed governance pattern, not a feature currently
implemented in the server. No expert approval, automated preflight gate, SSO,
per-tool authorization, audit service, FISMA authorization, or production
deployment is claimed. In a future enterprise deployment, identity verification
would be separate from authorization to each dataset and operation.
