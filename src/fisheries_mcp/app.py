"""Thin entry point for local stdio and explicit sandbox HTTP use."""

import ipaddress
import logging
import os
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from fisheries_mcp import __version__
from fisheries_mcp.config import Settings
from fisheries_mcp.data import SurveyStore
from fisheries_mcp.prepare import DataError
from fisheries_mcp.tools import register_tools


def _is_loopback(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def resolve_http_bind(
    settings: Settings, platform_port: str | None
) -> tuple[str, int] | None:
    if platform_port:
        if not settings.mcp_trusted_http_ingress:
            raise ValueError(
                "A platform-provided port requires MCP_TRUSTED_HTTP_INGRESS=true "
                "after verifying an approved authenticated ingress. This setting "
                "does not add authentication."
            )
        try:
            port = int(platform_port)
        except ValueError:
            raise ValueError("The platform-provided HTTP port is invalid.") from None
        if not 1 <= port <= 65535:
            raise ValueError("The platform-provided HTTP port is outside 1-65535.")
        return "0.0.0.0", port

    if settings.mcp_transport != "streamable-http":
        return None
    if not settings.mcp_trusted_http_ingress and not _is_loopback(settings.mcp_host):
        raise ValueError(
            "Non-loopback HTTP requires MCP_TRUSTED_HTTP_INGRESS=true after "
            "verifying an approved authenticated ingress. This setting does "
            "not add authentication."
        )
    return settings.mcp_host, settings.mcp_port


def create_server(database: Path) -> FastMCP:
    store = SurveyStore(database)
    mcp = FastMCP(
        name="Evidence-aware Fisheries",
        instructions=(
            "Use only this public audited NEFSC spring bottom-trawl snapshot for "
            "Atlantic cod and haddock (2021-2025); it is not the full database. "
            "Read fisheries://dictionary for source, scope, field meanings, and "
            "unsupported analyses. Search exact published names; do not guess. "
            "For 2023 or 2025 survey context, use get_spring_report_context; its "
            "curated report statements are separate from snapshot records. "
            "Preserve nulls, coverage, source identity and weight-unit uncertainty. "
            "Catch totals are not population indices, stock status, biomass, or "
            "fishing mortality. Do not treat absent catch rows as observed zero "
            "or evidence that no survey effort occurred. A count of strata is not "
            "a percentage of geographic area. Do not claim live/current data. "
            "For out-of-scope autumn, length, PARR "
            "export, or assessment requests, explain the limitation without "
            "substituting an unsupported calculation."
        ),
    )
    register_tools(mcp, store)

    @mcp.resource("fisheries://dictionary")
    def data_dictionary() -> dict:
        """Public source, supported scope, field meanings, and analysis limits."""
        return store.dictionary()

    @mcp.prompt()
    def responsible_comparison() -> str:
        """A reproducible public-data comparison with explicit scientific limits."""
        return (
            "Read fisheries://dictionary. Resolve Atlantic cod and haddock, then "
            "compare spring catch for 2021-2025 across all snapshot strata. Report "
            "coverage, complete matched years, missing measurements, source "
            "identity and unit uncertainty. Explain why this is not evidence of "
            "population growth or decline."
        )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        try:
            store.validate()
        except DataError:
            return JSONResponse({"status": "snapshot_unavailable"}, status_code=503)
        return JSONResponse({"status": "healthy", "service": "fisheries-mcp"})

    @mcp.custom_route("/version", methods=["GET"])
    async def version(request: Request) -> JSONResponse:
        return JSONResponse({"version": __version__})

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    settings = Settings()
    platform_port = os.getenv("DATABRICKS_APP_PORT") or os.getenv("PORT")
    try:
        http_bind = resolve_http_bind(settings, platform_port)
    except ValueError as error:
        raise SystemExit(f"Cannot start fisheries MCP: {error}") from None
    try:
        SurveyStore(settings.fisheries_database).validate()
    except DataError as error:
        raise SystemExit(f"Cannot start fisheries MCP: {error}") from None
    server = create_server(settings.fisheries_database)
    if http_bind:
        host, port = http_bind
        server.run(
            transport="streamable-http",
            host=host,
            port=port,
            stateless_http=True,
        )
    else:
        server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
