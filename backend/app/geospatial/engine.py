from __future__ import annotations
import math
from shapely.geometry import Point, Polygon, LineString, mapping
from shapely.ops import nearest_points
from app.models import BoundaryStatus, RoutePoint, RouteResult

_IMBL_DEMO = Polygon([
    (83.0, 8.0), (85.0, 8.0), (87.0, 10.0),
    (87.5, 13.0), (86.5, 16.0), (85.0, 18.0),
    (83.0, 18.0), (82.0, 14.0), (82.5, 10.0), (83.0, 8.0)
])

_EEZ_DEMO = Polygon([
    (72.0, 8.0), (85.0, 8.0), (88.0, 15.0),
    (86.0, 22.0), (80.0, 23.0), (72.0, 20.0),
    (70.0, 14.0), (72.0, 8.0)
])

MARITIME_ZONES = {
    "imbl-demo": {
        "id": "imbl-demo",
        "name": "IMBL Demonstration Zone",
        "type": "IMBL",
        "polygon": _IMBL_DEMO,
        "description": "Demonstration maritime boundary — not an official legal threshold.",
    },
}

BOUNDARY_THRESHOLDS = {
    "RED": 10,
    "ORANGE": 30,
    "YELLOW": 60,
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def check_boundary_status(lat: float, lon: float) -> BoundaryStatus:
    pt = Point(lon, lat)

    nearest_dist_km = float("inf")
    nearest_name = "Unknown"
    nearest_id = "none"
    inside = False

    for zone_id, zone in MARITIME_ZONES.items():
        poly: Polygon = zone["polygon"]
        if poly.contains(pt):
            inside = True
            nearest_dist_km = 0.0
            nearest_name = zone["name"]
            nearest_id = zone_id
            break

        nearest_pt = nearest_points(poly.boundary, pt)[0]
        dist_km = haversine_km(nearest_pt.y, nearest_pt.x, lat, lon)
        if dist_km < nearest_dist_km:
            nearest_dist_km = dist_km
            nearest_name = zone["name"]
            nearest_id = zone_id

    if inside or nearest_dist_km <= BOUNDARY_THRESHOLDS["RED"]:
        status = "RED"
    elif nearest_dist_km <= BOUNDARY_THRESHOLDS["ORANGE"]:
        status = "ORANGE"
    elif nearest_dist_km <= BOUNDARY_THRESHOLDS["YELLOW"]:
        status = "YELLOW"
    else:
        status = "NORMAL"

    return BoundaryStatus(
        nearest_restriction_id=nearest_id,
        nearest_restriction_name=nearest_name,
        distance_km=round(nearest_dist_km, 1),
        status=status,
        inside=inside,
    )


def get_geofence_geojson() -> dict:
    features = []
    for zone in MARITIME_ZONES.values():
        poly: Polygon = zone["polygon"]
        features.append({
            "type": "Feature",
            "properties": {
                "id": zone["id"],
                "name": zone["name"],
                "type": zone["type"],
                "description": zone["description"],
            },
            "geometry": mapping(poly),
        })
    return {"type": "FeatureCollection", "features": features}


def calculate_pfz_score(sst: float, chlorophyll: float, gradient: float = 0.5) -> float:
    chl_norm = min(1.0, max(0.0, (chlorophyll - 0.1) / 1.9))
    sst_dev = abs(sst - 27.5)
    sst_suit = max(0.0, 1.0 - sst_dev / 4.0)
    raw = 0.40 * chl_norm + 0.40 * sst_suit + 0.20 * gradient
    return round(raw * 100, 1)


def generate_pfz_candidates(lat: float, lon: float, ocean_sst: float | None, ocean_chl: float | None) -> list[dict]:
    from app.services.demo_fixtures import DEMO_PFZ_CANDIDATES

    if ocean_sst is None or ocean_chl is None:
        return DEMO_PFZ_CANDIDATES

    candidates = []
    offsets = [
        (0.20, 0.35, "Southeast"),
        (-0.12, 0.50, "East"),
        (0.35, 0.15, "South"),
    ]

    for i, (dlat, dlon, direction) in enumerate(offsets):
        c_lat = lat + dlat
        c_lon = lon + dlon
        dist = haversine_km(lat, lon, c_lat, c_lon)
        c_sst = ocean_sst + (i - 1) * 0.3
        c_chl = ocean_chl * (1.0 + (i - 1) * 0.15)
        score = calculate_pfz_score(c_sst, c_chl)
        suitability = "HIGH" if score >= 70 else "MODERATE" if score >= 50 else "LOW"
        chl_label = "HIGH" if c_chl > 1.0 else "MODERATE" if c_chl > 0.5 else "LOW"
        candidates.append({
            "id": f"pfz-{i+1}",
            "latitude": round(c_lat, 4),
            "longitude": round(c_lon, 4),
            "score": score,
            "distance_km": round(dist, 1),
            "sst_celsius": round(c_sst, 1),
            "chlorophyll_level": chl_label,
            "explanation": (
                f"SST {c_sst:.1f}°C and {chl_label.lower()} chlorophyll ({c_chl:.2f} mg/m³) "
                f"suggest {suitability.lower()} biological productivity. "
                f"Potentially suitable fishing zone — {direction} of current location."
            ),
            "suitability": suitability,
        })

    return sorted(candidates, key=lambda x: x["score"], reverse=True)
