from fastmcp import FastMCP

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.models import SummaryRequest, SummaryResult


def register(mcp: FastMCP, store: SurveyStore, annotations: dict) -> None:
    @mcp.tool(annotations=annotations)
    def get_spring_catch_summary(request: SummaryRequest) -> SummaryResult:
        """Summarize one species' public spring expanded catch and coverage.

        Use only for Atlantic cod or haddock in the fixed 2021-2025 public
        snapshot, not for current/live data. Provide an exact common name,
        scientific name, or published label; call search_species if uncertain.
        Years are inclusive and strata default to all. Returns yearly totals,
        measurement completeness, matched-scope station coverage and source
        provenance. Missing/unknown is not zero. Weight units are unspecified;
        totals are not abundance indices.
        """
        return store.summary(request)
