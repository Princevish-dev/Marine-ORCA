from datetime import datetime, timedelta, timezone

DEMO_LOCATION = {"latitude": 13.0827, "longitude": 80.2707}

NOW = datetime.now(timezone.utc)
TOMORROW_MORNING = (NOW + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

DEMO_WEATHER = {
    "source": "DEMO FIXTURE — not live data",
    "retrieved_at": NOW.isoformat(),
    "forecast_time": TOMORROW_MORNING.isoformat(),
    "latitude": 13.0827,
    "longitude": 80.2707,
    "wind_speed_kmh": 22.0,
    "wind_direction_deg": 225.0,
    "temperature_c": 28.5,
    "precipitation_mm": 0.4,
    "weather_condition": "Partly Cloudy",
    "is_demo": True,
}

DEMO_MARINE = {
    "source": "DEMO FIXTURE — not live data",
    "retrieved_at": NOW.isoformat(),
    "forecast_time": TOMORROW_MORNING.isoformat(),
    "latitude": 13.0827,
    "longitude": 80.2707,
    "wave_height_m": 1.8,
    "wave_direction_deg": 180.0,
    "wave_period_s": 8.5,
    "swell_height_m": 1.2,
    "current_speed_ms": 0.4,
    "current_direction_deg": 45.0,
    "is_demo": True,
}

DEMO_OCEAN = {
    "source": "DEMO FIXTURE (EO-derived) — not live data",
    "retrieved_at": NOW.isoformat(),
    "latitude": 13.0827,
    "longitude": 80.2707,
    "sst_celsius": 27.4,
    "chlorophyll_mgm3": 0.82,
    "data_type": "DEMO",
    "is_demo": True,
}

DEMO_PFZ_CANDIDATES = [
    {
        "id": "pfz-1",
        "latitude": 12.85,
        "longitude": 80.45,
        "score": 78.0,
        "distance_km": 22.3,
        "sst_celsius": 27.2,
        "chlorophyll_level": "HIGH",
        "explanation": "High chlorophyll concentration and optimal SST suggest elevated biological productivity.",
        "suitability": "HIGH",
    },
    {
        "id": "pfz-2",
        "latitude": 13.22,
        "longitude": 80.55,
        "score": 61.0,
        "distance_km": 38.7,
        "sst_celsius": 27.8,
        "chlorophyll_level": "MODERATE",
        "explanation": "Moderate chlorophyll with favorable SST range. Suitable for exploratory fishing.",
        "suitability": "MODERATE",
    },
]

DEMO_WARNING = {
    "id": "warn-demo-001",
    "source": "DEMO WARNING FEED",
    "severity": "YELLOW",
    "title": "Rough Sea Advisory",
    "description": "Wave heights 1.5–2.5 m expected off Chennai coast. Small boats advised caution.",
    "affected_area": "Bay of Bengal — Chennai to Pondicherry coast",
    "effective_time": NOW.isoformat(),
    "expiry_time": (NOW + timedelta(hours=24)).isoformat(),
    "is_active": True,
}
