"""Reconcile real MCP calls with independent raw-CSV/Decimal calculations.

This is a scripted integration benchmark, NOT an LLM/agent evaluation.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import math
import os
import platform
import statistics
import sys
import time
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError
from jsonschema import validate
from jsonschema.exceptions import ValidationError as SchemaError

EXPECTED_ARCHIVE_SHA = (
    "f273e8bbb56dcf8360e7df065b94f8dabaa3f2ea89111807951dea77c3eb65fd"
)
ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def server_source_hashes() -> dict[str, str]:
    package = ROOT / "src" / "fisheries_mcp"
    return {
        path.relative_to(ROOT).as_posix(): file_sha256(path)
        for path in sorted(package.rglob("*.py"))
    }


class Reference:
    """Independent aggregation: no application models, queries, or importer code."""

    def __init__(self, archive_path: Path):
        digest = file_sha256(archive_path)
        if digest != EXPECTED_ARCHIVE_SHA:
            raise ValueError("Reference archive is not the reviewed public snapshot.")
        self.sha256 = digest
        with zipfile.ZipFile(archive_path) as archive:

            def records(name):
                with archive.open(name) as raw:
                    with io.TextIOWrapper(raw, encoding="latin-1", newline="") as text:
                        yield from csv.DictReader(text)

            self.cruises = {
                row["CRUISE6"]: int(row["YEAR"])
                for row in records("22561_SVDBS_CRUISES.csv")
                if row["SEASON"] == "SPRING"
                and row["PURPOSE_CODE"] == "10"
                and row["STATUS_CODE"] == "10"
                and 2021 <= int(row["YEAR"]) <= 2025
            }
            self.stations = {
                row["ID"]: row
                for row in records("22561_UNION_FSCS_SVSTA.csv")
                if row["CRUISE6"] in self.cruises and row["STATUS_CODE"] == "10"
            }
            self.catches = [
                row
                for row in records("22561_UNION_FSCS_SVCAT.csv")
                if row["CRUISE6"] in self.cruises
                and row["STATUS_CODE"] == "10"
                and row["SVSPP"] in {"073", "074"}
            ]
        self.names = {
            "Atlantic cod": "073",
            "Gadus morhua": "073",
            "haddock": "074",
            "Melanogrammus aeglefinus": "074",
        }

    def selected_stations(self, request: dict, year: int) -> dict:
        return {
            key: row
            for key, row in self.stations.items()
            if self.cruises[row["CRUISE6"]] == year
            and request.get("minimum_stratum", "00000")
            <= row["STRATUM"]
            <= request.get("maximum_stratum", "99999")
        }

    def coverage(self, request: dict) -> list[dict]:
        result = []
        for year in range(
            request.get("start_year", 2021), request.get("end_year", 2025) + 1
        ):
            rows = list(self.selected_stations(request, year).values())
            result.append(
                {
                    "year": year,
                    "station_records": len(rows),
                    "cruises": len({row["CRUISE6"] for row in rows}),
                    "sampled_strata": len({row["STRATUM"] for row in rows}),
                    "status": "observed" if rows else "no_station_records",
                }
            )
        return result

    def series(self, request: dict, code: str) -> list[dict]:
        result = []
        for year in range(
            request.get("start_year", 2021), request.get("end_year", 2025) + 1
        ):
            stations = self.selected_stations(request, year)
            rows = [
                row
                for row in self.catches
                if row["SVSPP"] == code and row["ID"] in stations
            ]
            values = {}
            for source, field in (("EXPCATCHWT", "weight"), ("EXPCATCHNUM", "number")):
                known = [Decimal(row[source]) for row in rows if row[source].strip()]
                total = float(sum(known)) if known else None
                unknown = len(rows) - len(known)
                values.update(
                    {
                        f"known_expanded_{field}": total,
                        f"total_expanded_{field}": total if not unknown else None,
                        f"unknown_{field}_records": unknown,
                    }
                )
            incomplete = (
                values["unknown_weight_records"] or values["unknown_number_records"]
            )
            result.append(
                {
                    "year": year,
                    "catch_records": len(rows),
                    **values,
                    "status": "no_catch_records"
                    if not rows
                    else "incomplete_measurements"
                    if incomplete
                    else "observed",
                }
            )
        return result


def assert_equivalent(actual, expected, path="result"):
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert key in actual, f"{path}.{key} missing"
            assert_equivalent(actual[key], value, f"{path}.{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), f"{path} length"
        for index, value in enumerate(expected):
            assert_equivalent(actual[index], value, f"{path}[{index}]")
    elif isinstance(expected, float):
        assert isinstance(actual, (int, float)) and math.isclose(
            actual, expected, rel_tol=1e-10, abs_tol=1e-8
        ), f"{path}: {actual} != {expected}"
    else:
        assert actual == expected, f"{path}: {actual} != {expected}"


def check_result(case, result, reference):
    request = case["request"]
    provenance = result["provenance"]
    assert provenance["source_sha256"] == reference.sha256
    assert provenance["dataset_kind"] == "public"
    if case["check"] == "search":
        assert [row["code"] for row in result["species"]] == case["expected_codes"]
        assert "full survey" in result["note"]
        return
    assert_equivalent(result["annual_coverage"], reference.coverage(request))
    assert "not population" in " ".join(result["interpretation"])
    assert "unspecified" in provenance["weight_unit"]
    if case["check"] == "summary":
        code = reference.names[request["species_name"]]
        assert result["series"]["species"]["code"] == code
        assert_equivalent(
            result["series"]["annual_catch"], reference.series(request, code)
        )
    elif case["check"] == "comparison":
        series = []
        for name, actual in zip(
            request["species_names"], result["series"], strict=True
        ):
            expected = reference.series(request, reference.names[name])
            assert actual["species"]["code"] == reference.names[name]
            assert_equivalent(actual["annual_catch"], expected)
            series.append(expected)
        expected_matched = [
            year["year"]
            for index, year in enumerate(series[0])
            if all(item[index]["status"] == "observed" for item in series)
        ]
        assert result["complete_matched_years"] == expected_matched


async def run(args):
    reference = Reference(args.archive)
    database_sha256 = file_sha256(args.database)
    source_hashes = server_source_hashes()
    manifest_path = Path(__file__).parent / "questions.json"
    all_cases = json.loads(manifest_path.read_text())
    cases = (
        all_cases
        if args.split == "all"
        else [case for case in all_cases if case["split"] == args.split]
    )
    if not cases:
        raise ValueError(f"No cases found for split {args.split!r}.")
    trials = []
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "fisheries_mcp.app"],
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                filter(None, (str(ROOT / "src"), os.environ.get("PYTHONPATH")))
            ),
            "FISHERIES_DATABASE": str(args.database.resolve()),
            "MCP_TRANSPORT": "stdio",
            "PORT": "",
            "DATABRICKS_APP_PORT": "",
        },
    )
    started = time.perf_counter()
    async with Client(transport) as client:
        schemas = {tool.name: tool.outputSchema for tool in await client.list_tools()}
        startup_seconds = time.perf_counter() - started
        for repeat in range(args.repeats):
            for case in cases:
                tick = time.perf_counter()
                result = None
                error = None
                passed = False
                try:
                    response = await client.call_tool(
                        case["tool"], {"request": case["request"]}
                    )
                    call_ms = (time.perf_counter() - tick) * 1000
                    result = response.structured_content
                    assert case["check"] != "error", "Expected explicit tool error"
                    validate(result, schemas[case["tool"]])
                    check_result(case, result, reference)
                    passed = True
                except ToolError as exception:
                    call_ms = (time.perf_counter() - tick) * 1000
                    error = str(exception)
                    passed = (
                        case["check"] == "error" and case["error_contains"] in error
                    )
                except (AssertionError, SchemaError) as exception:
                    error = str(exception)
                trials.append(
                    {
                        "id": case["id"],
                        "repeat": repeat + 1,
                        "passed": passed,
                        "latency_ms": (time.perf_counter() - tick) * 1000,
                        "call_latency_ms": call_ms,
                        "tool": case["tool"],
                        "request": case["request"],
                        "expected_error": case["check"] == "error",
                        "error": error,
                        "result": result,
                    }
                )
    if file_sha256(args.database) != database_sha256:
        raise RuntimeError("The evaluated database changed during the benchmark.")
    if server_source_hashes() != source_hashes:
        raise RuntimeError("The evaluated server source changed during the benchmark.")
    # Includes response validation/reference calculation; not isolated DB latency.
    latencies = sorted(trial["latency_ms"] for trial in trials)
    calls = sorted(trial["call_latency_ms"] for trial in trials)
    report = {
        "evaluation_type": "scripted_stdio_mcp_integration_not_agent",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "fastmcp": version("fastmcp"),
        },
        "source_sha256": reference.sha256,
        "database_sha256": database_sha256,
        "server_source_sha256": source_hashes,
        "suite_version": "2.0.0",
        "split": args.split,
        "selected_case_ids": [case["id"] for case in cases],
        "questions_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "reference_method": "independent raw CSV filtering and Decimal aggregation",
        "comparison_tolerance": {"relative": 1e-10, "absolute": 1e-8},
        "trial_count": len(trials),
        "passed": sum(trial["passed"] for trial in trials),
        "startup_seconds": startup_seconds,
        "mcp_round_trip_latency_ms": {
            "p50": statistics.median(calls),
            "p95_nearest_rank": calls[math.ceil(len(calls) * 0.95) - 1],
            "includes": "Warm stdio MCP round trip; not LLM or database-only latency",
        },
        "trial_latency_ms": {
            "p50": statistics.median(latencies),
            "p95_nearest_rank": latencies[math.ceil(len(latencies) * 0.95) - 1],
            "includes": "MCP call, schema validation, and independent reference check",
        },
        "agent_evaluation": {
            "status": "not_run",
            "reason": "This artifact records scripted calls only; agent evaluation "
            "is separate.",
            "task_success_rate": None,
            "tool_selection_accuracy": None,
            "scientific_claim_accuracy": None,
        },
        "databricks": {
            "status": "not_run",
            "reason": "This scripted run does not execute in Databricks.",
        },
        "trials": trials,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.overwrite else "x"
    with args.output.open(mode, encoding="utf-8") as result_file:
        result_file.write(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "trials"}, indent=2
        )
    )
    return 0 if report["passed"] == report["trial_count"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--database", type=Path, default=Path("data/spring.sqlite"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the specified result file instead of preserving it.",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--split", choices=("development", "holdout", "all"), default="all"
    )
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        parser.error("output already exists; choose a new path or use --overwrite")
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
