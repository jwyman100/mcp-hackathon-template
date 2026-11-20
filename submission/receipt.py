"""Create and replay evidence receipts for the public scripted MCP demo."""

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "spring.sqlite"
RECEIPT_VERSION = 1
EXPECTED_TOOLS = [
    "search_species",
    "get_spring_catch_summary",
    "get_spring_report_context",
]
ALLOWED_TOOLS = set(EXPECTED_TOOLS)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def server_source_hashes(root: Path = ROOT) -> dict[str, str]:
    sources = sorted((root / "src" / "fisheries_mcp").rglob("*.py"))
    if not sources:
        raise FileNotFoundError("No fisheries MCP source files were found.")
    return {path.relative_to(root).as_posix(): sha256_file(path) for path in sources}


def submission_source_hashes(root: Path = ROOT) -> dict[str, str]:
    sources = [root / "submission" / name for name in ("demo.py", "receipt.py")]
    if any(not path.is_file() for path in sources):
        raise FileNotFoundError("The scripted demo source files are incomplete.")
    return {path.relative_to(root).as_posix(): sha256_file(path) for path in sources}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def make_receipt(
    calls: list[dict[str, Any]],
    question: str,
    *,
    database: Path = DATABASE,
    root: Path = ROOT,
    source_sha256: str,
) -> dict[str, Any]:
    if [call.get("tool") for call in calls] != EXPECTED_TOOLS:
        raise ValueError("A receipt must contain successful public demo tool calls.")
    summary = next(
        (
            call["result"]
            for call in calls
            if call["tool"] == "get_spring_catch_summary"
        ),
        None,
    )
    context = next(
        (
            call["result"]
            for call in calls
            if call["tool"] == "get_spring_report_context"
        ),
        None,
    )
    if summary is None or summary.get("provenance", {}).get("dataset_kind") != "public":
        raise ValueError("Receipts can only be created from the public snapshot.")
    if summary["provenance"].get("source_sha256") != source_sha256:
        raise ValueError("The MCP result source hash does not match the receipt input.")
    limitations = list(summary.get("interpretation", []))
    if context is not None:
        limitations.extend(context.get("limitations", []))
    return {
        "receipt_version": RECEIPT_VERSION,
        "execution_mode": "scripted_mcp_stdio",
        "scientific_review_status": "unverified",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "question": question,
        "public_source": {
            "title": summary["provenance"]["title"],
            "source_sha256": source_sha256,
        },
        "scope": summary["scope"],
        "weight_unit": summary["provenance"]["weight_unit"],
        "database_sha256": sha256_file(database),
        "server_source_sha256": server_source_hashes(root),
        "submission_source_sha256": submission_source_hashes(root),
        "tool_calls": calls,
        "interpretation_limits": list(dict.fromkeys(limitations)),
    }


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )


def read_receipt(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Receipt exceeds the 2 MiB size limit.")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    calls = receipt.get("tool_calls")
    if (
        receipt.get("receipt_version") != RECEIPT_VERSION
        or receipt.get("execution_mode") != "scripted_mcp_stdio"
        or not isinstance(calls, list)
        or not all(isinstance(call, dict) for call in calls)
        or [call.get("tool") for call in calls] != EXPECTED_TOOLS
    ):
        raise ValueError("Unsupported or malformed MCP demo receipt.")
    for call in calls:
        if (
            not isinstance(call, dict)
            or call.get("tool") not in ALLOWED_TOOLS
            or not isinstance(call.get("arguments"), dict)
            or not isinstance(call.get("result"), dict)
        ):
            raise ValueError("Receipt contains an invalid or unsupported tool call.")
    return receipt


def verify_environment(
    receipt: dict[str, Any],
    *,
    database: Path = DATABASE,
    root: Path = ROOT,
) -> None:
    current_database_hash = sha256_file(database)
    if current_database_hash != receipt.get("database_sha256"):
        raise ValueError("Replay mismatch: public SQLite snapshot hash changed.")
    if server_source_hashes(root) != receipt.get("server_source_sha256"):
        raise ValueError("Replay mismatch: fisheries MCP source hashes changed.")
    if submission_source_hashes(root) != receipt.get("submission_source_sha256"):
        raise ValueError("Replay mismatch: scripted demo source hashes changed.")


async def replay_receipt(
    receipt: dict[str, Any],
    *,
    database: Path = DATABASE,
    root: Path = ROOT,
) -> None:
    verify_environment(receipt, database=database, root=root)
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "fisheries_mcp.app"],
        cwd=str(root),
        env={
            **os.environ,
            "FISHERIES_DATABASE": str(database),
            "MCP_TRANSPORT": "stdio",
            "PORT": "",
            "DATABRICKS_APP_PORT": "",
            "FASTMCP_LOG_LEVEL": "ERROR",
        },
    )
    async with Client(transport) as client:
        for index, expected in enumerate(receipt["tool_calls"], start=1):
            result = await client.call_tool(expected["tool"], expected["arguments"])
            if result.is_error:
                raise ValueError(
                    f"Replay mismatch: tool call {index} returned an MCP error."
                )
            actual = result.structured_content
            if canonical_json(actual) != canonical_json(expected["result"]):
                raise ValueError(
                    f"Replay mismatch: result for {expected['tool']} changed."
                )
