from __future__ import annotations
import httpx
import math
import json
import re
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
from datetime import datetime, timezone
from app.models import WeatherObservation, MarineObservation, OceanObservation, WarningEvent
from app.config import settings
from app.services.demo_fixtures import DEMO_WEATHER, DEMO_MARINE, DEMO_OCEAN
import os

_WEATHER_PARAMS = (
    "wind_speed_10m,wind_direction_10m,temperature_2m,"
    "precipitation,weather_code"
)

_MARINE_PARAMS = (
    "wave_height,wave_direction,wave_period,"
    "swell_wave_height,ocean_current_velocity,ocean_current_direction"
)

_TIMEOUT = 10.0


def _parse_warning_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)


def _warning_severity(text: str) -> str:
    normalized = text.upper()
    if "RED" in normalized or "CYCLONE" in normalized:
        return "RED"
    if "ORANGE" in normalized:
        return "ORANGE"
    if "YELLOW" in normalized or "CAUTION" in normalized:
        return "YELLOW"
    return "INFO"


def _warning_from_mapping(item: dict, source: str, index: int) -> WarningEvent:
    title = str(item.get("title") or item.get("headline") or item.get("event") or "Marine warning")
    description = str(item.get("description") or item.get("summary") or title)
    severity = str(item.get("severity") or _warning_severity(f"{title} {description}")).upper()
    if severity not in {"INFO", "YELLOW", "ORANGE", "RED"}:
        severity = _warning_severity(f"{title} {description}")
    return WarningEvent(
        id=str(item.get("id") or f"{source}-{index}-{abs(hash(title))}"),
        source=source,
        severity=severity,
        title=title[:240],
        description=description[:1000],
        affected_area=str(item.get("affected_area") or item.get("area") or "India coast"),
        effective_time=_parse_warning_time(item.get("effective_time") or item.get("pubDate")),
        expiry_time=_parse_warning_time(item["expiry_time"]) if item.get("expiry_time") else None,
        is_active=bool(item.get("is_active", True)),
    )


def _parse_warning_feed(payload: str, source: str) -> list[WarningEvent]:
    try:
        data = json.loads(payload)
        items = data if isinstance(data, list) else data.get("warnings", data.get("items", []))
        if isinstance(items, list):
            return [_warning_from_mapping(item, source, i) for i, item in enumerate(items) if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass

    root = ElementTree.fromstring(payload)
    results: list[WarningEvent] = []
    for index, item in enumerate(root.findall(".//item")):
        text = lambda tag: next((node.text for node in item if node.tag.rsplit("}", 1)[-1] == tag), "")
        title = text("title") or "Marine warning"
        description = re.sub(r"<[^>]+>", " ", text("description") or title).strip()
        results.append(_warning_from_mapping({"title": title, "description": description, "pubDate": text("pubDate")}, source, index))
    return results


async def fetch_warning_events() -> list[WarningEvent]:
    if not settings.imd_feed_url:
        return []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(settings.imd_feed_url)
            response.raise_for_status()
        return _parse_warning_feed(response.text, "IMD Warning Feed")
    except Exception:
        return []


async def fetch_weather(lat: float, lon: float) -> WeatherObservation:
    if settings.use_historical_data:
        filepath = os.path.join(settings.historical_data_dir, "historical_weather.json")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Find the closest coordinate or just return the first for sample purposes
            # For simplicity, assuming the JSON is a list of observations and we return the first one or closest
            if isinstance(data, list) and len(data) > 0:
                return WeatherObservation(**data[0])
            elif isinstance(data, dict):
                return WeatherObservation(**data)
        except Exception:
            # Fallback to demo if the user hasn't provided the historical file yet
            pass
            
    if settings.demo_mode:
        return WeatherObservation(**DEMO_WEATHER)

    url = settings.weather_api_url
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": _WEATHER_PARAMS,
        "forecast_days": 2,
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        hourly = data["hourly"]
        idx = min(12, len(hourly["wind_speed_10m"]) - 1)
        forecast_iso = hourly["time"][idx]

        wmo = hourly.get("weather_code", [0])[idx]
        condition = _wmo_to_condition(wmo)

        return WeatherObservation(
            source="Open-Meteo (open-meteo.com) — Forecast",
            retrieved_at=datetime.now(timezone.utc),
            forecast_time=datetime.fromisoformat(forecast_iso).replace(tzinfo=timezone.utc),
            latitude=lat,
            longitude=lon,
            wind_speed_kmh=float(hourly["wind_speed_10m"][idx] or 0),
            wind_direction_deg=float(hourly["wind_direction_10m"][idx] or 0),
            temperature_c=float(hourly["temperature_2m"][idx] or 25),
            precipitation_mm=float(hourly["precipitation"][idx] or 0),
            weather_condition=condition,
            is_demo=False,
        )
    except Exception as exc:
        demo = WeatherObservation(**DEMO_WEATHER)
        demo.source = f"DEMO FALLBACK (live fetch failed: {str(exc)[:60]})"
        demo.is_demo = True
        return demo


async def fetch_marine(lat: float, lon: float) -> MarineObservation:
    if settings.use_historical_data:
        filepath = os.path.join(settings.historical_data_dir, "historical_marine.json")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return MarineObservation(**data[0])
            elif isinstance(data, dict):
                return MarineObservation(**data)
        except Exception:
            pass

    if settings.demo_mode:
        return MarineObservation(**DEMO_MARINE)

    url = settings.marine_api_url
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": _MARINE_PARAMS,
        "forecast_days": 2,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        hourly = data["hourly"]
        idx = min(12, len(hourly["wave_height"]) - 1)
        forecast_iso = hourly["time"][idx]

        return MarineObservation(
            source="Open-Meteo Marine (marine-api.open-meteo.com) — Forecast",
            retrieved_at=datetime.now(timezone.utc),
            forecast_time=datetime.fromisoformat(forecast_iso).replace(tzinfo=timezone.utc),
            latitude=lat,
            longitude=lon,
            wave_height_m=float(hourly["wave_height"][idx] or 0),
            wave_direction_deg=float(hourly["wave_direction"][idx] or 0),
            wave_period_s=float(hourly["wave_period"][idx] or 6),
            swell_height_m=float(hourly.get("swell_wave_height", [0])[idx] or 0),
            current_speed_ms=float(hourly.get("ocean_current_velocity", [0])[idx] or 0),
            current_direction_deg=float(hourly.get("ocean_current_direction", [0])[idx] or 0),
            is_demo=False,
        )
    except Exception as exc:
        demo = MarineObservation(**DEMO_MARINE)
        demo.source = f"DEMO FALLBACK (live fetch failed: {str(exc)[:60]})"
        demo.is_demo = True
        return demo


async def fetch_ocean_observation(lat: float, lon: float) -> OceanObservation:
    if settings.demo_mode:
        return OceanObservation(**DEMO_OCEAN)

    try:
        from app.services.isro_loader import get_isro_ocean_data
        isro_data = get_isro_ocean_data(lat, lon)
        
        if isro_data["sst_celsius"] is not None and isro_data["chlorophyll_mgm3"] is not None:
            return OceanObservation(
                source=isro_data["source"],
                retrieved_at=datetime.fromisoformat(isro_data["retrieved_at"]),
                latitude=lat,
                longitude=lon,
                sst_celsius=isro_data["sst_celsius"],
                chlorophyll_mgm3=isro_data["chlorophyll_mgm3"],
                data_type=isro_data["data_type"],
                is_demo=isro_data["is_demo"],
            )
        else:
            # Fallback to model if ISRO data doesn't cover this location
            weather = await fetch_weather(lat, lon)
            sst = weather.temperature_c - 1.5
            chlorophyll = 0.5 + 0.8 * math.exp(-abs(lat - 12.0) / 3.0)

            return OceanObservation(
                source="Modelled proxy (EO-derived estimate — not satellite observation)",
                retrieved_at=datetime.now(timezone.utc),
                latitude=lat,
                longitude=lon,
                sst_celsius=round(sst, 1),
                chlorophyll_mgm3=round(chlorophyll, 2),
                data_type="MODEL",
                is_demo=False,
            )
    except Exception as exc:
        demo = OceanObservation(**DEMO_OCEAN)
        demo.source = f"DEMO FALLBACK ocean (error: {str(exc)[:60]})"
        demo.is_demo = True
        return demo


def _wmo_to_condition(code: int) -> str:
    if code == 0:
        return "Clear Sky"
    elif code in (1, 2, 3):
        return "Partly Cloudy"
    elif code in range(45, 50):
        return "Foggy"
    elif code in range(51, 68):
        return "Rain / Drizzle"
    elif code in range(71, 78):
        return "Snow"
    elif code in range(80, 83):
        return "Rain Showers"
    elif code in range(85, 87):
        return "Snow Showers"
    elif code in (95, 96, 99):
        return "Thunderstorm"
    return "Unknown"
