"""
SismoWatch - Live USGS Real-Time Ingestion Client
Extracts real, unsimulated seismic event feeds directly from the official USGS API.
Endpoints:
1. Real-time hourly feed: https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson
2. Recent catalog query: https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson
"""
import os
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

from quality.validator import SeismicDataValidator

logger = logging.getLogger(__name__)

USGS_HOURLY_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

class USGSLiveClient:
    """Official USGS API live extractor and pipeline feeder."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.raw_dir = os.path.join(self.base_dir, "data", "lakehouse", "raw")
        self.curated_dir = os.path.join(self.base_dir, "data", "lakehouse", "curated")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.curated_dir, exist_ok=True)

    def fetch_live_catalog(self, min_magnitude: float = 2.0, limit: int = 25) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches the latest real-world seismic events from USGS catalog.
        Returns: (curated_records, extraction_metadata)
        """
        url = f"{USGS_QUERY_URL}?format=geojson&minmagnitude={min_magnitude}&limit={limit}&orderby=time"
        logger.info(f"Connecting to live USGS API: {url}")
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SismoWatch-RealTimeMonitor/2.0 (Academic/Enterprise Research)",
                "Accept": "application/json"
            }
        )

        payload = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        payload = json.loads(resp.read().decode("utf-8"))
                        break
            except Exception as e:
                logger.warning(f"USGS query attempt {attempt + 1} error: {e}")
                time.sleep(1)

        if not payload:
            # Resilient fallback to official USGS hourly GeoJSON summary
            try:
                logger.info("Falling back to USGS real-time hourly feed")
                fallback_req = urllib.request.Request(
                    USGS_HOURLY_URL,
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}
                )
                with urllib.request.urlopen(fallback_req, timeout=15) as resp:
                    if resp.status == 200:
                        payload = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                logger.error(f"Fallback to USGS hourly feed failed: {e}")
                raise RuntimeError(f"Failed to fetch live USGS data after retry: {e}")

        features = payload.get("features", [])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # 1. Save Raw GeoJSON snapshot for audit
        raw_path = os.path.join(self.raw_dir, f"usgs_live_{timestamp}.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # 2. Process through Medallion Data Quality Validator
        run_id = f"usgs_live_{timestamp}"
        clean_records, anomalies, stats = SeismicDataValidator.process_batch(features, run_id=run_id)

        # 3. Update Curated Lakehouse Snapshot
        curated_snapshot_path = os.path.join(self.curated_dir, "curated_snapshot.json")
        with open(curated_snapshot_path, "w", encoding="utf-8") as f:
            json.dump(clean_records, f, ensure_ascii=False, indent=2)

        metadata = {
            "source": "USGS_LIVE_API",
            "api_url": url,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "records_extracted": len(features),
            "records_curated": len(clean_records),
            "anomalies_detected": len(anomalies),
            "quality_score": stats.get("quality_score", 100.0),
            "raw_file": raw_path,
            "curated_file": curated_snapshot_path
        }

        return clean_records, metadata

    def fetch_realtime_hourly(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fetches the real-time feed updated every minute from USGS."""
        req = urllib.request.Request(
            USGS_HOURLY_URL,
            headers={"User-Agent": "SismoWatch-RealTimeMonitor/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        clean_records, _, stats = SeismicDataValidator.process_batch(payload.get("features", []))
        return clean_records, {
            "source": "USGS_HOURLY_FEED",
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "count": len(clean_records)
        }
