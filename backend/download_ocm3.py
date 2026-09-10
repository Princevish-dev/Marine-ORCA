"""
BhoonidhiOCM3Downloader — Production-ready satellite data downloader for ISRO Bhoonidhi portal.

Downloads EOS-06 (Oceansat-3) OCM-3 Level-2C Geophysical NetCDF products
for chlorophyll-a, SST, wave height, and wind speed parameters.

Feeds into ORCA Local-First backend for dynamic anomaly scoring R(t).
"""

from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import xarray as xr


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


AOI_PRESETS: dict[str, dict[str, float]] = {
    "default": {"min_lat": 5.0, "max_lat": 25.0, "min_lon": 65.0, "max_lon": 95.0},
    "arabian_sea": {"min_lat": 8.0, "max_lat": 24.0, "min_lon": 65.0, "max_lon": 77.0},
    "bay_of_bengal": {"min_lat": 5.0, "max_lat": 22.0, "min_lon": 78.0, "max_lon": 95.0},
}

SUB_TILE_SPLIT = 2


class BhoonidhiOCM3Downloader:
    """Downloads OCM-3 L2C geophysical NetCDF products from ISRO Bhoonidhi."""

    BASE_URL = "https://bhoonidhi.nrsc.gov.in/api/v1"
    SESSION_FILE = ".bhoonidhi_session"
    MANIFEST_FILE = "download_manifest.json"
    FAILED_FILE = "failed_downloads.json"
    MAX_RETRIES = 3
    BASE_DELAY = 5

    def __init__(
        self,
        output_dir: str | Path,
        days: int = 20,
        bbox: Optional[dict[str, float]] = None,
        dry_run: bool = False,
        resume: bool = True,
    ) -> None:
        """Initialise the downloader with configuration."""
        self.output_dir = Path(output_dir)
        self.ocm3_dir = self.output_dir / "ocm3"
        self.days = days
        self.bbox = bbox or AOI_PRESETS["default"]
        self.dry_run = dry_run
        self.resume = resume

        self.username = os.environ.get("BHOONIDHI_USERNAME", "")
        self.password = os.environ.get("BHOONIDHI_PASSWORD", "")
        self.session_token: Optional[str] = None

        self.manifest: list[dict] = []
        self.failed: list[dict] = []

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
        self._load_manifest()
        self._load_session()

    def _setup_logging(self) -> None:
        """Configure file and console logging."""
        log_path = self.output_dir / "download.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        self.logger = logging.getLogger("bhoonidhi")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _load_manifest(self) -> None:
        """Load existing download manifest from disk."""
        manifest_path = self.output_dir / self.MANIFEST_FILE
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                self.manifest = json.load(f)

    def _save_manifest(self) -> None:
        """Persist the download manifest to disk."""
        manifest_path = self.output_dir / self.MANIFEST_FILE
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, default=str)

    def _save_failed(self) -> None:
        """Persist failed downloads for later retry."""
        if not self.failed:
            return
        failed_path = self.output_dir / self.FAILED_FILE
        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(self.failed, f, indent=2, default=str)

    def _load_session(self) -> None:
        """Load a cached session token if available and not expired."""
        session_path = self.output_dir / self.SESSION_FILE
        if session_path.exists():
            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                expires = datetime.fromisoformat(data.get("expires", "2000-01-01"))
                if expires > datetime.now(timezone.utc).replace(tzinfo=None):
                    self.session_token = data["token"]
                    self.logger.info("Loaded cached session token (expires %s)", expires.isoformat())
            except Exception:
                pass

    def _save_session(self, token: str, expires_in_seconds: int = 3600) -> None:
        """Cache the session token to disk."""
        session_path = self.output_dir / self.SESSION_FILE
        data = {
            "token": token,
            "expires": (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).isoformat(),
        }
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _file_sha256(self, filepath: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _is_already_downloaded(self, filename: str, expected_size: Optional[int] = None) -> bool:
        """Check if a file was already downloaded based on manifest."""
        for entry in self.manifest:
            if entry.get("filename") == filename and entry.get("status") == "success":
                if expected_size is None:
                    return True
                if entry.get("size") == expected_size:
                    return True
        return False

    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Execute an HTTP request with exponential backoff retry."""
        all_headers = {"Accept": "application/json"}
        if self.session_token:
            all_headers["Authorization"] = f"Bearer {self.session_token}"
        if headers:
            all_headers.update(headers)

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=all_headers,
                        params=params,
                        json=json_body,
                    )
                    response.raise_for_status()
                    return response
            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
                delay = self.BASE_DELAY * (2 ** (attempt - 1))
                self.logger.warning(
                    "Request failed (attempt %d/%d): %s — retrying in %ds",
                    attempt, self.MAX_RETRIES, str(exc)[:120], delay,
                )
                time.sleep(delay)

        raise ConnectionError(f"All {self.MAX_RETRIES} retries exhausted for {url}") from last_exc

    def _download_file_with_retry(self, url: str, dest: Path) -> None:
        """Stream-download a large file with retry logic."""
        all_headers: dict[str, str] = {}
        if self.session_token:
            all_headers["Authorization"] = f"Bearer {self.session_token}"

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=300.0, follow_redirects=True) as client:
                    with client.stream("GET", url, headers=all_headers) as response:
                        response.raise_for_status()
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with open(dest, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=65536):
                                f.write(chunk)
                return
            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
                delay = self.BASE_DELAY * (2 ** (attempt - 1))
                self.logger.warning(
                    "Download failed (attempt %d/%d): %s — retrying in %ds",
                    attempt, self.MAX_RETRIES, str(exc)[:120], delay,
                )
                if dest.exists():
                    dest.unlink()
                time.sleep(delay)

        raise ConnectionError(f"Download failed after {self.MAX_RETRIES} retries: {url}") from last_exc

    def authenticate(self) -> bool:
        """Authenticate with Bhoonidhi portal and obtain a session token."""
        if self.session_token:
            self.logger.info("Using cached session token")
            return True

        if not self.username or not self.password:
            self.logger.error("BHOONIDHI_USERNAME and BHOONIDHI_PASSWORD environment variables required")
            return False

        self.logger.info("Authenticating with Bhoonidhi portal as '%s'...", self.username)

        try:
            response = self._request_with_retry(
                "POST",
                f"{self.BASE_URL}/auth/login",
                json_body={"username": self.username, "password": self.password},
            )
            data = response.json()
            token = data.get("token") or data.get("access_token") or data.get("sessionId")
            if not token:
                self.logger.error("Authentication response missing token field: %s", list(data.keys()))
                return False

            self.session_token = token
            expires_in = int(data.get("expires_in", data.get("expiresIn", 3600)))
            self._save_session(token, expires_in)
            self.logger.info("Authentication successful — token cached for %d seconds", expires_in)
            return True

        except Exception as exc:
            self.logger.error("Authentication failed: %s", exc)
            return False

    def build_date_range(self) -> list[datetime]:
        """Generate a list of dates from (today - days) to today."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return [today - timedelta(days=d) for d in range(self.days, -1, -1)]

    def _split_bbox_into_tiles(self) -> list[dict[str, float]]:
        """Split the bounding box into sub-tiles for large AOIs."""
        min_lat = self.bbox["min_lat"]
        max_lat = self.bbox["max_lat"]
        min_lon = self.bbox["min_lon"]
        max_lon = self.bbox["max_lon"]

        lat_step = (max_lat - min_lat) / SUB_TILE_SPLIT
        lon_step = (max_lon - min_lon) / SUB_TILE_SPLIT

        tiles: list[dict[str, float]] = []
        for i in range(SUB_TILE_SPLIT):
            for j in range(SUB_TILE_SPLIT):
                tiles.append({
                    "min_lat": min_lat + i * lat_step,
                    "max_lat": min_lat + (i + 1) * lat_step,
                    "min_lon": min_lon + j * lon_step,
                    "max_lon": min_lon + (j + 1) * lon_step,
                })
        return tiles

    def query_available_products(
        self, date: datetime, tile: dict[str, float]
    ) -> list[dict]:
        """Query Bhoonidhi API for available OCM-3 L2C products for a date and tile."""
        date_str = date.strftime("%Y-%m-%d")
        self.logger.info(
            "Querying products for %s | bbox [%.1f,%.1f → %.1f,%.1f]",
            date_str, tile["min_lat"], tile["min_lon"], tile["max_lat"], tile["max_lon"],
        )

        search_payload = {
            "satellite": "EOS-06",
            "sensor": "OCM-3",
            "productType": "GEOPHYSICAL",
            "processingLevel": "L2C",
            "startDate": date_str,
            "endDate": date_str,
            "boundingBox": {
                "minLat": tile["min_lat"],
                "maxLat": tile["max_lat"],
                "minLon": tile["min_lon"],
                "maxLon": tile["max_lon"],
            },
        }

        try:
            response = self._request_with_retry(
                "POST",
                f"{self.BASE_URL}/products/search",
                json_body=search_payload,
            )
            data = response.json()
            products = data.get("products", data.get("results", data.get("data", [])))

            if not isinstance(products, list):
                products = []

            self.logger.info("Found %d product(s) for %s", len(products), date_str)
            return products

        except Exception as exc:
            self.logger.warning("Query failed for %s: %s", date_str, exc)
            return []

    def download_product(self, product: dict, date: datetime) -> Optional[Path]:
        """Download a single product file to the date-organised directory."""
        product_id = product.get("productId") or product.get("id") or product.get("filename", "unknown")
        filename = product.get("filename") or f"OCM3_L2C_{product_id}.nc"
        file_size = product.get("fileSize") or product.get("size")
        download_url = product.get("downloadUrl") or product.get("url") or f"{self.BASE_URL}/products/download/{product_id}"

        day_dir = self.ocm3_dir / date.strftime("%Y") / date.strftime("%m") / date.strftime("%d")
        dest_path = day_dir / filename

        if self.resume and self._is_already_downloaded(filename, file_size):
            self.logger.info("SKIP (already downloaded): %s", filename)
            return dest_path if dest_path.exists() else None

        if self.dry_run:
            self.logger.info("DRY-RUN — would download: %s → %s", filename, dest_path)
            return None

        self.logger.info("Downloading: %s (%s bytes)", filename, file_size or "unknown")

        try:
            self._download_file_with_retry(download_url, dest_path)
            self.logger.info("Saved: %s", dest_path)
            return dest_path

        except Exception as exc:
            self.logger.error("Download failed for %s: %s", filename, exc)
            self.failed.append({
                "filename": filename,
                "product_id": product_id,
                "date": date.isoformat(),
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return None

    def validate_netcdf(self, filepath: Path) -> bool:
        """Validate that a downloaded .nc file opens correctly with xarray."""
        try:
            ds = xr.open_dataset(filepath, engine="netcdf4")
            var_names = list(ds.data_vars)
            ds.close()
            self.logger.info(
                "Validated NetCDF: %s — variables: %s",
                filepath.name, ", ".join(var_names[:10]),
            )
            return True
        except Exception as exc:
            self.logger.error("NetCDF validation FAILED for %s: %s", filepath.name, exc)
            return False

    def update_manifest(
        self, filename: str, date: datetime, filepath: Optional[Path], status: str
    ) -> None:
        """Add or update a manifest entry for a downloaded product."""
        entry = {
            "filename": filename,
            "date": date.strftime("%Y-%m-%d"),
            "size": filepath.stat().st_size if filepath and filepath.exists() else None,
            "sha256": self._file_sha256(filepath) if filepath and filepath.exists() and status == "success" else None,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        existing_idx = next(
            (i for i, e in enumerate(self.manifest) if e.get("filename") == filename),
            None,
        )
        if existing_idx is not None:
            self.manifest[existing_idx] = entry
        else:
            self.manifest.append(entry)

        self._save_manifest()

    def run(self) -> dict[str, int]:
        """Execute the full download pipeline."""
        self.logger.info("=" * 70)
        self.logger.info("ORCA Bhoonidhi OCM-3 Downloader — Starting")
        self.logger.info("  Output    : %s", self.output_dir.resolve())
        self.logger.info("  Date range: last %d days", self.days)
        self.logger.info("  AOI bbox  : %s", self.bbox)
        self.logger.info("  Dry run   : %s", self.dry_run)
        self.logger.info("  Resume    : %s", self.resume)
        self.logger.info("=" * 70)

        stats = {"queried": 0, "downloaded": 0, "skipped": 0, "failed": 0, "validated": 0}

        if not self.dry_run:
            auth_ok = self.authenticate()
            if not auth_ok:
                self.logger.error("Cannot proceed without authentication")
                return stats

        dates = self.build_date_range()
        tiles = self._split_bbox_into_tiles()
        self.logger.info("Processing %d dates × %d tiles = %d queries", len(dates), len(tiles), len(dates) * len(tiles))

        for date in dates:
            date_str = date.strftime("%Y-%m-%d")

            for tile_idx, tile in enumerate(tiles):
                products = self.query_available_products(date, tile)
                stats["queried"] += 1

                if not products:
                    self.logger.info("No data available for %s tile %d — skipping", date_str, tile_idx + 1)
                    continue

                for product in products:
                    filename = product.get("filename") or product.get("id", "unknown")

                    if self.resume and self._is_already_downloaded(filename):
                        stats["skipped"] += 1
                        continue

                    dest = self.download_product(product, date)

                    if dest and dest.exists():
                        valid = self.validate_netcdf(dest)
                        status = "success" if valid else "invalid_netcdf"

                        if valid:
                            stats["downloaded"] += 1
                            stats["validated"] += 1
                        else:
                            stats["failed"] += 1

                        self.update_manifest(filename, date, dest, status)
                    elif not self.dry_run:
                        stats["failed"] += 1
                        self.update_manifest(filename, date, None, "download_failed")

        self._save_failed()

        self.logger.info("=" * 70)
        self.logger.info("Download complete — Summary:")
        self.logger.info("  Queries made  : %d", stats["queried"])
        self.logger.info("  Downloaded    : %d", stats["downloaded"])
        self.logger.info("  Validated     : %d", stats["validated"])
        self.logger.info("  Skipped       : %d", stats["skipped"])
        self.logger.info("  Failed        : %d", stats["failed"])
        self.logger.info("=" * 70)

        return stats


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="download_ocm3",
        description="Download ISRO Bhoonidhi OCM-3 L2C NetCDF products for ORCA",
    )
    parser.add_argument("--days", type=int, default=20, help="Number of past days to download (default: 20)")
    parser.add_argument("--aoi", choices=["default", "arabian_sea", "bay_of_bengal", "custom"], default="default", help="Area of interest preset")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("MIN_LAT", "MAX_LAT", "MIN_LON", "MAX_LON"), help="Custom bounding box (requires --aoi custom)")
    parser.add_argument("--output", type=str, default="./data/bhoonidhi", help="Output directory (default: ./data/bhoonidhi)")
    parser.add_argument("--dry-run", action="store_true", help="List files without downloading")
    parser.add_argument("--resume", action="store_true", default=True, help="Skip already-downloaded files (default: True)")
    parser.add_argument("--no-resume", action="store_false", dest="resume", help="Re-download all files")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.aoi == "custom":
        if not args.bbox or len(args.bbox) != 4:
            print("ERROR: --bbox MIN_LAT MAX_LAT MIN_LON MAX_LON required when --aoi is 'custom'")
            sys.exit(1)
        bbox = {
            "min_lat": args.bbox[0],
            "max_lat": args.bbox[1],
            "min_lon": args.bbox[2],
            "max_lon": args.bbox[3],
        }
    else:
        bbox = AOI_PRESETS[args.aoi]

    downloader = BhoonidhiOCM3Downloader(
        output_dir=args.output,
        days=args.days,
        bbox=bbox,
        dry_run=args.dry_run,
        resume=args.resume,
    )
    result = downloader.run()
    sys.exit(0 if result["failed"] == 0 else 1)
