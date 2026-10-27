"""
Unit Tests for Task 5: OpenMetadata Data Catalog, Lineage, and Quality Suite
Verifies:
1. Catalog schemas for all 4 Medallion tables (raw, staging, curated, diagnostics).
2. End-to-end data lineage graph from Raw to Curated & Diagnostics.
3. Column-level lineage mappings.
4. OpenMetadata data quality test definitions (20 rows, magnitude range, depth positive).
5. Standalone metadata bundle export and YAML configuration.
"""
import os
import json
import pytest
from openmetadata.lineage_and_catalog import SismoWatchOpenMetadataCatalog

BUNDLE_FILE = os.path.join(os.path.dirname(__file__), "..", "openmetadata", "openmetadata_bundle.json")
CONFIG_YAML = os.path.join(os.path.dirname(__file__), "..", "openmetadata", "openmetadata_ingestion_config.yaml")

def test_yaml_config_exists():
    """Verify OpenMetadata ingestion YAML specification exists."""
    assert os.path.exists(CONFIG_YAML), f"Config file not found at {CONFIG_YAML}"

def test_catalog_defines_all_four_medallion_tables():
    """Verify that all 4 Medallion layers are defined in the catalog."""
    tables = SismoWatchOpenMetadataCatalog.get_table_definitions()
    assert len(tables) == 4

    table_names = [t["name"] for t in tables]
    assert "seismic_events_raw" in table_names
    assert "seismic_events" in table_names
    assert "sensor_anomalies" in table_names

    # Check curated table schema
    curated_table = next(t for t in tables if "curated" in t["databaseSchema"])
    assert curated_table["tableType"] == "Regular"
    curated_col_names = [c["name"] for c in curated_table["columns"]]
    expected_cols = {"event_id", "event_time", "latitude", "longitude", "depth", "magnitude", "place", "status", "ingested_at", "updated_at"}
    assert set(curated_col_names) == expected_cols

def test_lineage_graph_end_to_end_topology():
    """
    Verify complete Data Lineage graph:
    raw -> staging -> curated & diagnostics
    """
    lineage = SismoWatchOpenMetadataCatalog.get_lineage_graph()
    
    assert "nodes" in lineage
    assert "edges" in lineage
    assert len(lineage["nodes"]) == 4
    assert len(lineage["edges"]) == 3

    # Check edge connections
    edge_pairs = [(e["fromEntity"], e["toEntity"]) for e in lineage["edges"]]
    
    raw_fqn = f"{SismoWatchOpenMetadataCatalog.SERVICE_NAME}.{SismoWatchOpenMetadataCatalog.DATABASE_NAME}.raw.seismic_events_raw"
    staging_fqn = f"{SismoWatchOpenMetadataCatalog.SERVICE_NAME}.{SismoWatchOpenMetadataCatalog.DATABASE_NAME}.staging.seismic_events"
    curated_fqn = f"{SismoWatchOpenMetadataCatalog.SERVICE_NAME}.{SismoWatchOpenMetadataCatalog.DATABASE_NAME}.curated.seismic_events"
    diagnostics_fqn = f"{SismoWatchOpenMetadataCatalog.SERVICE_NAME}.{SismoWatchOpenMetadataCatalog.DATABASE_NAME}.diagnostics.sensor_anomalies"

    assert (raw_fqn, staging_fqn) in edge_pairs
    assert (staging_fqn, curated_fqn) in edge_pairs
    assert (staging_fqn, diagnostics_fqn) in edge_pairs

def test_column_level_lineage():
    """Verify column-level lineage tracking."""
    lineage = SismoWatchOpenMetadataCatalog.get_lineage_graph()
    col_lineage = lineage.get("columnLineage", [])
    assert len(col_lineage) >= 5

    # Verify event_id derivation
    from_cols = [c["from"] for c in col_lineage]
    to_cols = [c["to"] for c in col_lineage]
    assert any("source_id" in f and "event_id" in t for f, t in zip(from_cols, to_cols))
    assert any("magnitude" in f and "magnitude" in t for f, t in zip(from_cols, to_cols))

def test_openmetadata_data_quality_test_suite():
    """Verify Data Quality tests enforcing the 20-event rule and geophysical limits."""
    dq = SismoWatchOpenMetadataCatalog.get_data_quality_test_suite()
    assert dq["testSuiteName"] == "SismoWatch_Curated_Quality_Suite"
    tests = dq["tests"]

    # 1. Row count = 20
    row_count_test = next(t for t in tests if t["testDefinition"] == "tableRowCountToEqual")
    assert row_count_test["parameterValues"][0]["value"] == "20"

    # 2. Magnitude range [-1.0, 10.0]
    mag_test = next(t for t in tests if t.get("columnName") == "magnitude")
    assert mag_test["testDefinition"] == "columnValuesToBeBetween"

    # 3. Depth >= 0.0
    depth_test = next(t for t in tests if t.get("columnName") == "depth")
    assert depth_test["testDefinition"] == "columnValuesToBeGreaterThanOrEqualTo"

def test_metadata_bundle_file_export():
    """Verify that export_bundle creates a valid, readable JSON file."""
    exported_path = SismoWatchOpenMetadataCatalog.export_bundle(BUNDLE_FILE)
    assert os.path.exists(exported_path)

    with open(exported_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata_version"] == "1.3.0"
    assert len(data["tables"]) == 4
    assert len(data["lineage"]["edges"]) == 3
