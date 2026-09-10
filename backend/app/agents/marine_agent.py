import math
import asyncio
from app.models import OrcaState, Coordinates, EvidenceItem
from app.services.data_providers import fetch_marine, fetch_ocean_observation
from app.agents.utils import start_stage, complete_stage, skip_stage

def marine_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "marine" not in s.planned_agents:
        return skip_stage(s, "marine", "Marine Agent").model_dump()

    s = start_stage(s, "marine", "Marine Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        m = asyncio.get_event_loop().run_until_complete(
            fetch_marine(loc.latitude, loc.longitude)
        )
        s.marine_result = m
        s.evidence.append(EvidenceItem(
            source=m.source,
            type="Demo" if m.is_demo else "Forecast",
            description=f"Wave height: {m.wave_height_m:.1f} m | Period: {m.wave_period_s:.1f} s | Swell: {m.swell_height_m:.1f} m",
            valid_at=m.forecast_time,
            is_demo=m.is_demo,
        ))
        summary = f"Wave: {m.wave_height_m:.1f} m | Period: {m.wave_period_s:.1f} s | Current: {m.current_speed_ms:.1f} m/s"
        s = complete_stage(s, "marine", source=m.source, summary=summary,
                             confidence=0.7 if m.is_demo else 0.9,
                             warning="DEMO DATA" if m.is_demo else "")
    except Exception as exc:
        s = complete_stage(s, "marine", summary=f"Error: {exc}", error=True)

    return s.model_dump()

def compute_anomaly_score(current_obs: dict, historical_window: list) -> tuple:
    w = [0.35, 0.25, 0.20, 0.20]
    theta_dynamic = 2.0
    
    val_wave = current_obs.get("wave_height_m", 0)
    val_wind = current_obs.get("wind_speed_kmh", 0)
    val_sst = current_obs.get("sst_celsius", 0)
    val_chl = current_obs.get("chlorophyll_mgm3", 0)
    
    def get_stats(hist: list, key: str):
        vals = [h.get(key, 0) for h in hist if h.get(key) is not None]
        if not vals: return 0.0, 1.0
        mu = sum(vals) / len(vals)
        sig = math.sqrt(sum((v - mu)**2 for v in vals) / len(vals)) if len(vals) > 1 else 1.0
        return mu, sig if sig > 0.01 else 1.0
        
    mu_wave, sig_wave = get_stats(historical_window, "wave_height_m")
    mu_wind, sig_wind = get_stats(historical_window, "wind_speed_kmh")
    mu_sst, sig_sst = get_stats(historical_window, "sst_celsius")
    mu_chl, sig_chl = get_stats(historical_window, "chlorophyll_mgm3")
    
    z_wave = (val_wave - mu_wave) / sig_wave
    z_wind = (val_wind - mu_wind) / sig_wind
    z_sst = (val_sst - mu_sst) / sig_sst
    z_chl = (val_chl - mu_chl) / sig_chl
    
    sum_z = (w[0] * z_wave) + (w[1] * z_wind) + (w[2] * z_sst) + (w[3] * z_chl)
    r_t = 1 / (1 + math.exp(-(sum_z - theta_dynamic)))
    
    is_anomaly = r_t > 0.8
    return r_t, is_anomaly

def ocean_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "ocean" not in s.planned_agents:
        return skip_stage(s, "ocean", "Ocean Analytics Agent").model_dump()

    s = start_stage(s, "ocean", "Ocean Analytics Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        o = asyncio.get_event_loop().run_until_complete(
            fetch_ocean_observation(loc.latitude, loc.longitude)
        )
        
        if getattr(o, "sst_celsius", None) is not None:
            historical_baseline = 28.5
            o.sst_anomaly = o.sst_celsius - historical_baseline
        else:
            o.sst_anomaly = None
            
        current_obs = {
            "sst_celsius": getattr(o, "sst_celsius", 0),
            "chlorophyll_mgm3": getattr(o, "chlorophyll_mgm3", 0)
        }
        if s.marine_result:
            current_obs["wave_height_m"] = s.marine_result.wave_height_m
        if s.weather_result:
            current_obs["wind_speed_kmh"] = s.weather_result.wind_speed_kmh
            
        r_t, is_anomaly = compute_anomaly_score(current_obs, [])
            
        s.ocean_result = o
        
        anomaly_str = f" | Anomaly: {o.sst_anomaly:+.1f}°C" if getattr(o, "sst_anomaly", None) is not None else ""
        s.evidence.append(EvidenceItem(
            source=o.source,
            type="Demo" if o.is_demo else "EO",
            description=f"SST: {o.sst_celsius}°C{anomaly_str} | Chlorophyll: {o.chlorophyll_mgm3} mg/m³ | R(t): {r_t:.2f}",
            valid_at=o.retrieved_at,
            is_demo=o.is_demo,
        ))
        summary = f"SST: {o.sst_celsius}°C{anomaly_str} | Chl: {o.chlorophyll_mgm3} mg/m³ | R(t): {r_t:.2f}"
        warning_msg = "MIGRATION_LIKELY: Significant SST anomaly" if getattr(o, "sst_anomaly", 0) and o.sst_anomaly > 1.5 else ""
        if is_anomaly:
            warning_msg = f"{warning_msg} | SYSTEM ANOMALY R(t)={r_t:.2f}".strip(" | ")
            
        s = complete_stage(s, "ocean", source=o.source, summary=summary, warning=warning_msg)
    except Exception as exc:
        s = complete_stage(s, "ocean", summary=f"Error: {exc}", error=True)

    return s.model_dump()
