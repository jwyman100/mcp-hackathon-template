#!/usr/bin/env python
"""Local MCP toolkit entrypoint for watsonx Orchestrate (stdio transport).

watsonx Orchestrate runs a LOCAL MCP toolkit by starting this script inside its
own runtime and speaking MCP over stdio. This entrypoint reuses the EXISTING
FastMCP server defined in the `fisheries_mcp` package and runs it over stdio —
no HTTP, no Code Engine, no container.

The register script stages this file NEXT TO the `fisheries_mcp` package
(flattened out of the repo's src/ layout), so `fisheries_mcp` is importable
from this script's own directory. We add that directory to sys.path defensively
in case Orchestrate runs the command from a different working directory.

Orchestrate invokes:  python server.py
"""

import os
import sys

# Ensure the directory containing this file (which also contains the
# `fisheries_mcp` package after staging) is importable, regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path  # noqa: E402

from fisheries_mcp.app import create_server  # noqa: E402
from fisheries_mcp.data import SurveyStore  # noqa: E402

if __name__ == "__main__":
    # stdio is the transport watsonx Orchestrate uses for local MCP toolkits.
    database = Path(__file__).resolve().parent / "data" / "spring.sqlite"
    SurveyStore(database).validate()
    create_server(database).run(transport="stdio")
