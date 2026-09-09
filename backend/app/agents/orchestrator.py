from __future__ import annotations
import asyncio
import uuid
import json
import math
import re
from datetime import datetime, timezone, timedelta
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.models import (
    OrcaState, Coordinates, TimeWindow,
    WeatherObservation, MarineObservation, OceanObservation,
    WarningEvent, BoundaryStatus, PFZCandidate,
    SafetyAssessment, CriticResult, ConflictItem,
    RouteResult, EvidenceItem, AgentTrace, TraceStage,
    ChatRequest, ChatResponse, MapData,
)
from app.config import settings
from app.services.data_providers import fetch_weather, fetch_marine, fetch_ocean_observation
from app.services.safety_calculator import calculate_safety
from app.geospatial.engine import check_boundary_status, generate_pfz_candidates, get_geofence_geojson
from app.routing.astar import build_route_grid


def _get_llm():
    if not settings.gemini_api_key:
        return None
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.2,
        max_tokens=1024,
    )


def _llm_call(prompt: str, system: str = "") -> str:
    llm = _get_llm()
    if not llm:
        return prompt
    try:
        msgs = []
        if system:
            msgs.append(SystemMessage(content=system))
        msgs.append(HumanMessage(content=prompt))
        response = llm.invoke(msgs)
        return response.content
    except Exception as exc:
        return f"[LLM unavailable: {str(exc)[:80]}]"


def _start_stage(state: OrcaState, stage_id: str, name: str) -> OrcaState:
    stage = TraceStage(id=stage_id, name=name, status="RUNNING", started_at=datetime.now(timezone.utc))
    state.trace.stages.append(stage)
    return state


def _complete_stage(
    state: OrcaState, stage_id: str,
    source: str = "", summary: str = "",
    confidence: float = 1.0, warning: str = "", error: bool = False,
) -> OrcaState:
    for st in state.trace.stages:
        if st.id == stage_id:
            st.status = "ERROR" if error else "COMPLETED"
            st.completed_at = datetime.now(timezone.utc)
            if st.started_at:
                st.duration_ms = (st.completed_at - st.started_at).total_seconds() * 1000
            st.source = source
            st.result_summary = summary
            st.confidence = confidence
            st.warning = warning or None
    return state


def _skip_stage(state: OrcaState, stage_id: str, name: str) -> OrcaState:
    stage = TraceStage(id=stage_id, name=name, status="SKIPPED")
    state.trace.stages.append(stage)
    return state


def planner_node(state: dict) -> dict:
    s = OrcaState(**state)
    s = _start_stage(s, "planner", "Planner")

    query = s.query
    lang = s.language

    if not s.location:
        s.location = Coordinates(latitude=13.0827, longitude=80.2707)

    now = datetime.now(timezone.utc)
    s.time_window = TimeWindow(
        start=now + timedelta(hours=8),
        end=now + timedelta(hours=14),
        description="Tomorrow morning",
    )

    system = (
        "You are ORCA Planner. Extract intent from the marine query. "
        "Respond ONLY with JSON: "
        '{"intent": "...", "location_hint": "...", "time_hint": "...", '
        '"agents": ["weather","marine","safety","geospatial","pfz","critic","report"]}'
        "\nPossible intents: marine_safety, pfz_query, route_planning, general_info"
    )
    try:
        llm_out = _llm_call(query, system)
        json_match = re.search(r'\{.*\}', llm_out, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            s.intent = parsed.get("intent", "marine_safety")
            agents = parsed.get("agents", [])
            mandatory = ["weather", "marine", "safety", "critic", "report"]
            s.planned_agents = list(set(mandatory + agents))
        else:
            raise ValueError("No JSON in LLM response")
    except Exception:
        q_lower = query.lower()
        if any(w in q_lower for w in ["route", "navigate", "shortest", "path", "रास्ता"]):
            s.intent = "route_planning"
            s.planned_agents = ["weather", "marine", "safety", "geospatial", "route", "critic", "report"]
        elif any(w in q_lower for w in ["pfz", "fishing zone", "where to fish", "मछली", "zone"]):
            s.intent = "pfz_query"
            s.planned_agents = ["marine", "ocean", "pfz", "geospatial", "safety", "critic", "report"]
        else:
            s.intent = "marine_safety"
            s.planned_agents = ["weather", "marine", "safety", "geospatial", "critic", "report"]

    summary = f"Intent: {s.intent} | Agents: {', '.join(s.planned_agents)}"
    s = _complete_stage(s, "planner", source="ORCA Planner + Gemini", summary=summary)
    return s.model_dump()


def weather_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "weather" not in s.planned_agents:
        return _skip_stage(s, "weather", "Weather Agent").model_dump()

    s = _start_stage(s, "weather", "Weather Agent")
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
        s = _complete_stage(s, "weather", source=w.source, summary=summary,
                             confidence=0.7 if w.is_demo else 0.9,
                             warning="DEMO DATA" if w.is_demo else "")
    except Exception as exc:
        s = _complete_stage(s, "weather", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def marine_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "marine" not in s.planned_agents:
        return _skip_stage(s, "marine", "Marine Agent").model_dump()

    s = _start_stage(s, "marine", "Marine Agent")
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
        s = _complete_stage(s, "marine", source=m.source, summary=summary,
                             confidence=0.7 if m.is_demo else 0.9,
                             warning="DEMO DATA" if m.is_demo else "")
    except Exception as exc:
        s = _complete_stage(s, "marine", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def ocean_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "ocean" not in s.planned_agents:
        return _skip_stage(s, "ocean", "Ocean Analytics Agent").model_dump()

    s = _start_stage(s, "ocean", "Ocean Analytics Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        o = asyncio.get_event_loop().run_until_complete(
            fetch_ocean_observation(loc.latitude, loc.longitude)
        )
        s.ocean_result = o
        s.evidence.append(EvidenceItem(
            source=o.source,
            type="Demo" if o.is_demo else "EO",
            description=f"SST: {o.sst_celsius}°C | Chlorophyll: {o.chlorophyll_mgm3} mg/m³",
            valid_at=o.retrieved_at,
            is_demo=o.is_demo,
        ))
        summary = f"SST: {o.sst_celsius}°C | Chl: {o.chlorophyll_mgm3} mg/m³ ({o.data_type})"
        s = _complete_stage(s, "ocean", source=o.source, summary=summary,
                             warning="EO-derived estimate" if o.data_type == "MODEL" else "")
    except Exception as exc:
        s = _complete_stage(s, "ocean", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def pfz_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "pfz" not in s.planned_agents:
        return _skip_stage(s, "pfz", "PFZ Agent").model_dump()

    s = _start_stage(s, "pfz", "PFZ Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        sst = s.ocean_result.sst_celsius if s.ocean_result else None
        chl = s.ocean_result.chlorophyll_mgm3 if s.ocean_result else None
        candidates_raw = generate_pfz_candidates(loc.latitude, loc.longitude, sst, chl)
        s.pfz_result = [PFZCandidate(**c) for c in candidates_raw]
        top = s.pfz_result[0] if s.pfz_result else None
        summary = (
            f"Found {len(s.pfz_result)} candidates. "
            + (f"Best: {top.suitability} @ {top.distance_km} km (score {top.score})" if top else "No candidates.")
        )
        s = _complete_stage(s, "pfz", source="ORCA PFZ Engine (EO-derived)", summary=summary, confidence=0.75)
    except Exception as exc:
        s = _complete_stage(s, "pfz", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def geospatial_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "geospatial" not in s.planned_agents:
        return _skip_stage(s, "geospatial", "Geospatial Agent").model_dump()

    s = _start_stage(s, "geospatial", "Geospatial Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        boundary = check_boundary_status(loc.latitude, loc.longitude)
        s.geo_result = boundary
        summary = (
            f"Boundary status: {boundary.status} | "
            f"Nearest: {boundary.nearest_restriction_name} ({boundary.distance_km} km)"
        )
        s = _complete_stage(s, "geospatial", source="ORCA Geospatial Engine (Shapely)", summary=summary)
    except Exception as exc:
        s = _complete_stage(s, "geospatial", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def safety_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "safety" not in s.planned_agents:
        return _skip_stage(s, "safety", "Safety Agent").model_dump()

    s = _start_stage(s, "safety", "Safety Agent")

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
        s = _complete_stage(s, "safety", source="ORCA Safety Engine (deterministic)", summary=summary, confidence=0.95)
    except Exception as exc:
        s = _complete_stage(s, "safety", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def route_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "route" not in s.planned_agents:
        return _skip_stage(s, "route", "Route Agent").model_dump()

    s = _start_stage(s, "route", "Route Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        if s.pfz_result:
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
        s = _complete_stage(s, "route", source="ORCA A* Route Engine", summary=summary)
    except Exception as exc:
        s = _complete_stage(s, "route", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def critic_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "critic" not in s.planned_agents:
        return _skip_stage(s, "critic", "Critic Agent").model_dump()

    s = _start_stage(s, "critic", "Critic Agent")

    conflicts: list[ConflictItem] = []
    missing: list[str] = []
    stale: list[str] = []

    try:
        if s.weather_result and s.warnings:
            for w in s.warnings:
                if w.is_active and w.severity in ("RED", "ORANGE"):
                    if s.weather_result.wind_speed_kmh < 25:
                        conflicts.append(ConflictItem(
                            source_a=s.weather_result.source,
                            source_a_value=f"Wind {s.weather_result.wind_speed_kmh:.0f} km/h (Calm)",
                            source_b=w.source,
                            source_b_value=f"{w.severity} — {w.title}",
                            resolution="Official warning takes priority. Forecast conditions may not capture localized severe event.",
                        ))

        if s.safety_result and s.pfz_result:
            if s.safety_result.score < 40 and any(p.score > 70 for p in s.pfz_result):
                conflicts.append(ConflictItem(
                    source_a="PFZ Engine",
                    source_a_value="High fishing zone suitability",
                    source_b="Safety Engine",
                    source_b_value=f"Safety score {s.safety_result.score}/100 (hazardous)",
                    resolution="Safety takes precedence. Fishing zone suitability does not override hazardous conditions.",
                ))

        if not s.weather_result:
            missing.append("Weather forecast")
        if not s.marine_result:
            missing.append("Marine forecast")

        confidence = max(0.5, 1.0 - len(conflicts) * 0.2 - len(missing) * 0.1)
        resolution = (
            f"Detected {len(conflicts)} conflict(s). "
            + ("Official sources prioritized." if conflicts else "No critical conflicts found.")
        )

        s.critic_result = CriticResult(
            has_conflict=len(conflicts) > 0,
            conflicts=conflicts,
            stale_sources=stale,
            missing_sources=missing,
            resolution_summary=resolution,
            confidence=confidence,
        )
        s = _complete_stage(s, "critic", source="ORCA Critic Engine",
                             summary=resolution, confidence=confidence,
                             warning="CONFLICT DETECTED" if conflicts else "")
    except Exception as exc:
        s = _complete_stage(s, "critic", summary=f"Error: {exc}", error=True)

    return s.model_dump()


def report_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    s = _start_stage(s, "report", "Report Agent")

    try:
        safety = s.safety_result
        weather = s.weather_result
        marine = s.marine_result
        lang = s.language

        context_lines = [f"User query: {s.query}"]
        if safety:
            context_lines.append(f"Safety score: {safety.score}/100 ({safety.label})")
            context_lines.append(f"Safety explanation: {safety.explanation}")
        if weather:
            context_lines.append(f"Wind: {weather.wind_speed_kmh:.0f} km/h, Condition: {weather.weather_condition}")
        if marine:
            context_lines.append(f"Wave height: {marine.wave_height_m:.1f} m, Period: {marine.wave_period_s:.1f} s")
        if s.geo_result:
            context_lines.append(f"Boundary status: {s.geo_result.status} ({s.geo_result.distance_km} km)")
        if s.pfz_result:
            top = s.pfz_result[0]
            context_lines.append(f"Nearest PFZ: {top.distance_km} km away (score {top.score}/100)")
        if s.route_result:
            context_lines.append(
                f"ORCA route: {s.route_result.orca_distance_km} km "
                f"(vs direct {s.route_result.direct_distance_km} km), "
                f"modelled fuel saving {s.route_result.fuel_reduction_pct}%"
            )
        context = "\n".join(context_lines)
        is_demo = any([
            getattr(s.weather_result, "is_demo", False),
            getattr(s.marine_result, "is_demo", False),
        ])

        lang_instruction = {
            "hi": "Respond in Hindi (Devanagari script). Keep source names in English.",
            "bn": "Respond in Bengali.",
            "ta": "Respond in Tamil.",
            "te": "Respond in Telugu.",
            "mr": "Respond in Marathi.",
            "gu": "Respond in Gujarati.",
            "kn": "Respond in Kannada.",
        }.get(lang, "Respond in English.")

        system_prompt = f"""You are ORCA, a professional marine decision-support AI.
Generate a clear, structured response based ONLY on the provided data. Do NOT invent any numbers.
Use professional marine terminology. Mention evidence sources.
{lang_instruction}
{"NOTE: Data is from DEMO FIXTURES — clearly state this." if is_demo else ""}
If safety score < 50, recommend caution clearly. If score >= 80, state conditions look favorable.
Format: Brief assessment paragraph, then key conditions list, then recommendation."""

        answer = _llm_call(context, system_prompt)

        if "[LLM unavailable" in answer or not answer.strip():
            if safety:
                if safety.score >= 80:
                    status_word = "favorable" if lang == "en" else "अनुकूल" if lang == "hi" else "favorable"
                elif safety.score >= 60:
                    status_word = "moderate with caution advised"
                else:
                    status_word = "hazardous — avoid if possible"
                answer = (
                    f"ORCA Assessment — Safety: {safety.score}/100 ({safety.label})\n\n"
                    f"Conditions appear {status_word}.\n\n"
                    f"{safety.explanation}\n\n"
                    + (f"Wind: {weather.wind_speed_kmh:.0f} km/h | " if weather else "")
                    + (f"Waves: {marine.wave_height_m:.1f} m\n\n" if marine else "")
                    + "Verify latest official marine warnings before departure."
                )
            else:
                answer = "ORCA could not complete the full assessment. Please retry."

        s.final_answer = answer
        s = _complete_stage(s, "report", source="Gemini 1.5 Flash + ORCA Evidence Engine",
                             summary="Response generated successfully")
    except Exception as exc:
        s.final_answer = "ORCA could not complete the reasoning workflow. Please retry."
        s = _complete_stage(s, "report", summary=f"Error: {exc}", error=True)

    if s.trace.stages:
        first = next((st.started_at for st in s.trace.stages if st.started_at), None)
        last = max((st.completed_at for st in s.trace.stages if st.completed_at), default=None)
        if first and last:
            s.trace.total_duration_ms = (last - first).total_seconds() * 1000

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
    graph.add_edge("route", "critic")
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
        if request.latitude and request.longitude else None,
        trace=AgentTrace(request_id=request_id, stages=[]),
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
        trace=s.trace,
        is_demo=is_demo,
    )
