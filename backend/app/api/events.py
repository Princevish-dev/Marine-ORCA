from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.guardian.guardian import event_bus, trigger_test_alert, get_guardian_status

router = APIRouter()


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
async def trigger_test(request: Request):
    alert = await trigger_test_alert()
    return {"status": "ok", "alert_id": alert.id}


@router.get("/alerts")
async def get_alerts():
    alerts = event_bus.get_recent_alerts()
    return {"alerts": [a.model_dump() for a in alerts], "guardian": get_guardian_status()}
