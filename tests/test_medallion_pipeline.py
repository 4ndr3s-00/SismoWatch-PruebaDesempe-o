"""
Unit & Integration Tests for Task 3: Seismic Medallion Pipeline Execution
Validates:
1. Full pipeline execution: Bronze -> Silver -> Gold.
2. 20-in -> 20-out strict integrity constraint.
3. Idempotence: Duplicate runs do not produce duplicate events.
4. Updates: Magnitude revisions update records in-place.
5. SLA compliance: Latency under 5 minutes (300s).
"""
import json
import os
import copy
import pytest
from spark.jobs.seismic_medallion_job import SeismicMedallionPipeline

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_20_FILE = os.path.join(DATA_DIR, "raw_seismic_events_20.json")

@pytest.fixture
def raw_payload():
    with open(RAW_20_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def pipeline(tmp_path):
    # Use temporary directory for isolated test lakehouse
    lakehouse_dir = str(tmp_path / "lakehouse")
    return SeismicMedallionPipeline(lakehouse_dir=lakehouse_dir)

def test_pipeline_20_records_end_to_end(pipeline, raw_payload):
    """Verify that 20 raw events produce exactly 20 curated events with 100% quality."""
    result = pipeline.run_pipeline(raw_payload, run_id="test_run_e2e_20")
    metrics = result["metrics"]

    assert metrics["records_ingested"] == 20
    assert metrics["records_staged"] == 20
    assert metrics["records_curated"] == 20
    assert metrics["sensor_alerts_count"] == 0
    assert metrics["quality_score"] == 100.0
    assert metrics["sla_met"] is True
    assert len(result["curated_events"]) == 20

def test_pipeline_idempotency_duplicate_run(pipeline, raw_payload):
    """
    IDEMPOTENCY TEST:
    Running the pipeline twice on the same raw dataset must yield the exact same 20 curated records.
    """
    res1 = pipeline.run_pipeline(raw_payload, run_id="run_idempotency_1")
    res2 = pipeline.run_pipeline(raw_payload, run_id="run_idempotency_2")

    assert res1["metrics"]["records_curated"] == 20
    assert res2["metrics"]["records_curated"] == 20

    # Ensure curated snapshot file contains exactly 20 unique events
    curated_snapshot_file = os.path.join(pipeline.curated_dir, "curated_snapshot.json")
    with open(curated_snapshot_file, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    event_ids = [e["event_id"] for e in snapshot]
    assert len(event_ids) == 20
    assert len(set(event_ids)) == 20, "Curated events must have unique IDs (no duplicates)"

def test_pipeline_handles_magnitude_revision(pipeline, raw_payload):
    """
    UPDATE REVISION TEST:
    If a geological network recalculates an earthquake's magnitude (e.g. from 4.5 to 4.9),
    the pipeline updates the record cleanly without creating duplicate rows.
    """
    # 1. First run with original mag (4.5)
    pipeline.run_pipeline(raw_payload, run_id="run_orig")

    # 2. Modify first event magnitude in payload
    updated_payload = copy.deepcopy(raw_payload)
    target_event_id = updated_payload["features"][0]["id"]
    updated_payload["features"][0]["properties"]["mag"] = 4.9

    # 3. Second run with updated mag
    result_updated = pipeline.run_pipeline(updated_payload, run_id="run_updated")

    assert result_updated["metrics"]["records_curated"] == 20
    target_curated = next(e for e in result_updated["curated_events"] if e["event_id"] == target_event_id)
    assert target_curated["magnitude"] == 4.9, "Record should reflect updated magnitude"
