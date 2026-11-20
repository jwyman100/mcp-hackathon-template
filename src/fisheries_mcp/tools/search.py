from fastmcp import FastMCP

from fisheries_mcp.data import SurveyStore
from fisheries_mcp.models import SearchRequest, SearchResult


def register(mcp: FastMCP, store: SurveyStore, annotations: dict) -> None:
    @mcp.tool(annotations=annotations)
    def search_species(request: SearchRequest) -> SearchResult:
        """Find published common/scientific names in the fixed public snapshot.

        Search partial names first; analysis tools accept the exact common name,
        scientific name, or published label returned here.
        Only Atlantic cod and haddock are in this fixed snapshot, not the full
        NOAA/SVDBS catalog. An empty result does not mean absent from the source
        survey. Returns matching names/codes and exact public provenance.
        """
        return store.search(request)
