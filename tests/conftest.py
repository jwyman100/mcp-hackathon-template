"""Invented fixtures; no source database records or credentials."""

import csv
import hashlib
import io
import json
import sqlite3
import zipfile

import pytest

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.prepare import FILES, build_snapshot


def fixture_rows():
    return {
        "cruises": [
            {
                "CRUISE6": f"{year}02",
                "YEAR": str(year),
                "SEASON": "SPRING",
                "PURPOSE_CODE": "10",
                "STATUS_CODE": "10",
            }
            for year in (2021, 2022, 2023, 2024, 2025)
        ],
        "stations": [
            {
                "ID": station,
                "CRUISE6": f"{year}02",
                "STRATUM": stratum,
                "STATUS_CODE": "10",
            }
            for station, year, stratum in (
                ("a", 2021, "01130"),
                ("b", 2021, "01140"),
                ("c", 2022, "01130"),
                ("d", 2024, "01130"),
            )
        ],
        "catches": [
            {
                "ID": station,
                "CRUISE6": f"{year}02",
                "STRATUM": stratum,
                "SVSPP": code,
                "CATCHSEX": "0",
                "EXPCATCHWT": weight,
                "EXPCATCHNUM": number,
                "SCIENTIFIC_NAME": label,
                "STATUS_CODE": "10",
            }
            for station, year, stratum, code, weight, number, label in (
                ("a", 2021, "01130", "073", "0", "0", "Gadus morhua (Atlantic cod)"),
                ("b", 2021, "01140", "073", "", "2", "Gadus morhua (Atlantic cod)"),
                ("c", 2022, "01130", "073", "3.25", "2", "Gadus morhua (Atlantic cod)"),
                ("d", 2024, "01130", "073", "0", "0", "Gadus morhua (Atlantic cod)"),
                (
                    "a",
                    2021,
                    "01130",
                    "074",
                    "5",
                    "4",
                    "Melanogrammus aeglefinus (haddock)",
                ),
                (
                    "c",
                    2022,
                    "01130",
                    "074",
                    "",
                    "",
                    "Melanogrammus aeglefinus (haddock)",
                ),
            )
        ],
    }


def write_archive(path, rows):
    with zipfile.ZipFile(path, "w") as archive:
        for table, records in rows.items():
            text = io.StringIO(newline="")
            writer = csv.DictWriter(text, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
            archive.writestr(FILES[table], text.getvalue().encode("latin-1"))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def snapshot(tmp_path):
    archive, database = tmp_path / "invented.zip", tmp_path / "invented.sqlite"
    digest = write_archive(archive, fixture_rows())
    build_snapshot(archive, database, expected_sha256=digest)
    with sqlite3.connect(database) as connection:
        raw = connection.execute(
            "SELECT value FROM metadata WHERE key='provenance'"
        ).fetchone()[0]
        provenance = json.loads(raw)
        provenance.update(
            dataset_kind="synthetic",
            title="Invented test fixture",
            source_url="urn:synthetic:test",
            metadata_url="urn:synthetic:test",
            extracted_on="not applicable",
        )
        connection.execute(
            "UPDATE metadata SET value=? WHERE key='provenance'",
            (json.dumps(provenance),),
        )
    return database


@pytest.fixture
def store(snapshot):
    return SurveyStore(snapshot)
