"""
Unit Tests for Task 2: Seismic Dataset Contract & Data Quality Engine
Verifies that:
1. The 20 test events pass 100% cleanly without data loss.
2. Useless API fields are pruned immediately.
3. Physical sensor anomalies trigger diagnostic alerts properly.
"""
import json
import os
import pytest
from quality.validator import SeismicDataValidator

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_20_FILE = os.path.join(DATA_DIR, "raw_seismic_events_20.json")
ANOMALIES_FILE = os.path.join(DATA_DIR, "sensor_anomalies_test.json")

def test_raw_dataset_file_exists():
    """Verify that the official 20-event raw dataset file exists."""
    assert os.path.exists(RAW_20_FILE), f"Dataset file not found at {RAW_20_FILE}"

def test_raw_dataset_has_exactly_20_records():
    """Verify that the raw dataset has an exact count of 20 features."""
    with open(RAW_20_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    assert payload.get("type") == "FeatureCollection"
    features = payload.get("features", [])
    assert len(features) == 20, f"Expected 20 records, got {len(features)}"

def test_validation_20_records_pass_cleanly_with_zero_quarantine():
    """
    CRITICAL REQUIREMENT:
    If 20 events arrive, exactly 20 events must pass quality gates cleanly (20 in -> 20 out).
    Zero records diverted to sensor alerts, quality score must be 100%.
    """
    with open(RAW_20_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    features = payload.get("features", [])
    clean_events, sensor_alerts, metrics = SeismicDataValidator.process_batch(features, run_id="test_run_20")

    # Assert 1:1 data integrity
    assert len(clean_events) == 20, f"Expected 20 curated events, got {len(clean_events)}"
    assert len(sensor_alerts) == 0, f"Expected 0 sensor alerts, got {len(sensor_alerts)}"
    assert metrics["quality_score"] == 100.0, f"Expected 100% quality score, got {metrics['quality_score']}"
    assert metrics["records_ingested"] == 20
    assert metrics["records_curated"] == 20

def test_useless_api_fields_are_pruned_in_curated():
    """Verify that bloated raw API fields are immediately removed."""
    with open(RAW_20_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    first_raw = payload["features"][0]
    # Raw feature contains bloat
    assert "felt" in first_raw["properties"]
    assert "cdi" in first_raw["properties"]
    assert "rms" in first_raw["properties"]

    clean_record, alert = SeismicDataValidator.validate_and_extract(first_raw, run_id="test_run_pruning")
    assert alert is None
    assert clean_record is not None

    # Curated record only contains core business fields
    expected_keys = {"event_id", "event_time", "latitude", "longitude", "depth", "magnitude", "place", "status"}
    assert set(clean_record.keys()) == expected_keys
    assert "felt" not in clean_record
    assert "cdi" not in clean_record
    assert "rms" not in clean_record

def test_sensor_diagnostic_detection_on_anomalous_events():
    """Verify that corrupt or anomalous sensor events are captured by the diagnostics module."""
    with open(ANOMALIES_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    features = payload.get("features", [])
    assert len(features) == 2

    clean_events, sensor_alerts, metrics = SeismicDataValidator.process_batch(features, run_id="test_run_anomalies")

    assert len(clean_events) == 0, "Anomalous events must not pass to clean data"
    assert len(sensor_alerts) == 2, "Both anomalous events must generate sensor diagnostic alerts"
    assert metrics["quality_score"] == 0.0

    # Inspect first alert (negative depth / extreme mag)
    alert_1 = sensor_alerts[0]
    assert alert_1["sensor_id"] == "sensor_err_01"
    assert alert_1["sensor_status"] == "NEEDS_CHECK"
    assert alert_1["issue_code"] in ["ERR_SENSOR_CALIBRATION_MAGNITUDE", "ERR_SENSOR_DEPTH_NEGATIVE"]

    # Inspect second alert (out-of-bounds coordinates / empty place)
    alert_2 = sensor_alerts[1]
    assert alert_2["sensor_id"] == "sensor_err_02"
    assert alert_2["sensor_status"] == "NEEDS_CHECK"
    assert alert_2["issue_code"] in ["ERR_SENSOR_CALIBRATION_MAGNITUDE", "ERR_SENSOR_GEOGRAPHIC_BOUNDS"]
