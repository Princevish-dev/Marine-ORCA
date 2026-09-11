"""
OCM3Ingestor — Scan, validate, organize, and catalog ISRO OCM-3 NetCDF files
for the ORCA Local-First marine monitoring backend.

Drop .nc files into ./incoming/ and run this script. It will:
  - Walk incoming/ recursively
  - Open each file with xarray to validate
  - Extract metadata from global attributes
  - Move to canonical structure: data/bhoonidhi/ocm3/YYYY/MM/DD/
  - Update manifest.json for marine_agent.py consumption
  - Quarantine corrupt or unreadable files
"""

from __future__ import annotations

import os
import sys
import json
import shutil
import hashlib
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import xarray as xr


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# ─────────────────────────────────────────────────────────────────────────────
# Shared source of truth for variable aliases — also imported by marine_agent.py
# ─────────────────────────────────────────────────────────────────────────────
EXPECTED_VARIABLES: dict[str, list[str]] = {
    "chlorophyll": ["chlor_a", "chlorophyll", "CHL", "chl_a", "Chlorophyll_a", "CHLA"],
    "sst": ["sst", "SST", "sea_surface_temperature", "SkinSST", "tskin"],
    "wind_speed": ["wind_speed", "WIND_SPEED", "wind", "WSPD", "ws", "wind_spd"],
    "wave_height": ["wave_height", "WAVE_HEIGHT", "significant_wave_height", "SWH", "swh"],
}

REQUIRED_VARIABLES = {"chlorophyll"}

LAT_ALIASES = ["latitude", "lat", "LAT", "Latitude", "LATITUDE"]
LON_ALIASES = ["longitude", "lon", "LON", "Longitude", "LONGITUDE"]


class OCM3Ingestor:
    """Scans incoming NetCDF files, validates, organizes, and catalogs them."""

    MANIFEST_FILE = "manifest.json"
    FAILED_FILE = "failed_ingest.json"
    LOG_FILE = "ingest.log"

    def __init__(
        self,
        incoming_dir: str | Path,
        output_dir: str | Path,
        quarantine_dir: str | Path,
        dry_run: bool = False,
        keep_source: bool = False,
        rebuild_manifest: bool = False,
    ) -> None:
        """Initialise ingestor with directory paths and runtime flags."""
        self.incoming_dir = Path(incoming_dir)
        self.output_dir = Path(output_dir)
        self.ocm3_dir = self.output_dir / "ocm3"
        self.quarantine_dir = Path(quarantine_dir)
        self.dry_run = dry_run
        self.keep_source = keep_source
        self.rebuild_manifest = rebuild_manifest

        self.manifest_entries: list[dict] = []
        self.failed_entries: list[dict] = []

        for d in [self.incoming_dir, self.output_dir, self.quarantine_dir, self.ocm3_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._setup_logging()
        self._load_existing_manifest()

    def _setup_logging(self) -> None:
        """Configure timestamped file and console logging."""
        log_path = self.output_dir / self.LOG_FILE
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        self.logger = logging.getLogger("ocm3_ingest")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _load_existing_manifest(self) -> None:
        """Load previously written manifest entries to support incremental runs."""
        if self.rebuild_manifest:
            self.logger.info("--rebuild-manifest set: starting fresh manifest")
            return
        manifest_path = self.output_dir / self.MANIFEST_FILE
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.manifest_entries = data.get("files", [])
                self.logger.info(
                    "Loaded existing manifest with %d entries", len(self.manifest_entries)
                )
            except Exception as exc:
                self.logger.warning("Could not load existing manifest: %s", exc)

    def scan_incoming(self) -> list[Path]:
        """Recursively walk incoming_dir and return all .nc / .nc4 file paths."""
        found: list[Path] = []
        for root, _, files in os.walk(self.incoming_dir):
            for fname in files:
                if fname.lower().endswith((".nc", ".nc4")):
                    found.append(Path(root) / fname)
        self.logger.info("Found %d NetCDF file(s) in %s", len(found), self.incoming_dir)
        return found

    def extract_metadata(self, nc_path: Path) -> dict:
        """
        Open a NetCDF file with xarray and extract global attributes,
        date, lat/lon ranges, variable list, and units.
        Raises an exception if the file cannot be opened.
        """
        ds = xr.open_dataset(nc_path, engine="netcdf4")
        attrs = ds.attrs

        raw_date = (
            attrs.get("DateOfPass")
            or attrs.get("Scene_Start_Time")
            or attrs.get("time_coverage_start")
        )
        obs_date = self._parse_date(raw_date, nc_path)

        lat_range = self._extract_coord_range(ds, LAT_ALIASES)
        lon_range = self._extract_coord_range(ds, LON_ALIASES)

        variables_info: list[dict] = []
        for var_name in ds.data_vars:
            var = ds[var_name]
            variables_info.append({
                "name": var_name,
                "units": var.attrs.get("units", ""),
                "shape": list(var.shape),
            })

        meta = {
            "satellite": attrs.get("Satellite", attrs.get("satellite", "EOS-06")),
            "sensor": attrs.get("Sensor", attrs.get("sensor", "OCM-3")),
            "product_type": attrs.get("Product_Type", attrs.get("product_type", "GEOPHYSICAL")),
            "processing_level": attrs.get("Processing_level", attrs.get("processing_level", "L2C")),
            "date": obs_date,
            "scene_start": str(attrs.get("Scene_Start_Time", "")),
            "scene_end": str(attrs.get("Scene_End_Time", "")),
            "upper_left": str(attrs.get("UpperLeft_LatLon", "")),
            "lower_right": str(attrs.get("LowerRight_LatLon", "")),
            "lat_range": lat_range,
            "lon_range": lon_range,
            "all_variables": variables_info,
            "variable_names": [v["name"] for v in variables_info],
        }

        ds.close()
        return meta

    def _parse_date(self, raw_date: Optional[str], nc_path: Path) -> str:
        """
        Parse an observation date string from global attributes.
        Falls back to the file's modification time if attribute is absent or unparseable.
        """
        if raw_date:
            for fmt in ("%Y-%m-%d", "%Y%m%d", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(str(raw_date).strip()[:19], fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        mtime = nc_path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")

    def _extract_coord_range(self, ds: xr.Dataset, aliases: list[str]) -> Optional[list[float]]:
        """Extract [min, max] range for a coordinate using a list of possible aliases."""
        for alias in aliases:
            if alias in ds.coords or alias in ds.data_vars:
                arr = ds[alias].values.flatten()
                arr = arr[~np.isnan(arr)]
                if arr.size > 0:
                    return [float(arr.min()), float(arr.max())]
        return None

    def compute_sha256(self, filepath: Path) -> str:
        """Compute a SHA-256 hash of a file using streaming 64KB chunks."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def resolve_target_path(self, nc_path: Path, obs_date: str) -> Path:
        """
        Build the canonical target path under ocm3/YYYY/MM/DD/filename
        using the observation date extracted from metadata.
        """
        year, month, day = obs_date.split("-")
        return self.ocm3_dir / year / month / day / nc_path.name

    def validate_variables(self, variable_names: list[str]) -> tuple[list[str], list[str]]:
        """
        Fuzzy-match variable names against EXPECTED_VARIABLES aliases.
        Returns (found_canonical_names, missing_canonical_names).
        """
        lower_names = {v.lower() for v in variable_names}
        found: list[str] = []
        missing: list[str] = []

        for canonical, aliases in EXPECTED_VARIABLES.items():
            matched = any(alias.lower() in lower_names for alias in aliases)
            if matched:
                found.append(canonical)
            else:
                missing.append(canonical)

        return found, missing

    def move_to_target(self, src: Path, dest: Path) -> None:
        """
        Move or copy a file from src to dest, creating parent directories as needed.
        Controlled by self.keep_source: if True, copies instead of moving.
        """
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.keep_source:
            shutil.copy2(src, dest)
        else:
            shutil.move(str(src), str(dest))

    def quarantine_file(self, nc_path: Path, reason: str) -> None:
        """
        Move a corrupt or unreadable file to the quarantine directory
        and write a sidecar .error.txt file with the failure reason.
        """
        if self.dry_run:
            self.logger.warning("DRY-RUN quarantine: %s | reason: %s", nc_path.name, reason[:80])
            return

        dest = self.quarantine_dir / nc_path.name
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(nc_path), str(dest))
        except Exception:
            shutil.copy2(nc_path, dest)

        error_file = dest.with_suffix(dest.suffix + ".error.txt")
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"Source: {nc_path}\n")
            f.write(f"Quarantined at: {datetime.now(timezone.utc).isoformat()}\n\n")
            f.write(reason)

        self.logger.warning("Quarantined: %s", nc_path.name)

    def update_manifest(self, entry: dict) -> None:
        """
        Insert or replace a manifest entry by filename and persist to manifest.json.
        """
        existing_idx = next(
            (i for i, e in enumerate(self.manifest_entries) if e.get("filename") == entry["filename"]),
            None,
        )
        if existing_idx is not None:
            self.manifest_entries[existing_idx] = entry
        else:
            self.manifest_entries.append(entry)

        self._save_manifest()

    def _save_manifest(self) -> None:
        """Write the full manifest.json with summary statistics to disk."""
        sizes = [e.get("size_bytes", 0) or 0 for e in self.manifest_entries]
        dates = sorted(
            [e["date"] for e in self.manifest_entries if e.get("date") and e["date"] != "unknown"],
            key=str,
        )

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_files": len(self.manifest_entries),
            "total_size_bytes": sum(sizes),
            "date_range": {
                "start": dates[0] if dates else None,
                "end": dates[-1] if dates else None,
            },
            "files": self.manifest_entries,
        }

        out = self.output_dir / self.MANIFEST_FILE
        with open(out, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

    def _save_failed(self) -> None:
        """Persist failed_ingest.json with all entries that errored."""
        if not self.failed_entries:
            return
        out = self.output_dir / self.FAILED_FILE
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.failed_entries, f, indent=2, default=str)

    def _already_ingested(self, sha256: str) -> bool:
        """Return True if a file with the same SHA-256 hash is already in the manifest."""
        return any(e.get("sha256") == sha256 for e in self.manifest_entries)

    def run(self) -> dict[str, int]:
        """
        Execute the full ingest pipeline:
        scan -> validate -> hash -> move -> catalog.
        Returns a summary dict of counts.
        """
        self.logger.info("=" * 70)
        self.logger.info("OCM3 Ingestor Starting")
        self.logger.info("  incoming  : %s", self.incoming_dir.resolve())
        self.logger.info("  output    : %s", self.output_dir.resolve())
        self.logger.info("  quarantine: %s", self.quarantine_dir.resolve())
        self.logger.info("  dry_run   : %s", self.dry_run)
        self.logger.info("  keep_source: %s", self.keep_source)
        self.logger.info("=" * 70)

        stats = {"scanned": 0, "ingested": 0, "skipped": 0, "quarantined": 0, "failed": 0}
        nc_files = self.scan_incoming()
        stats["scanned"] = len(nc_files)

        for nc_path in nc_files:
            self.logger.info("Processing: %s", nc_path.name)

            try:
                sha256 = self.compute_sha256(nc_path)
            except Exception as exc:
                self.logger.error("Cannot hash %s: %s", nc_path.name, exc)
                stats["failed"] += 1
                continue

            if not self.rebuild_manifest and self._already_ingested(sha256):
                self.logger.info("SKIP (already ingested by hash): %s", nc_path.name)
                stats["skipped"] += 1
                continue

            try:
                meta = self.extract_metadata(nc_path)
            except Exception as exc:
                reason = traceback.format_exc()
                self.logger.error("Cannot open NetCDF %s: %s", nc_path.name, exc)
                self.quarantine_file(nc_path, reason)
                self.failed_entries.append({
                    "filename": nc_path.name,
                    "source_path": str(nc_path),
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                stats["quarantined"] += 1
                continue

            obs_date = meta["date"]
            target_path = self.resolve_target_path(nc_path, obs_date)

            variables_found, missing_vars = self.validate_variables(meta["variable_names"])

            required_missing = [v for v in missing_vars if v in REQUIRED_VARIABLES]
            if required_missing:
                status = "partial"
                self.logger.warning(
                    "%s: missing required variable(s): %s — marking partial",
                    nc_path.name, required_missing,
                )
            else:
                status = "ok"

            size_bytes = nc_path.stat().st_size

            if not self.dry_run:
                try:
                    self.move_to_target(nc_path, target_path)
                except Exception as exc:
                    self.logger.error("Move failed for %s: %s", nc_path.name, exc)
                    stats["failed"] += 1
                    self.failed_entries.append({
                        "filename": nc_path.name,
                        "error": str(exc),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    continue
            else:
                self.logger.info(
                    "DRY-RUN: would move %s -> %s [status=%s]",
                    nc_path.name, target_path, status,
                )

            entry = {
                "filename": nc_path.name,
                "source_path": str(nc_path),
                "target_path": str(target_path),
                "date": obs_date,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "satellite": meta["satellite"],
                "sensor": meta["sensor"],
                "product_type": meta["product_type"],
                "processing_level": meta["processing_level"],
                "variables_found": variables_found,
                "missing_expected_vars": missing_vars,
                "lat_range": meta["lat_range"],
                "lon_range": meta["lon_range"],
                "status": status,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

            self.update_manifest(entry)
            stats["ingested"] += 1
            self.logger.info("Ingested: %s -> %s [status=%s]", nc_path.name, target_path, status)

        self._save_failed()

        self.logger.info("=" * 70)
        self.logger.info("Ingest complete:")
        self.logger.info("  Scanned    : %d", stats["scanned"])
        self.logger.info("  Ingested   : %d", stats["ingested"])
        self.logger.info("  Skipped    : %d", stats["skipped"])
        self.logger.info("  Quarantined: %d", stats["quarantined"])
        self.logger.info("  Failed     : %d", stats["failed"])
        self.logger.info("=" * 70)

        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Standalone helper for marine_agent.py
# ─────────────────────────────────────────────────────────────────────────────

def get_latest_manifest(output_dir: str | Path = "./data/bhoonidhi") -> Optional[dict]:
    """
    Load and return the manifest.json from the given output directory.
    Returns None if the manifest does not exist or cannot be parsed.
    Intended for direct import by marine_agent.py.
    """
    manifest_path = Path(output_dir) / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the OCM3 ingestor."""
    parser = argparse.ArgumentParser(
        prog="ingest_ocm3",
        description="Ingest manually downloaded ISRO OCM-3 NetCDF files into ORCA",
    )
    parser.add_argument("--incoming", default="./incoming", help="Folder where you drop .nc files (default: ./incoming)")
    parser.add_argument("--output", default="./data/bhoonidhi", help="Output folder (default: ./data/bhoonidhi)")
    parser.add_argument("--quarantine", default="./quarantine", help="Quarantine folder for corrupt files (default: ./quarantine)")
    parser.add_argument("--dry-run", action="store_true", help="Scan and validate without moving any files")
    parser.add_argument("--keep-source", action="store_true", help="Copy files instead of moving them")
    parser.add_argument("--rebuild-manifest", action="store_true", help="Ignore existing manifest and re-ingest all files")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingestor = OCM3Ingestor(
        incoming_dir=args.incoming,
        output_dir=args.output,
        quarantine_dir=args.quarantine,
        dry_run=args.dry_run,
        keep_source=args.keep_source,
        rebuild_manifest=args.rebuild_manifest,
    )
    result = ingestor.run()
    sys.exit(0 if result["failed"] == 0 and result["quarantined"] == 0 else 1)
