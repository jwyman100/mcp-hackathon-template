"""Run a reproducible, public-only MCP demonstration without a model call."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from receipt import make_receipt, read_receipt, replay_receipt, write_receipt

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--receipt",
        type=Path,
        help="write a public-only receipt to a new path after the scripted demo",
    )
    parser.add_argument(
        "--replay",
        type=Path,
        help="replay a receipt and fail if its source, server, or results changed",
    )
    args = parser.parse_args()
    if args.receipt and args.replay:
        parser.error("--receipt and --replay cannot be used together")
    if args.replay:
        await replay_receipt(read_receipt(args.replay))
        print(f"Replay passed: {args.replay}")
        return

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "fisheries_mcp.app"],
        cwd=str(ROOT),
        env={
            **os.environ,
            "FISHERIES_DATABASE": str(ROOT / "data" / "spring.sqlite"),
            "MCP_TRANSPORT": "stdio",
            "PORT": "",
            "DATABRICKS_APP_PORT": "",
            "FASTMCP_LOG_LEVEL": "ERROR",
        },
    )
    calls = []

    async with Client(transport) as client:
        search = await client.call_tool("search_species", {"request": {"term": "cod"}})
        found = search.structured_content["species"]
        if len(found) != 1 or found[0]["code"] != "073":
            raise RuntimeError("The public demo snapshot must contain Atlantic cod.")
        species = found[0]
        calls.append(
            {
                "tool": "search_species",
                "arguments": {"request": {"term": "cod"}},
                "result": search.structured_content,
            }
        )
        request = {
            "species_name": species["published_label"],
            "start_year": 2022,
            "end_year": 2023,
        }
        summary = await client.call_tool(
            "get_spring_catch_summary", {"request": request}
        )
        calls.append(
            {
                "tool": "get_spring_catch_summary",
                "arguments": {"request": request},
                "result": summary.structured_content,
            }
        )
        context = await client.call_tool(
            "get_spring_report_context", {"request": {"year": 2023}}
        )
        calls.append(
            {
                "tool": "get_spring_report_context",
                "arguments": {"request": {"year": 2023}},
                "result": context.structured_content,
            }
        )

    data = summary.structured_content
    card = context.structured_content
    print("SCRIPTED MCP DEMO: no model selected these calls or wrote this output.")
    print("Research question: How should 2023 cod catch be interpreted against 2022?")
    print(f"\n1. search_species('cod') -> {species['published_label']}")
    print("2. get_spring_catch_summary: exact returned label; 2022-2023")
    print("   Year  Expanded weight  Expanded number  Station records  Sampled strata")
    coverage = {item["year"]: item for item in data["annual_coverage"]}
    for row in data["series"]["annual_catch"]:
        weight = row["total_expanded_weight"]
        number = row["total_expanded_number"]
        weight_text = "null" if weight is None else f"{weight:.3f}"
        number_text = "null" if number is None else f"{number:g}"
        scope = coverage[row["year"]]
        print(
            f"   {row['year']}  {weight_text:>15}  {number_text:>15}  "
            f"{scope['station_records']:>15}  {scope['sampled_strata']:>14}"
        )
    print("\n3. get_spring_report_context(2023): curated NOAA source card")
    for fact in card["facts"]:
        print(f"   - {fact}")
    print(f"   Source: {card['source']['url']}")
    print(f"\nSnapshot metadata: {data['provenance']['metadata_url']}")
    print(
        "Handoff: weights are in unspecified source units; station records "
        "and the report's sampled trawl stations are different measures."
    )
    print(
        "A stratum count is not geographic area. Catch totals do not establish "
        "a population trend; a scientist must review sampling and analysis "
        "before drawing that conclusion."
    )
    print(
        "Interpretation boundary: the shortened survey is relevant context, "
        "not proof of why the cod totals differ."
    )
    print(
        "Question for a scientist: which locations and sampling conditions "
        "are comparable, and what analysis would support that comparison?"
    )
    if args.receipt:
        receipt = make_receipt(
            calls,
            "How should 2023 cod catch be interpreted against 2022?",
            source_sha256=data["provenance"]["source_sha256"],
        )
        write_receipt(args.receipt, receipt)
        print(f"\nPublic-only evidence receipt written to: {args.receipt}")


if __name__ == "__main__":
    asyncio.run(main())
