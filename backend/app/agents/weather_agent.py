import asyncio
from app.models import OrcaState, Coordinates, EvidenceItem
from app.services.data_providers import fetch_weather
from app.agents.utils import start_stage, complete_stage, skip_stage

def weather_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "weather" not in s.planned_agents:
        return skip_stage(s, "weather", "Weather Agent").model_dump()

    s = start_stage(s, "weather", "Weather Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        w = asyncio.get_event_loop().run_until_complete(
            fetch_weather(loc.latitude, loc.longitude)
        )
        s.weather_result = w
        s.evidence.append(EvidenceItem(
            source=w.source,
            type="Demo" if w.is_demo else "Forecast",
            description=f"Wind {w.wind_speed_kmh:.0f} km/h, Temp {w.temperature_c:.1f}°C, {w.weather_condition}",
            valid_at=w.forecast_time,
            is_demo=w.is_demo,
        ))
        summary = f"Wind: {w.wind_speed_kmh:.0f} km/h | Condition: {w.weather_condition}"
        s = complete_stage(s, "weather", source=w.source, summary=summary,
                             confidence=0.7 if w.is_demo else 0.9,
                             warning="DEMO DATA" if w.is_demo else "")
    except Exception as exc:
        s = complete_stage(s, "weather", summary=f"Error: {exc}", error=True)

    return s.model_dump()
