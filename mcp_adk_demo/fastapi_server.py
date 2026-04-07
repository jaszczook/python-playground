"""
FastAPI server that proxies user queries to a Google ADK agent.

The agent and runner are shared across all requests (created once at startup).
Per-request JWT forwarding works via MCPToolset's header_provider, which is
called on every tool invocation and reads the JWT from ADK session state.

Flow:
  request (JWT) → store JWT in session.state
               → runner.run_async()
               → MCPToolset calls header_provider(callback_context)
               → header_provider reads session.state["jwt"]
               → MCP server receives Authorization header
               → MCP server forwards it to the real API

Run:
  MCP_URL=http://mcp-server:8080/mcp uvicorn fastapi_server:app --reload
"""

import os

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai import types
from pydantic import BaseModel

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8080/mcp")
APP_NAME = "tasks_app"

security = HTTPBearer()

# ---------------------------------------------------------------------------
# Shared agent + runner — created once at startup
# ---------------------------------------------------------------------------

def _header_provider(readonly_context: ReadonlyContext) -> dict[str, str]:
    """Called by McpToolset before every tool invocation."""
    jwt = readonly_context.state.get("jwt", "")
    return {"Authorization": f"Bearer {jwt}"} if jwt else {}


agent = LlmAgent(
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

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    user_id: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str

# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

app = FastAPI()


@app.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ChatResponse:
    jwt = credentials.credentials

    if body.session_id:
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=body.user_id, session_id=body.session_id
        )
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=body.user_id
        )

    # Store JWT in session state — header_provider reads it on every tool call
    session.state["jwt"] = jwt

    message = types.Content(role="user", parts=[types.Part(text=body.query)])

    response_parts: list[str] = []
    async for event in runner.run_async(
        user_id=body.user_id,
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)

    return ChatResponse(response="".join(response_parts), session_id=session.id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
