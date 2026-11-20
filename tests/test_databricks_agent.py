import importlib.util
import json
from pathlib import Path

import pytest
from fastmcp import Client

from fisheries_mcp.app import create_server

SPEC = importlib.util.spec_from_file_location(
    "databricks_agent",
    Path(__file__).resolve().parents[1] / "eval" / "databricks_agent.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
run_agent = MODULE.run_agent


def response(arguments=None, name="search_species"):
    message = {"role": "assistant", "content": "Published cod identity found."}
    if arguments is not None:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call1",
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
            ],
        }
    return {
        "choices": [
            {
                "message": message,
                "finish_reason": "tool_calls" if arguments is not None else "stop",
            }
        ]
    }


@pytest.mark.asyncio
async def test_model_selected_call_reaches_real_mcp_without_gold(snapshot):
    async with Client(create_server(snapshot)) as client:
        discovered = await client.list_tools()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in discovered
        ]
        calls = 0

        async def complete(messages, available_tools):
            nonlocal calls
            calls += 1
            assert available_tools == tools
            assert messages[1] == {"role": "user", "content": "Find cod"}
            assert all("gold" not in item for item in messages)
            if calls == 1:
                return response(json.dumps({"request": {"term": "cod"}}))
            assert (
                json.loads(messages[-1]["content"])["content"]["species"][0]["code"]
                == "073"
            )
            return response()

        async def invoke(name, arguments):
            result = await client.call_tool(name, arguments)
            return {"is_error": False, "content": result.structured_content}

        result = await run_agent("Find cod", tools, "Public scope", complete, invoke)
        assert calls == 2
        assert result["tool_calls"][0]["name"] == "search_species"
        assert result["scientific_review"] == "UNVERIFIED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "name"),
    [("not json", "search_species"), ("[]", "search_species"), ("{}", "execute_sql")],
)
async def test_invalid_model_call_is_not_dispatched(arguments, name):
    tools = [{"function": {"name": "search_species"}}]
    responses = iter([response(arguments, name), response()])

    async def complete(messages, available_tools):
        return next(responses)

    async def invoke(name, arguments):
        pytest.fail("Invalid or undiscovered tool must not execute.")

    result = await run_agent("Find cod", tools, "Public scope", complete, invoke)
    assert result["tool_calls"][0]["result"]["is_error"] is True


@pytest.mark.asyncio
async def test_infinite_tool_loop_is_bounded():
    async def complete(messages, tools):
        return response("{}")

    async def invoke(name, arguments):
        return {"is_error": True, "content": "Invalid request."}

    with pytest.raises(RuntimeError, match="tool-call budget"):
        await run_agent(
            "Find cod",
            [{"function": {"name": "search_species"}}],
            "Public scope",
            complete,
            invoke,
            max_tool_calls=1,
        )


@pytest.mark.asyncio
async def test_truncated_answer_is_not_reported_as_completed():
    async def complete(messages, tools):
        value = response()
        value["choices"][0]["finish_reason"] = "length"
        return value

    async def invoke(name, arguments):
        pytest.fail("No tool should execute.")

    with pytest.raises(RuntimeError, match="Incomplete model response"):
        await run_agent("Find cod", [], "Public scope", complete, invoke)


@pytest.mark.asyncio
async def test_no_tool_baseline_preserves_context_but_cannot_dispatch():
    async def complete(messages, tools):
        assert tools == []
        assert messages[1]["content"] == "Find cod"
        assert "Public scope" in messages[0]["content"]
        assert "without tools or external data access" in messages[0]["content"]
        return response()

    async def invoke(name, arguments):
        pytest.fail("Baseline cannot dispatch tools.")

    result = await run_agent(
        "Find cod",
        [{"function": {"name": "search_species"}}],
        "Public scope",
        complete,
        invoke,
        arm="no_tools",
    )
    assert result["tool_calls"] == []
    assert result["evaluation_arm"] == "no_tools"
    assert result["scientific_review"] == "UNVERIFIED"


@pytest.mark.asyncio
async def test_no_tool_baseline_rejects_unexpected_call():
    async def complete(messages, tools):
        return response("{}")

    async def invoke(name, arguments):
        pytest.fail("Baseline cannot dispatch tools.")

    with pytest.raises(RuntimeError, match="unexpected tool call"):
        await run_agent(
            "Find cod", [], "Public scope", complete, invoke, arm="no_tools"
        )
