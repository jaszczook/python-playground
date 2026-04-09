"""
FastMCP server — auto-loads OpenAPI specs from examples/*.json.

JWT is forwarded to upstream APIs via FastMCP's get_http_headers() dependency.

Run:
  TASKS_API_BASE_URL=http://localhost:8000 USERS_API_BASE_URL=http://localhost:9000 python mcp_server.py
"""

import json
import os
from pathlib import Path

import httpx
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.providers.openapi import OpenAPIProvider

SPECS_DIR = Path(__file__).parent / "examples"
SSL_CA_BUNDLE = os.environ.get("SSL_CA_BUNDLE")  # path to CA cert or bundle; "false" disables verification (dev only)

_verify: bool | str = False if SSL_CA_BUNDLE == "false" else (SSL_CA_BUNDLE or True)


async def _inject_jwt(request: httpx.Request) -> None:
    auth = get_http_headers(include={"authorization"}).get("authorization", "")
    if auth:
        request.headers["Authorization"] = auth


def _make_client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        verify=_verify,
        timeout=30.0,
        event_hooks={"request": [_inject_jwt]},
    )


def _load_spec(path: Path) -> dict:
    return json.loads(path.read_text())


mcp = FastMCP("Task Manager", middleware=[LoggingMiddleware()])
for spec_file in sorted(SPECS_DIR.glob("*.json")):
    namespace = spec_file.stem
    base_url = os.environ.get(f"{namespace.upper()}_API_BASE_URL", "http://localhost:8000").rstrip("/")
    mcp.add_provider(
        OpenAPIProvider(openapi_spec=_load_spec(spec_file), client=_make_client(base_url)),
        namespace=namespace,
    )

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
