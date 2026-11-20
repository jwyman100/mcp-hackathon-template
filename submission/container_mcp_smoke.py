"""Verify tool discovery and public-snapshot results through an MCP connection."""

import argparse
import asyncio
import math

from fastmcp import Client


async def verify(client: Client) -> None:
    names = {tool.name for tool in await client.list_tools()}
    if not {"search_species", "get_spring_catch_summary"} <= names:
        raise RuntimeError("The expected fisheries MCP tools were not discovered.")
    search = await client.call_tool("search_species", {"request": {"term": "cod"}})
    species = search.structured_content["species"]
    if len(species) != 1 or species[0]["code"] != "073":
        raise RuntimeError("The MCP server did not return the expected cod identity.")
    summary = await client.call_tool(
        "get_spring_catch_summary",
        {
            "request": {
                "species_name": species[0]["published_label"],
                "start_year": 2022,
                "end_year": 2023,
            }
        },
    )
    rows = summary.structured_content["series"]["annual_catch"]
    weights = {row["year"]: row["total_expanded_weight"] for row in rows}
    expected = {2022: 609.78, 2023: 416.396}
    if set(weights) != set(expected) or any(
        not isinstance(weights[year], (int, float))
        or not math.isclose(weights[year], value, rel_tol=1e-10, abs_tol=1e-8)
        for year, value in expected.items()
    ):
        raise RuntimeError(f"Unexpected public-snapshot cod weights: {weights}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="MCP endpoint URL, including /mcp")
    args = parser.parse_args()
    async with Client(args.url) as client:
        await verify(client)
    print("MCP initialization, discovery, cod search and public catch query passed.")


if __name__ == "__main__":
    asyncio.run(main())
