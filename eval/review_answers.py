"""Create and summarize hash-bound analyst reviews; never infer scientific approval."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DIMENSIONS = (
    "numerical_fidelity",
    "missing_vs_zero",
    "ranking",
    "provenance",
    "causal_claims",
    "scope",
    "tool_use",
)


class Judgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    verdict: Literal["PASS", "FAIL", "UNVERIFIED", "NOT_APPLICABLE"] = "UNVERIFIED"
    evidence: str = ""

    @model_validator(mode="after")
    def require_evidence(self):
        if self.verdict != "UNVERIFIED" and not self.evidence.strip():
            raise ValueError("Every judgment needs an answer/trace/reference note.")
        return self


class TrialReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1)
    dimensions: dict[str, Judgment]

    @model_validator(mode="after")
    def require_dimensions(self):
        if set(self.dimensions) != set(DIMENSIONS):
            raise ValueError("Each trial must include exactly the seven dimensions.")
        return self


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    method: Literal["analyst_assessment_not_scientific_approval"]
    answers_sha256: str
    configuration_sha256: str
    trials: list[TrialReview]


def read_inputs(answers_path: Path, configuration_path: Path) -> tuple[dict, dict]:
    answers_bytes = answers_path.read_bytes()
    config_bytes = configuration_path.read_bytes()
    answers = json.loads(answers_bytes)
    configuration = json.loads(config_bytes)
    trials = answers["trials"]
    if not isinstance(trials, list) or not trials:
        raise ValueError("Expected a nonempty answers.json trials list.")
    ids = [trial["id"] for trial in trials]
    if any(not isinstance(key, str) or not key.strip() for key in ids):
        raise ValueError("Each exported trial needs a nonempty string ID.")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate exported trial IDs.")
    for trial in trials:
        if trial.get("execution_status") != "completed":
            raise ValueError("Use completed answers; preserve failed runs separately.")
        if not isinstance(trial.get("answer"), str) or not trial["answer"].strip():
            raise ValueError("Each completed trial needs its original answer.")
        if not isinstance(trial.get("tool_calls"), list):
            raise ValueError("Each trial needs its recorded tool_calls list.")
    if not isinstance(configuration, dict) or not configuration.get("endpoint"):
        raise ValueError("Use the matching exported configuration.json.")
    arm = configuration.get("evaluation_arm", "mcp")
    if arm not in {"mcp", "no_tools"}:
        raise ValueError("Unknown evaluation arm.")
    if any(trial.get("evaluation_arm", "mcp") != arm for trial in trials):
        raise ValueError("Trial arms differ from the supplied configuration.")
    return answers, {
        "answers_sha256": hashlib.sha256(answers_bytes).hexdigest(),
        "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "evaluation_arm": arm,
    }


def make_template(answers: dict, identity: dict) -> dict:
    return {
        "schema_version": 1,
        "method": "analyst_assessment_not_scientific_approval",
        "answers_sha256": identity["answers_sha256"],
        "configuration_sha256": identity["configuration_sha256"],
        "trials": [
            {
                "id": trial["id"],
                "dimensions": {
                    name: {"verdict": "UNVERIFIED", "evidence": ""}
                    for name in DIMENSIONS
                },
            }
            for trial in answers["trials"]
        ],
    }


def summarize(answers: dict, identity: dict, document: dict) -> dict:
    review = Review.model_validate(document)
    for name in ("answers_sha256", "configuration_sha256"):
        if getattr(review, name) != identity[name]:
            raise ValueError(f"Review does not match original input: {name}")
    ids = [trial.id for trial in review.trials]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate review trial IDs.")
    if set(ids) != {trial["id"] for trial in answers["trials"]}:
        raise ValueError("Review must contain exactly the exported trial IDs.")
    dimensions = {name: Counter() for name in DIMENSIONS}
    statuses = {}
    for trial in review.trials:
        values = [judgment.verdict for judgment in trial.dimensions.values()]
        for name, judgment in trial.dimensions.items():
            dimensions[name][judgment.verdict] += 1
        statuses[trial.id] = (
            "FAIL"
            if "FAIL" in values
            else "UNVERIFIED"
            if "UNVERIFIED" in values or "PASS" not in values
            else "PASS"
        )
    by_case: dict[str, list[str]] = {}
    for key, status in statuses.items():
        by_case.setdefault(key.rsplit(":", 1)[0], []).append(status)
    return {
        "schema_version": 1,
        "method": review.method,
        **identity,
        "scientific_review": "UNVERIFIED",
        "denominator": "Completed trials in supplied export, not all planned attempts.",
        "trial_count": len(statuses),
        "counts": {
            status: sum(value == status for value in statuses.values())
            for status in ("PASS", "FAIL", "UNVERIFIED")
        },
        "dimensions": {
            name: {
                verdict: counts[verdict]
                for verdict in ("PASS", "FAIL", "UNVERIFIED", "NOT_APPLICABLE")
            }
            for name, counts in dimensions.items()
        },
        "trials": statuses,
        "repeat_consistency": {
            case: {
                "exported_repeats": len(values),
                "all_exported_repeats_pass": all(v == "PASS" for v in values),
            }
            for case, values in by_case.items()
        },
        "limits": (
            "Summarizes explicit analyst judgments, not automated answer grading, "
            "independent scientific validation, or a statistical accuracy estimate. "
            "Hashes bind the selected files; the operator must verify they came "
            "from the same MLflow run. Keep failures and omitted attempts visible."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("template", "summarize"))
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument("--configuration", required=True, type=Path)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if (args.operation == "summarize") != (args.reviews is not None):
        parser.error("--reviews is required only for summarize")
    answers, identity = read_inputs(args.answers, args.configuration)
    result = (
        make_template(answers, identity)
        if args.operation == "template"
        else summarize(
            answers, identity, json.loads(args.reviews.read_text(encoding="utf-8"))
        )
    )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Created {args.output.name}; scientific review remains UNVERIFIED.")


if __name__ == "__main__":
    main()
