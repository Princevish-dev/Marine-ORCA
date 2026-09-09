# 🌊 ORCA — Marine EcOsystem Reasoning with Collaborative Agents

> **Smart India Hackathon 2026 | PS-26176 | ISRO / Department of Space**

ORCA is an **agentic AI marine intelligence platform** that continuously observes marine conditions, reasons across heterogeneous information sources, detects risk, explains its evidence, and helps fishers and operators make safer decisions.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  ORCA Frontend (Next.js)             │
│   Chat UI │ Marine Map │ Safety Gauge │ Alert Toasts │
└────────────────────┬────────────────────────────────┘
                     │ REST + SSE
┌────────────────────▼────────────────────────────────┐
│                 ORCA Backend (FastAPI)                │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │          LangGraph Agent Orchestrator         │   │
│  │  Planner → Weather → Marine → Ocean → PFZ    │   │
│  │  → Geospatial → Safety → Route → Critic      │   │
│  │  → Report                                    │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │
│  │ Safety   │  │ Geo      │  │  A* Router      │    │
│  │ Engine   │  │ Engine   │  │  (Hydrodynamic) │    │
│  │(Deterministic)│(Shapely)│  │                │    │
│  └──────────┘  └──────────┘  └────────────────┘    │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │     Background Guardian (asyncio task)        │  │
│  │  Open-Meteo Marine ──► Alert Eval ──► SSE Bus │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

External: Open-Meteo (Marine + Weather) — free, no key needed
LLM:      Google Gemini 1.5 Flash — interpretation + explanation only
```

---

## Key Features

| Feature | Status | Notes |
|---------|--------|-------|
| Conversational AI (EN + 7 Indian languages) | ✅ | Gemini 1.5 Flash |
| Agentic orchestration (LangGraph) | ✅ | 10 specialized agents |
| Safety barometer (0–100, deterministic) | ✅ | No LLM scoring |
| PFZ suitability engine | ✅ | EO-derived formula |
| A* hydrodynamic routing | ✅ | Fuel + risk optimization |
| Background Guardian (SSE push alerts) | ✅ | Async, non-blocking |
| Geofence (IMBL demo) | ✅ | Shapely point-in-polygon |
| Critic agent (conflict detection) | ✅ | Source priority system |
| Agent trace (expandable) | ✅ | Per-stage timing + source |
| Voice I/O | ✅ | Browser Web Speech API |
| Interactive marine map (Leaflet) | ✅ | PFZ, route, geofence layers |
| Supabase Auth (Email + Google OAuth) | ✅ | Protected dashboard |
| User Profiles (vessel, captain) | ✅ | Supabase Postgres + RLS |
| ISRO EO Data Loader | ✅ | CSV ingestion for SST/Chl |
| Demo mode (fixture data) | ✅ | Clearly labelled |

---

## REAL vs MODELLED

| Component | Type | Source |
|-----------|------|--------|
| Wave height, period | **Real forecast** | Open-Meteo Marine API |
| Wind speed, direction | **Real forecast** | Open-Meteo Weather API |
| SST | **Modelled proxy** | Derived from temperature (labelled) |
| Chlorophyll | **Modelled proxy** | Latitude-based coastal estimate |
| PFZ score | **Derived formula** | EO-derived SST + Chl model |
| Safety score | **Deterministic formula** | ORCA calculation |
| Route fuel savings | **Modelled estimate** | A* hydrodynamic model |
| NL response | **LLM explanation** | Gemini — explains evidence only |
| Maritime boundary | **Demo demonstration** | Not official legal boundary |

---

## Project Structure

```
orca/
├── frontend/              
│   └── src/
│       ├── app/           
│       │   ├── login/     
│       │   └── profile/   
│       ├── components/    
│       ├── hooks/         
│       ├── lib/           
│       └── types/         
│
├── backend/
│   └── app/
│       ├── agents/        
│       ├── api/           
│       ├── geospatial/    
│       ├── guardian/      
│       ├── models/        
│       ├── routing/       
│       └── services/      
│   └── data/
│       └── isro/          
│
├── supabase/
│   └── schema.sql         
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## HOW TO RUN

### Prerequisites
- Python 3.11+
- Node.js 20+
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### Backend

```bash
cd orca/backend

copy .env.example .env

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Backend starts at **http://localhost:8000**
API docs at **http://localhost:8000/docs**

### Frontend

```bash
cd orca/frontend

npm install

npm run dev
```

Frontend starts at **http://localhost:3000**

### Demo Mode (no live APIs)

```bash
DEMO_MODE=true
GUARDIAN_INTERVAL_SECONDS=15
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Main conversational endpoint |
| `GET` | `/api/health` | System health + Guardian status |
| `GET` | `/api/events` | SSE stream for Guardian alerts |
| `GET` | `/api/marine` | Marine + weather + ocean data |
| `GET` | `/api/pfz` | PFZ candidates for location |
| `GET` | `/api/layers` | Map layer GeoJSON |
| `POST` | `/api/route` | Route calculation |
| `GET` | `/api/alerts` | Recent Guardian alerts |
| `POST` | `/api/alerts/test` | Trigger test alert (dev only) |

---

## Agent Architecture

```
Planner Agent        → Intent, location, time extraction
Weather Agent        → Open-Meteo weather forecast
Marine Agent         → Open-Meteo marine forecast
Ocean Analytics      → SST, Chlorophyll (EO-derived)
PFZ Agent            → Suitability scoring formula
Geospatial Agent     → Shapely boundary + distance
Safety Agent         → Deterministic safety score
Route Agent          → A* hydrodynamic routing
Critic Agent         → Source conflict detection
Report Agent         → Gemini NL response generation
```

LLM is used **only** for interpretation and explanation.
Numbers are calculated by deterministic engines.

---

## Testing

```bash
cd orca/backend
pytest tests/ -v
```

Tests cover: safety scoring, alert predicates, geospatial engine, route engine.

---

## Demo Scenarios

1. **"Is it safe to go fishing tomorrow morning?"** → Safety barometer + agent trace
2. **"कल सुबह यहाँ मछली पकड़ना सुरक्षित है?"** → Hindi response
3. **"Find a fishing zone and show me the route"** → PFZ + route comparison
4. **Click ⚡ Test Alert button** → Guardian SSE push notification
5. **Move near boundary on map** → Geofence YELLOW/ORANGE/RED alert

---

## Environment Variables

See [`.env.example`](./.env.example) for all configurable variables.

Critical:
- `GEMINI_API_KEY` — LLM (get free at aistudio.google.com)
- `DEMO_MODE=true` — use fixture data (no live APIs needed)
- `GUARDIAN_INTERVAL_SECONDS=15` — fast guardian for demo
- `NEXT_PUBLIC_SUPABASE_URL` — your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — your Supabase anon key
- `ISRO_DATA_DIR=data/isro` — path to downloaded ISRO CSV data

---

## Known Limitations (Prototype)

- SST and chlorophyll use modelled proxies, not satellite data (clearly labelled)
- Maritime boundaries are demonstration thresholds, not legal boundaries
- Route fuel savings are modelled estimates, not vessel measurements
- Voice recognition quality depends on browser and microphone
- Gemini API key required for NL responses; deterministic fallback provided

---

*Built for Smart India Hackathon 2026 | PS-26176 | ISRO / Department of Space*
