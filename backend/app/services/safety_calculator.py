from __future__ import annotations
from app.models import (
    WeatherObservation, MarineObservation, WarningEvent,
    BoundaryStatus, PFZCandidate,
    SafetyAssessment, SafetyFactor,
)

WIND_MODERATE = 25.0
WIND_HIGH = 40.0
WIND_EXTREME = 60.0

WAVE_MODERATE = 1.5
WAVE_HIGH = 2.5
WAVE_EXTREME = 4.0

PFZ_BONUS_MAX = 10.0


def calculate_safety(
    weather: WeatherObservation | None,
    marine: MarineObservation | None,
    warnings: list[WarningEvent],
    boundary: BoundaryStatus | None,
    pfz_candidates: list[PFZCandidate],
) -> SafetyAssessment:
    score = 100.0
    factors: list[SafetyFactor] = []
    critical_override = False

    wind_penalty = 0.0
    wind_status = "GOOD"
    wind_label = "Calm"
    if weather:
        ws = weather.wind_speed_kmh
        if ws >= WIND_EXTREME:
            wind_penalty = 35.0
            wind_status = "CRITICAL"
            wind_label = f"Extreme ({ws:.0f} km/h)"
        elif ws >= WIND_HIGH:
            wind_penalty = 20.0
            wind_status = "WARNING"
            wind_label = f"High ({ws:.0f} km/h)"
        elif ws >= WIND_MODERATE:
            wind_penalty = 10.0
            wind_status = "MODERATE"
            wind_label = f"Moderate ({ws:.0f} km/h)"
        else:
            wind_label = f"Light ({ws:.0f} km/h)"
    factors.append(SafetyFactor(name="Wind", value=wind_label, penalty=wind_penalty, status=wind_status))
    score -= wind_penalty

    wave_penalty = 0.0
    wave_status = "GOOD"
    wave_label = "Calm"
    if marine:
        wh = marine.wave_height_m
        if wh >= WAVE_EXTREME:
            wave_penalty = 40.0
            wave_status = "CRITICAL"
            wave_label = f"Extreme ({wh:.1f} m)"
        elif wh >= WAVE_HIGH:
            wave_penalty = 25.0
            wave_status = "WARNING"
            wave_label = f"High ({wh:.1f} m)"
        elif wh >= WAVE_MODERATE:
            wave_penalty = 12.0
            wave_status = "MODERATE"
            wave_label = f"Moderate ({wh:.1f} m)"
        else:
            wave_label = f"Low ({wh:.1f} m)"
    factors.append(SafetyFactor(name="Waves", value=wave_label, penalty=wave_penalty, status=wave_status))
    score -= wave_penalty

    warn_penalty = 0.0
    warn_status = "GOOD"
    warn_label = "None"
    active_warnings = [w for w in warnings if w.is_active]
    if active_warnings:
        max_sev = max(active_warnings, key=lambda w: {"INFO": 1, "YELLOW": 2, "ORANGE": 3, "RED": 4}[w.severity])
        if max_sev.severity == "RED":
            warn_penalty = 60.0
            warn_status = "CRITICAL"
            warn_label = f"RED — {max_sev.title}"
            critical_override = True
        elif max_sev.severity == "ORANGE":
            warn_penalty = 35.0
            warn_status = "WARNING"
            warn_label = f"ORANGE — {max_sev.title}"
        elif max_sev.severity == "YELLOW":
            warn_penalty = 15.0
            warn_status = "CAUTION"
            warn_label = f"YELLOW — {max_sev.title}"
        elif max_sev.severity == "INFO":
            warn_penalty = 5.0
            warn_status = "MODERATE"
            warn_label = f"INFO — {max_sev.title}"
    factors.append(SafetyFactor(name="Warnings", value=warn_label, penalty=warn_penalty, status=warn_status))
    score -= warn_penalty

    boundary_penalty = 0.0
    boundary_status = "GOOD"
    boundary_label = "Clear"
    if boundary:
        if boundary.inside:
            boundary_penalty = 50.0
            boundary_status = "CRITICAL"
            boundary_label = "INSIDE restricted zone"
        elif boundary.status == "RED":
            boundary_penalty = 30.0
            boundary_status = "CRITICAL"
            boundary_label = f"Critical ({boundary.distance_km:.1f} km)"
        elif boundary.status == "ORANGE":
            boundary_penalty = 15.0
            boundary_status = "WARNING"
            boundary_label = f"Close ({boundary.distance_km:.1f} km)"
        elif boundary.status == "YELLOW":
            boundary_penalty = 8.0
            boundary_status = "CAUTION"
            boundary_label = f"Approaching ({boundary.distance_km:.1f} km)"
    factors.append(SafetyFactor(name="Boundary", value=boundary_label, penalty=boundary_penalty, status=boundary_status))
    score -= boundary_penalty

    pfz_bonus = 0.0
    pfz_status = "GOOD"
    pfz_label = "No data"
    if pfz_candidates and not critical_override:
        best = max(pfz_candidates, key=lambda p: p.score)
        if best.score >= 70:
            pfz_bonus = 10.0
            pfz_status = "GOOD"
            pfz_label = f"Favorable (score {best.score:.0f})"
        elif best.score >= 50:
            pfz_bonus = 5.0
            pfz_status = "MODERATE"
            pfz_label = f"Moderate (score {best.score:.0f})"
        else:
            pfz_label = f"Low (score {best.score:.0f})"
    elif not pfz_candidates:
        pfz_label = "Not assessed"
    factors.append(SafetyFactor(name="PFZ", value=pfz_label, penalty=-pfz_bonus, status=pfz_status))
    score += pfz_bonus

    score = max(0.0, min(100.0, score))
    final_score = int(round(score))

    if critical_override:
        final_score = min(final_score, 30)

    label, color = _score_to_label(final_score, critical_override)
    explanation = _build_explanation(factors, critical_override, final_score)

    return SafetyAssessment(
        score=final_score,
        label=label,
        color=color,
        factors=factors,
        explanation=explanation,
        critical_override=critical_override,
    )


def _score_to_label(score: int, override: bool):
    if override or score < 30:
        return "CRITICAL", "#ef4444"
    elif score < 50:
        return "WARNING", "#f97316"
    elif score < 65:
        return "CAUTION", "#eab308"
    elif score < 80:
        return "GOOD", "#22c55e"
    return "EXCELLENT", "#10b981"


def _build_explanation(factors: list[SafetyFactor], override: bool, score: int) -> str:
    lines = []
    penalties = [(f.name, f.penalty) for f in factors if f.penalty > 0]
    penalties.sort(key=lambda x: x[1], reverse=True)
    if penalties:
        top = penalties[0]
        lines.append(f"{top[0]} conditions are the largest contributor to risk.")
    if override:
        lines.append("A severe official warning has triggered a CRITICAL override regardless of other factors.")
    if score >= 80:
        lines.append("Overall conditions appear favorable for marine activities.")
    elif score >= 65:
        lines.append("Conditions are acceptable but require situational awareness.")
    elif score >= 50:
        lines.append("Exercise caution and monitor official forecasts closely.")
    else:
        lines.append("Avoid marine activity unless essential. Verify official warnings.")
    return " ".join(lines)


def is_high_wave(marine: MarineObservation) -> bool:
    return marine.wave_height_m >= WAVE_HIGH


def is_severe_warning(warnings: list[WarningEvent]) -> bool:
    return any(w.severity in ("RED", "ORANGE") and w.is_active for w in warnings)


def is_cyclone(warnings: list[WarningEvent]) -> bool:
    return any("cyclone" in w.title.lower() and w.is_active for w in warnings)


def is_extreme_weather(weather: WeatherObservation) -> bool:
    return weather.wind_speed_kmh >= WIND_EXTREME


def is_boundary_warning(boundary: BoundaryStatus) -> bool:
    return boundary.status in ("ORANGE", "RED") or boundary.inside
