import hashlib
import sqlite3

import pytest

from fisheries_mcp.prepare import DataError, build_snapshot, measurement
from tests.conftest import fixture_rows, write_archive


def test_import_preserves_ids_nulls_and_provenance(tmp_path):
    archive, output = tmp_path / "fixture.zip", tmp_path / "data.sqlite"
    digest = write_archive(archive, fixture_rows())
    result = build_snapshot(archive, output, expected_sha256=digest)
    assert result["provenance"]["source_sha256"] == digest
    assert result["row_counts"] == {
        "cruises": 5,
        "stations": 4,
        "species": 2,
        "catches": 6,
    }
    with sqlite3.connect(output) as connection:
        assert connection.execute(
            "SELECT stratum FROM stations WHERE id='a'"
        ).fetchone() == ("01130",)
        assert connection.execute(
            "SELECT weight FROM catches WHERE station_id='b'"
        ).fetchone() == (None,)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_station",
        "duplicate_catch",
        "orphan",
        "scope_mismatch",
        "conflicting_label",
        "bad_header",
        "bad_weight",
    ],
)
def test_import_rejects_ambiguity_atomically(tmp_path, snapshot, mutation):
    rows = fixture_rows()
    if mutation == "duplicate_station":
        rows["stations"].append(rows["stations"][0].copy())
    elif mutation == "duplicate_catch":
        rows["catches"].append(rows["catches"][0].copy())
    elif mutation == "orphan":
        rows["catches"][0]["ID"] = "missing"
    elif mutation == "scope_mismatch":
        rows["catches"][0]["STRATUM"] = "01150"
    elif mutation == "conflicting_label":
        rows["catches"][1]["SCIENTIFIC_NAME"] = "Gadus (changed)"
    elif mutation == "bad_header":
        for row in rows["stations"]:
            del row["STRATUM"]
    elif mutation == "bad_weight":
        rows["catches"][0]["EXPCATCHWT"] = "NaN"
    archive = tmp_path / "bad.zip"
    digest = write_archive(archive, rows)
    before = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    with pytest.raises(DataError):
        build_snapshot(archive, snapshot, expected_sha256=digest)
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == before
    assert not list(tmp_path.glob(".spring-*.sqlite"))


def test_changed_archive_requires_review(tmp_path):
    archive = tmp_path / "fixture.zip"
    write_archive(archive, fixture_rows())
    with pytest.raises(DataError, match="checksum"):
        build_snapshot(archive, tmp_path / "out.sqlite")
    assert not (tmp_path / "out.sqlite").exists()


@pytest.mark.parametrize("value", ["NaN", "inf", "-1", "not numeric"])
def test_invalid_measurements_are_not_silently_zero(value):
    with pytest.raises(DataError):
        measurement(value)
