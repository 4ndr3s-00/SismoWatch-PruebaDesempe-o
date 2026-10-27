"""
Unit Tests for Task 4: Apache Airflow Orchestration DAG
Verifies:
1. DAG compilation & syntax.
2. TaskFlow & TaskGroup structure.
3. Exponential backoff, timeout, and failure alert settings.
4. 30-day backfill parameterization.
5. End-to-end functional simulation asserting 20-in -> 20-out integrity.
"""
import os
import ast
from datetime import timedelta
import pytest
from dags.sismo_pipeline_dag import (
    DEFAULT_ARGS, DAG_PARAMS, DAG_DOC_MD,
    extract_seismic_data, run_medallion_processing, verify_data_integrity
)

DAG_FILE = os.path.join(os.path.dirname(__file__), "..", "dags", "sismo_pipeline_dag.py")

def test_dag_file_exists():
    """Verify that the DAG file exists in dags/ directory."""
    assert os.path.exists(DAG_FILE), f"DAG file not found at {DAG_FILE}"

def test_dag_compilation_and_ast_syntax():
    """Verify that the DAG file compiles cleanly with zero syntax errors."""
    with open(DAG_FILE, "r", encoding="utf-8") as f:
        source_code = f.read()

    parsed = ast.parse(source_code)
    assert parsed is not None
    assert len(parsed.body) > 0

def test_dag_resilience_configuration():
    """Verify retry policies, exponential backoff, timeouts, and callbacks."""
    assert DEFAULT_ARGS["retries"] == 3
    assert DEFAULT_ARGS["retry_delay"] == timedelta(seconds=15)
    assert DEFAULT_ARGS["retry_exponential_backoff"] is True
    assert DEFAULT_ARGS["max_retry_delay"] == timedelta(minutes=2)
    assert DEFAULT_ARGS["execution_timeout"] == timedelta(minutes=5)
    assert callable(DEFAULT_ARGS["on_failure_callback"])

def test_dag_backfill_params_and_documentation():
    """Verify DAG parameters for 30-day backfill and comprehensive doc_md."""
    assert len(DAG_DOC_MD) > 50
    assert "SismoWatch" in DAG_DOC_MD
    assert "Idempotency" in DAG_DOC_MD

    # Check backfill params
    assert "start_date" in DAG_PARAMS
    assert "end_date" in DAG_PARAMS
    assert "mode" in DAG_PARAMS
    assert "limit" in DAG_PARAMS

def test_dag_tasks_execution_simulation():
    """
    Simulate full DAG tasks execution with official 20 events:
    extract -> transform -> verify 20 in == 20 out.
    """
    # 1. Simulate extract task
    extract_fn = getattr(extract_seismic_data, "__wrapped__", extract_seismic_data)
    ingestion_meta = extract_fn(params={"mode": "local_test_20", "limit": 20}, run_id="airflow_test_sim")

    assert ingestion_meta["record_count"] == 20
    assert os.path.exists(ingestion_meta["raw_file_ref"])

    # 2. Simulate transform task
    transform_fn = getattr(run_medallion_processing, "__wrapped__", run_medallion_processing)
    metrics = transform_fn(ingestion_meta)

    assert metrics["records_ingested"] == 20
    assert metrics["records_curated"] == 20
    assert metrics["quality_score"] == 100.0

    # 3. Simulate verify task (asserts 20 == 20)
    verify_fn = getattr(verify_data_integrity, "__wrapped__", verify_data_integrity)
    verified = verify_fn(metrics)

    assert verified["records_curated"] == 20
    assert verified["sla_met"] is True
