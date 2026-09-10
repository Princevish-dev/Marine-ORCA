from __future__ import annotations

from typing import Any


def vision_anomaly_agent(
    sar_coordinate: dict[str, float],
    ais_vessels: list[dict[str, Any]],
    wake_detected: bool,
    match_radius_km: float = 2.0,
) -> dict[str, Any]:
    if not wake_detected:
        return {"detected": False, "alerts": []}

    latitude = sar_coordinate["latitude"]
    longitude = sar_coordinate["longitude"]
    matching_vessel = next(
        (
            vessel for vessel in ais_vessels
            if abs(vessel.get("latitude", 999) - latitude) <= match_radius_km / 111
            and abs(vessel.get("longitude", 999) - longitude) <= match_radius_km / 111
        ),
        None,
    )
    if matching_vessel:
        return {"detected": False, "alerts": [], "ais_match": matching_vessel}

    return {
        "detected": True,
        "alerts": [{
            "tag": "DARK_VESSEL_DETECTED",
            "severity": "HIGH",
            "coordinate": sar_coordinate,
            "source": "Sentinel-1 SAR mock vision model",
            "message": "Physical ship wake detected without a matching AIS signal.",
        }],
    }