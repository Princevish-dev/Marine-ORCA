import re
import json
import asyncio
from datetime import datetime, timezone, timedelta

from app.models import OrcaState, Coordinates, TimeWindow, WarningEvent
from app.config import settings
from app.services.demo_fixtures import DEMO_WARNING
from app.services.data_providers import fetch_warning_events
from app.agents.utils import start_stage, complete_stage, llm_call

def planner_node(state: dict) -> dict:
    s = OrcaState(**state)
    s = start_stage(s, "planner", "Planner")

    query = s.query
    lang = s.language

    if not s.location:
        s.location = Coordinates(latitude=13.0827, longitude=80.2707)

    greeting_words = {
        "hi", "hello", "hey", "hii", "helo", "namaste", "namaskar",
        "good morning", "good afternoon", "good evening", "thanks", "thank you",
    }
    if query.strip().lower() in greeting_words:
        s.intent = "conversation"
        s.planned_agents = ["report"]
        s = complete_stage(
            s,
            "planner",
            source="ORCA Intent Router",
            summary="Conversation message; marine data agents skipped",
        )
        return s.model_dump()

    if settings.demo_mode:
        s.warnings = [WarningEvent(**DEMO_WARNING)]
    elif settings.imd_feed_url:
        try:
            s.warnings = asyncio.get_event_loop().run_until_complete(fetch_warning_events())
        except Exception:
            s.warnings = []

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
        '"agents": ["weather","marine","safety","geospatial","pfz","critic","route","report"]}'
        "\nPossible intents: marine_safety, pfz_query, route_planning, escape_route, general_info"
    )
    try:
        llm_out = llm_call(query, system)
        json_match = re.search(r'\{.*\}', llm_out, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            s.intent = parsed.get("intent", "marine_safety")
            agents = parsed.get("agents", [])
            mandatory = ["weather", "marine", "safety", "collective_impact", "critic", "report"]
            if s.intent == "conversation":
                mandatory = ["report"]
            query_lower = query.lower()
            route_requested = any(word in query_lower for word in [
                "route", "navigate", "shortest", "path", "escape", "nearest port", "रास्ता",
            ])
            if s.intent == "escape_route" or s.intent == "route_planning" or route_requested:
                mandatory.append("route")
            s.planned_agents = list(set(mandatory + agents))
        else:
            raise ValueError("No JSON in LLM response")
    except Exception:
        s.intent = "marine_safety"
        s.planned_agents = ["weather", "marine", "ocean", "pfz", "geospatial", "safety", "route", "collective_impact", "critic", "report"]

    summary = f"Intent: {s.intent} | Agents: {', '.join(s.planned_agents)}"
    s = complete_stage(s, "planner", source="ORCA Planner + Ollama", summary=summary)
    return s.model_dump()
