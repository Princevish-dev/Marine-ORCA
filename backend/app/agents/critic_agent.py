from app.models import OrcaState, CriticResult, ConflictItem
from app.agents.utils import start_stage, complete_stage, skip_stage

def critic_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "critic" not in s.planned_agents:
        return skip_stage(s, "critic", "Critic Agent").model_dump()

    s = start_stage(s, "critic", "Critic Agent")

    conflicts: list[ConflictItem] = []
    missing: list[str] = []
    stale: list[str] = []

    try:
        # Conflict 1: Weather vs Official Warning
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

        # Conflict 2: PFZ vs Safety Engine (Hazardous)
        if s.safety_result and s.pfz_result:
            if s.safety_result.score < 40 and any(p.score > 70 for p in s.pfz_result):
                conflicts.append(ConflictItem(
                    source_a="PFZ Engine",
                    source_a_value="High fishing zone suitability",
                    source_b="Safety Engine",
                    source_b_value=f"Safety score {s.safety_result.score}/100 (hazardous)",
                    resolution="SAFETY WARNING MUST ALWAYS OVERRIDE PRODUCTIVITY.",
                ))
                
        # Conflict 3: IUU Fishing (RESTRICTED ZONE VIOLATION)
        if s.geo_result and s.geo_result.inside:
            conflicts.append(ConflictItem(
                source_a="Geospatial Agent",
                source_a_value="Inside restricted area",
                source_b="Operations",
                source_b_value="Planned activity",
                resolution="CRITICAL: RESTRICTED_ZONE_VIOLATION. No fishing recommendation.",
            ))
            
        # Conflict 4: Overfishing (STOCK DEPLETION RISK)
        if s.pfz_result:
            best_pfz = max(s.pfz_result, key=lambda p: p.score)
            if best_pfz.score >= 70 and best_pfz.stock_depletion_risk:
                conflicts.append(ConflictItem(
                    source_a="PFZ Engine",
                    source_a_value="High PFZ score (FISH)",
                    source_b="Sustainability Check",
                    source_b_value="Stock depletion signal",
                    resolution="CONSERVE overrides FISH due to historical catch density depletion.",
                ))

        if not s.weather_result:
            missing.append("Weather forecast")
        if not s.marine_result:
            missing.append("Marine forecast")

        if s.collective_impact_result and s.collective_impact_result.collective_pressure_warning:
            avoided = s.collective_impact_result.avoided_zones
            diversified = s.collective_impact_result.diversified_zones
            conflicts.append(ConflictItem(
                source_a="PFZ Engine",
                source_a_value=f"Top zone(s) scored highest fish probability",
                source_b="Collective Impact Agent",
                source_b_value=f"HIGH fleet congestion in {', '.join(avoided)}. FCR > 60.",
                resolution=(
                    f"ANTI-CONGESTION OVERRIDE: {', '.join(avoided)} individually optimal "
                    f"but collectively unsafe. Diversify to {', '.join(diversified[:3])}. "
                    f"{s.collective_impact_result.redistribution_note}"
                ),
            ))

        confidence = max(0.5, 1.0 - len(conflicts) * 0.2 - len(missing) * 0.1)
        resolution_msg = (
            f"Detected {len(conflicts)} conflict(s). "
            + ("Official safety/sustainability rules prioritized." if conflicts else "No critical conflicts found.")
        )

        s.critic_result = CriticResult(
            has_conflict=len(conflicts) > 0,
            conflicts=conflicts,
            stale_sources=stale,
            missing_sources=missing,
            resolution_summary=resolution_msg,
            confidence=confidence,
        )
        s = complete_stage(s, "critic", source="ORCA Critic Engine",
                             summary=resolution_msg, confidence=confidence,
                             warning="CONFLICT DETECTED" if conflicts else "")
    except Exception as exc:
        s = complete_stage(s, "critic", summary=f"Error: {exc}", error=True)

    return s.model_dump()
