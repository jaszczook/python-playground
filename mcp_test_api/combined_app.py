"""
Single FastAPI app combining both Tasks and Users routes on one port.

Use this when running against the MCP server (single API_HOST):
  uv run python combined_app.py        # port 8000 by default
  PORT=8080 uv run python combined_app.py

Then start the MCP server with:
  API_HOST=http://localhost:8000 uv run python ../mcp_adk_demo/mcp_server.py
"""

import logging
import os

import uvicorn
from fastapi import FastAPI

from tasks_app import router as tasks_router
from users_app import router as users_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

app = FastAPI(title="Mock API (Tasks + Users)", version="1.0.0")
app.include_router(tasks_router)
app.include_router(users_router)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
