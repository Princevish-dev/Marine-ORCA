# ORCA Demo Guide

## Setup for Demo

```bash
# Backend .env
DEMO_MODE=false           # Use live APIs
GEMINI_API_KEY=...        # Your Gemini key
GUARDIAN_INTERVAL_SECONDS=15   # Fast for demo

# OR for offline demo:
DEMO_MODE=true
GUARDIAN_INTERVAL_SECONDS=15
```

---

## 5 Judge-Impressive Demo Moments

### 1. Safety Assessment + Agent Trace

**Ask:** "Is it safe to go fishing tomorrow morning?"

**Show:**
- Thinking indicator pulses (4–7 seconds)
- Click "▾ Agent Trace" to expand
- Show 10 agents executing with timings
- Safety Gauge updates to live score
- Evidence panel populates with sources

### 2. Multilingual (Hindi)

**Switch language** to हिन्दी
**Ask:** "कल सुबह यहाँ मछली पकड़ना सुरक्षित है क्या?"

**Show:**
- Same agent pipeline executes
- Response returns in Hindi
- Technical source names stay in English

### 3. PFZ + Route Optimisation

**Ask:** "Find a fishing zone and show me the safest route"

**Show:**
- PFZ panel populates with scored zones
- Map updates with 🐟 zone markers
- Route panel shows Direct vs ORCA route
- Fuel/risk savings displayed (labelled as modelled)

### 4. Guardian Alert (SSE)

**Click** ⚡ Test Alert button (top right of map)

**Show:**
- Alert appears without any user action
- Toast slides in from right
- "ORCA Guardian connected" pushed via SSE
- Alerts panel updates

### 5. Source Conflict (Critic Agent)

Configure DEMO_MODE=true with YELLOW warning + calm weather
to trigger critic conflict card showing:
- Weather says CALM
- Warning feed says YELLOW
- ORCA resolves: Official warning prioritised

---

## Key Messages for Judges

1. **LLM does NOT invent data** — it only explains evidence
2. **Safety score is deterministic** — formula-based, auditable
3. **Guardian runs proactively** — not just on user query
4. **Evidence is always shown** — every number has a source
5. **Multilingual** — 8 Indian languages supported
