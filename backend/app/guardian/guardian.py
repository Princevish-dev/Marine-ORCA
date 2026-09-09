from __future__ import annotations
import asyncio
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

from app.config import settings
from app.models import AlertEvent
from app.services.safety_calculator import is_high_wave, is_extreme_weather

logger = logging.getLogger("guardian")


class EventBus:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._seen_events: dict[str, AlertEvent] = {}

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    async def publish(self, event: AlertEvent):
        ev_id = event.id
        existing = self._seen_events.get(ev_id)

        if existing:
            sev_order = {"INFO": 1, "YELLOW": 2, "ORANGE": 3, "RED": 4}
            if sev_order[event.severity] <= sev_order[existing.severity]:
                return
            event.status = "UPDATED"

        self._seen_events[ev_id] = event
        payload = event.model_dump_json()

        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    def get_recent_alerts(self, limit: int = 10) -> list[AlertEvent]:
        events = list(self._seen_events.values())
        return sorted(events, key=lambda e: e.detected_at, reverse=True)[:limit]


event_bus = EventBus()

_MONITOR_LOCATIONS = [
    {"name": "Chennai Coast", "lat": 13.0827, "lon": 80.2707},
    {"name": "Mumbai Harbour", "lat": 18.9388, "lon": 72.8355},
    {"name": "Kochi Port", "lat": 9.9312, "lon": 76.2673},
]

_guardian_status = {
    "last_scan": None,
    "status": "STARTING",
    "scan_count": 0,
}


async def _evaluate_marine_alerts(lat: float, lon: float, location_name: str):
    url = settings.marine_api_url
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height",
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        wave_heights = data["hourly"]["wave_height"]
        max_wave = max((h for h in wave_heights if h is not None), default=0.0)

        if max_wave >= 4.0:
            severity = "RED"
            title = f"Extreme Wave Alert — {location_name}"
            desc = f"Wave heights up to {max_wave:.1f} m forecast. Avoid sea."
        elif max_wave >= 2.5:
            severity = "ORANGE"
            title = f"High Wave Warning — {location_name}"
            desc = f"Wave heights {max_wave:.1f} m forecast. Small boats exercise extreme caution."
        elif max_wave >= 1.5:
            severity = "YELLOW"
            title = f"Rough Sea Advisory — {location_name}"
            desc = f"Wave heights up to {max_wave:.1f} m. Exercise caution."
        else:
            return

        event = AlertEvent(
            id=f"wave-{location_name.lower().replace(' ', '-')}-{int(max_wave*10)}",
            type="high_wave",
            severity=severity,
            source="Open-Meteo Marine (open-meteo.com)",
            title=title,
            description=desc,
            latitude=lat,
            longitude=lon,
            affected_area=location_name,
            effective_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=12),
            detected_at=datetime.now(timezone.utc),
            status="NEW",
        )
        await event_bus.publish(event)
        logger.info(f"Guardian alert: {title}")

    except Exception as exc:
        logger.warning(f"Guardian marine fetch failed for {location_name}: {exc}")


async def run_guardian():
    if not settings.guardian_enabled:
        return

    _guardian_status["status"] = "ACTIVE"
    logger.info(f"Guardian started (interval: {settings.guardian_interval_seconds}s)")

    while True:
        _guardian_status["last_scan"] = datetime.now(timezone.utc).isoformat()
        _guardian_status["scan_count"] += 1

        tasks = [
            _evaluate_marine_alerts(loc["lat"], loc["lon"], loc["name"])
            for loc in _MONITOR_LOCATIONS
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(settings.guardian_interval_seconds)


async def trigger_test_alert() -> AlertEvent:
    event = AlertEvent(
        id=f"test-{uuid.uuid4().hex[:8]}",
        type="test",
        severity="ORANGE",
        source="ORCA DEMO — Synthetic Test Alert",
        title="⚠ TEST: Cyclone Development Detected",
        description=(
            "DEMONSTRATION ALERT — This is a synthetic event for demo purposes only. "
            "A low-pressure system is being tracked 450 km ESE of Chennai. "
            "Continue monitoring official IMD feeds."
        ),
        latitude=13.5,
        longitude=84.0,
        affected_area="Bay of Bengal — Eastern Sector",
        effective_time=datetime.now(timezone.utc),
        expiry_time=datetime.now(timezone.utc) + timedelta(hours=6),
        detected_at=datetime.now(timezone.utc),
        status="NEW",
    )
    await event_bus.publish(event)
    return event


def get_guardian_status() -> dict:
    return {**_guardian_status, "subscriber_count": len(event_bus._subscribers)}
