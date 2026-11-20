"""Agent-visible requests, results, and scientific interpretation contracts."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Stratum = Annotated[str, Field(pattern=r"^[0-9]{5}$")]
Name = Annotated[str, Field(min_length=2, max_length=120)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchRequest(Contract):
    term: Name = Field(
        description=(
            "Partial published common or scientific name. This fixed snapshot "
            "contains Atlantic cod and haddock only; search results are not a "
            "complete SVDBS species catalog."
        )
    )


class SurveyScope(Contract):
    start_year: int = Field(
        default=2021,
        ge=2021,
        le=2025,
        description="Inclusive start year. Only years 2021-2025 are in this snapshot.",
    )
    end_year: int = Field(
        default=2025,
        ge=2021,
        le=2025,
        description="Inclusive end year. Only years 2021-2025 are in this snapshot.",
    )
    minimum_stratum: Stratum = Field(
        default="00000",
        description="Inclusive lower five-digit stratum code; default includes all.",
    )
    maximum_stratum: Stratum = Field(
        default="99999",
        description="Inclusive upper five-digit stratum code; default includes all.",
    )

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_year < self.start_year:
            raise ValueError("end_year must be on or after start_year.")
        if self.minimum_stratum > self.maximum_stratum:
            raise ValueError("minimum_stratum must not exceed maximum_stratum.")
        return self


class SummaryRequest(SurveyScope):
    species_name: Name = Field(
        description=(
            "Exact common name, scientific name, or published label returned by "
            "search_species for Atlantic cod or haddock."
        )
    )


class ComparisonRequest(SurveyScope):
    species_names: list[Name] = Field(
        min_length=2,
        max_length=2,
        description=(
            "Two distinct species from this snapshot. Aliases resolving to the "
            "same species are rejected."
        ),
    )


class ReportContextRequest(Contract):
    year: Literal[2023, 2025] = Field(
        description="Year of the curated NOAA report context: 2023 or 2025."
    )


class ReportSource(Contract):
    title: str
    url: str
    locator: str
    source_checked_on: str
    scientific_review_status: Literal["not_reviewed"] = Field(
        description="This source card has not received independent scientific review."
    )


class ReportContextResult(Contract):
    year: Literal[2023, 2025]
    source: ReportSource
    facts: list[str] = Field(description="Manually curated statements from the source.")
    limitations: list[str]


class Species(Contract):
    code: str = Field(description="Published three-digit SVSPP code.")
    common_name: str = Field(description="Common name parsed from published label.")
    scientific_name: str = Field(
        description="Scientific name parsed from published label."
    )
    published_label: str = Field(description="Original label published in catch rows.")


class Provenance(Contract):
    dataset_kind: Literal["public", "synthetic"] = Field(
        description="Distinguishes the public snapshot from invented test fixtures."
    )
    title: str
    source_url: str
    metadata_url: str
    source_sha256: str
    extracted_on: str
    schema_version: int
    start_year: int
    end_year: int
    species_codes: list[str]
    weight_unit: str = Field(
        description="Public metadata does not specify EXPCATCHWT units."
    )
    selection: str


class CoverageYear(Contract):
    year: int
    station_records: int = Field(
        description="Number of public station records; not necessarily valid tows."
    )
    cruises: int
    sampled_strata: int = Field(
        description="Distinct selected stratum codes, not a measure of area."
    )
    status: Literal["observed", "no_station_records"] = Field(
        description="No selected station records does not establish no survey effort."
    )


class CatchYear(Contract):
    year: int
    catch_records: int = Field(description="Published rows for the selected species.")
    total_expanded_weight: float | None = Field(
        description=(
            "Complete expanded weight total in unspecified source units; null if "
            "records are absent or any weight measurement is unknown."
        )
    )
    total_expanded_number: float | None = Field(
        description=(
            "Complete expanded individual count; null if records are absent or "
            "any number measurement is unknown."
        )
    )
    known_expanded_weight: float | None = Field(
        description=(
            "Subtotal of available weights, not a complete total if unknowns exist."
        )
    )
    known_expanded_number: float | None = Field(
        description=(
            "Subtotal of available numbers, not a complete total if unknowns exist."
        )
    )
    unknown_weight_records: int = Field(
        description="Selected catch rows with no expanded weight measurement."
    )
    unknown_number_records: int = Field(
        description="Selected catch rows with no expanded number measurement."
    )
    status: Literal["observed", "incomplete_measurements", "no_catch_records"] = Field(
        description=(
            "No catch rows means unknown, not observed zero. Compare station "
            "coverage separately."
        )
    )


class SearchResult(Contract):
    species: list[Species]
    provenance: Provenance
    note: str


class CoverageResult(Contract):
    scope: SurveyScope
    annual_coverage: list[CoverageYear]
    provenance: Provenance
    interpretation: list[str]


class SpeciesSeries(Contract):
    species: Species
    annual_catch: list[CatchYear]


class SummaryResult(CoverageResult):
    series: SpeciesSeries


class ComparisonResult(CoverageResult):
    series: list[SpeciesSeries]
    complete_matched_years: list[int]


INTERPRETATION = [
    "These are published expanded catch totals, not population abundance estimates.",
    "Coverage counts station records, not effort-standardized or valid-haul counts.",
    "No haul/gear validity, stratum-area weighting, or vessel calibration is applied.",
    "Missing catch rows are unknown, not observed zero; absent species rows do not "
    "establish zero-catch tows.",
    "No selected station records do not establish that no survey effort occurred.",
    "A count of sampled strata is not a measure or percentage of geographic area.",
    "If any measurement is unknown, its annual total is null; known subtotals are "
    "reported separately.",
    "EXPCATCHWT units are unspecified in the linked public metadata; do not assume "
    "a unit or conversion without an authoritative reference.",
    "The fixed public snapshot is not live or a complete species catalog.",
]
