from fastmcp import FastMCP

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.models import ComparisonRequest, ComparisonResult


def register(mcp: FastMCP, store: SurveyStore, annotations: dict) -> None:
    @mcp.tool(annotations=annotations)
    def compare_spring_catch(request: ComparisonRequest) -> ComparisonResult:
        """Compare distinct species on identical years/strata with shared coverage.

        Compare exactly two distinct species from the fixed snapshot (Atlantic
        cod and haddock). Years are inclusive 2021-2025; strata must match.
        Returns each series, shared station coverage, and complete_matched_years
        where both species have all catch measurements. Alias names resolving to
        one species are rejected. Exact published labels returned by search are
        accepted. This does not establish matched effort, calibration, or
        population abundance.
        """
        return store.compare(request)
