import random
import hashlib
from app.models import OrcaState, Coordinates, ZoneCongestion, CollectiveImpactResult, EvidenceItem
from app.agents.utils import start_stage, complete_stage, skip_stage

_recommendation_ledger: dict[str, int] = {}

def _get_simulated_vessel_density(zone_id: str, lat: float, lon: float) -> int:
    seed = int(hashlib.md5(f"{zone_id}{lat:.2f}{lon:.2f}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.randint(0, 35)

def _get_predicted_incoming(zone_id: str, current_count: int) -> int:
    seed = int(hashlib.md5(zone_id.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.randint(0, max(1, current_count // 2))

def _get_fishing_pressure(zone_id: str, historical_catch_density: float) -> float:
    base = max(0.0, 100.0 - historical_catch_density)
    return min(100.0, base * 1.2)

def _get_gear_conflict_risk(vessel_count: int) -> float:
    if vessel_count < 5:
        return 5.0
    elif vessel_count < 15:
        return 25.0
    elif vessel_count < 25:
        return 50.0
    return 80.0

def _get_ecological_pressure(zone_id: str, stock_depletion_risk: bool, esz_proximity: bool) -> float:
    base = 10.0
    if stock_depletion_risk:
        base += 40.0
    if esz_proximity:
        base += 30.0
    return min(100.0, base)

def compute_fcr(vessel_density: int, predicted_incoming: int, fishing_pressure: float,
                gear_conflict_risk: float, ecological_pressure: float) -> float:
    w_density = 0.30
    w_predicted = 0.15
    w_fishing = 0.20
    w_gear = 0.15
    w_eco = 0.20

    norm_density = min(100.0, vessel_density * 3.0)
    norm_predicted = min(100.0, predicted_incoming * 5.0)

    fcr = (w_density * norm_density +
           w_predicted * norm_predicted +
           w_fishing * fishing_pressure +
           w_gear * gear_conflict_risk +
           w_eco * ecological_pressure)

    return round(min(100.0, max(0.0, fcr)), 1)

def classify_congestion(fcr: float) -> str:
    if fcr < 30:
        return "LOW"
    elif fcr <= 60:
        return "MODERATE"
    return "HIGH"

def zone_recommendation(fcr: float, safety_score: float) -> str:
    if safety_score < 40:
        return "AVOID"
    if fcr > 60:
        return "AVOID"
    if fcr > 30:
        return "CAUTION"
    return "GO"

def collective_impact_agent_node(state: dict) -> dict:
    s = OrcaState(**state)
    if "collective_impact" not in s.planned_agents and "critic" not in s.planned_agents:
        return skip_stage(s, "collective_impact", "Collective Impact Agent").model_dump()

    if not s.pfz_result:
        s = skip_stage(s, "collective_impact", "Collective Impact Agent")
        return s.model_dump()

    s = start_stage(s, "collective_impact", "Collective Impact Agent")

    try:
        safety_score = s.safety_result.score if s.safety_result else 80.0
        esz_proximity = getattr(s.geo_result, "esz_proximity", False) if s.geo_result else False

        zones: list[ZoneCongestion] = []

        for pfz in s.pfz_result:
            vessel_count = _get_simulated_vessel_density(pfz.id, pfz.latitude, pfz.longitude)
            predicted_incoming = _get_predicted_incoming(pfz.id, vessel_count)
            fishing_pressure = _get_fishing_pressure(pfz.id, getattr(pfz, "historical_catch_density", 50.0) or 50.0)
            gear_conflict = _get_gear_conflict_risk(vessel_count)
            eco_pressure = _get_ecological_pressure(pfz.id, pfz.stock_depletion_risk, esz_proximity)

            orca_recs = _recommendation_ledger.get(pfz.id, 0)
            recommendation_overlap_penalty = min(40.0, orca_recs * 5.0)

            fcr = compute_fcr(
                vessel_count + orca_recs,
                predicted_incoming,
                fishing_pressure,
                gear_conflict + recommendation_overlap_penalty,
                eco_pressure,
            )
            congestion_class = classify_congestion(fcr)
            rec = zone_recommendation(fcr, safety_score)

            fuel_eff = max(0.0, 100.0 - pfz.distance_km * 2)

            zone = ZoneCongestion(
                zone_id=pfz.id,
                fish_probability=pfz.score,
                safety_score=safety_score,
                fuel_efficiency=round(fuel_eff, 1),
                current_vessel_count=vessel_count,
                predicted_incoming=predicted_incoming,
                fishing_pressure=round(fishing_pressure, 1),
                gear_conflict_risk=round(gear_conflict, 1),
                ecological_pressure=round(eco_pressure, 1),
                fcr_score=fcr,
                congestion_class=congestion_class,
                recommendation=rec,
            )
            zones.append(zone)

            pfz.fcr_score = fcr
            pfz.congestion_class = congestion_class
            pfz.fleet_recommendation = rec

        avoided = [z for z in zones if z.recommendation == "AVOID"]
        diversified = [z for z in zones if z.recommendation in ("GO", "CAUTION")]
        pressure_warning = len(avoided) > 0

        best_zone = max(zones, key=lambda z: z.fish_probability) if zones else None
        concentration = 0.0
        if best_zone and best_zone.recommendation == "AVOID":
            concentration = best_zone.fcr_score

        redistribution_note = ""
        if pressure_warning and best_zone:
            alt_names = ", ".join(z.zone_id for z in diversified[:3])
            redistribution_note = (
                f"{best_zone.zone_id} is individually best (fish probability "
                f"{best_zone.fish_probability}%) but collectively unsafe due to "
                f"high vessel density ({best_zone.current_vessel_count} boats, "
                f"FCR {best_zone.fcr_score}). "
                f"ORCA recommends diversifying to {alt_names}."
            )

        if diversified:
            top_rec = sorted(diversified, key=lambda z: z.fish_probability, reverse=True)[0]
            _recommendation_ledger[top_rec.zone_id] = _recommendation_ledger.get(top_rec.zone_id, 0) + 1

        result = CollectiveImpactResult(
            zones=zones,
            collective_pressure_warning=pressure_warning,
            redistribution_note=redistribution_note,
            recommendation_concentration=concentration,
            diversified_zones=[z.zone_id for z in diversified],
            avoided_zones=[z.zone_id for z in avoided],
        )
        s.collective_impact_result = result

        if pressure_warning:
            s.evidence.append(EvidenceItem(
                source="ORCA Collective Impact Engine",
                type="Derived",
                description=redistribution_note,
                is_demo=True,
            ))

        summary = (
            f"Analyzed {len(zones)} zones. "
            f"Avoided: {len(avoided)}. Diversified: {len(diversified)}. "
            f"Pressure warning: {pressure_warning}."
        )
        warning_str = "COLLECTIVE_PRESSURE_HIGH" if pressure_warning else ""
        s = complete_stage(s, "collective_impact",
                          source="ORCA Anti-Congestion Intelligence (prototype)",
                          summary=summary, confidence=0.8, warning=warning_str)
    except Exception as exc:
        s = complete_stage(s, "collective_impact", summary=f"Error: {exc}", error=True)

    return s.model_dump()
