"""Semantic wrapper tools for the Users API.

These return minimal subsets of user data tailored to what the agent
actually needs, rather than exposing raw API responses.
"""

import httpx
from fastmcp import FastMCP


def register(mcp: FastMCP, client: httpx.AsyncClient) -> None:
    @mcp.tool
    async def list_user_summaries() -> list[dict]:
        """Return a minimal summary (id + name) for every user.

        Use this instead of users_list_users when you only need to identify
        users — it keeps context small and avoids leaking PII like email.
        """
        resp = await client.get("/users")
        resp.raise_for_status()
        return [{"id": u["id"], "name": u["name"]} for u in resp.json()]
