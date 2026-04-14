"""Tasks API — matches mcp_adk_demo/examples/tasks.json (port 8000).

Exposes both a standalone `app` (FastAPI) and a `router` (APIRouter) for
embedding in the combined app.
"""

import logging
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Header
from pydantic import BaseModel

import db

logger = logging.getLogger("tasks_api")

router = APIRouter()


def _log_auth(authorization: Optional[str]) -> None:
    if authorization:
        token = authorization.removeprefix("Bearer ").strip()
        logger.info("JWT received (first 30 chars): %s...", token[:30])
    else:
        logger.warning("No Authorization header")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/tasks")
def list_tasks(authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    return db.list_tasks()


@router.post("/tasks", status_code=201)
def create_task(body: CreateTaskRequest, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    return db.create_task(body.title, body.description or None)


@router.get("/tasks/{task_id}")
def get_task(task_id: str, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    if not db.delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"deleted": task_id}


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    task = db.complete_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


# Standalone app (port 8000)
app = FastAPI(title="Tasks API", version="1.0.0")
app.include_router(router)
