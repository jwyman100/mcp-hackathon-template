# Public demonstration snapshot

`spring.sqlite` is generated from the NOAA public archive linked at
https://www.fisheries.noaa.gov/inport/item/22561, not from an internal database.

- Source extraction: June 25, 2026.
- Source ZIP SHA-256:
  `f273e8bbb56dcf8360e7df065b94f8dabaa3f2ea89111807951dea77c3eb65fd`.
- Selection: audited spring cruises/stations/catches, 2021-2025; species 073
  (Atlantic cod) and 074 (haddock); all published station strata.
- Tables: 5 cruises, 1,570 stations, 2 species, 758 catch rows, plus provenance.
- Retained fields: cruise/year, station ID/stratum, published species labels,
  catch sex, expanded weight/number. No comments, locations, or biology records.
- Species names are parsed from the selected public `SCIENTIFIC_NAME` values,
  not asserted to be a complete authoritative taxonomy catalog.
- Duplicate selected station/catch keys and conflicting names fail import.
- `EXPCATCHWT` unit is not stated in the linked public field metadata. No unit
  conversion or kg labeling is performed.

Rebuild with `uv run fisheries-prepare --download`. Review any upstream checksum
change before altering the pin. The extraction date is not a promise that all
observations have equal completeness or scientific suitability.

Please acknowledge NOAA/NMFS/NEFSC and read the source metadata/use constraints.
The included file is a demonstration subset, not an official data release of
this project or an official stock assessment product.
