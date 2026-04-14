"""Shared in-memory database state with seed data."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

_TASKS: dict[str, dict] = {
    "task-1": {
        "id": "task-1",
        "title": "Set up CI pipeline",
        "description": "Configure GitHub Actions for automated testing",
        "completed": False,
        "created_at": "2026-04-01T09:00:00+00:00",
    },
    "task-2": {
        "id": "task-2",
        "title": "Write API documentation",
        "description": "Document all endpoints using OpenAPI spec",
        "completed": True,
        "created_at": "2026-04-02T10:30:00+00:00",
    },
    "task-3": {
        "id": "task-3",
        "title": "Fix login bug",
        "description": None,
        "completed": False,
        "created_at": "2026-04-10T14:00:00+00:00",
    },
}


def list_tasks() -> list[dict]:
    return list(_TASKS.values())


def get_task(task_id: str) -> Optional[dict]:
    return _TASKS.get(task_id)


def create_task(title: str, description: Optional[str] = None) -> dict:
    task = {
        "id": str(uuid4()),
        "title": title,
        "description": description or "",
        "completed": False,
        "created_at": _now(),
    }
    _TASKS[task["id"]] = task
    return task


def complete_task(task_id: str) -> Optional[dict]:
    task = _TASKS.get(task_id)
    if task is None:
        return None
    task["completed"] = True
    return task


def delete_task(task_id: str) -> bool:
    if task_id not in _TASKS:
        return False
    del _TASKS[task_id]
    return True


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

_USERS: dict[str, dict] = {
    "user-1": {
        "id": "user-1",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "active": True,
        "created_at": "2026-03-15T08:00:00+00:00",
    },
    "user-2": {
        "id": "user-2",
        "name": "Bob Smith",
        "email": "bob@example.com",
        "active": True,
        "created_at": "2026-03-20T11:00:00+00:00",
    },
    "user-3": {
        "id": "user-3",
        "name": "Carol White",
        "email": "carol@example.com",
        "active": False,
        "created_at": "2026-04-01T09:30:00+00:00",
    },
}


def list_users() -> list[dict]:
    return list(_USERS.values())


def get_user(user_id: str) -> Optional[dict]:
    return _USERS.get(user_id)


def create_user(name: str, email: str) -> dict:
    user = {
        "id": str(uuid4()),
        "name": name,
        "email": email,
        "active": True,
        "created_at": _now(),
    }
    _USERS[user["id"]] = user
    return user


def deactivate_user(user_id: str) -> Optional[dict]:
    user = _USERS.get(user_id)
    if user is None:
        return None
    user["active"] = False
    return user


def delete_user(user_id: str) -> bool:
    if user_id not in _USERS:
        return False
    del _USERS[user_id]
    return True
