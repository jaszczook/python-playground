"""
Run both mock API servers concurrently:
  - Tasks API on port 8000
  - Users API on port 9000

Usage:
  uv run python main.py

Both servers share the same in-memory state (db.py).
"""

import asyncio
import logging

import uvicorn

from tasks_app import app as tasks_app
from users_app import app as users_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)


async def _serve(app, port: int) -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    await asyncio.gather(
        _serve(tasks_app, port=8000),
        _serve(users_app, port=9000),
    )


if __name__ == "__main__":
    asyncio.run(main())
