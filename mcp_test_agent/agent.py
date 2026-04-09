"""
ADK agent for local testing with `adk web` or by running this file directly.
Mock JWT is hardcoded — swap it for a real token when needed.

Run via CLI:    adk web
Run in IntelliJ: run this file (uses the same internals as `adk web`)
"""

import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

MOCK_JWT = "mock-jwt-token-for-testing"
MCP_URL = os.environ.get("MCP_URL", "http://localhost:8080/mcp")


def _header_provider(readonly_context: ReadonlyContext) -> dict[str, str]:
    return {"Authorization": f"Bearer {MOCK_JWT}"}


root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="task_manager_agent",
    instruction=(
        "You are a helpful task-management assistant. "
        "Use the available tools to create, list, complete, and delete tasks "
        "on behalf of the user. Always confirm what you did after each action."
    ),
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=MCP_URL),
            header_provider=_header_provider,
        )
    ],
)

if __name__ == "__main__":
    import uvicorn
    from google.adk.cli.fast_api import get_fast_api_app

    app = get_fast_api_app(
        agents_dir=str(Path(__file__).parent.parent),
        web=True,
    )
    uvicorn.run(app, host="localhost", port=8000)
