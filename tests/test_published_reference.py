import json
from pathlib import Path

import pytest

from deploy.databricks import build_eval_notebook as builder


@pytest.fixture
def published_files(tmp_path, monkeypatch):
    root = tmp_path / "eval/published_reference"
    root.mkdir(parents=True)
    for suffix, split in (
        ("a", "published_reference"),
        ("a02", "published_reference_corrected"),
        ("b", "published_context"),
        ("c", "published_c_preflight"),
        ("d", "published_report_context"),
    ):
        (root / f"benchmark-{suffix}.json").write_text(
            json.dumps(
                [{"id": suffix, "split": split, "source_archive_sha256": "reviewed"}]
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    return root


def test_supplemental_cases_load_without_mutating_baseline(published_files):
    baseline = [{"id": "Q01", "split": "development"}]
    cases = builder.load_published_questions(baseline, "reviewed")
    assert [case["split"] for case in cases] == [
        "published_reference",
        "published_reference_corrected",
        "published_context",
        "published_c_preflight",
        "published_report_context",
    ]
    assert baseline == [{"id": "Q01", "split": "development"}]


@pytest.mark.parametrize("duplicate", ["Q01", "a"])
def test_duplicate_ids_rejected_across_all_suites(published_files, duplicate):
    (published_files / "benchmark-b.json").write_text(
        json.dumps([{"id": duplicate, "source_archive_sha256": "reviewed"}]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="IDs must be unique"):
        builder.load_published_questions([{"id": "Q01"}], "reviewed")


def test_different_archive_reference_cannot_be_packaged(published_files):
    with pytest.raises(ValueError, match="different public archive"):
        builder.load_published_questions([], "unreviewed")


def test_candidate_v7_notebook_uses_only_recorded_model_options(tmp_path, monkeypatch):
    results = tmp_path / "eval" / "results"
    results.mkdir(parents=True)
    (results / "candidate-v7-agent-evaluation.json").write_text(
        json.dumps(
            {
                "configuration": {
                    "endpoint": "approved-endpoint",
                    "options": {"max_tokens": 4000},
                    "temperature": None,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    endpoint, options = builder.notebook_model_configuration(True)
    assert endpoint == "approved-endpoint"
    assert options == {"max_tokens": 4000}
    assert "temperature" not in options


def test_c01_question_does_not_expose_reference_totals():
    root = Path(__file__).resolve().parents[1]
    cases = json.loads(
        (root / "eval/published_reference/benchmark-c.json").read_text(encoding="utf-8")
    )
    assert len(cases) == 1
    case = cases[0]
    assert case["id"] == "NOAA-C01"
    assert case["split"] == "published_c_preflight"
    assert case["check"] == "comparison"
    for value in ("404.15", "2231.485", "868.8", "4869.4", "4,869.4"):
        assert value not in case["question"]


def test_corrected_a02_preserves_original_and_d01_does_not_supply_report_facts():
    root = Path(__file__).resolve().parents[1] / "eval/published_reference"
    original = json.loads((root / "benchmark-a.json").read_text(encoding="utf-8"))[0]
    corrected = json.loads((root / "benchmark-a02.json").read_text(encoding="utf-8"))[0]
    new_case = json.loads((root / "benchmark-d.json").read_text(encoding="utf-8"))[0]
    assert original["id"] == "NOAA-A01" and "PDF p. 1" in original["question"]
    assert corrected["id"] == "NOAA-A02"
    assert "physical PDF page 3" in corrected["question"]
    assert corrected["source"]["physical_pdf_page"] == 3
    assert new_case["id"] == "NOAA-D01"
    assert new_case["split"] == "published_report_context"
    assert any("get_spring_report_context" in item for item in new_case["rubric"])
    for value in ("70", "377", "Georges Bank", "daytime", "fisheries.noaa.gov"):
        assert value not in new_case["question"]
