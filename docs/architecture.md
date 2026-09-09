# ORCA Architecture

## System Overview

ORCA is an **agentic marine intelligence platform** built around a strict separation:

- **LLM**: interprets intent, generates explanations
- **Deterministic engines**: calculate safety scores, distances, geofence states, routes
- **External APIs**: provide real weather/marine data (Open-Meteo)
- **SSE Guardian**: proactively monitors and pushes alerts

## Component Map

```
Frontend (Next.js 14)
  └── ChatPanel          → user interaction, voice I/O
  └── MarineMap          → Leaflet, layers, click info
  └── SafetyGauge        → SVG arc gauge
  └── AgentTrace         → expandable execution trace
  └── AlertComponents    → SSE-pushed toast alerts, conflict card
  └── EvidencePanel      → structured evidence display
  └── PFZPanel           → fishing zone candidates
  └── RouteComparison    → direct vs ORCA route

Backend (FastAPI + Python)
  └── api/               → REST endpoints + SSE
  └── agents/            → LangGraph orchestrator (10 agents)
  └── services/          → data providers + safety calculator
  └── geospatial/        → Shapely engine (boundary, PFZ)
  └── routing/           → A* hydrodynamic router
  └── guardian/          → asyncio background task + event bus
  └── models/            → Pydantic typed models
```

## Data Flow

```
User Query
    │
    ▼
POST /api/chat
    │
    ▼
LangGraph Pipeline
    │
    ├── Planner → parse intent (LLM structured output, validated)
    ├── Weather → Open-Meteo (async HTTP)
    ├── Marine  → Open-Meteo Marine (async HTTP)
    ├── Ocean   → modelled SST/Chl proxy
    ├── PFZ     → deterministic formula (SST × Chl × gradient)
    ├── Geo     → Shapely point-in-polygon + haversine
    ├── Safety  → deterministic formula (penalties + clamp)
    ├── Route   → A* grid (optional, when route intent)
    ├── Critic  → source priority conflict check
    └── Report  → Gemini LLM (explains evidence only)
    │
    ▼
ChatResponse (JSON)
    │
    ├── answer          (NL text)
    ├── safety          (structured score)
    ├── evidence        (source list)
    ├── map_data        (GeoJSON overlays)
    ├── route           (direct + ORCA polylines)
    ├── pfz_candidates  (scored zones)
    ├── critic          (conflicts)
    └── trace           (per-agent timing)
```

## Source Priority

```
1. Official warning (RED > ORANGE > YELLOW > INFO)
2. Authoritative observation
3. Forecast provider (Open-Meteo)
4. Derived ORCA calculation (safety score, PFZ)
5. LLM explanation
```

When sources conflict, the Critic agent detects and the Report agent discloses.
