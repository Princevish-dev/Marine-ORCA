from __future__ import annotations
import os
import csv
import json
import glob
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

try:
    import xarray as xr
    XARRAY_AVAILABLE = True
except ImportError:
    XARRAY_AVAILABLE = False


# Primary data dir: data/isro for CSV files
DATA_DIR = Path(os.environ.get("ISRO_DATA_DIR", "data/isro"))

# E06 (EOS-06 / Oceansat-3) NetCDF folders — user places them here manually
# Expected structure: data/isro/E06_*/  (any folder starting with E06)
E06_DATA_DIR = DATA_DIR


def _parse_float(val: str) -> Optional[float]:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


# ─────────────────────────────────────────────
# NetCDF (.nc) Loader — reads E06_* folders
# ─────────────────────────────────────────────

def find_e06_netcdf_files() -> list[Path]:
    """Scan data/isro/ for all .nc files inside folders starting with E06."""
    pattern = str(E06_DATA_DIR / "E06*" / "*.nc")
    files = [Path(f) for f in glob.glob(pattern, recursive=False)]
    # Also check flat placement: data/isro/E06*.nc
    flat_pattern = str(E06_DATA_DIR / "E06*.nc")
    files += [Path(f) for f in glob.glob(flat_pattern)]
    return list(set(files))


def extract_from_netcdf(nc_path: Path, lat: float, lon: float) -> dict:
    """
    Open an E06 OCM-3 NetCDF file and extract the nearest pixel values
    for SST, chlorophyll, wave_height, and wind_speed to the given lat/lon.
    Returns a dict with extracted values or None for missing variables.
    """
    if not XARRAY_AVAILABLE:
        return {}

    result = {
        "sst_celsius": None,
        "chlorophyll_mgm3": None,
        "wave_height_m": None,
        "wind_speed_kmh": None,
        "source_file": nc_path.name,
    }

    try:
        ds = xr.open_dataset(nc_path, engine="netcdf4")

        # Common variable name mappings from ISRO OCM-3 products
        sst_vars = ["sst", "sea_surface_temperature", "SST", "sst_celsius"]
        chl_vars = ["chlor_a", "chlorophyll", "CHL", "chl_a", "Chlorophyll_a"]
        wave_vars = ["wave_height", "SWH", "significant_wave_height"]
        wind_vars = ["wind_speed", "wind_spd", "WSPD", "ws"]
        lat_vars = ["latitude", "lat", "LAT", "Latitude"]
        lon_vars = ["longitude", "lon", "LON", "Longitude"]

        def find_var(candidates):
            for name in candidates:
                if name in ds.data_vars or name in ds.coords:
                    return name
            return None

        lat_var = find_var(lat_vars)
        lon_var = find_var(lon_vars)

        if lat_var and lon_var:
            lats = ds[lat_var].values
            lons = ds[lon_var].values

            # Find index of nearest pixel
            import numpy as np
            dist = (lats - lat) ** 2 + (lons - lon) ** 2 if lats.ndim == 1 else None

            def get_nearest_val(var_name):
                if var_name not in ds.data_vars:
                    return None
                arr = ds[var_name].values
                if arr.ndim == 1 and dist is not None:
                    idx = int(dist.argmin())
                    val = float(arr[idx])
                    return None if val != val else val  # NaN check
                elif arr.ndim == 2:
                    # 2D grid — find closest row/col
                    lat_idx = int(abs(lats - lat).argmin()) if lats.ndim == 1 else 0
                    lon_idx = int(abs(lons - lon).argmin()) if lons.ndim == 1 else 0
                    val = float(arr[lat_idx][lon_idx])
                    return None if val != val else val
                return None

            sst_var = find_var(sst_vars)
            chl_var = find_var(chl_vars)
            wave_var = find_var(wave_vars)
            wind_var = find_var(wind_vars)

            if sst_var:
                result["sst_celsius"] = get_nearest_val(sst_var)
            if chl_var:
                result["chlorophyll_mgm3"] = get_nearest_val(chl_var)
            if wave_var:
                result["wave_height_m"] = get_nearest_val(wave_var)
            if wind_var:
                ws = get_nearest_val(wind_var)
                # Convert m/s to km/h if needed (ISRO typically provides m/s)
                result["wind_speed_kmh"] = round(ws * 3.6, 2) if ws is not None else None

        ds.close()
    except Exception as exc:
        result["_error"] = str(exc)

    return result


def load_from_e06_folders(lat: float, lon: float) -> Optional[dict]:
    """
    Scan all E06_* NetCDF files and return ocean data for the nearest pixel.
    Returns None if no E06 files are found.
    """
    nc_files = find_e06_netcdf_files()
    if not nc_files:
        return None

    # Try each file and return first successful extraction with at least SST or Chl
    for nc_path in sorted(nc_files):
        data = extract_from_netcdf(nc_path, lat, lon)
        if data.get("sst_celsius") is not None or data.get("chlorophyll_mgm3") is not None:
            data["source"] = f"ISRO EOS-06 OCM-3 | {nc_path.name}"
            data["data_type"] = "EO_NETCDF"
            data["is_demo"] = False
            data["retrieved_at"] = datetime.now(timezone.utc).isoformat()
            return data

    return None


# ─────────────────────────────────────────────
# CSV Loaders (legacy / backup)
# ─────────────────────────────────────────────

def load_sst_grid(filepath: Optional[str] = None) -> list[dict]:
    """Load SST grid from a CSV file (latitude, longitude, sst_celsius columns)."""
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
    """Load chlorophyll grid from a CSV file (latitude, longitude, chlorophyll_mgm3 columns)."""
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
    """Return the nearest grid point to a given lat/lon using Euclidean distance."""
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
    """
    Get ocean data from ISRO EO datasets.
    Priority: E06 NetCDF folders → CSV grids → empty result.
    """
    # Priority 1: E06_* NetCDF folders (manually placed by user)
    nc_data = load_from_e06_folders(lat, lon)
    if nc_data:
        return nc_data

    # Priority 2: CSV grid files (legacy)
    Sstgrid = load_sst_grid()
    Chlgrid = load_chlorophyll_grid()

    Nearest_sst = find_nearest_observation(Sstgrid, lat, lon)
    Nearest_chl = find_nearest_observation(Chlgrid, lat, lon)

    return {
        "source": "ISRO EO Dataset (CSV)",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "latitude": lat,
        "longitude": lon,
        "sst_celsius": Nearest_sst["sst_celsius"] if Nearest_sst else None,
        "chlorophyll_mgm3": Nearest_chl["chlorophyll_mgm3"] if Nearest_chl else None,
        "data_type": "EO",
        "is_demo": len(Sstgrid) == 0 and len(Chlgrid) == 0,
    }


def load_pfz_advisories(filepath: Optional[str] = None) -> list[dict]:
    """Load PFZ advisories from a JSON file."""
    Fpath = Path(filepath) if filepath else DATA_DIR / "pfz_advisories.json"
    if not Fpath.exists():
        return []
    with open(Fpath, "r", encoding="utf-8") as F:
        Data = json.load(F)
    if isinstance(Data, list):
        return Data
    return Data.get("advisories", [])
