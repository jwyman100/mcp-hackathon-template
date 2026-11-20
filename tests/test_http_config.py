import pytest
from fastmcp import Client

from fisheries_mcp.app import create_server, main, resolve_http_bind
from fisheries_mcp.config import Settings
from submission.container_mcp_smoke import verify


def test_trusted_ingress_setting_uses_documented_environment_name(monkeypatch):
    monkeypatch.setenv("MCP_TRUSTED_HTTP_INGRESS", "true")

    assert Settings(_env_file=None).mcp_trusted_http_ingress is True


def test_platform_port_requires_trusted_ingress() -> None:
    with pytest.raises(ValueError, match="MCP_TRUSTED_HTTP_INGRESS=true"):
        resolve_http_bind(Settings(_env_file=None), "8080")


def test_entrypoint_fails_closed_before_starting_platform_http(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("DATABRICKS_APP_PORT", "")
    monkeypatch.setenv("MCP_TRUSTED_HTTP_INGRESS", "false")

    with pytest.raises(SystemExit, match="MCP_TRUSTED_HTTP_INGRESS=true"):
        main()


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_loopback_http_is_allowed_without_trusted_ingress(host: str) -> None:
    settings = Settings(
        _env_file=None,
        mcp_transport="streamable-http",
        mcp_host=host,
        mcp_port=8123,
    )

    assert resolve_http_bind(settings, None) == (host, 8123)


def test_non_loopback_http_requires_trusted_ingress() -> None:
    settings = Settings(
        _env_file=None,
        mcp_transport="streamable-http",
        mcp_host="0.0.0.0",
    )

    with pytest.raises(ValueError, match="does not add authentication"):
        resolve_http_bind(settings, None)


def test_trusted_ingress_allows_platform_port_but_does_not_authenticate() -> None:
    settings = Settings(_env_file=None, mcp_trusted_http_ingress=True)

    assert resolve_http_bind(settings, "8080") == ("0.0.0.0", 8080)


@pytest.mark.parametrize("port", ["0", "65536", "not-a-port"])
def test_platform_port_is_validated(port: str) -> None:
    settings = Settings(_env_file=None, mcp_trusted_http_ingress=True)

    with pytest.raises(ValueError, match="port"):
        resolve_http_bind(settings, port)


@pytest.mark.asyncio
async def test_container_smoke_checks_real_public_snapshot() -> None:
    from pathlib import Path

    database = Path(__file__).resolve().parents[1] / "data" / "spring.sqlite"
    async with Client(create_server(database)) as client:
        await verify(client)
