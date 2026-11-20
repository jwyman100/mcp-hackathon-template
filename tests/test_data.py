import json
import sqlite3

import pytest
from pydantic import ValidationError

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.models import (
    ComparisonRequest,
    SearchRequest,
    SummaryRequest,
    SurveyScope,
)
from fisheries_mcp.prepare import DataError


def test_unknown_zero_and_absent_are_distinct(store):
    result = store.summary(SummaryRequest(species_name="Atlantic cod"))
    partial, complete, absent, zero, _ = result.series.annual_catch
    assert partial.total_expanded_weight is None
    assert partial.known_expanded_weight == 0
    assert partial.unknown_weight_records == 1
    assert partial.total_expanded_number == 2
    assert partial.status == "incomplete_measurements"
    assert complete.total_expanded_weight == 3.25
    assert complete.status == "observed"
    assert absent.catch_records == 0 and absent.total_expanded_weight is None
    assert absent.status == "no_catch_records"
    assert zero.total_expanded_weight == zero.total_expanded_number == 0
    assert zero.status == "observed"
    assert result.provenance.dataset_kind == "synthetic"


def test_all_unknown_measurements_remain_null(store):
    result = store.summary(SummaryRequest(species_name="haddock"))
    year = result.series.annual_catch[1]
    assert year.total_expanded_number is None
    assert year.known_expanded_number is None
    assert year.unknown_number_records == 1


def test_coverage_is_independent_of_species_catch(store):
    result = store.coverage(SurveyScope())
    assert [row.station_records for row in result.annual_coverage] == [2, 1, 0, 1, 0]
    assert result.annual_coverage[0].sampled_strata == 2
    assert result.annual_coverage[2].status == "no_station_records"
    scoped = store.coverage(SurveyScope(maximum_stratum="01130"))
    assert scoped.annual_coverage[0].station_records == 1


def test_comparison_resolves_identity_and_matches_only_complete_years(store):
    with pytest.raises(DataError, match="distinct resolved species"):
        store.compare(ComparisonRequest(species_names=["Atlantic cod", "Gadus morhua"]))
    result = store.compare(
        ComparisonRequest(
            species_names=["Atlantic cod", "haddock"],
            maximum_stratum="01130",
        )
    )
    assert result.complete_matched_years == [2021]
    assert len(result.series) == 2


@pytest.mark.parametrize("term", ["cod", "haddock"])
def test_published_search_label_is_an_exact_analysis_name(store, term):
    species = store.search(SearchRequest(term=term)).species[0]
    result = store.summary(SummaryRequest(species_name=species.published_label.upper()))
    assert result.series.species.code == species.code
    with pytest.raises(DataError, match="distinct resolved species"):
        store.compare(
            ComparisonRequest(
                species_names=[species.published_label, species.common_name]
            )
        )


def test_species_lookup_does_not_guess(store):
    assert store.search(SearchRequest(term="GADUS")).species[0].code == "073"
    assert store.search(SearchRequest(term="salmon")).species == []
    assert store.search(SearchRequest(term="%'")).species == []
    with pytest.raises(DataError, match="search_species"):
        store.summary(SummaryRequest(species_name="cod"))
    with pytest.raises(DataError, match="search_species"):
        store.summary(SummaryRequest(species_name="Gadus morhua (Atlantic cod) extra"))


def test_ambiguous_published_names_are_not_guessed(store, snapshot):
    with sqlite3.connect(snapshot) as connection:
        connection.execute("UPDATE species SET common_name='fish'")
    with pytest.raises(DataError, match="ambiguous"):
        store.resolve("fish")


def test_published_label_collision_is_not_guessed(store, snapshot):
    with sqlite3.connect(snapshot) as connection:
        connection.execute(
            "UPDATE species SET common_name="
            "(SELECT published_label FROM species WHERE code='073') WHERE code='074'"
        )
    with pytest.raises(DataError, match="ambiguous"):
        store.resolve("Gadus morhua (Atlantic cod)")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_stratum": "1130"},
        {"minimum_stratum": "01150", "maximum_stratum": "01130"},
        {"start_year": 2025, "end_year": 2021},
        {"start_year": 1968, "end_year": 2025},
        {"surprise": "parameter"},
    ],
)
def test_invalid_scope_rejected(kwargs):
    with pytest.raises(ValidationError):
        SurveyScope(**kwargs)


def test_outside_snapshot_is_not_a_missing_year(store):
    with pytest.raises(DataError, match="out-of-snapshot"):
        store.coverage(SurveyScope.model_construct(start_year=2020, end_year=2020))


def test_tool_schema_exposes_supported_years_and_comparison_scope():
    scope = SurveyScope.model_json_schema()
    assert scope["properties"]["start_year"]["minimum"] == 2021
    assert scope["properties"]["start_year"]["maximum"] == 2025
    year_description = scope["properties"]["start_year"]["description"].lower()
    assert "only years 2021-2025" in year_description
    comparison = ComparisonRequest.model_json_schema()["properties"]["species_names"]
    assert comparison["minItems"] == comparison["maxItems"] == 2
    assert "same species" in comparison["description"]


def test_connection_is_read_only(store):
    with pytest.raises(DataError, match="unreadable"):
        with store.connect() as connection:
            connection.execute("DELETE FROM catches")
    assert store.summary(
        SummaryRequest(species_name="Atlantic cod")
    ).series.annual_catch


def test_missing_corrupt_and_incompatible_snapshots_fail(tmp_path, snapshot):
    with pytest.raises(DataError, match="not found"):
        SurveyStore(tmp_path / "absent.sqlite").validate()
    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"not a database")
    with pytest.raises(DataError, match="unreadable"):
        SurveyStore(corrupt).validate()
    with sqlite3.connect(snapshot) as connection:
        value = json.loads(
            connection.execute(
                "SELECT value FROM metadata WHERE key='provenance'"
            ).fetchone()[0]
        )
        value["schema_version"] = 900
        connection.execute(
            "UPDATE metadata SET value=? WHERE key='provenance'", (json.dumps(value),)
        )
    with pytest.raises(DataError, match="schema version"):
        SurveyStore(snapshot).validate()
