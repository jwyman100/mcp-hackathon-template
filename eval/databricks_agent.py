"""Bounded model-selected tool loop without database access or gold answers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

Complete = Callable[[list[dict], list[dict]], Awaitable[dict]]
Invoke = Callable[[str, dict], Awaitable[dict]]


async def run_agent(
    question: str,
    tools: list[dict],
    dictionary: str,
    complete: Complete,
    invoke: Invoke,
    *,
    max_rounds: int = 6,
    max_tool_calls: int = 8,
    arm: str = "mcp",
) -> dict[str, Any]:
    """Give a model only discovered tools, shared context, and a question."""
    if max_rounds < 1 or max_tool_calls < 1:
        raise ValueError("Agent limits must be positive.")
    if arm not in {"mcp", "no_tools"}:
        raise ValueError("Evaluation arm must be mcp or no_tools.")
    if arm == "no_tools":
        tools = []
    allowed = {tool["function"]["name"] for tool in tools}
    access_instruction = (
        "Answer using the provided fisheries MCP tools. Use tools for "
        "numerical results. "
        if arm == "mcp"
        else "Answer without tools or external data access. If the available "
        "context cannot support numerical results, say so. "
    )
    messages = [
        {
            "role": "system",
            "content": (
                access_instruction + "Preserve source, scope, missing values, units "
                "and scientific limitations. Explain unsupported requests without "
                "inventing answers. The shared MCP data dictionary follows:\n"
                + dictionary
            ),
        },
        {"role": "user", "content": question},
    ]
    calls = []
    usages = []
    for _ in range(max_rounds):
        response = await complete(messages, tools)
        usages.append(response.get("usage"))
        choice = response["choices"][0]
        if choice["finish_reason"] not in {"stop", "tool_calls"}:
            raise RuntimeError(f"Incomplete model response: {choice['finish_reason']}")
        message = choice["message"]
        requested = message.get("tool_calls") or []
        if arm == "no_tools" and requested:
            raise RuntimeError("No-tool baseline returned an unexpected tool call.")
        assistant = {"role": "assistant", "content": message.get("content")}
        if requested:
            assistant["tool_calls"] = requested
        messages.append(assistant)
        if not requested:
            answer = message.get("content") or message.get("refusal")
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("Model returned neither an answer nor a tool call.")
            return {
                "answer": answer,
                "tool_calls": calls,
                "messages": messages,
                "model_usage": usages,
                "execution_status": "completed",
                "scientific_review": "UNVERIFIED",
                "evaluation_arm": arm,
            }
        if len(calls) + len(requested) > max_tool_calls:
            raise RuntimeError("Agent tool-call budget exceeded.")
        for call in requested:
            name = call["function"]["name"]
            raw_arguments = call["function"]["arguments"]
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = None
            if name not in allowed:
                result = {"is_error": True, "content": "Use a discovered MCP tool."}
            elif not isinstance(arguments, dict):
                result = {
                    "is_error": True,
                    "content": "Arguments must be a JSON object.",
                }
            else:
                result = await invoke(name, arguments)
            calls.append(
                {
                    "name": name,
                    "arguments": arguments,
                    "raw_arguments": raw_arguments,
                    "result": result,
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                }
            )
    raise RuntimeError("Agent model-round budget exceeded without a final answer.")
