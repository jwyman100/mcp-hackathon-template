import json
import subprocess
import sys
from pathlib import Path

import pytest

from submission.receipt import read_receipt, verify_environment

ROOT = Path(__file__).resolve().parents[1]


def run_demo(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "submission/demo.py", *arguments],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )


def test_demo_receipt_replays_and_detects_result_and_source_mismatches(tmp_path):
    receipt_path = tmp_path / "demo-receipt.json"
    written = run_demo("--receipt", str(receipt_path))
    assert written.returncode == 0, written.stderr
    receipt = read_receipt(receipt_path)
    assert receipt["public_source"]["source_sha256"]
    assert receipt["database_sha256"]
    assert receipt["server_source_sha256"]
    assert receipt["submission_source_sha256"]
    assert receipt["scope"]["start_year"] == 2022
    assert "unspecified" in receipt["weight_unit"]
    assert receipt["scientific_review_status"] == "unverified"
    assert [call["tool"] for call in receipt["tool_calls"]] == [
        "search_species",
        "get_spring_catch_summary",
        "get_spring_report_context",
    ]

    replayed = run_demo("--replay", str(receipt_path))
    assert replayed.returncode == 0, replayed.stderr
    assert "Replay passed" in replayed.stdout

    changed_result = json.loads(receipt_path.read_text(encoding="utf-8"))
    changed_result["tool_calls"][0]["result"]["note"] = "tampered result"
    changed_path = tmp_path / "changed-receipt.json"
    changed_path.write_text(json.dumps(changed_result), encoding="utf-8")
    mismatch = run_demo("--replay", str(changed_path))
    assert mismatch.returncode != 0
    assert "result for search_species changed" in mismatch.stderr

    changed_source = dict(receipt)
    changed_source["submission_source_sha256"] = {"submission/fake.py": "0" * 64}
    with pytest.raises(ValueError, match="demo source hashes changed"):
        verify_environment(changed_source)


def test_demo_refuses_to_overwrite_a_receipt(tmp_path):
    receipt_path = tmp_path / "demo-receipt.json"
    receipt_path.write_text("keep", encoding="utf-8")
    result = run_demo("--receipt", str(receipt_path))
    assert result.returncode != 0
    assert receipt_path.read_text(encoding="utf-8") == "keep"
