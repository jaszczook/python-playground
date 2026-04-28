"""
Factories for per-domain McpToolset instances.

Each function returns a McpToolset pre-filtered to one namespace so that
sub-agents only see the tools relevant to their domain.

Usage:
    tasks_agent = LlmAgent(
        name="tasks_agent",
        tools=[tasks_toolset(MCP_URL, header_provider)],
        ...
    )
"""

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams


def tasks_toolset(
    mcp_url: str,
    header_provider: callable,
) -> McpToolset:
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=mcp_url),
        header_provider=header_provider,
        tool_filter=["tasks_get_task_status"],
    )


def users_toolset(
    mcp_url: str,
    header_provider: callable,
) -> McpToolset:
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=mcp_url),
        header_provider=header_provider,
        tool_filter=["users_list_user_summaries"],
    )
