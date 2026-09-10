"""
Tests for BhoonidhiOCM3Downloader.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from download_ocm3 import BhoonidhiOCM3Downloader, AOI_PRESETS


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide a temporary output directory for tests."""
    return tmp_path / "data"


@pytest.fixture
def downloader(temp_output_dir):
    """Provide a BhoonidhiOCM3Downloader instance."""
    return BhoonidhiOCM3Downloader(
        output_dir=temp_output_dir,
        days=5,
        bbox=AOI_PRESETS["default"],
        dry_run=True,
    )


def test_build_date_range(downloader):
    """Ensure the date range builder returns the correct number of past days."""
    dates = downloader.build_date_range()
    
    assert len(dates) == downloader.days + 1  # Includes today
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    assert dates[-1] == today
    assert dates[0] == today - timedelta(days=downloader.days)


def test_split_bbox_into_tiles(downloader):
    """Ensure bounding boxes are correctly split into 4 sub-tiles."""
    tiles = downloader._split_bbox_into_tiles()
    
    assert len(tiles) == 4
    
    # Check that the bounds match the default AOI
    min_lat_total = min(t["min_lat"] for t in tiles)
    max_lat_total = max(t["max_lat"] for t in tiles)
    min_lon_total = min(t["min_lon"] for t in tiles)
    max_lon_total = max(t["max_lon"] for t in tiles)
    
    default = AOI_PRESETS["default"]
    assert min_lat_total == default["min_lat"]
    assert max_lat_total == default["max_lat"]
    assert min_lon_total == default["min_lon"]
    assert max_lon_total == default["max_lon"]


def test_update_manifest(downloader, temp_output_dir):
    """Ensure the manifest is correctly updated and saved."""
    today = datetime.now(timezone.utc)
    
    # Create a dummy file to check size and hash logic (if it wasn't skipped for missing file)
    dummy_file = temp_output_dir / "dummy.nc"
    dummy_file.write_text("dummy data")
    
    downloader.update_manifest(
        filename="test_file.nc",
        date=today,
        filepath=dummy_file,
        status="success"
    )
    
    assert len(downloader.manifest) == 1
    entry = downloader.manifest[0]
    assert entry["filename"] == "test_file.nc"
    assert entry["status"] == "success"
    assert entry["size"] == 10
    assert "sha256" in entry
    
    # Ensure it was saved to disk
    manifest_path = temp_output_dir / "download_manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
        
    assert len(saved) == 1
    assert saved[0]["filename"] == "test_file.nc"


def test_already_downloaded_logic(downloader):
    """Ensure resuming works based on manifest size matching."""
    downloader.manifest = [
        {"filename": "exist.nc", "status": "success", "size": 100},
        {"filename": "failed.nc", "status": "download_failed", "size": None},
        {"filename": "partial.nc", "status": "success", "size": 50},
    ]
    
    # Exact match on filename and size
    assert downloader._is_already_downloaded("exist.nc", 100) is True
    
    # Name match but size mismatch (maybe interrupted)
    assert downloader._is_already_downloaded("exist.nc", 999) is False
    
    # Name match but marked as failed
    assert downloader._is_already_downloaded("failed.nc", None) is False
    
    # Name match and no expected size provided (fallback check)
    assert downloader._is_already_downloaded("exist.nc") is True
