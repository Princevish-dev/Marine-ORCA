from fastapi import APIRouter, Query, Body
from app.services.data_providers import fetch_weather, fetch_marine, fetch_ocean_observation
from app.geospatial.engine import check_boundary_status, generate_pfz_candidates, get_geofence_geojson
from app.routing.astar import build_route_grid

router = APIRouter()


@router.get("/marine")
async def marine_data(lat: float = Query(13.0827, ge=-90, le=90), lon: float = Query(80.2707, ge=-180, le=180)):
    marine = await fetch_marine(lat, lon)
    weather = await fetch_weather(lat, lon)
    ocean = await fetch_ocean_observation(lat, lon)
    return {"marine": marine.model_dump(), "weather": weather.model_dump(), "ocean": ocean.model_dump()}


@router.get("/pfz/nearest")
async def pfz_nearest_data(lat: float = Query(13.0827, ge=-90, le=90), lon: float = Query(80.2707, ge=-180, le=180)):
    ocean = await fetch_ocean_observation(lat, lon)
    candidates = generate_pfz_candidates(lat, lon, getattr(ocean, "sst_celsius", 28.5), getattr(ocean, "chlorophyll_mgm3", 0.5))
    return {"candidates": candidates, "source": ocean.source}


@router.get("/layers")
async def map_layers():
    geofence = get_geofence_geojson()
    return {"geofence": geofence}


@router.post("/route/optimize")
async def calculate_route_optimize(payload: dict = Body(...)):
    start_lat = payload.get("start_lat", 13.0827)
    start_lon = payload.get("start_lon", 80.2707)
    end_lat = payload.get("end_lat", 12.85)
    end_lon = payload.get("end_lon", 80.45)
    
    marine = await fetch_marine(start_lat, start_lon)
    route = build_route_grid(
        start_lat, start_lon, end_lat, end_lon,
        wave_height=getattr(marine, "wave_height_m", 1.0),
        current_speed=getattr(marine, "current_speed_ms", 0.3),
        current_dir=getattr(marine, "current_direction_deg", 90.0),
    )
    return route.model_dump()

@router.post("/telemetry/ingest")
async def ingest_telemetry(payload: dict = Body(...)):
    from app.agents.marine_agent import compute_anomaly_score
    obs = {
        "wave_height_m": payload.get("wave_height_m", 0),
        "wind_speed_kmh": payload.get("wind_speed_kmh", 0),
        "sst_celsius": payload.get("sst_celsius", 0),
        "chlorophyll_mgm3": payload.get("chlorophyll_mgm3", 0)
    }
    r_t, is_anomaly = compute_anomaly_score(obs, [])
    return {
        "status": "ingested",
        "anomaly_score": r_t,
        "is_anomaly": is_anomaly
    }
