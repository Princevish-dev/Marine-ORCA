from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from app.guardian.guardian import event_bus, get_guardian_status
from app.api.auth import require_api_user

router = APIRouter()
def _event_payload(alert) -> dict:
    payload = alert.model_dump(mode="json")
    payload["timestamp"] = payload["detected_at"]
    payload["coordinate"] = {
        "latitude": alert.latitude,
        "longitude": alert.longitude,
    }
    payload["warning"] = alert.description
    return payload


async def _event_stream(request: Request):
    queue = event_bus.subscribe()
    try:
        yield f"data: {json.dumps({'type': 'connected', 'message': 'ORCA Guardian connected'})}\n\n"

        recent = event_bus.get_recent_alerts(limit=3)
        for alert in recent:
            yield f"data: {json.dumps(_event_payload(alert))}\n\n"

        while True:
            if await request.is_disconnected():
                break
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                alert = next((item for item in event_bus.get_recent_alerts() if item.id == json.loads(payload).get("id")), None)
                yield f"data: {json.dumps(_event_payload(alert)) if alert else payload}\n\n"
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


@router.get("/v1/guardian/stream")
async def guardian_stream(request: Request):
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/alerts")
async def get_alerts(_user: dict = Depends(require_api_user)):
    alerts = event_bus.get_recent_alerts()
    return {"alerts": [a.model_dump() for a in alerts], "guardian": get_guardian_status()}
