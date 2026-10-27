"""
SismoWatch - Data Quality & Sensor Diagnostics Validator
Validates seismic events, prunes raw API bloat, and routes sensor anomalies to diagnostics.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

class SeismicDataValidator:
    """Validator implementing domain quality checks and sensor anomaly detection."""

    MIN_MAGNITUDE = -1.0
    MAX_MAGNITUDE = 10.0
    MIN_DEPTH_KM = 0.0
    MIN_LATITUDE = -90.0
    MAX_LATITUDE = 90.0
    MIN_LONGITUDE = -180.0
    MAX_LONGITUDE = 180.0

    @staticmethod
    def validate_and_extract(feature: Dict[str, Any], run_id: str = "run_default") -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Extracts the 7 core business fields and validates quality.
        Returns:
            (clean_record, None) if completely valid.
            (None, sensor_alert) if an anomaly or corruption is detected.
        """
        # 1. Structural Schema Validation
        if not isinstance(feature, dict):
            return None, {
                "sensor_id": "UNKNOWN",
                "raw_reading": {},
                "issue_code": "ERR_INVALID_OBJECT",
                "diagnostic_message": "Feature is not a JSON object",
                "pipeline_stage": "RAW_TO_STAGING",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        event_id = feature.get("id")
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []

        if not event_id:
            return None, {
                "sensor_id": "UNKNOWN",
                "raw_reading": feature,
                "issue_code": "ERR_MISSING_EVENT_ID",
                "diagnostic_message": "Feature missing required 'id' attribute",
                "pipeline_stage": "RAW_TO_STAGING",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        if len(coordinates) < 3:
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_INCOMPLETE_COORDINATES",
                "diagnostic_message": f"Expected [lon, lat, depth], got {coordinates}",
                "pipeline_stage": "RAW_TO_STAGING",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        # 2. Extract Coordinates (GeoJSON format: [longitude, latitude, depth])
        try:
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])
            depth = float(coordinates[2])
        except (ValueError, TypeError) as e:
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_COORDINATES_TYPE",
                "diagnostic_message": f"Non-numeric coordinate: {str(e)}",
                "pipeline_stage": "RAW_TO_STAGING",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        # 3. Extract Properties
        raw_mag = properties.get("mag")
        raw_time = properties.get("time")
        place = str(properties.get("place") or "").strip()
        status = str(properties.get("status") or "reviewed").strip()

        try:
            magnitude = float(raw_mag) if raw_mag is not None else None
        except (ValueError, TypeError):
            magnitude = None

        if magnitude is None:
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_NULL_MAGNITUDE",
                "diagnostic_message": "Magnitude value is null or non-numeric",
                "pipeline_stage": "RAW_TO_STAGING",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        if not raw_time:
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_MISSING_TIMESTAMP",
                "diagnostic_message": "Event time timestamp missing",
                "pipeline_stage": "RAW_TO_STAGING",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        try:
            # USGS time is epoch milliseconds
            event_time = datetime.fromtimestamp(raw_time / 1000.0, tz=timezone.utc).isoformat()
        except Exception as e:
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_INVALID_TIMESTAMP_FORMAT",
                "diagnostic_message": f"Unable to parse timestamp: {str(e)}",
                "pipeline_stage": "RAW_TO_STAGING",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        # 4. Domain & Physics Rules Validation
        if not (SeismicDataValidator.MIN_MAGNITUDE <= magnitude <= SeismicDataValidator.MAX_MAGNITUDE):
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_SENSOR_CALIBRATION_MAGNITUDE",
                "diagnostic_message": f"Magnitude {magnitude} outside realistic bounds [-1.0, 10.0]",
                "pipeline_stage": "STAGING_TO_CURATED",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        if depth < SeismicDataValidator.MIN_DEPTH_KM:
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_SENSOR_DEPTH_NEGATIVE",
                "diagnostic_message": f"Seismic depth cannot be negative: {depth} km",
                "pipeline_stage": "STAGING_TO_CURATED",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        if not (SeismicDataValidator.MIN_LATITUDE <= latitude <= SeismicDataValidator.MAX_LATITUDE and
                SeismicDataValidator.MIN_LONGITUDE <= longitude <= SeismicDataValidator.MAX_LONGITUDE):
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_SENSOR_GEOGRAPHIC_BOUNDS",
                "diagnostic_message": f"Coordinates ({latitude}, {longitude}) out of earthly bounds",
                "pipeline_stage": "STAGING_TO_CURATED",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        if not place:
            return None, {
                "sensor_id": event_id,
                "raw_reading": feature,
                "issue_code": "ERR_EMPTY_LOCATION_NAME",
                "diagnostic_message": "Event location 'place' is empty",
                "pipeline_stage": "STAGING_TO_CURATED",
                "run_id": run_id,
                "sensor_status": "NEEDS_CHECK"
            }

        # 5. Clean Record with all useless API fields stripped away
        clean_record = {
            "event_id": str(event_id),
            "event_time": event_time,
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "depth": round(depth, 2),
            "magnitude": round(magnitude, 2),
            "place": place,
            "status": status
        }
        return clean_record, None

    @classmethod
    def process_batch(cls, features: List[Dict[str, Any]], run_id: str = "run_default") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """Processes an entire batch of raw features."""
        clean_events = []
        sensor_alerts = []

        for feat in features:
            clean, alert = cls.validate_and_extract(feat, run_id=run_id)
            if clean:
                clean_events.append(clean)
            elif alert:
                sensor_alerts.append(alert)

        total_ingested = len(features)
        total_curated = len(clean_events)
        total_alerts = len(sensor_alerts)
        quality_score = round((total_curated / total_ingested * 100.0), 2) if total_ingested > 0 else 100.0

        metrics = {
            "run_id": run_id,
            "records_ingested": total_ingested,
            "records_curated": total_curated,
            "sensor_alerts_count": total_alerts,
            "quality_score": quality_score,
            "sla_met": True
        }
        return clean_events, sensor_alerts, metrics
