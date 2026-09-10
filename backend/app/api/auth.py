from __future__ import annotations

from fastapi import Request

async def require_api_user(request: Request) -> dict:
    # Local-first architecture: Auth is bypassed for local execution.
    return {"sub": "local-user", "email": "local@orca.demo"}
