import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "review_answers",
    Path(__file__).resolve().parents[1] / "eval" / "review_answers.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def inputs(tmp_path):
    answers = tmp_path / "answers.json"
    config = tmp_path / "configuration.json"
    answers.write_text(
        json.dumps(
            {
                "trials": [
                    {
                        "id": f"Q01:{repeat}",
                        "answer": "A preserved answer.",
                        "execution_status": "completed",
                        "tool_calls": [],
                    }
                    for repeat in (1, 2, 3)
                ]
            }
        ),
        encoding="utf-8",
    )
    config.write_text(json.dumps({"endpoint": "test-model"}), encoding="utf-8")
    return MODULE.read_inputs(answers, config)


def test_unreviewed_export_never_becomes_a_pass(inputs):
    answers, identity = inputs
    result = MODULE.summarize(
        answers, identity, MODULE.make_template(answers, identity)
    )
    assert result["counts"] == {"PASS": 0, "FAIL": 0, "UNVERIFIED": 3}
    assert result["scientific_review"] == "UNVERIFIED"


def test_failures_and_repeat_consistency_are_not_hidden(inputs):
    answers, identity = inputs
    review = MODULE.make_template(answers, identity)
    for trial in review["trials"]:
        for judgment in trial["dimensions"].values():
            judgment.update(verdict="PASS", evidence="Answer agrees with reference.")
    review["trials"][1]["dimensions"]["causal_claims"] = {
        "verdict": "FAIL",
        "evidence": "Answer asserts causation; reference does not establish it.",
    }
    result = MODULE.summarize(answers, identity, review)
    assert result["counts"] == {"PASS": 2, "FAIL": 1, "UNVERIFIED": 0}
    assert result["dimensions"]["causal_claims"]["FAIL"] == 1
    assert not result["repeat_consistency"]["Q01"]["all_exported_repeats_pass"]
    assert result["scientific_review"] == "UNVERIFIED"


@pytest.mark.parametrize("verdict", ["PASS", "FAIL", "NOT_APPLICABLE"])
def test_judgment_requires_evidence(inputs, verdict):
    answers, identity = inputs
    review = MODULE.make_template(answers, identity)
    review["trials"][0]["dimensions"]["ranking"]["verdict"] = verdict
    with pytest.raises(ValueError, match="needs an answer/trace/reference note"):
        MODULE.summarize(answers, identity, review)


@pytest.mark.parametrize("change", ["hash", "duplicate", "missing"])
def test_review_cannot_attach_to_other_or_partial_answers(inputs, change):
    answers, identity = inputs
    review = MODULE.make_template(answers, identity)
    if change == "hash":
        review["answers_sha256"] = "changed"
    elif change == "duplicate":
        review["trials"].append(review["trials"][0])
    else:
        review["trials"].pop()
    with pytest.raises(ValueError):
        MODULE.summarize(answers, identity, review)


def test_all_not_applicable_is_not_a_success(inputs):
    answers, identity = inputs
    review = MODULE.make_template(answers, identity)
    for trial in review["trials"]:
        for judgment in trial["dimensions"].values():
            judgment.update(verdict="NOT_APPLICABLE", evidence="No applicable claim.")
    assert MODULE.summarize(answers, identity, review)["counts"]["UNVERIFIED"] == 3
