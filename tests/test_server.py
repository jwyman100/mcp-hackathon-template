import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError
from jsonschema import validate

from fisheries_mcp.app import create_server


@pytest.mark.asyncio
async def test_mcp_discovery_results_resource_and_prompt(snapshot):
    async with Client(create_server(snapshot)) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == {
            "search_species",
            "get_spring_catch_summary",
            "compare_spring_catch",
            "get_spring_survey_coverage",
            "get_spring_report_context",
        }
        assert all(tool.annotations.readOnlyHint for tool in tools)
        tool_schemas = {tool.name: tool.inputSchema for tool in tools}
        year_schema = tool_schemas["get_spring_survey_coverage"]["properties"][
            "request"
        ]["properties"]["start_year"]
        assert year_schema["minimum"] == 2021
        assert year_schema["maximum"] == 2025
        result = await client.call_tool(
            "get_spring_catch_summary", {"request": {"species_name": "Atlantic cod"}}
        )
        assert result.structured_content["series"]["species"]["code"] == "073"
        resource = await client.read_resource("fisheries://dictionary")
        dictionary = json.loads(resource[0].text)
        assert dictionary["provenance"]["dataset_kind"] == "synthetic"
        assert dictionary["supported_analyses"]
        assert dictionary["unsupported_analyses"]
        prompt = await client.get_prompt("responsible_comparison")
        assert "population" in prompt.messages[0].content.text
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_spring_survey_coverage", {"request": {"minimum_stratum": "bad"}}
            )
        with pytest.raises(ToolError, match="greater than or equal to 2021"):
            await client.call_tool(
                "get_spring_survey_coverage", {"request": {"start_year": 2020}}
            )


@pytest.mark.asyncio
async def test_real_stdio_transport(snapshot):
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "fisheries_mcp.app"],
        env={
            **os.environ,
            "FISHERIES_DATABASE": str(snapshot),
            "MCP_TRANSPORT": "stdio",
            "PORT": "",
            "DATABRICKS_APP_PORT": "",
        },
    )
    async with Client(transport) as client:
        result = await client.call_tool(
            "search_species", {"request": {"term": "haddock"}}
        )
        species = result.structured_content["species"][0]
        assert species["code"] == "074"
        summary = await client.call_tool(
            "get_spring_catch_summary",
            {"request": {"species_name": species["published_label"]}},
        )
        assert summary.structured_content["series"]["species"]["code"] == "074"
        context = await client.call_tool(
            "get_spring_report_context", {"request": {"year": 2023}}
        )
        tools = await client.list_tools()
        context_schema = next(
            tool.outputSchema
            for tool in tools
            if tool.name == "get_spring_report_context"
        )
        validate(context.structured_content, context_schema)
        assert context.structured_content["year"] == 2023
        assert context.structured_content["source"]["url"].startswith(
            "https://www.fisheries.noaa.gov/"
        )
        assert context.structured_content["source"]["source_checked_on"]
        assert (
            context.structured_content["source"]["scientific_review_status"]
            == "not_reviewed"
        )
        assert any("70 of 377" in fact for fact in context.structured_content["facts"])
        overview = await client.call_tool(
            "get_spring_report_context", {"request": {"year": 2025}}
        )
        assert overview.structured_content["source"]["locator"] == (
            "Overview, physical PDF page 3"
        )
        assert (
            "370 representative and 25 non-representative"
            in (overview.structured_content["facts"][0])
        )
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_spring_report_context", {"request": {"year": 2024}}
            )


@pytest.mark.asyncio
async def test_loopback_http_and_snapshot_readiness(snapshot):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "fisheries_mcp.app"],
        env={
            **os.environ,
            "FISHERIES_DATABASE": str(snapshot),
            "MCP_TRANSPORT": "streamable-http",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(port),
            "PORT": "",
            "DATABRICKS_APP_PORT": "",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=1) as http:
            for _ in range(100):
                if process.poll() is not None:
                    pytest.fail(process.communicate()[1].decode(errors="replace"))
                try:
                    response = await http.get(base + "/health")
                    if response.status_code == 200:
                        break
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    pass
                await asyncio.sleep(0.1)
            else:
                pytest.fail("Loopback HTTP server did not become ready.")
            async with Client(base + "/mcp") as client:
                assert len(await client.list_tools()) == 5
                result = await client.call_tool(
                    "compare_spring_catch",
                    {"request": {"species_names": ["Atlantic cod", "haddock"]}},
                )
                assert (
                    result.structured_content["provenance"]["dataset_kind"]
                    == "synthetic"
                )
            snapshot.rename(snapshot.with_suffix(".unavailable"))
            assert (await http.get(base + "/health")).status_code == 503
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def test_startup_rejects_missing_snapshot(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "fisheries_mcp.app"],
        env={**os.environ, "FISHERIES_DATABASE": str(tmp_path / "absent.sqlite")},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0
    assert "Run fisheries-prepare first" in result.stderr


def test_public_demo_runs_over_mcp_stdio():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "submission" / "demo.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "no model selected these calls" in result.stdout
    assert "Gadus morhua (Atlantic cod)" in result.stdout
    assert "609.780" in result.stdout and "416.396" in result.stdout
    assert "curated NOAA source card" in result.stdout
    assert "A stratum count is not geographic area" in result.stdout
