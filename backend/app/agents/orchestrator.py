from __future__ import annotations
import asyncio
import uuid
import logging

from langgraph.graph import StateGraph, END

from app.models import (
    OrcaState, Coordinates, AgentTrace, ChatRequest, ChatResponse, MapData
)
from app.geospatial.engine import get_geofence_geojson

# Import the 7 required agent nodes
from app.agents.planner import planner_node
from app.agents.weather_agent import weather_agent_node
from app.agents.marine_agent import marine_agent_node, ocean_agent_node
from app.agents.pfz_agent import pfz_agent_node
from app.agents.geospatial_agent import geospatial_agent_node
from app.agents.critic_agent import critic_agent_node
from app.agents.report_agent import report_agent_node
from app.agents.collective_impact_agent import collective_impact_agent_node

# Import shared utils
from app.agents.utils import start_stage, complete_stage, skip_stage

# Local services for the nodes kept in orchestrator
from app.services.safety_calculator import calculate_safety
from app.routing.astar import build_route_grid

logger = logging.getLogger("orca.orchestrator")


def safety_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "safety" not in s.planned_agents:
        return skip_stage(s, "safety", "Safety Agent").model_dump()

    s = start_stage(s, "safety", "Safety Agent")

    try:
        safety = calculate_safety(
            weather=s.weather_result,
            marine=s.marine_result,
            warnings=s.warnings,
            boundary=s.geo_result,
            pfz_candidates=s.pfz_result,
        )
        s.safety_result = safety
        summary = f"Score: {safety.score}/100 ({safety.label}) | Override: {safety.critical_override}"
        s = complete_stage(s, "safety", source="ORCA Safety Engine (deterministic)", summary=summary, confidence=0.95)
    except Exception as exc:
        s = complete_stage(s, "safety", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def route_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "route" not in s.planned_agents:
        return skip_stage(s, "route", "Route Agent").model_dump()

    s = start_stage(s, "route", "Route Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        if s.intent == "escape_route" or "nearest port" in s.query.lower():
            safe_ports = [
                (13.0900, 80.2900), # Chennai Port
                (17.6833, 83.2833), # Visakhapatnam Port
                (9.9667, 76.2667),  # Kochi Port
                (18.9333, 72.8333), # Mumbai Port
                (22.0400, 88.0600), # Haldia Port
            ]
            import math
            def dist(p1, p2):
                return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
            
            nearest = min(safe_ports, key=lambda p: dist((loc.latitude, loc.longitude), p))
            end_lat, end_lon = nearest
        elif s.pfz_result:
            dest = s.pfz_result[0]
            end_lat, end_lon = dest.latitude, dest.longitude
        else:
            end_lat = loc.latitude + 0.5
            end_lon = loc.longitude + 0.5

        wave = s.marine_result.wave_height_m if s.marine_result else 1.5
        cur_speed = s.marine_result.current_speed_ms if s.marine_result else 0.3
        cur_dir = s.marine_result.current_direction_deg if s.marine_result else 90.0

        route = build_route_grid(
            loc.latitude, loc.longitude,
            end_lat, end_lon,
            wave_height=wave,
            current_speed=cur_speed,
            current_dir=cur_dir,
        )
        s.route_result = route
        summary = (
            f"Direct: {route.direct_distance_km} km | ORCA: {route.orca_distance_km} km | "
            f"Fuel reduction: {route.fuel_reduction_pct}% | Risk reduction: {route.risk_reduction_pct}%"
        )
        s = complete_stage(s, "route", source="ORCA A* Route Engine", summary=summary)
    except Exception as exc:
        s = complete_stage(s, "route", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def _build_graph():
    graph = StateGraph(dict)

    graph.add_node("planner", planner_node)
    graph.add_node("weather", weather_agent_node)
    graph.add_node("marine", marine_agent_node)
    graph.add_node("ocean", ocean_agent_node)
    graph.add_node("pfz", pfz_agent_node)
    graph.add_node("geospatial", geospatial_agent_node)
    graph.add_node("safety", safety_agent_node)
    graph.add_node("route", route_agent_node)
    graph.add_node("collective_impact", collective_impact_agent_node)
    graph.add_node("critic", critic_agent_node)
    graph.add_node("report", report_agent_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "weather")
    graph.add_edge("weather", "marine")
    graph.add_edge("marine", "ocean")
    graph.add_edge("ocean", "pfz")
    graph.add_edge("pfz", "geospatial")
    graph.add_edge("geospatial", "safety")
    graph.add_edge("safety", "route")
    graph.add_edge("route", "collective_impact")
    graph.add_edge("collective_impact", "critic")
    graph.add_edge("critic", "report")
    graph.add_edge("report", END)

    return graph.compile()


_COMPILED_GRAPH = None

def get_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = _build_graph()
    return _COMPILED_GRAPH


async def run_orca(request: ChatRequest) -> ChatResponse:
    request_id = str(uuid.uuid4())[:8]

    initial_state = OrcaState(
        request_id=request_id,
        query=request.query,
        language=request.language,
        location=Coordinates(latitude=request.latitude, longitude=request.longitude)
        if request.latitude is not None and request.longitude is not None else None,
        trace=AgentTrace(request_id=request_id, stages=[]),
        session_context={"history": request.history},
    )

    try:
        graph = get_graph()
        loop = asyncio.get_event_loop()
        result_dict = await loop.run_in_executor(
            None, lambda: graph.invoke(initial_state.model_dump())
        )
        s = OrcaState(**result_dict)
    except Exception as exc:
        return ChatResponse(
            request_id=request_id,
            answer=f"ORCA could not complete the reasoning workflow: {str(exc)[:120]}. Please retry.",
            language=request.language,
            trace=AgentTrace(request_id=request_id, stages=[]),
        )

    map_data = MapData()
    if s.location:
        map_data.user_location = {"lat": s.location.latitude, "lng": s.location.longitude}
    if s.pfz_result:
        map_data.pfz_candidates = [
            {"lat": p.latitude, "lng": p.longitude, "score": p.score, "id": p.id, "suitability": p.suitability}
            for p in s.pfz_result
        ]
    if s.route_result:
        map_data.route_geojson = {
            "direct": [{"lat": r.latitude, "lng": r.longitude} for r in s.route_result.direct_route],
            "orca": [{"lat": r.latitude, "lng": r.longitude} for r in s.route_result.orca_route],
        }
    map_data.geofence_geojson = get_geofence_geojson()
    if s.geo_result and s.geo_result.status != "NORMAL":
        map_data.layers_to_activate.append("geofence")
    if s.pfz_result:
        map_data.layers_to_activate.append("pfz")

    if s.collective_impact_result:
        map_data.fleet_congestion = {
            "zones": [
                {
                    "zone_id": z.zone_id,
                    "fcr": z.fcr_score,
                    "class": z.congestion_class,
                    "vessels": z.current_vessel_count,
                    "recommendation": z.recommendation,
                }
                for z in s.collective_impact_result.zones
            ],
            "pressure_warning": s.collective_impact_result.collective_pressure_warning,
        }
        if s.collective_impact_result.collective_pressure_warning:
            map_data.layers_to_activate.append("fleet_congestion")

    is_demo = any([
        getattr(s.weather_result, "is_demo", False),
        getattr(s.marine_result, "is_demo", False),
    ])

    return ChatResponse(
        request_id=request_id,
        answer=s.final_answer,
        language=s.language,
        safety=s.safety_result,
        evidence=s.evidence,
        map_data=map_data,
        route=s.route_result,
        pfz_candidates=s.pfz_result,
        critic=s.critic_result,
        collective_impact=s.collective_impact_result,
        trace=s.trace,
        is_demo=is_demo,
    )
