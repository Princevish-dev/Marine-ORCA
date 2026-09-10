import asyncio
import json
import random
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Body
from sse_starlette.sse import EventSourceResponse
from app.services.data_providers import fetch_weather, fetch_marine
from app.config import settings

router = APIRouter()

def _create_alert(alert_type: str, severity: str, title: str, loc: dict, desc: str) -> dict:
    return {
        "event_id": f"evt_{random.randint(1000, 9999)}",
        "type": alert_type,
        "severity": severity,
        "title": title,
        "description": desc,
        "location": loc,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }

def evaluate_thresholds(weather_data, marine_data, warnings) -> list:
    alerts = []
    loc = {"lat": marine_data.latitude, "lng": marine_data.longitude} if marine_data else {}
    
    if marine_data and marine_data.wave_height_m > 2.5:
        alerts.append(_create_alert("high_waves", "critical", "High Wave Alert", loc, f"Waves at {marine_data.wave_height_m}m"))
        
    if weather_data and weather_data.wind_speed_kmh > 30:
        alerts.append(_create_alert("severe_weather", "critical", "High Wind Alert", loc, f"Winds at {weather_data.wind_speed_kmh}km/h"))
        
    for w in warnings:
        if w.severity in ["ORANGE", "RED"]:
            alerts.append(_create_alert("marine_warning", "critical", w.title, loc, w.description))
            
    return alerts

@router.post("/poll")
async def guardian_poll(payload: dict = Body(...)):
    lat = payload.get("lat")
    lng = payload.get("lng")
    if not lat or not lng:
        return {"alerts": []}
    
    weather_data = await fetch_weather(lat, lng)
    marine_data = await fetch_marine(lat, lng)
    warnings = []
    
    alerts = evaluate_thresholds(weather_data, marine_data, warnings)
    return {"alerts": alerts}

async def historical_alerts_poll():
    """
    Reads alerts from data/historical/historical_alerts.json.
    If USE_HISTORICAL_DATA is true, we only emit these alerts.
    """
    filepath = os.path.join(settings.historical_data_dir, "historical_alerts.json")
    if not os.path.exists(filepath):
        # Provide one initial info message that system is waiting for historical alerts
        event_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "warning": "Historical mode enabled. Waiting for sample alerts data...",
            "severity": 1,
            "source": "System"
        }
        yield json.dumps(event_data)
        while True:
            await asyncio.sleep(60)
            
    while True:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                alerts = json.load(f)
            
            # Emit alerts one by one for demo purposes, or handle as a batch
            for alert in alerts:
                yield json.dumps(alert)
                await asyncio.sleep(15) # Wait 15s between emitting historical alerts
                
        except Exception as e:
            print(f"Error reading historical alerts: {e}")
            await asyncio.sleep(60)
            
        # Loop over historical alerts periodically or wait
        await asyncio.sleep(300)

@router.get("/stream")
async def guardian_stream(request: Request):
    """
    FastAPI Server-Sent Events (SSE) endpoint for Background Guardian.
    Clients connect to this endpoint to receive proactive 'toast' notifications.
    """
    async def event_generator():
        async for event_payload in historical_alerts_poll():
            if await request.is_disconnected():
                break
            yield {
                "event": "message",
                "id": "message_id",
                "retry": 15000,
                "data": event_payload
            }
            
    return EventSourceResponse(event_generator())
