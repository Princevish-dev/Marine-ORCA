from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter, Request, HTTPException, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import StreamingResponse
from app.guardian.guardian import event_bus, trigger_test_alert, get_guardian_status
from app.api.auth import require_api_user

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def _event_stream(request: Request):
    queue = event_bus.subscribe()
    try:
        yield f"data: {json.dumps({'type': 'connected', 'message': 'ORCA Guardian connected'})}\n\n"

        recent = event_bus.get_recent_alerts(limit=3)
        for alert in recent:
            yield f"data: {alert.model_dump_json()}\n\n"

        while True:
            if await request.is_disconnected():
                break
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    finally:
        event_bus.unsubscribe(queue)


@router.get("/events")
async def sse_events(request: Request):
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/alerts/test")
@limiter.limit("5/minute")
async def trigger_test(request: Request, _user: dict = Depends(require_api_user)):
    from app.config import settings
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Test alerts are available only in demo mode")
    alert = await trigger_test_alert()
    return {"status": "ok", "alert_id": alert.id}


@router.get("/alerts")
async def get_alerts(_user: dict = Depends(require_api_user)):
    alerts = event_bus.get_recent_alerts()
    return {"alerts": [a.model_dump() for a in alerts], "guardian": get_guardian_status()}
