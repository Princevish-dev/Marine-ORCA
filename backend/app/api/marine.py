from fastapi import APIRouter, Query
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


@router.get("/pfz")
async def pfz_data(lat: float = Query(13.0827, ge=-90, le=90), lon: float = Query(80.2707, ge=-180, le=180)):
    ocean = await fetch_ocean_observation(lat, lon)
    candidates = generate_pfz_candidates(lat, lon, ocean.sst_celsius, ocean.chlorophyll_mgm3)
    return {"candidates": candidates, "source": ocean.source}


@router.get("/layers")
async def map_layers():
    geofence = get_geofence_geojson()
    return {"geofence": geofence}


@router.post("/route")
async def calculate_route(
    start_lat: float = Query(13.0827, ge=-90, le=90),
    start_lon: float = Query(80.2707, ge=-180, le=180),
    end_lat: float = Query(12.85, ge=-90, le=90),
    end_lon: float = Query(80.45, ge=-180, le=180),
):
    marine = await fetch_marine(start_lat, start_lon)
    route = build_route_grid(
        start_lat, start_lon, end_lat, end_lon,
        wave_height=marine.wave_height_m,
        current_speed=marine.current_speed_ms,
        current_dir=marine.current_direction_deg,
    )
    return route.model_dump()
