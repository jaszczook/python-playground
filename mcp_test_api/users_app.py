"""Users API — matches mcp_adk_demo/examples/users.json (port 9000).

Exposes both a standalone `app` (FastAPI) and a `router` (APIRouter) for
embedding in the combined app.
"""

import logging
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Header
from pydantic import BaseModel

import db

logger = logging.getLogger("users_api")

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

class CreateUserRequest(BaseModel):
    name: str
    email: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/users")
def list_users(authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    return db.list_users()


@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    return db.create_user(body.name, body.email)


@router.get("/users/{user_id}")
def get_user(user_id: str, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    user = db.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: str, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    if not db.delete_user(user_id):
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return {"deleted": user_id}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: str, authorization: Optional[str] = Header(default=None)):
    _log_auth(authorization)
    user = db.deactivate_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return user


# Standalone app (port 9000)
app = FastAPI(title="Users API", version="1.0.0")
app.include_router(router)
