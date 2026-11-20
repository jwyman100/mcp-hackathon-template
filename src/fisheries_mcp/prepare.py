"""Build a bounded, reproducible SQLite snapshot from the official NOAA ZIP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sqlite3
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import httpx

from fisheries_mcp.models import Provenance

SOURCE_URL = (
    "https://storage.googleapis.com/nmfs_odp_nefsc/PARR/PEMAD/ESB/22561/"
    "22561_NEFSCSpringFisheriesIndependentBottomTrawlData.zip"
)
SOURCE_SHA256 = "f273e8bbb56dcf8360e7df065b94f8dabaa3f2ea89111807951dea77c3eb65fd"
METADATA_URL = "https://www.fisheries.noaa.gov/inport/item/22561"
START_YEAR, END_YEAR = 2021, 2025
SPECIES_CODES = ("073", "074")
FILES = {
    "cruises": "22561_SVDBS_CRUISES.csv",
    "stations": "22561_UNION_FSCS_SVSTA.csv",
    "catches": "22561_UNION_FSCS_SVCAT.csv",
}
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE cruises (id TEXT PRIMARY KEY, year INTEGER NOT NULL);
CREATE TABLE stations (
    id TEXT PRIMARY KEY, cruise_id TEXT NOT NULL REFERENCES cruises(id),
    stratum TEXT NOT NULL
);
CREATE TABLE species (
    code TEXT PRIMARY KEY, common_name TEXT NOT NULL,
    scientific_name TEXT NOT NULL, published_label TEXT NOT NULL
);
CREATE TABLE catches (
    station_id TEXT NOT NULL REFERENCES stations(id),
    species_code TEXT NOT NULL REFERENCES species(code),
    catch_sex TEXT NOT NULL, weight REAL, number REAL,
    UNIQUE(station_id, species_code, catch_sex)
);
CREATE INDEX station_scope ON stations(stratum, cruise_id);
CREATE INDEX catch_species ON catches(species_code, station_id);
"""


class DataError(ValueError):
    """A public input or prepared snapshot does not satisfy the data contract."""


def download_archive(destination: Path) -> None:
    """Only this pinned official source is downloadable; redirects are rejected."""
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", SOURCE_URL) as response:
            if response.status_code != 200:
                raise DataError(f"NOAA download returned HTTP {response.status_code}.")
            with destination.open("wb") as stream:
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 30_000_000:
                        raise DataError("NOAA download exceeds the pinned size limit.")
                    stream.write(chunk)


def read_rows(
    archive: zipfile.ZipFile, name: str, required: set[str]
) -> Iterator[dict[str, str]]:
    if archive.namelist().count(name) != 1:
        raise DataError(f"Expected exactly one archive member: {name}.")
    if archive.getinfo(name).file_size > 50_000_000:
        raise DataError(f"Archive member exceeds the size limit: {name}.")
    # The pinned export includes non-UTF-8 comment bytes. Comments are not imported.
    with archive.open(name) as raw:
        with io.TextIOWrapper(raw, encoding="latin-1", newline="") as text:
            reader = csv.DictReader(text)
            fields = reader.fieldnames or []
            if len(set(fields)) != len(fields) or not required.issubset(fields):
                raise DataError(f"Incompatible CSV header in {name}.")
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise DataError(f"Malformed CSV row in {name}.")
                yield {key: value.strip() for key, value in row.items()}


def measurement(value: str) -> float | None:
    if not value:
        return None
    try:
        result = float(value)
    except ValueError:
        raise DataError("A catch measurement is not numeric.") from None
    if not math.isfinite(result) or result < 0:
        raise DataError("Catch measurements must be finite and nonnegative.")
    return result


def build_snapshot(
    archive_path: Path, output: Path, *, expected_sha256: str = SOURCE_SHA256
) -> dict:
    with archive_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected_sha256:
        raise DataError(
            "Archive checksum differs from the reviewed snapshot. Do not override "
            "the pin without reviewing the new data contract."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".spring-", suffix=".sqlite", dir=output.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            connection = sqlite3.connect(temporary)
            try:
                connection.executescript(SCHEMA)
                _import_rows(connection, archive)
                counts = {
                    table: connection.execute(
                        f"SELECT COUNT(*) FROM {table}"  # operator-owned table names
                    ).fetchone()[0]
                    for table in ("cruises", "stations", "species", "catches")
                }
                if any(value == 0 for value in counts.values()):
                    raise DataError(
                        "The selected public slice contains an empty table."
                    )
                provenance = Provenance(
                    dataset_kind="public",
                    title="NOAA NEFSC public spring survey: cod/haddock, 2021-2025",
                    source_url=SOURCE_URL,
                    metadata_url=METADATA_URL,
                    source_sha256=digest,
                    extracted_on="2026-06-25",
                    schema_version=1,
                    start_year=START_YEAR,
                    end_year=END_YEAR,
                    species_codes=list(SPECIES_CODES),
                    weight_unit="source units; unspecified in linked public metadata",
                    selection=(
                        "SPRING; PURPOSE_CODE=10; cruise/station/catch STATUS_CODE=10; "
                        "years 2021-2025; all published station strata; "
                        "catch SVSPP 073 and 074; no haul/gear validity filtering"
                    ),
                )
                for key, value in {
                    "provenance": provenance.model_dump(),
                    "row_counts": counts,
                }.items():
                    connection.execute(
                        "INSERT INTO metadata VALUES (?, ?)", (key, json.dumps(value))
                    )
                connection.commit()
                if connection.execute("PRAGMA foreign_key_check").fetchone():
                    raise DataError("Snapshot contains orphan records.")
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise DataError("Snapshot failed SQLite integrity checks.")
            finally:
                connection.close()
        os.replace(temporary, output)
        return {"provenance": provenance.model_dump(), "row_counts": counts}
    except (sqlite3.Error, zipfile.BadZipFile, KeyError) as error:
        raise DataError(
            f"Snapshot import failed ({type(error).__name__}); check public input "
            "keys and structure. The previous snapshot was not replaced."
        ) from error
    finally:
        temporary.unlink(missing_ok=True)


def _import_rows(connection: sqlite3.Connection, archive: zipfile.ZipFile) -> None:
    cruises: set[str] = set()
    for row in read_rows(
        archive,
        FILES["cruises"],
        {"CRUISE6", "YEAR", "SEASON", "PURPOSE_CODE", "STATUS_CODE"},
    ):
        if not re.fullmatch(r"[0-9]{4}", row["YEAR"]):
            raise DataError("Invalid cruise year.")
        if not START_YEAR <= int(row["YEAR"]) <= END_YEAR:
            continue
        if (row["SEASON"], row["PURPOSE_CODE"], row["STATUS_CODE"]) != (
            "SPRING",
            "10",
            "10",
        ):
            continue
        cruise = row["CRUISE6"]
        if not re.fullmatch(r"[0-9]{6}", cruise) or cruise[:4] != row["YEAR"]:
            raise DataError("Cruise identifier and year disagree.")
        connection.execute("INSERT INTO cruises VALUES (?, ?)", (cruise, row["YEAR"]))
        cruises.add(cruise)

    stations: dict[str, tuple[str, str]] = {}
    for row in read_rows(
        archive, FILES["stations"], {"ID", "CRUISE6", "STRATUM", "STATUS_CODE"}
    ):
        if row["CRUISE6"] not in cruises or row["STATUS_CODE"] != "10":
            continue
        if not row["ID"] or not re.fullmatch(r"[0-9]{5}", row["STRATUM"]):
            raise DataError("Invalid station identifier or stratum.")
        connection.execute(
            "INSERT INTO stations VALUES (?, ?, ?)",
            (row["ID"], row["CRUISE6"], row["STRATUM"]),
        )
        stations[row["ID"]] = (row["CRUISE6"], row["STRATUM"])

    labels: dict[str, str] = {}
    for row in read_rows(
        archive,
        FILES["catches"],
        {
            "ID",
            "CRUISE6",
            "STRATUM",
            "SVSPP",
            "CATCHSEX",
            "EXPCATCHWT",
            "EXPCATCHNUM",
            "SCIENTIFIC_NAME",
            "STATUS_CODE",
        },
    ):
        code = row["SVSPP"]
        if (
            row["CRUISE6"] not in cruises
            or code not in SPECIES_CODES
            or row["STATUS_CODE"] != "10"
        ):
            continue
        if stations.get(row["ID"]) != (row["CRUISE6"], row["STRATUM"]):
            raise DataError("Selected catch has no matching station/scope.")
        label = row["SCIENTIFIC_NAME"]
        if code in labels and labels[code] != label:
            raise DataError("Multiple published labels for a selected species code.")
        if code not in labels:
            match = re.fullmatch(r"([^()]+) \(([^()]+)\)", label)
            if match is None:
                raise DataError("Selected species label lacks unambiguous names.")
            scientific, common = match.groups()
            connection.execute(
                "INSERT INTO species VALUES (?, ?, ?, ?)",
                (code, common.strip(), scientific.strip(), label),
            )
            labels[code] = label
        connection.execute(
            "INSERT INTO catches VALUES (?, ?, ?, ?, ?)",
            (
                row["ID"],
                code,
                row["CATCHSEX"],
                measurement(row["EXPCATCHWT"]),
                measurement(row["EXPCATCHNUM"]),
            ),
        )
    if set(labels) != set(SPECIES_CODES):
        raise DataError("The snapshot must contain both selected species.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path)
    source.add_argument("--download", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/spring.sqlite"))
    args = parser.parse_args()
    try:
        if args.download:
            with tempfile.TemporaryDirectory(prefix="fisheries-public-") as folder:
                archive = Path(folder) / "spring.zip"
                download_archive(archive)
                report = build_snapshot(archive, args.output)
        else:
            report = build_snapshot(args.archive, args.output)
    except (DataError, OSError, httpx.HTTPError) as error:
        parser.exit(1, f"Preparation failed: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
