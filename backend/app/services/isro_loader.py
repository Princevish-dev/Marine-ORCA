from __future__ import annotations
import os
import csv
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone


DATA_DIR = Path(os.environ.get("ISRO_DATA_DIR", "data/isro"))


def _parse_float(val: str) -> Optional[float]:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def load_sst_grid(filepath: Optional[str] = None) -> list[dict]:
    Fpath = Path(filepath) if filepath else DATA_DIR / "sst_grid.csv"
    if not Fpath.exists():
        return []
    Rows = []
    with open(Fpath, "r", encoding="utf-8") as F:
        Reader = csv.DictReader(F)
        for Row in Reader:
            Lat = _parse_float(Row.get("latitude", ""))
            Lon = _parse_float(Row.get("longitude", ""))
            Sst = _parse_float(Row.get("sst", Row.get("sst_celsius", "")))
            if Lat is not None and Lon is not None and Sst is not None:
                Rows.append({"latitude": Lat, "longitude": Lon, "sst_celsius": Sst})
    return Rows


def load_chlorophyll_grid(filepath: Optional[str] = None) -> list[dict]:
    Fpath = Path(filepath) if filepath else DATA_DIR / "chlorophyll_grid.csv"
    if not Fpath.exists():
        return []
    Rows = []
    with open(Fpath, "r", encoding="utf-8") as F:
        Reader = csv.DictReader(F)
        for Row in Reader:
            Lat = _parse_float(Row.get("latitude", ""))
            Lon = _parse_float(Row.get("longitude", ""))
            Chl = _parse_float(Row.get("chlorophyll", Row.get("chlorophyll_mgm3", "")))
            if Lat is not None and Lon is not None and Chl is not None:
                Rows.append({"latitude": Lat, "longitude": Lon, "chlorophyll_mgm3": Chl})
    return Rows


def find_nearest_observation(grid: list[dict], lat: float, lon: float) -> Optional[dict]:
    if not grid:
        return None
    Best = None
    Bestdist = float("inf")
    for Point in grid:
        Dist = (Point["latitude"] - lat) ** 2 + (Point["longitude"] - lon) ** 2
        if Dist < Bestdist:
            Bestdist = Dist
            Best = Point
    return Best


def get_isro_ocean_data(lat: float, lon: float) -> dict:
    Sstgrid = load_sst_grid()
    Chlgrid = load_chlorophyll_grid()

    Nearest_sst = find_nearest_observation(Sstgrid, lat, lon)
    Nearest_chl = find_nearest_observation(Chlgrid, lat, lon)

    Result = {
        "source": "ISRO EO Dataset (Downloaded)",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "latitude": lat,
        "longitude": lon,
        "sst_celsius": Nearest_sst["sst_celsius"] if Nearest_sst else None,
        "chlorophyll_mgm3": Nearest_chl["chlorophyll_mgm3"] if Nearest_chl else None,
        "data_type": "EO",
        "is_demo": len(Sstgrid) == 0 and len(Chlgrid) == 0,
    }
    return Result


def load_pfz_advisories(filepath: Optional[str] = None) -> list[dict]:
    Fpath = Path(filepath) if filepath else DATA_DIR / "pfz_advisories.json"
    if not Fpath.exists():
        return []
    with open(Fpath, "r", encoding="utf-8") as F:
        Data = json.load(F)
    if isinstance(Data, list):
        return Data
    return Data.get("advisories", [])
