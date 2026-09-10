from app.models import OrcaState, Coordinates
from app.geospatial.engine import check_boundary_status
from app.agents.utils import start_stage, complete_stage, skip_stage

def geospatial_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "geospatial" not in s.planned_agents:
        return skip_stage(s, "geospatial", "Geospatial Agent").model_dump()

    s = start_stage(s, "geospatial", "Geospatial Agent")
    loc = s.location or Coordinates(latitude=13.0827, longitude=80.2707)

    try:
        boundary = check_boundary_status(loc.latitude, loc.longitude)
        
        # IUU Fishing & Habitat Destruction enhancements
        # In a full implementation, we would query ESZ layers from a DB.
        # Here we simulate an ESZ proximity check for demonstration.
        esz_distance_km = 6.0 # Mock distance
        if esz_distance_km < 5.0:
            setattr(boundary, "ecological_penalty", 10.0)
            setattr(boundary, "esz_proximity", True)
        else:
            setattr(boundary, "ecological_penalty", 0.0)
            setattr(boundary, "esz_proximity", False)
            
        s.geo_result = boundary
        summary = (
            f"Boundary status: {boundary.status} | "
            f"Nearest: {boundary.nearest_restriction_name} ({boundary.distance_km} km)"
        )
        s = complete_stage(s, "geospatial", source="ORCA Geospatial Engine (Shapely)", summary=summary)
    except Exception as exc:
        s = complete_stage(s, "geospatial", summary=f"Error: {exc}", error=True)

    return s.model_dump()
