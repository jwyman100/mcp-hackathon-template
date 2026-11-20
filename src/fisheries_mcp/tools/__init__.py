from fastmcp import FastMCP

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.tools import compare, coverage, report_context, search, summary

READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


def register_tools(mcp: FastMCP, store: SurveyStore) -> None:
    for module in (search, summary, compare, coverage, report_context):
        module.register(mcp, store, READ_ONLY)
