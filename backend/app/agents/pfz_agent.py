from app.models import OrcaState, Coordinates, PFZCandidate
from app.geospatial.engine import generate_pfz_candidates
from app.agents.utils import start_stage, complete_stage, skip_stage

def pfz_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "pfz" not in s.planned_agents:
        return skip_stage(s, "pfz", "PFZ Agent").model_dump()

    s = start_stage(s, "pfz", "PFZ Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        sst = s.ocean_result.sst_celsius if s.ocean_result else None
        chl = s.ocean_result.chlorophyll_mgm3 if s.ocean_result else None
        candidates_raw = generate_pfz_candidates(loc.latitude, loc.longitude, sst, chl)
        
        pfz_list = []
        for c in candidates_raw:
            p = PFZCandidate(**c)
            # Food Security / Catch Efficiency Enhancement
            p.catch_probability = min(0.95, p.score / 100.0 * 1.2)
            # Overfishing Enhancement: Simulate historical catch density
            p.historical_catch_density = max(10.0, 100.0 - (p.distance_km * 2))
            if p.historical_catch_density < 30.0:
                p.stock_depletion_risk = True
            pfz_list.append(p)
            
        s.pfz_result = pfz_list
        top = s.pfz_result[0] if s.pfz_result else None
        
        if top and top.stock_depletion_risk:
            summary_risk = " | STOCK DEPLETION RISK detected"
        else:
            summary_risk = ""
            
        summary = (
            f"Found {len(s.pfz_result)} candidates. "
            + (f"Best: {top.suitability} @ {top.distance_km} km (score {top.score})" + summary_risk if top else "No candidates.")
        )
        s = complete_stage(s, "pfz", source="ORCA PFZ Engine (EO-derived)", summary=summary, confidence=0.75)
    except Exception as exc:
        s = complete_stage(s, "pfz", summary=f"Error: {exc}", error=True)

    return s.model_dump()
