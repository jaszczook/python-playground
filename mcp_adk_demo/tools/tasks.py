"""Exemplary hand-written tools for the Tasks API.

Four patterns illustrated here:

1. get_task_status      — tool with a single path argument
2. list_tasks_by_status — tool with an argument used as a client-side filter
3. create_task          — tool that sends a POST request with a JSON body
4. get_task_report      — graceful handling of expected "no data" error codes
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

    # ------------------------------------------------------------------
    # Pattern 4: graceful handling of expected "no data" error codes
    #
    # Some APIs signal "nothing here" via 4xx/5xx instead of an empty
    # payload. Treat those specific codes as valid empty results rather
    # than failures; re-raise everything else so real errors still surface.
    # ------------------------------------------------------------------
    _NO_DATA_STATUSES = {
        428,  # Precondition Required — report not ready / no data yet
        500,  # Internal Server Error — upstream signals no data for params
    }

    @mcp.tool
    async def get_task_report(task_id: str, period: str) -> dict | None:
        """Fetch the activity report for a task over a given period.

        The upstream report API sometimes returns 428 or 500 to indicate that
        no data exists for the requested parameters — those are treated as an
        empty result, not an error.

        Args:
            task_id: The task to report on.
            period:  Reporting period, e.g. "2024-Q1" or "last_30_days".

        Returns:
            Report dict, or None if the API has no data for these params.
        """
        resp = await client.get(f"/tasks/{task_id}/report", params={"period": period})

        if resp.status_code in _NO_DATA_STATUSES:
            return None  # expected "no data" — not a real failure

        resp.raise_for_status()  # anything else unexpected → propagate
        return resp.json()
