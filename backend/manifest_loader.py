"""
manifest_loader.py — Lightweight manifest reader for ORCA backend modules.

Import this in marine_agent.py, ocean_agent.py, or any backend service
that needs to discover ingested ISRO OCM-3 NetCDF files without re-scanning.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Optional


DEFAULT_OUTPUT_DIR = "./data/bhoonidhi"


def get_latest_manifest(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Optional[dict]:
    """
    Load the ingest manifest from output_dir/manifest.json.

    Returns the full manifest dict if found and parseable, or None otherwise.
    The returned dict has the shape::

        {
            "generated_at": str,
            "total_files": int,
            "total_size_bytes": int,
            "date_range": {"start": str, "end": str},
            "files": [
                {
                    "filename": str,
                    "target_path": str,
                    "date": str,
                    "size_bytes": int,
                    "sha256": str,
                    "satellite": str,
                    "sensor": str,
                    "product_type": str,
                    "variables_found": list[str],
                    "missing_expected_vars": list[str],
                    "lat_range": list[float] | None,
                    "lon_range": list[float] | None,
                    "status": str,
                    "ingested_at": str
                },
                ...
            ]
        }
    """
    manifest_path = Path(output_dir) / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_files_for_date(date: str, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> list[dict]:
    """
    Return manifest file entries for a specific date string (YYYY-MM-DD).
    Only returns entries with status 'ok' or 'partial'.
    """
    manifest = get_latest_manifest(output_dir)
    if not manifest:
        return []
    return [
        f for f in manifest.get("files", [])
        if f.get("date") == date and f.get("status") in ("ok", "partial")
    ]


def get_all_nc_paths(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """
    Return a sorted list of Path objects for all successfully ingested .nc files.
    Only includes files with status 'ok' or 'partial' that exist on disk.
    """
    manifest = get_latest_manifest(output_dir)
    if not manifest:
        return []
    paths: list[Path] = []
    for entry in manifest.get("files", []):
        if entry.get("status") in ("ok", "partial"):
            p = Path(entry["target_path"])
            if p.exists():
                paths.append(p)
    return sorted(paths)


def get_date_range(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Optional[dict]:
    """
    Return the date_range dict {"start": str, "end": str} from the manifest,
    or None if no manifest exists.
    """
    manifest = get_latest_manifest(output_dir)
    if not manifest:
        return None
    return manifest.get("date_range")


def manifest_is_stale(output_dir: str | Path = DEFAULT_OUTPUT_DIR, max_age_hours: int = 24) -> bool:
    """
    Return True if the manifest has not been updated in more than max_age_hours.
    Useful for triggering a re-ingest warning in the backend.
    """
    manifest = get_latest_manifest(output_dir)
    if not manifest:
        return True
    generated_at = manifest.get("generated_at")
    if not generated_at:
        return True
    try:
        generated_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        from datetime import timezone
        now = datetime.now(timezone.utc)
        age_hours = (now - generated_dt).total_seconds() / 3600
        return age_hours > max_age_hours
    except Exception:
        return True
