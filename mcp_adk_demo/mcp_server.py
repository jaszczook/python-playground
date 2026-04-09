"""
FastMCP server — auto-loads OpenAPI specs from examples/*.json.

JWT is forwarded to upstream APIs via FastMCP's get_http_headers() dependency.

A single httpx client is shared across all providers (one connection pool to
the upstream host). Each spec's gateway prefix comes from servers[0].url and
is prepended to all its paths before being handed to OpenAPIProvider, so the
client only needs base_url=API_HOST.

Run:
  API_HOST=http://localhost:8000 python mcp_server.py
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.providers.openapi import OpenAPIProvider

SPECS_DIR = Path(__file__).parent / "examples"
API_HOST = os.environ.get("API_HOST", "http://localhost:8000").rstrip("/")
SSL_CA_BUNDLE = os.environ.get("SSL_CA_BUNDLE")  # path to CA cert or bundle; "false" disables verification (dev only)

_verify: bool | str = False if SSL_CA_BUNDLE == "false" else (SSL_CA_BUNDLE or True)


async def _inject_jwt(request: httpx.Request) -> None:
    auth = get_http_headers(include={"authorization"}).get("authorization", "")
    if auth:
        request.headers["Authorization"] = auth


def _load_spec(path: Path) -> dict:
    return json.loads(path.read_text())


def _prefix_spec_paths(spec: dict) -> dict:
    """Prepend the gateway prefix from servers[0].url to every path in the spec.

    This allows all providers to share a single httpx client with base_url=API_HOST
    while still routing to the correct gateway prefix per spec.
    """
    servers = spec.get("servers", [])
    prefix = urlparse(servers[0]["url"]).path.rstrip("/") if servers else ""
    if not prefix:
        return spec
    return {**spec, "paths": {prefix + p: v for p, v in spec.get("paths", {}).items()}}


# Single shared client — one connection pool to the upstream host.
_client = httpx.AsyncClient(
    base_url=API_HOST,
    verify=_verify,
    timeout=30.0,
    event_hooks={"request": [_inject_jwt]},
)


@lifespan
async def _lifespan(server: FastMCP):
    yield
    await _client.aclose()


mcp = FastMCP("Task Manager", middleware=[LoggingMiddleware()], lifespan=_lifespan)
for spec_file in sorted(SPECS_DIR.glob("*.json")):
    mcp.add_provider(
        OpenAPIProvider(openapi_spec=_prefix_spec_paths(_load_spec(spec_file)), client=_client, validate_output=False),
        namespace=spec_file.stem,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
