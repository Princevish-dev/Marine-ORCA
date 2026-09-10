import asyncio
import json
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

async def mock_imd_rss_poll():
    """
    Simulates polling an IMD RSS feed or Open-Meteo API for severe weather.
    Yields high severity alerts (severity >= 3).
    """
    while True:
        # Simulate polling interval (e.g. 5 minutes in reality, shorter for demo)
        await asyncio.sleep(10)
        
        # Randomly generate a severity for demonstration
        severity = random.randint(1, 5)
        
        if severity >= 3:
            event_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "coordinate": {"lat": 13.0827 + random.uniform(-0.1, 0.1), "lon": 80.2707 + random.uniform(-0.1, 0.1)},
                "warning": f"SEVERE WEATHER ALERT: Level {severity} storm approaching.",
                "severity": severity
            }
            yield json.dumps(event_data)

@router.get("/stream")
async def guardian_stream(request: Request):
    """
    FastAPI Server-Sent Events (SSE) endpoint for Background Guardian.
    Clients connect to this endpoint to receive proactive 'toast' notifications.
    """
    async def event_generator():
        async for event_payload in mock_imd_rss_poll():
            if await request.is_disconnected():
                break
            yield {
                "event": "message",
                "id": "message_id",
                "retry": 15000,
                "data": event_payload
            }
            
    return EventSourceResponse(event_generator())
