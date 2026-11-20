from fastmcp import FastMCP

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.models import CoverageResult, SurveyScope


def register(mcp: FastMCP, store: SurveyStore, annotations: dict) -> None:
    @mcp.tool(annotations=annotations)
    def get_spring_survey_coverage(request: SurveyScope) -> CoverageResult:
        """Check public station/cruise/stratum coverage before interpreting catch.

        Use only the fixed 2021-2025 snapshot. Years are inclusive and strata
        default to all published strata. Counts stations, cruises and sampled
        strata, not necessarily valid hauls or standardized effort. Years with
        no station records are explicit; out-of-snapshot years are rejected.
        """
        return store.coverage(request)
