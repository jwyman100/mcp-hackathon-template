from fastmcp import FastMCP

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.models import ReportContextRequest, ReportContextResult, ReportSource

CONTEXT = {
    2023: ReportContextResult(
        year=2023,
        source=ReportSource(
            title="2023 Northeast Spring Bottom Trawl Survey Summary",
            url=(
                "https://www.fisheries.noaa.gov/new-england-mid-atlantic/"
                "ecosystems/2023-northeast-spring-bottom-trawl-survey-summary"
            ),
            locator="Opening operational-summary paragraphs",
            source_checked_on="2026-11-19",
            scientific_review_status="not_reviewed",
        ),
        facts=[
            "NOAA reports that ship repair and maintenance delays reduced "
            "sea days by about 75%.",
            "A crew shortage reduced operations from 24 to 12 hours per day.",
            "The survey focused on Georges Bank and sampled 70 of 377 planned "
            "trawl stations.",
            "Stations were sampled during daytime only; NOAA says combining "
            "these observations with previous day/night data requires "
            "additional evaluation.",
        ],
        limitations=[
            "These are curated statements from the linked NOAA page, not live "
            "report retrieval or facts derived from snapshot rows.",
            "The report's sampled trawl stations and the snapshot's station "
            "records are distinct measures; no reconciliation is implied.",
            "Neither a stratum count nor catch totals establish geographic area "
            "coverage, the cause of catch changes, or a population trend.",
        ],
    ),
    2025: ReportContextResult(
        year=2025,
        source=ReportSource(
            title="2025 Spring Multispecies Bottom Trawl Survey",
            url="https://repository.library.noaa.gov/view/noaa/72382",
            locator="Overview, physical PDF page 3",
            source_checked_on="2026-11-19",
            scientific_review_status="not_reviewed",
        ),
        facts=["NOAA reports 370 representative and 25 non-representative stations."],
        limitations=[
            "This is a curated statement from the linked NOAA report, not live "
            "report retrieval or a classification of snapshot records.",
            "Equal aggregate station counts do not prove record-by-record "
            "identity or make all records representative hauls.",
            "The tool does not expose the report's haul-level catch table or "
            "establish a representative-haul catch reconciliation.",
        ],
    ),
}


def register(mcp: FastMCP, _store: SurveyStore, annotations: dict) -> None:
    @mcp.tool(annotations=annotations)
    def get_spring_report_context(request: ReportContextRequest) -> ReportContextResult:
        """Read curated, cited NOAA survey-report context for 2023 or 2025.

        Use alongside catch and coverage when interpreting survey conditions.
        Returns selected source statements and limitations, not the full report
        or live retrieval. Report counts are separate from snapshot records.
        Only 2023 and 2025 context cards are available.
        """
        return CONTEXT[request.year]
