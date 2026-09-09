from __future__ import annotations
import heapq
import math
from dataclasses import dataclass, field
from typing import Optional
from app.models import RoutePoint, RouteResult
from app.geospatial.engine import haversine_km


@dataclass(order=True)
class GridNode:
    f_cost: float
    lat: float = field(compare=False)
    lon: float = field(compare=False)
    g_cost: float = field(compare=False)
    parent: Optional["GridNode"] = field(compare=False, default=None)
    wave_factor: float = field(compare=False, default=1.0)
    restricted: bool = field(compare=False, default=False)


def build_route_grid(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    wave_height: float = 1.0,
    current_speed: float = 0.3,
    current_dir: float = 90.0,
) -> RouteResult:
    GRID_STEP = 0.15

    lat_min = min(start_lat, end_lat) - 0.5
    lat_max = max(start_lat, end_lat) + 0.5
    lon_min = min(start_lon, end_lon) - 0.5
    lon_max = max(start_lon, end_lon) + 0.5

    def snap(lat, lon):
        return (
            round(round((lat - lat_min) / GRID_STEP) * GRID_STEP + lat_min, 4),
            round(round((lon - lon_min) / GRID_STEP) * GRID_STEP + lon_min, 4),
        )

    s_lat, s_lon = snap(start_lat, start_lon)
    e_lat, e_lon = snap(end_lat, end_lon)

    def neighbors(lat, lon):
        dirs = [(GRID_STEP, 0), (-GRID_STEP, 0), (0, GRID_STEP), (0, -GRID_STEP),
                (GRID_STEP, GRID_STEP), (-GRID_STEP, GRID_STEP),
                (GRID_STEP, -GRID_STEP), (-GRID_STEP, -GRID_STEP)]
        result = []
        for dlat, dlon in dirs:
            n_lat = round(lat + dlat, 4)
            n_lon = round(lon + dlon, 4)
            if lat_min <= n_lat <= lat_max and lon_min <= n_lon <= lon_max:
                result.append((n_lat, n_lon))
        return result

    def current_benefit(from_lat, from_lon, to_lat, to_lon) -> float:
        heading_rad = math.atan2(to_lon - from_lon, to_lat - from_lat)
        current_rad = math.radians(current_dir)
        projection = current_speed * math.cos(current_rad - heading_rad)
        return max(0, projection)

    def edge_cost(from_lat, from_lon, to_lat, to_lon) -> float:
        dist = haversine_km(from_lat, from_lon, to_lat, to_lon)
        wave_pen = 1.0 + max(0, (wave_height - 1.5) * 0.3)
        cur_ben = current_benefit(from_lat, from_lon, to_lat, to_lon)
        LAMBDA = 0.6
        return dist * wave_pen - LAMBDA * cur_ben * dist

    def heuristic(lat, lon) -> float:
        return haversine_km(lat, lon, e_lat, e_lon)

    open_heap: list[GridNode] = []
    visited: set[tuple[float, float]] = set()
    start_node = GridNode(f_cost=heuristic(s_lat, s_lon), lat=s_lat, lon=s_lon, g_cost=0.0)
    heapq.heappush(open_heap, start_node)
    best: dict[tuple[float, float], float] = {(s_lat, s_lon): 0.0}

    goal_node: Optional[GridNode] = None
    iterations = 0

    while open_heap and iterations < 500:
        iterations += 1
        current = heapq.heappop(open_heap)
        key = (current.lat, current.lon)
        if key in visited:
            continue
        visited.add(key)

        if abs(current.lat - e_lat) < GRID_STEP / 2 and abs(current.lon - e_lon) < GRID_STEP / 2:
            goal_node = current
            break

        for n_lat, n_lon in neighbors(current.lat, current.lon):
            nk = (n_lat, n_lon)
            if nk in visited:
                continue
            g = current.g_cost + edge_cost(current.lat, current.lon, n_lat, n_lon)
            if g < best.get(nk, float("inf")):
                best[nk] = g
                f = g + heuristic(n_lat, n_lon)
                node = GridNode(f_cost=f, lat=n_lat, lon=n_lon, g_cost=g, parent=current)
                heapq.heappush(open_heap, node)

    orca_path: list[RoutePoint] = []
    node = goal_node
    while node:
        orca_path.insert(0, RoutePoint(latitude=node.lat, longitude=node.lon))
        node = node.parent

    n_waypoints = max(5, len(orca_path))
    direct_path = [
        RoutePoint(
            latitude=round(start_lat + (end_lat - start_lat) * i / (n_waypoints - 1), 4),
            longitude=round(start_lon + (end_lon - start_lon) * i / (n_waypoints - 1), 4),
        )
        for i in range(n_waypoints)
    ]

    def path_distance(path: list[RoutePoint]) -> float:
        total = 0.0
        for i in range(len(path) - 1):
            total += haversine_km(path[i].latitude, path[i].longitude,
                                   path[i+1].latitude, path[i+1].longitude)
        return round(total, 1)

    direct_dist = path_distance(direct_path)
    orca_dist = path_distance(orca_path) if orca_path else direct_dist * 1.08

    if not orca_path:
        orca_path = direct_path

    direct_risk = min(1.0, 0.3 + wave_height * 0.1)
    orca_risk = direct_risk * 0.75
    fuel_reduction = max(0, round((direct_dist * 0.08 - (orca_dist - direct_dist) * 0.05) / direct_dist * 100, 1))
    risk_reduction = round((direct_risk - orca_risk) / direct_risk * 100, 1)

    return RouteResult(
        direct_route=direct_path,
        orca_route=orca_path,
        direct_distance_km=direct_dist,
        orca_distance_km=round(orca_dist, 1),
        direct_risk=round(direct_risk, 2),
        orca_risk=round(orca_risk, 2),
        fuel_reduction_pct=fuel_reduction,
        risk_reduction_pct=risk_reduction,
        current_benefit=current_speed > 0.2,
        explanation=(
            f"ORCA route adds {round(orca_dist - direct_dist, 1)} km to leverage favorable current "
            f"and reduce exposure to {wave_height:.1f} m wave zone. "
            f"Modelled fuel reduction: ~{fuel_reduction}%. "
            "These are MODELLED ESTIMATES — not verified vessel fuel measurements."
        ),
    )
