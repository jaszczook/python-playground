"""
FastMCP server built from openapi_spec.json.

JWT forwarding strategy is selected via JWT_METHOD env var (default: CONTEXT_VAR).

Available methods:
  FASTMCP_DEPS  — use FastMCP's get_http_headers() dependency (works only if FastMCP
                  populates it correctly for the transport in use; may return empty)
  CONTEXT_VAR   — Starlette middleware captures the incoming Authorization header into
                  a ContextVar; the httpx hook reads it from there (reliable)
  ENV_TOKEN     — read a static Bearer token from JWT_TOKEN env var (useful for local
                  dev / testing without a real auth flow)

Run:
  API_BASE_URL=http://real-api:8000 python mcp_server.py
  JWT_METHOD=ENV_TOKEN JWT_TOKEN=mytoken API_BASE_URL=... python mcp_server.py
"""

import json
import logging
import os
from contextvars import ContextVar
from enum import Enum
from pathlib import Path

import httpx
import uvicorn
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from starlette.middleware.base import BaseHTTPMiddleware

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
SSL_CA_BUNDLE = os.environ.get("SSL_CA_BUNDLE")  # path to CA cert or bundle, or "false" to disable


class JwtMethod(str, Enum):
    FASTMCP_DEPS = "FASTMCP_DEPS"  # FastMCP get_http_headers() — may not work on all transports
    CONTEXT_VAR = "CONTEXT_VAR"    # ContextVar set by Starlette middleware — reliable
    ENV_TOKEN = "ENV_TOKEN"        # static token from JWT_TOKEN env var — for local dev


JWT_METHOD = JwtMethod(os.environ.get("JWT_METHOD", JwtMethod.CONTEXT_VAR))

# ---------------------------------------------------------------------------
# Method: CONTEXT_VAR
# ---------------------------------------------------------------------------

_auth_ctx: ContextVar[str] = ContextVar("auth_header", default="")


class _CaptureAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = _auth_ctx.set(request.headers.get("authorization", ""))
        try:
            return await call_next(request)
        finally:
            _auth_ctx.reset(token)


# ---------------------------------------------------------------------------
# httpx event hook — resolves auth based on selected method
# ---------------------------------------------------------------------------

logger = logging.getLogger("mcp_server.openapi")


async def _inject_jwt(request: httpx.Request) -> None:
    """Forward a Bearer token to every upstream API call."""
    auth = _resolve_auth()
    if auth:
        request.headers["Authorization"] = auth


async def _log_response(response: httpx.Response) -> None:
    """Log every response (and error bodies) from the upstream OpenAPI provider."""
    await response.aread()
    level = logging.WARNING if response.is_error else logging.DEBUG
    logger.log(
        level,
        "%s %s → %s\n%s",
        response.request.method,
        response.request.url,
        response.status_code,
        response.text,
    )


def _resolve_auth() -> str:
    if JWT_METHOD == JwtMethod.FASTMCP_DEPS:
        return get_http_headers().get("authorization", "")

    if JWT_METHOD == JwtMethod.CONTEXT_VAR:
        return _auth_ctx.get()

    if JWT_METHOD == JwtMethod.ENV_TOKEN:
        token = os.environ.get("JWT_TOKEN", "")
        return f"Bearer {token}" if token else ""

    return ""


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

_verify: bool | str = False if SSL_CA_BUNDLE == "false" else (SSL_CA_BUNDLE or True)
client = httpx.AsyncClient(
    base_url=API_BASE_URL,
    verify=_verify,
    event_hooks={"request": [_inject_jwt], "response": [_log_response]},
)

spec = json.loads((Path(__file__).parent / "openapi_spec.json").read_text())
mcp = FastMCP.from_openapi(openapi_spec=spec, client=client)

class _LogExceptionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error during %s %s", request.method, request.url.path)
            raise


app = mcp.http_app()

app.add_middleware(_LogExceptionsMiddleware)
if JWT_METHOD == JwtMethod.CONTEXT_VAR:
    app.add_middleware(_CaptureAuthMiddleware)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
    print(f"JWT_METHOD={JWT_METHOD.value}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
