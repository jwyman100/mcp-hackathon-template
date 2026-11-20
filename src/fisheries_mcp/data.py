"""Read-only, parameterized access to the prepared public snapshot."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from fisheries_mcp.models import (
    INTERPRETATION,
    CatchYear,
    ComparisonRequest,
    ComparisonResult,
    CoverageResult,
    CoverageYear,
    Provenance,
    SearchRequest,
    SearchResult,
    Species,
    SpeciesSeries,
    SummaryRequest,
    SummaryResult,
    SurveyScope,
)
from fisheries_mcp.prepare import DataError

logger = logging.getLogger(__name__)


class SurveyStore:
    def __init__(self, path: Path):
        self.path = path.resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise DataError("Snapshot not found. Run fisheries-prepare first.")
        try:
            connection = sqlite3.connect(
                self.path.as_uri() + "?mode=ro", uri=True, timeout=5
            )
            try:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA query_only=ON")
                yield connection
            finally:
                connection.close()
        except sqlite3.Error:
            logger.error("Prepared snapshot failed a SQLite operation.")
            raise DataError(
                "Snapshot is unreadable or incompatible. "
                "Rebuild with fisheries-prepare."
            ) from None

    def provenance(self) -> Provenance:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key='provenance'"
            ).fetchone()
        try:
            if row is None:
                raise DataError("Snapshot provenance is missing.")
            result = Provenance.model_validate_json(row["value"])
        except ValidationError:
            raise DataError(
                "Snapshot provenance is invalid. Rebuild the snapshot."
            ) from None
        if result.schema_version != 1:
            raise DataError("Unsupported snapshot schema version.")
        return result

    def validate(self) -> None:
        self.provenance()
        with self.connect() as connection:
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise DataError("Snapshot integrity check failed.")
            for table, columns in {
                "cruises": "id, year",
                "stations": "id, cruise_id, stratum",
                "species": "code, common_name, scientific_name, published_label",
                "catches": "station_id, species_code, catch_sex, weight, number",
            }.items():
                connection.execute(f"SELECT {columns} FROM {table} LIMIT 0")

    def scope(self, request: SurveyScope) -> tuple[SurveyScope, Provenance]:
        provenance = self.provenance()
        if (
            request.start_year < provenance.start_year
            or request.end_year > provenance.end_year
        ):
            raise DataError(
                f"Snapshot covers {provenance.start_year}-{provenance.end_year}; "
                "out-of-snapshot years are not missing observations."
            )
        scope = SurveyScope.model_validate(
            request.model_dump(include=set(SurveyScope.model_fields))
        )
        return scope, provenance

    def species(self) -> list[Species]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM species ORDER BY code").fetchall()
        return [Species.model_validate(dict(row)) for row in rows]

    def search(self, request: SearchRequest) -> SearchResult:
        term = request.term.casefold()
        matches = [
            species
            for species in self.species()
            if term in species.common_name.casefold()
            or term in species.scientific_name.casefold()
        ]
        return SearchResult(
            species=matches,
            provenance=self.provenance(),
            note="Only species in this snapshot are searched. No match does not "
            "mean a species is absent from the full survey.",
        )

    def resolve(self, name: str) -> Species:
        matches = [
            species
            for species in self.species()
            if name.casefold()
            in {
                species.common_name.casefold(),
                species.scientific_name.casefold(),
                species.published_label.casefold(),
            }
        ]
        if len(matches) != 1:
            raise DataError(
                "Species name is unavailable or ambiguous in this snapshot. "
                "Call search_species and use an exact returned name."
            )
        return matches[0]

    @staticmethod
    def _parameters(scope: SurveyScope) -> tuple:
        return (
            scope.start_year,
            scope.end_year,
            scope.minimum_stratum,
            scope.maximum_stratum,
        )

    def coverage(self, request: SurveyScope) -> CoverageResult:
        scope, provenance = self.scope(request)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.year, COUNT(*) AS stations,
                       COUNT(DISTINCT c.id) AS cruises,
                       COUNT(DISTINCT s.stratum) AS strata
                FROM stations s JOIN cruises c ON c.id = s.cruise_id
                WHERE c.year BETWEEN ? AND ? AND s.stratum BETWEEN ? AND ?
                GROUP BY c.year
                """,
                self._parameters(scope),
            ).fetchall()
        by_year = {row["year"]: row for row in rows}
        annual = []
        for year in range(scope.start_year, scope.end_year + 1):
            row = by_year.get(year)
            annual.append(
                CoverageYear(
                    year=year,
                    station_records=row["stations"] if row else 0,
                    cruises=row["cruises"] if row else 0,
                    sampled_strata=row["strata"] if row else 0,
                    status="observed" if row else "no_station_records",
                )
            )
        return CoverageResult(
            scope=scope,
            annual_coverage=annual,
            provenance=provenance,
            interpretation=INTERPRETATION,
        )

    def catch_series(self, species: Species, scope: SurveyScope) -> SpeciesSeries:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.year, COUNT(*) AS records,
                       SUM(t.weight) AS weight, SUM(t.number) AS number,
                       COUNT(*) - COUNT(t.weight) AS unknown_weight,
                       COUNT(*) - COUNT(t.number) AS unknown_number
                FROM catches t JOIN stations s ON s.id = t.station_id
                JOIN cruises c ON c.id = s.cruise_id
                WHERE c.year BETWEEN ? AND ? AND s.stratum BETWEEN ? AND ?
                  AND t.species_code = ?
                GROUP BY c.year
                """,
                (*self._parameters(scope), species.code),
            ).fetchall()
        by_year = {row["year"]: row for row in rows}
        annual = []
        for year in range(scope.start_year, scope.end_year + 1):
            row = by_year.get(year)
            unknown_weight = row["unknown_weight"] if row else 0
            unknown_number = row["unknown_number"] if row else 0
            annual.append(
                CatchYear(
                    year=year,
                    catch_records=row["records"] if row else 0,
                    total_expanded_weight=(
                        row["weight"] if row and not unknown_weight else None
                    ),
                    total_expanded_number=(
                        row["number"] if row and not unknown_number else None
                    ),
                    known_expanded_weight=row["weight"] if row else None,
                    known_expanded_number=row["number"] if row else None,
                    unknown_weight_records=unknown_weight,
                    unknown_number_records=unknown_number,
                    status=(
                        "no_catch_records"
                        if row is None
                        else "incomplete_measurements"
                        if unknown_weight or unknown_number
                        else "observed"
                    ),
                )
            )
        return SpeciesSeries(species=species, annual_catch=annual)

    def summary(self, request: SummaryRequest) -> SummaryResult:
        coverage = self.coverage(request)
        species = self.resolve(request.species_name)
        return SummaryResult(
            **coverage.model_dump(), series=self.catch_series(species, coverage.scope)
        )

    def compare(self, request: ComparisonRequest) -> ComparisonResult:
        coverage = self.coverage(request)
        species = [self.resolve(name) for name in request.species_names]
        if len({item.code for item in species}) != len(species):
            raise DataError(
                "Comparison must contain distinct resolved species, not aliases."
            )
        series = [self.catch_series(item, coverage.scope) for item in species]
        matched = [
            year
            for index, year in enumerate(
                range(coverage.scope.start_year, coverage.scope.end_year + 1)
            )
            if all(item.annual_catch[index].status == "observed" for item in series)
        ]
        return ComparisonResult(
            **coverage.model_dump(), series=series, complete_matched_years=matched
        )

    def dictionary(self) -> dict:
        with self.connect() as connection:
            counts = connection.execute(
                "SELECT value FROM metadata WHERE key='row_counts'"
            ).fetchone()
        if counts is None:
            raise DataError("Snapshot row-count metadata is missing.")
        try:
            row_counts = json.loads(counts["value"])
        except json.JSONDecodeError:
            raise DataError("Snapshot row-count metadata is invalid.") from None
        return {
            "provenance": self.provenance().model_dump(),
            "row_counts": row_counts,
            "supported_analyses": [
                "Search published cod/haddock names in this selected snapshot.",
                "Summarize audited NEFSC spring expanded catch for 2021-2025.",
                "Compare Atlantic cod and haddock on matching years and strata.",
                "Report selected-scope station, cruise, and stratum coverage.",
                "Read curated NOAA report context for 2023 and 2025; the source "
                "statements are separate from the selected snapshot records.",
            ],
            "unsupported_analyses": [
                "Live/current survey data, unselected species, or another survey.",
                "Length composition, autumn estimates, and fall PARR exports.",
                "Official abundance indices, biomass, recruitment, fishing mortality, "
                "or stock status.",
                "Area-weighted or vessel-calibrated estimates, valid-tow filtering, "
                "or statistical uncertainty.",
            ],
            "fields": {
                "CRUISE6": "Six-character cruise ID; YEAR checked against its prefix.",
                "ID": "Unique station key; catch rows must join one station.",
                "STRATUM": "Five-character code; leading zeros preserved.",
                "SVSPP": "Three-character species code, not a row-level unique key.",
                "SCIENTIFIC_NAME": "Published combined scientific/common label.",
                "EXPCATCHWT": "Expanded catch weight; source units unspecified.",
                "EXPCATCHNUM": "Expanded number of individuals; may be fractional.",
                "CATCHSEX": "Sex category retained in the catch uniqueness key.",
            },
            "interpretation": INTERPRETATION,
        }
