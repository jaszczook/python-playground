"""Exemplary hand-written tools for the Tasks API.

Three patterns illustrated here:

1. get_task_status   — tool with a single path argument
2. list_tasks_by_status — tool with an argument used as a client-side filter
3. create_task       — tool that sends a POST request with a JSON body
"""

import httpx
from fastmcp import FastMCP


def register(mcp: FastMCP, client: httpx.AsyncClient) -> None:

    # ------------------------------------------------------------------
    # Pattern 1: tool with a single path argument
    # ------------------------------------------------------------------
    @mcp.tool
    async def get_task_status(task_id: str) -> dict:
        """Return the completion status and title for a specific task.

        Args:
            task_id: The ID of the task to look up.
        """
        resp = await client.get(f"/tasks/{task_id}")
        if resp.status_code == 404:
            return {"error": f"Task '{task_id}' not found"}
        resp.raise_for_status()
        task = resp.json()
        return {"id": task["id"], "title": task.get("title"), "completed": task["completed"]}

    # ------------------------------------------------------------------
    # Pattern 2: tool with an argument used for client-side filtering
    # ------------------------------------------------------------------
    @mcp.tool
    async def list_tasks_by_status(completed: bool) -> list[dict]:
        """Return all tasks that match the given completion status.

        Args:
            completed: Pass True to list only completed tasks,
                       False to list only pending tasks.
        """
        resp = await client.get("/tasks")
        resp.raise_for_status()
        tasks = resp.json()
        return [
            {"id": t["id"], "title": t.get("title"), "completed": t["completed"]}
            for t in tasks
            if t["completed"] is completed
        ]

    # ------------------------------------------------------------------
    # Pattern 3: tool that sends a POST request with a JSON body
    # ------------------------------------------------------------------
    @mcp.tool
    async def create_task(title: str, description: str = "") -> dict:
        """Create a new task and return its ID and title.

        Args:
            title: Short title for the task (required).
            description: Optional longer description.
        """
        resp = await client.post(
            "/tasks",
            json={"title": title, "description": description},
        )
        resp.raise_for_status()
        task = resp.json()
        return {"id": task["id"], "title": task.get("title"), "completed": task["completed"]}
