"""
SismoWatch - PySpark Schemas for Medallion Architecture
Pragmatically extracts core seismic attributes and immediately discards API bloat.
"""
try:
    from pyspark.sql.types import (
        StructType, StructField, StringType, DoubleType,
        LongType, TimestampType, ArrayType
    )
except ImportError:
    # Allow schema inspection and unit tests in environments without full pyspark runtime
    StructType = None
    StructField = None
    StringType = None
    DoubleType = None
    LongType = None
    TimestampType = None
    ArrayType = None

# 1. Clean Core Business Schema (Curated & Staging)
# Strictly the 7 essential fields - all other raw API metadata is pruned.
CORE_COLUMNS = [
    "event_id",
    "event_time",
    "latitude",
    "longitude",
    "depth",
    "magnitude",
    "place",
    "status"
]

def get_spark_curated_schema():
    """Returns PySpark StructType for Curated / Staging table."""
    if StructType is None:
        raise ImportError("pyspark is not installed in the current environment")
        
    return StructType([
        StructField("event_id", StringType(), False),
        StructField("event_time", TimestampType(), False),
        StructField("latitude", DoubleType(), False),
        StructField("longitude", DoubleType(), False),
        StructField("depth", DoubleType(), False),
        StructField("magnitude", DoubleType(), False),
        StructField("place", StringType(), False),
        StructField("status", StringType(), False)
    ])

# 2. Raw Ingestion Expected Field Names
RAW_FEATURE_KEYS = ["id", "properties", "geometry"]
RAW_PROPERTY_KEYS = ["mag", "place", "time", "status"]
RAW_GEOMETRY_KEYS = ["coordinates"]
