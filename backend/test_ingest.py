"""
Tests for OCM3Ingestor using a synthetic NetCDF fixture.
All NetCDF files are created inline with xarray — no external data required.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from datetime import datetime

import numpy as np
import pytest
import xarray as xr

from ingest_ocm3 import OCM3Ingestor, EXPECTED_VARIABLES, get_latest_manifest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dirs(tmp_path):
    """Set up incoming, output, and quarantine directories."""
    incoming = tmp_path / "incoming"
    output = tmp_path / "data" / "bhoonidhi"
    quarantine = tmp_path / "quarantine"
    for d in [incoming, output, quarantine]:
        d.mkdir(parents=True)
    return {"incoming": incoming, "output": output, "quarantine": quarantine, "tmp": tmp_path}


@pytest.fixture
def ingestor(tmp_dirs):
    """Create a default OCM3Ingestor pointed at temp directories."""
    return OCM3Ingestor(
        incoming_dir=tmp_dirs["incoming"],
        output_dir=tmp_dirs["output"],
        quarantine_dir=tmp_dirs["quarantine"],
        dry_run=False,
        keep_source=True,  # keep source so tests can inspect original
        rebuild_manifest=True,
    )


def make_valid_nc(path: Path, date_str: str = "2026-09-08") -> Path:
    """
    Create a minimal synthetic OCM-3-like NetCDF file with chlorophyll and SST.
    Global attributes match what ISRO OCM-3 L2C products typically contain.
    """
    lats = np.linspace(8.0, 22.0, 10)
    lons = np.linspace(68.0, 90.0, 10)
    chl = np.random.rand(10, 10).astype(np.float32) * 2.0
    sst = (np.random.rand(10, 10).astype(np.float32) * 5.0) + 25.0

    ds = xr.Dataset(
        {
            "chlor_a": xr.DataArray(chl, dims=["latitude", "longitude"], attrs={"units": "mg/m3"}),
            "sst": xr.DataArray(sst, dims=["latitude", "longitude"], attrs={"units": "celsius"}),
        },
        coords={
            "latitude": lats,
            "longitude": lons,
        },
        attrs={
            "Satellite": "EOS-06",
            "Sensor": "OCM-3",
            "Product_Type": "GEOPHYSICAL",
            "Processing_level": "L2C",
            "DateOfPass": date_str,
            "Scene_Start_Time": f"{date_str}T05:30:00",
            "Scene_End_Time": f"{date_str}T05:35:00",
        },
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(str(path), engine="netcdf4")
    return path


def make_corrupt_nc(path: Path) -> Path:
    """Write a file with .nc extension that is not valid NetCDF (simulates corruption)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"NOTANETCDFFILE_CORRUPTED_BYTES_XYZ")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDateParsing:
    def test_date_from_dateofpass_attribute(self, ingestor, tmp_dirs):
        """Date should be extracted from the DateOfPass global attribute."""
        nc = make_valid_nc(tmp_dirs["incoming"] / "test.nc", date_str="2026-09-09")
        meta = ingestor.extract_metadata(nc)
        assert meta["date"] == "2026-09-09"

    def test_fallback_to_mtime(self, ingestor, tmp_dirs):
        """If DateOfPass is missing, should fall back to file mtime."""
        lats = np.array([10.0, 11.0])
        lons = np.array([70.0, 71.0])
        chl = np.ones((2, 2), dtype=np.float32)
        ds = xr.Dataset(
            {"chlor_a": xr.DataArray(chl, dims=["latitude", "longitude"])},
            coords={"latitude": lats, "longitude": lons},
            attrs={"Satellite": "EOS-06"},  # No DateOfPass
        )
        nc_path = tmp_dirs["incoming"] / "no_date.nc"
        ds.to_netcdf(str(nc_path), engine="netcdf4")
        meta = ingestor.extract_metadata(nc_path)
        # Should parse to today's date approximately
        assert len(meta["date"]) == 10
        assert meta["date"].count("-") == 2


class TestVariableFuzzyMatching:
    def test_chlorophyll_matched_via_alias(self, ingestor):
        """chlor_a alias should resolve to canonical chlorophyll key."""
        found, missing = ingestor.validate_variables(["chlor_a", "sst", "wind_speed"])
        assert "chlorophyll" in found
        assert "sst" in found

    def test_missing_required_chlorophyll(self, ingestor):
        """If no chlorophyll alias is present, it should appear in missing list."""
        found, missing = ingestor.validate_variables(["sst", "wave_height"])
        assert "chlorophyll" in missing

    def test_all_variables_found(self, ingestor):
        """All four canonical variables should be found when all aliases are present."""
        var_names = ["chlor_a", "SST", "wind_speed", "significant_wave_height"]
        found, missing = ingestor.validate_variables(var_names)
        assert set(found) == set(EXPECTED_VARIABLES.keys())
        assert missing == []

    def test_case_insensitive_matching(self, ingestor):
        """Variable matching should be case-insensitive."""
        found, missing = ingestor.validate_variables(["CHLOROPHYLL", "SST"])
        assert "chlorophyll" in found


class TestTargetPathResolution:
    def test_correct_path_structure(self, ingestor, tmp_dirs):
        """Target path should follow ocm3/YYYY/MM/DD/filename structure."""
        nc = tmp_dirs["incoming"] / "sample.nc"
        nc.write_bytes(b"dummy")
        target = ingestor.resolve_target_path(nc, "2026-09-08")
        assert target == ingestor.ocm3_dir / "2026" / "09" / "08" / "sample.nc"

    def test_different_dates_produce_different_paths(self, ingestor, tmp_dirs):
        """Two different dates should produce different target directories."""
        nc = tmp_dirs["incoming"] / "file.nc"
        nc.write_bytes(b"dummy")
        p1 = ingestor.resolve_target_path(nc, "2026-09-08")
        p2 = ingestor.resolve_target_path(nc, "2026-09-09")
        assert p1.parent != p2.parent


class TestManifestSchema:
    def test_manifest_written_after_ingest(self, ingestor, tmp_dirs):
        """Running ingest on a valid file should produce manifest.json."""
        make_valid_nc(tmp_dirs["incoming"] / "scene1.nc", "2026-09-08")
        ingestor.run()
        manifest_path = tmp_dirs["output"] / "manifest.json"
        assert manifest_path.exists()

    def test_manifest_has_correct_schema(self, ingestor, tmp_dirs):
        """Manifest should contain all required top-level keys."""
        make_valid_nc(tmp_dirs["incoming"] / "scene1.nc", "2026-09-08")
        ingestor.run()
        manifest = get_latest_manifest(tmp_dirs["output"])
        assert manifest is not None
        assert "generated_at" in manifest
        assert "total_files" in manifest
        assert "total_size_bytes" in manifest
        assert "date_range" in manifest
        assert "files" in manifest
        assert isinstance(manifest["files"], list)

    def test_file_entry_has_required_fields(self, ingestor, tmp_dirs):
        """Each file entry in manifest should have the required schema fields."""
        make_valid_nc(tmp_dirs["incoming"] / "scene1.nc", "2026-09-08")
        ingestor.run()
        manifest = get_latest_manifest(tmp_dirs["output"])
        entry = manifest["files"][0]
        required_keys = [
            "filename", "target_path", "date", "size_bytes", "sha256",
            "satellite", "sensor", "variables_found", "missing_expected_vars",
            "status", "ingested_at"
        ]
        for key in required_keys:
            assert key in entry, f"Missing key in manifest entry: {key}"

    def test_date_range_reflects_ingested_dates(self, ingestor, tmp_dirs):
        """date_range should span from earliest to latest ingested date."""
        make_valid_nc(tmp_dirs["incoming"] / "day1.nc", "2026-09-08")
        make_valid_nc(tmp_dirs["incoming"] / "day2.nc", "2026-09-09")
        ingestor.run()
        manifest = get_latest_manifest(tmp_dirs["output"])
        assert manifest["date_range"]["start"] == "2026-09-08"
        assert manifest["date_range"]["end"] == "2026-09-09"


class TestQuarantineOnCorruptFile:
    def test_corrupt_file_is_quarantined(self, ingestor, tmp_dirs):
        """A file that cannot be opened as NetCDF should be moved to quarantine."""
        make_corrupt_nc(tmp_dirs["incoming"] / "corrupt.nc")
        ingestor.run()
        quarantine_file = tmp_dirs["quarantine"] / "corrupt.nc"
        assert quarantine_file.exists()

    def test_quarantine_error_sidecar_created(self, ingestor, tmp_dirs):
        """A .error.txt sidecar should be written alongside the quarantined file."""
        make_corrupt_nc(tmp_dirs["incoming"] / "bad.nc")
        ingestor.run()
        error_file = tmp_dirs["quarantine"] / "bad.nc.error.txt"
        assert error_file.exists()
        content = error_file.read_text(encoding="utf-8")
        assert "Source" in content or "Quarantined" in content

    def test_corrupt_does_not_abort_valid_ingest(self, ingestor, tmp_dirs):
        """A corrupt file should not prevent valid files from being ingested."""
        make_corrupt_nc(tmp_dirs["incoming"] / "bad.nc")
        make_valid_nc(tmp_dirs["incoming"] / "good.nc", "2026-09-08")
        stats = ingestor.run()
        assert stats["quarantined"] == 1
        assert stats["ingested"] == 1
