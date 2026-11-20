"""Build a single importable notebook containing only allowlisted public-demo files."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import io
import json
import sqlite3
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def cell(kind: str, source: str) -> dict:
    result = {
        "cell_type": kind,
        "metadata": {},
        "source": textwrap.dedent(source).strip() + "\n",
    }
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def load_published_questions(questions: list[dict], source_sha256: str) -> list[dict]:
    published = []
    for name in (
        "benchmark-a.json",
        "benchmark-a02.json",
        "benchmark-b.json",
        "benchmark-c.json",
        "benchmark-d.json",
    ):
        path = ROOT / "eval/published_reference" / name
        published.extend(json.loads(path.read_text(encoding="utf-8")))
    ids = [case["id"] for case in questions + published]
    if len(set(ids)) != len(ids):
        raise ValueError("Evaluation question IDs must be unique.")
    if any(case.get("source_archive_sha256") != source_sha256 for case in published):
        raise ValueError("Published-reference case uses a different public archive.")
    return published


def notebook_model_configuration(candidate_v7_config: bool) -> tuple[str, dict]:
    if not candidate_v7_config:
        return "databricks-claude-sonnet-4-6", {"temperature": 0, "max_tokens": 1500}
    manifest_path = ROOT / "eval/results/candidate-v7-agent-evaluation.json"
    configuration = json.loads(manifest_path.read_text(encoding="utf-8"))[
        "configuration"
    ]
    return configuration["endpoint"], configuration["options"]


def make_notebook(
    archive: Path, output: Path, *, candidate_v7_config: bool = False
) -> None:
    endpoint, model_options = notebook_model_configuration(candidate_v7_config)
    spec = importlib.util.spec_from_file_location(
        "public_reference", ROOT / "eval/run.py"
    )
    reference_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference_module)
    reference = reference_module.Reference(archive)
    database = ROOT / "data/spring.sqlite"
    uri = database.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        provenance = json.loads(
            connection.execute(
                "SELECT value FROM metadata WHERE key='provenance'"
            ).fetchone()[0]
        )
    if (
        provenance["dataset_kind"] != "public"
        or provenance["source_sha256"] != reference.sha256
    ):
        raise ValueError("Only the source-verified public snapshot may be packaged.")
    questions_path = ROOT / "eval/questions.json"
    questions = json.loads(questions_path.read_text())
    published_questions = load_published_questions(questions, reference.sha256)
    questions.extend(published_questions)
    gold = {}
    for case in questions:
        expected = {
            "criteria": case["rubric"],
            "source_sha256": reference.sha256,
            "weight_unit": "unspecified in the public metadata",
        }
        if case.get("expected_facts"):
            expected["expected_facts"] = case["expected_facts"]
        if case.get("reference_answer"):
            expected["reference_answer"] = case["reference_answer"]
        if case.get("source"):
            expected["published_source"] = case["source"]
        request = case["request"]
        if case["check"] == "error":
            expected["behavior"] = (
                "Explain the unsupported request. A valid refusal need not issue "
                "the deliberately invalid scripted tool call."
            )
        elif case["check"] == "search":
            expected["species_codes"] = case["expected_codes"]
        else:
            expected["coverage"] = reference.coverage(request)
            if case["check"] == "summary":
                code = reference.names[request["species_name"]]
                expected["series"] = {code: reference.series(request, code)}
            elif case["check"] == "comparison":
                expected["series"] = {
                    reference.names[name]: reference.series(
                        request, reference.names[name]
                    )
                    for name in request["species_names"]
                }
                series = list(expected["series"].values())
                expected["complete_matched_years"] = [
                    row["year"]
                    for index, row in enumerate(series[0])
                    if all(item[index]["status"] == "observed" for item in series)
                ]
        gold[case["id"]] = expected
    files = {
        path.relative_to(ROOT / "src").as_posix(): path.read_bytes()
        for path in sorted((ROOT / "src/fisheries_mcp").rglob("*.py"))
    }
    files.update(
        {
            "spring.sqlite": database.read_bytes(),
            "questions.json": questions_path.read_bytes(),
            "published_reference.json": json.dumps(published_questions).encode(),
            "gold.json": json.dumps(gold).encode(),
            "databricks_agent.py": (ROOT / "eval/databricks_agent.py").read_bytes(),
        }
    )
    manifest = {
        "source_sha256": reference.sha256,
        "files": {
            name: hashlib.sha256(content).hexdigest()
            for name, content in sorted(files.items())
        },
        "reference_method": (
            "Original public CSVs filtered and aggregated with Decimal; "
            "published-source interpretation criteria manually curated."
        ),
    }
    files["manifest.json"] = json.dumps(manifest).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
    payload = buffer.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    requirements_path = ROOT / "deploy/databricks/requirements-eval.txt"
    requirements = requirements_path.read_text().split()
    pip = "%pip install " + " ".join(f'"{item}"' for item in requirements)
    cells = [
        cell(
            "markdown",
            """
            # Fisheries MCP: Databricks agent evaluation

            Import this notebook through Workspace > your folder > Import.
            Attach approved Python 3.11+ compute and run cells **one at a time**.
            Only the public snapshot and curated demo code are embedded below.
            Confirm upload/release and sandbox/model approval before importing.

            This notebook calls an actual model, which chooses actual MCP tools.
            It records answers and tool traces in MLflow. Answer assessment is
            **manual**, against independent public-CSV reference answers.
            Analyst assessment is separate from scientific approval, which stays
            UNVERIFIED. No automatic judge model is called.

            This is a fixed public-data prototype, not an internal Oracle service.
            SSO, per-tool/data authorization, guardrails and auditability are
            future enterprise plans, not controls implemented or tested here.
            The example scientific schema contract is provisional and not
            expert-approved. SSO alone would not authorize dataset access.

            Dependencies download from package indexes; compute and model use may
            cost credits. Model calls are disabled by default. No Genie, Apps,
            SQL warehouse, new cluster, or public deployment is created here.
            Workspace-specific MLflow storage permissions may still be required.
            """,
        ),
        cell("markdown", "## 1. Install notebook-scoped dependencies"),
        cell("code", pip),
        cell("code", "dbutils.library.restartPython()"),
        cell("markdown", "## 2. Unpack and verify the public-only bundle"),
        cell(
            "code",
            f"""
            import base64, hashlib, io, json, os, sys, tempfile, zipfile
            from pathlib import Path, PurePosixPath

            if sys.version_info < (3, 11):
                raise RuntimeError("Select Python 3.11 or newer compute.")
            PAYLOAD = "{base64.b64encode(payload).decode()}"
            BUNDLE_SHA256 = "{digest}"
            raw = base64.b64decode(PAYLOAD, validate=True)
            assert hashlib.sha256(raw).hexdigest() == BUNDLE_SHA256
            WORK = Path(tempfile.mkdtemp(prefix="fisheries-mcp-"))
            with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
                manifest = json.loads(bundle.read("manifest.json"))
                expected_names = set(manifest["files"]) | {{"manifest.json"}}
                assert set(bundle.namelist()) == expected_names
                assert sum(item.file_size for item in bundle.infolist()) < 50_000_000
                for name, expected in manifest["files"].items():
                    path = PurePosixPath(name)
                    assert not path.is_absolute() and ".." not in path.parts
                    content = bundle.read(name)
                    assert hashlib.sha256(content).hexdigest() == expected, name
                    target = WORK.joinpath(*path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
            sys.path.insert(0, str(WORK))
            CASES = json.loads((WORK / "questions.json").read_text()) + json.loads(
                (WORK / "published_reference.json").read_text()
            )
            GOLD = json.loads((WORK / "gold.json").read_text())
            print("Verified public bundle. Python:", sys.version.split()[0])
            """,
        ),
        cell("markdown", "## 3. Discover endpoints (metadata only; no model request)"),
        cell(
            "code",
            """
            from databricks.sdk import WorkspaceClient

            workspace = WorkspaceClient()
            names = [endpoint.name for endpoint in workspace.serving_endpoints.list()]
            print("\\n".join(names) if names else "No endpoints; ask the admin.")
            """,
        ),
        cell(
            "markdown",
            """
            ## 4. Configuration

            ENDPOINT defaults to a chat model visible in your workspace. Confirm
            it is approved, or choose another tool-calling endpoint from step 3.
            Listing alone does not prove query permission.
            EXPERIMENT_PATH can stay empty to use the notebook's default
            experiment; otherwise enter an experiment you can write to.

            SPLIT supports smoke, development, holdout, published_reference (A01),
            published_reference_corrected (A02), published_context (B01),
            published_c_preflight (C01), and published_report_context (D01).
            Each supplementary split is one question; run it separately with
            REPEATS=1. B01 supplies NOAA context in its question; D01 instead
            requires discovering the curated context tool. C01 tests the limits
            of the available tools, not full report reconciliation. None tests
            live report retrieval.
            A01 citation erratum: its Overview is on physical PDF page 3, not 1.
            The original A01 question is retained to preserve prior-run identity.

            First keep SPLIT="smoke", REPEATS=1 and ENABLE_MODEL_CALLS=False.
            After the MCP check succeeds, set ENABLE_MODEL_CALLS=True and run
            step 6. Run step 6 only when ready to incur model usage.

            EVALUATION_ARM="mcp" is the primary experiment. The optional
            "no_tools" arm uses the same question, dictionary and model options,
            but offers no tools or numerical-data access. It measures the added
            value of access plus tooling, not MCP against equally informed SQL
            or another interface. Do not mix arms in one reported denominator.
            The shared dictionary may itself help with scope questions.
            """,
        ),
        cell(
            "code",
            f"""
            ENDPOINT = {endpoint!r}
            EXPERIMENT_PATH = ""
            ENABLE_MODEL_CALLS = False
            EVALUATION_ARM = "mcp"  # optional separate run: "no_tools"
            SPLIT = "smoke"  # published_c_preflight: C01
            REPEATS = 1     # use 3 only after the smoke run works
            MAX_MODEL_ROUNDS = 6
            MAX_TOOL_CALLS = 8
            QUESTION_TIMEOUT_SECONDS = 180
            MODEL_OPTIONS = {model_options!r}
            # The selected chat endpoint must accept these options.
            """,
        ),
        cell("markdown", "## 5. Check the actual MCP server (no model request)"),
        cell(
            "code",
            """
            import asyncio
            from fastmcp import Client
            from fastmcp.client.transports import StdioTransport

            def transport():
                return StdioTransport(
                    command=sys.executable,
                    args=["-m", "fisheries_mcp.app"],
                    cwd=str(WORK),
                    env={
                        "PYTHONPATH": str(WORK),
                        "FISHERIES_DATABASE": str(WORK / "spring.sqlite"),
                        "MCP_TRANSPORT": "stdio",
                        "PORT": "",
                        "DATABRICKS_APP_PORT": "",
                    },
                )

            async with Client(transport(), timeout=30) as mcp:
                discovered = await mcp.list_tools()
                assert {tool.name for tool in discovered} == {
                    "search_species", "get_spring_catch_summary",
                    "compare_spring_catch", "get_spring_survey_coverage",
                    "get_spring_report_context",
                }
                resource = await mcp.read_resource("fisheries://dictionary")
                DICTIONARY = resource[0].text
                provenance = json.loads(DICTIONARY)["provenance"]
                assert provenance["dataset_kind"] == "public"
                assert provenance["source_sha256"] == manifest["source_sha256"]
                result = await mcp.call_tool(
                    "search_species", {"request": {"term": "cod"}}
                )
                species = result.structured_content["species"][0]
                assert species["code"] == "073"
                summary = await mcp.call_tool(
                    "get_spring_catch_summary",
                    {"request": {"species_name": species["published_label"]}},
                )
                assert summary.structured_content["series"]["species"]["code"] == "073"
                context = await mcp.call_tool(
                    "get_spring_report_context", {"request": {"year": 2023}}
                )
                assert context.structured_content["year"] == 2023
            TOOLS = [
                {"type": "function", "function": {
                    "name": tool.name, "description": tool.description,
                    "parameters": tool.inputSchema,
                }}
                for tool in discovered
            ]
            print("MCP check passed: five tools, public provenance, and cod handoff.")
            """,
        ),
        cell(
            "markdown",
            """
            ## 6. Run the model-driven evaluation

            Start with one smoke question. Inspect its tool spans and final
            answer in the notebook's MLflow experiment before expanding.
            If permissions, model options, authentication, or quotas fail, this
            run stops and records failure rather than charging for more cases.
            Limits bound requests, not dollars; check sandbox billing separately.

            For the hardened-runtime confirmation, keep the candidate fixed:
            development/3 = 24 trials; holdout/3 = 12 trials; A02, D01 and C01
            separately at 3 repeats = 9 more trials. Total: 45 plus the smoke.
            The holdout is repository-visible, not blind. Do not tune between
            these batches. Any subsequent change is a separate experiment.
            Every trial starts a fresh conversation.
            """,
        ),
        cell(
            "code",
            """
            import time
            from importlib.metadata import version
            import mlflow
            from databricks_openai import DatabricksOpenAI
            from databricks_agent import run_agent

            RESULTS = []
            RUN_ID = None
            if not ENABLE_MODEL_CALLS:
                print("No model calls. Review step 4 and enable calls when approved.")
            else:
                if EVALUATION_ARM not in {"mcp", "no_tools"}:
                    raise ValueError("Choose mcp or no_tools as EVALUATION_ARM.")
                if not ENDPOINT or SPLIT not in {
                    "smoke", "development", "holdout", "published_reference",
                    "published_reference_corrected", "published_context",
                    "published_c_preflight", "published_report_context",
                }:
                    raise ValueError("Set ENDPOINT and choose a valid SPLIT.")
                if REPEATS not in {1, 2, 3} or (SPLIT == "smoke" and REPEATS != 1):
                    raise ValueError("Smoke uses 1 repeat; other splits allow 1-3.")
                if not 1 <= MAX_MODEL_ROUNDS <= 10 or not 1 <= MAX_TOOL_CALLS <= 12:
                    raise ValueError("Use 1-10 model rounds and 1-12 tool calls.")
                if not 1 <= QUESTION_TIMEOUT_SECONDS <= 300:
                    raise ValueError("Use a per-question timeout of 1-300 seconds.")
                mlflow.set_tracking_uri("databricks")
                if EXPERIMENT_PATH:
                    mlflow.set_experiment(EXPERIMENT_PATH)
                model = DatabricksOpenAI().with_options(timeout=60, max_retries=0)
                selected = CASES[:1] if SPLIT == "smoke" else [
                    case for case in CASES if case["split"] == SPLIT
                ]
                if not selected:
                    raise ValueError(f"No evaluation questions found for {SPLIT}.")

                @mlflow.trace(span_type="CHAT_MODEL")
                def model_request(messages, tools):
                    tool_options = (
                        {"tools": tools, "tool_choice": "auto"} if tools else {}
                    )
                    response = model.chat.completions.create(
                        model=ENDPOINT, messages=messages,
                        **tool_options, **MODEL_OPTIONS,
                    )
                    return response.model_dump(exclude_none=True)

                async def complete(messages, tools):
                    return await asyncio.to_thread(model_request, messages, tools)

                with mlflow.start_run(
                    run_name=f"fisheries-{EVALUATION_ARM}-{SPLIT}"
                ) as run:
                    RUN_ID = run.info.run_id
                    mlflow.log_dict({
                        "endpoint": ENDPOINT, "options": MODEL_OPTIONS,
                        "bundle_sha256": BUNDLE_SHA256, "manifest": manifest,
                        "split": SPLIT, "repeats": REPEATS,
                        "evaluation_arm": EVALUATION_ARM,
                        "planned_trials": len(selected) * REPEATS,
                        "comparison_limit": (
                            "no_tools has shared dictionary but no numerical "
                            "data access; measures access plus tooling"
                        ),
                        "max_rounds": MAX_MODEL_ROUNDS, "max_tools": MAX_TOOL_CALLS,
                        "question_timeout_seconds": QUESTION_TIMEOUT_SECONDS,
                        "model_request_timeout_seconds": 60, "model_retries": 0,
                        "versions": {name: version(name) for name in [
                            "fastmcp", "mlflow", "openai", "databricks-openai",
                        ]},
                        "grading": "analyst assessment; not scientific approval",
                    }, "configuration.json")
                    mlflow.log_dict({
                        "tools": TOOLS if EVALUATION_ARM == "mcp" else [],
                        "dictionary": DICTIONARY,
                    },
                                    "agent_context.json")
                    async with Client(transport(), timeout=30) as mcp:
                        @mlflow.trace(span_type="TOOL")
                        async def invoke(name, arguments):
                            result = await mcp.call_tool(
                                name, arguments, timeout=30, raise_on_error=False
                            )
                            content = result.structured_content
                            if content is None:
                                content = [
                                    item.model_dump(mode="json")
                                    for item in result.content
                                ]
                            return {"is_error": result.is_error, "content": content}

                        @mlflow.trace(span_type="AGENT")
                        async def answer(question):
                            return await run_agent(
                                question, TOOLS, DICTIONARY, complete, invoke,
                                max_rounds=MAX_MODEL_ROUNDS,
                                max_tool_calls=MAX_TOOL_CALLS,
                                arm=EVALUATION_ARM,
                            )

                        for repeat in range(1, REPEATS + 1):
                            for case in selected:
                                key = f"{case['id']}:{repeat}"
                                tick = time.perf_counter()
                                try:
                                    result = await asyncio.wait_for(
                                        answer(case["question"]),
                                        timeout=QUESTION_TIMEOUT_SECONDS,
                                    )
                                except Exception as error:
                                    mlflow.log_dict({
                                        "id": key, "execution_status": "failed",
                                        "error_type": type(error).__name__,
                                        "evaluation_arm": EVALUATION_ARM,
                                        "scientific_review": "UNVERIFIED",
                                    }, f"trials/{case['id']}-{repeat}-failure.json")
                                    raise
                                result.update(
                                    id=key, question=case["question"],
                                    latency_seconds=time.perf_counter() - tick,
                                )
                                RESULTS.append(result)
                                mlflow.log_dict(
                                    result, f"trials/{case['id']}-{repeat}.json"
                                )
                                print(key, result["answer"])
                    # Reference material is an evaluation artifact, never model input.
                    mlflow.log_dict({c["id"]: GOLD[c["id"]] for c in selected},
                                    "independent_reference.json")
                    mlflow.log_metric("completed_trials", len(RESULTS))
                    mlflow.log_metric("unverified_trials", len(RESULTS))
                    mlflow.log_dict({"trials": RESULTS}, "answers.json")
                print("MLflow run:", RUN_ID, "- quality still UNVERIFIED.")
            """,
        ),
        cell(
            "markdown",
            """
            ## 7. Export and review before claiming accuracy

            In Experiments, open the run and its **Traces** and **Artifacts**.
            Compare each answer and tool trace with independent_reference.json
            and the case criteria. An accurate supported refusal can pass without
            a tool call; do not require the scripted runner's exact call sequence.

            Download answers.json, configuration.json, agent_context.json and
            independent_reference.json from the SAME run. Retain trials/ and
            failure records, especially if a batch stopped before answers.json.
            Do not copy the expandable trace viewer or combine different runs.

            Back in the local repository, use eval/review_answers.py to create
            an ungraded review template and then summarize explicit judgments.
            The detailed instructions and seven dimensions are in eval/README.md.
            Use UNVERIFIED for anything not checked and explain every judgment
            with an answer/trace/reference note. Analyst assessment never changes
            scientific_review from UNVERIFIED. Obtain separate specialist review
            before claiming scientific approval.

            Completing a model run is not a PASS. A correct refusal can satisfy
            an unsupported task, but failure to supply requested available
            numerical facts is not successful task completion in the baseline.
            Mark tool_use NOT_APPLICABLE for the no_tools arm.
            """,
        ),
        cell(
            "code",
            """
            if RUN_ID is None:
                print("No model run to export yet.")
            else:
                print("Export artifacts from MLflow run:", RUN_ID)
                print("Completed answers in memory:", len(RESULTS))
                print("Scientific review remains UNVERIFIED.")
            """,
        ),
        cell(
            "markdown",
            """
            ## Troubleshooting and finish

            - **No compute / permission denied:** ask the sandbox owner for notebook
              compute, permission to query an approved tool-calling model, and an
              MLflow experiment you can write to. Do not create paid services blindly.
            - **Package install fails:** retain the resolver error. Do not upgrade
              or replace the pinned stack without retesting.
            - **Subprocess/file access blocked:** this notebook path is unavailable on
              that compute. Use approved compatible compute or an OAuth-protected
              Databricks Apps MCP deployment as a separate setup.
            - **401/403:** notebook identity needs access. Do not paste a token into
              notebook code. Listing endpoints is not query authorization.
            - **400 / unsupported tools or model options:** choose an approved chat
              endpoint with function calling and supported request options.
            - **MLflow storage failure:** ask the admin for the workspace's experiment
              and trace-storage permissions; these vary by sandbox.
            - **429/timeouts:** stop, inspect quota and limits, and rerun a smoke case
              only after addressing the issue. Failed runs remain failed.

            Export answers.json, configuration.json, agent_context.json,
            independent_reference.json and relevant traces from the MLflow run.
            Do not publish credentials or private workspace identifiers. Keep the
            public-only benchmark evidence separate from the internal MCP project.
            Stop/detach compute according to sandbox policy when finished.

            This notebook was assembled and its agent loop checked locally.
            Your Databricks compute, endpoint permissions, model calls, and MLflow
            storage have **not** been tested by the author.
            """,
        ),
    ]
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 4,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        },
        "cells": cells,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
    print(f"Created {output.name}; {len(files)} public-only bundle files.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--candidate-v7-config",
        action="store_true",
        help="use the recorded candidate-v7 endpoint and model options",
    )
    args = parser.parse_args()
    make_notebook(
        args.archive, args.output, candidate_v7_config=args.candidate_v7_config
    )


if __name__ == "__main__":
    main()
