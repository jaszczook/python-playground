"""
FastMCP server built from openapi_spec.json.

JWT forwarding: FastMCP's get_http_headers() is called inside the httpx
event hook (which runs during tool execution, inside FastMCP's request
context), so no custom middleware or ContextVar is needed.

Run:
  API_BASE_URL=http://real-api:8000 python mcp_server.py
"""

import json
import os
from pathlib import Path

import httpx
import uvicorn
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")


async def _inject_jwt(request: httpx.Request) -> None:
    """Forward the caller's Bearer token to every upstream API call."""
    auth = get_http_headers().get("authorization", "")
    if auth:
        request.headers["Authorization"] = auth


client = httpx.AsyncClient(
    base_url=API_BASE_URL,
    event_hooks={"request": [_inject_jwt]},
)

spec = json.loads((Path(__file__).parent / "openapi_spec.json").read_text())
mcp = FastMCP.from_openapi(openapi_spec=spec, client=client)

app = mcp.http_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
