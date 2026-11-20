# C: representative-haul catch reproduction - feasibility findings

The full representative-haul reconciliation has not been frozen or run. Do
not include the exploratory sums below in benchmark accuracy or pass-rate
claims. A separate [C01 preflight](benchmark-c.json) tests the existing tools'
available all-snapshot results and their inability to complete that comparison.

## Public evidence

Source: [NOAA 2025 Spring Resource Survey Report](https://repository.library.noaa.gov/view/noaa/72382),
[DOI](https://doi.org/10.25923/zv6b-t597).
The downloaded PDF matches its published SHA-512:
`0d4bd7f1bd7e78227eac7ea3406e0242859b9ece3c97c6e0066df5440b69a8dff1c56fd98c1c0fd09d20398233080c8f4eac0957fa6883a3feba68599b10f1c0`.

| Item | Finding |
|---|---|
| Table 1, physical PDF pages 9-23 | 370 unique representative-station entries |
| Pinned 2025 archive | All 370 report station numbers occur once among 395 station records; the other 25 archive station numbers are not in Table 1 |
| Table 3, physical PDF pages 29-45 | 364 unique catch-table station rows; every row is in Table 1 |
| Table 1 stations without extracted Table 3 rows | 17, 19, 21, 25, 266, 304 |
| Table 3 stations outside Table 1 | None |
| Sum of printed Table 3 Atlantic cod values | 868.8 lb |
| Sum of printed Table 3 haddock values | 4,869.4 lb |

The Table 3 caption specifies pounds and representative hauls. Xpdf's `-table`
and `-raw` text modes agree on all 364 rows, each with 24 numeric fields after
the station identifier. Those are two extraction modes of the same PDF, not
independent scientific corroboration. A separate exact station-number
crosswalk against the pinned NOAA ZIP matched all 370 Table 1 entries to
distinct archive station rows, and the remaining 25 rows were outside Table 1.
This confirms the aggregate split at the station-number level for this report
and snapshot; it does not prove that the two sources are otherwise identical.

The six Table 1 stations omitted from Table 3 do have catch rows in the ZIP
(3-8 rows per station), but no Atlantic cod (SVSPP 073) or haddock (074) rows.
That suggests their absence does not remove cod/haddock catch from a target-
species total, but it does not document NOAA's Table 3 inclusion rule. The
printed-row sums use Decimal arithmetic on one-decimal values, not unrounded
report calculations.

Summing cod/haddock archive weights for the 370 crosswalked representative
station numbers and multiplying by a candidate factor of 2.20462262185 gives
868.9079 and 4,869.8769, respectively, versus printed sums of 868.8 and
4,869.4 lb. At one decimal place, 360/364 cod and 359/364 haddock rows match
using that factor; the remaining rows differ by 0.1. These are strong
numerical clues, **not an authoritative unit conversion**: NOAA InPort
describes `EXPCATCHWT` as expanded catch weight but does not state its unit.
The multiplier, data-version correspondence, and small discrepancies still
need owner review. The calculation is reproducible with the session artifact
`check_noaa_c.py`; its machine-readable output is `noaa-c-feasibility.json`.

The public MCP server has neither the report table nor a representative-haul
filter. Do not add a generic report/SQL tool or freeze totals before reviewing
the table inclusion and unit semantics.

## Full-reconciliation limitation

The originally selected course was full reconciliation and scientific
clarification. The report station list and public archive station numbers now
crosswalk exactly, but the six omitted Table 3 rows, the relationship between
the archive's weight units and the report's pounds, and the remaining rounded
differences are unresolved. Scientific review was not performed.

The separate C01 preflight does not replace or complete that reconciliation.
It asks the agent to retrieve all-snapshot catch and coverage and identify the
limitations; report-table totals are not supplied to the agent. Do not present
the preflight as reproduction of the representative-haul totals.

## Suggested scientific-review request

In NOAA's 2025 Spring Resource Survey Report (DOI 10.25923/zv6b-t597), Table 1
lists 370 representative station numbers and Table 3 lists 364 of them. A
crosswalk against the public InPort 22561 spring archive matches all 370 Table 1
numbers to unique 2025 station rows; the other 25 archive station rows are not
in Table 1. Stations 17, 19, 21, 25, 266 and 304 have no Table 3 row. They do
have catch records in the ZIP, but no cod or haddock rows. Does Table 3
intentionally omit hauls without one of its listed species, despite the
"Other"/"Total" columns? Does the public archive contain the same underlying
catch version used for the report? The Table 3 cod/haddock row sums are 868.8
lb/4,869.4 lb. The corresponding selected archive sums, multiplied by
2.20462262185, are 868.9079/4,869.8769, with some per-row 0.1-lb differences
after rounding. Can NOAA confirm the authoritative `EXPCATCHWT` unit,
conversion and rounding rules, and advise the correct reproducible comparison?

No external request has been sent. C01 preflight can run without this
clarification, but does not resolve these questions. The extraction script and
JSON output are retained in the session as `check_noaa_c.py` and
`noaa-c-feasibility.json`.
