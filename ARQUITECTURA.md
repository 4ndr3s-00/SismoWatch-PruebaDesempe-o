# ARQUITECTURA.md - SismoWatch

## 1. Executive Summary & Purpose

**SismoWatch** is a streamlined seismic event monitoring and intelligence platform designed under the **Medallion Architecture (Raw $\rightarrow$ Staging $\rightarrow$ Curated)** accompanied by an operational **Sensor Diagnostics & Telemetry Module**.

The system automates the ingestion of seismic data from geological services (USGS / SGC), orchestrates data transformations and validation rules using **Apache Airflow** and **Apache Spark (PySpark)**, enforces a pragmatic data quality framework without over-engineering, immediately prunes all useless API fields in the Silver transition, and provides a real-time reactive consumption layer powered by a **Local AI Agent** with deterministic anti-hallucination guardrails.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph INGESTION["1. Ingestion Layer"]
        API["Seismic Data Source (USGS / SGC API)"]
        AF_INGEST["Airflow DAG: Ingestion Task\n(Parameterized & Idempotent Backfill)"]
        API -->|Fetch 20 Test Events / Historical| AF_INGEST
    end

    subgraph STORAGE_RAW["2. Raw Layer (Bronze)"]
        RAW_FILES["Lakehouse Filesystem\n/data/lakehouse/raw/YYYY/MM/DD/*.json\n(WORM: Write Once, Read Many)"]
        RAW_DB["PostgreSQL: raw.seismic_events_raw\n(Audit trail & raw payload)"]
        AF_INGEST -->|Append-Only| RAW_FILES
        AF_INGEST -->|Audit Log| RAW_DB
    end

    subgraph SPARK_TRANSFORMATION["3. Transformation & Validation Engine (PySpark)"]
        SPARK_JOB["PySpark Job: Seismic Medallion Pipeline\n(Micro-batch execution)"]
        RAW_FILES --> SPARK_JOB
        
        subgraph QUALITY_GATEWAYS["Data Quality Framework"]
            QG1{"Stage 1 Validation:\nSchema & Typing\n(JSON, ISO-8601, required fields)"}
            QG2{"Stage 2 Validation:\nDomain & Business Rules\n(Mag [-1,10], Depth >= 0, Coordinates)"}
        end

        SPARK_JOB --> QG1
        QG1 -->|Pass: Keep only 7 core fields| STAGING_LAYER["Staging Layer (Silver)\nParquet Files + staging.seismic_events\n(All useless API metadata pruned)"]
        QG1 -->|Anomaly Detected| DIAGNOSTICS_MODULE
        
        STAGING_LAYER --> QG2
        QG2 -->|Pass| CURATED_STAGING["staging.temp_curated_events"]
        QG2 -->|Anomaly Detected| DIAGNOSTICS_MODULE
    end

    subgraph DIAGNOSTICS_MODULE["Operator View: Sensor Diagnostics & Telemetry"]
        DIAGNOSTICS_TABLE["PostgreSQL: diagnostics.sensor_anomalies\n- diagnostic_id\n- sensor_id\n- raw_reading (JSONB)\n- issue_code & diagnostic_message\n- detected_at & sensor_status (NEEDS_CHECK/RESOLVED)\n(Provides real-time visibility into sensor health)"]
    end

    subgraph CURATED_LAYER["4. Curated Layer (Gold)"]
        UPSERT_OP["Atomic UPSERT via JDBC/SQL:\nINSERT ... ON CONFLICT (event_id)\nDO UPDATE SET ...\nWHERE (... IS DISTINCT FROM ...)"]
        CURATED_STAGING --> UPSERT_OP
        CURATED_DB[("PostgreSQL: curated.seismic_events\n- event_id (PK)\n- event_time\n- latitude, longitude, depth\n- magnitude, place, status\n- ingested_at, updated_at")]
        UPSERT_OP --> CURATED_DB
        NOTIFY_TRIGGER["Postgres Trigger / Notify Step:\nNOTIFY curated_event_channel,\n'{\"event_id\":\"...\", \"action\":\"UPSERT\"}'"]
        CURATED_DB --> NOTIFY_TRIGGER
    end

    subgraph CONSUMPTION_PLATFORM["5. Real-Time Consumption & Serving"]
        API_BACKEND["FastAPI Backend Service\n(Role: app_curated_reader)\n- LISTEN curated_event_channel\n- Catch-up cursor via Last-Event-ID"]
        NOTIFY_TRIGGER -->|Instant Push| API_BACKEND
        
        SSE_STREAM["Server-Sent Events (SSE) Stream\n/api/events/live"]
        API_BACKEND --> SSE_STREAM
        
        WEB_UI["Interactive Dashboard Web App\n- Real-time Leaflet Map\n- KPIs & Seismic Charts\n- CSV / PDF Export\n- Audio / Text Chat UI"]
        SSE_STREAM -->|Reactive Updates| WEB_UI
    end

    subgraph AI_AGENT["6. Local AI Agent & Anti-Hallucination Guardrail"]
        DETERMINISTIC_CALC["Deterministic SQL Metric Calculator\n(Exact counts, min/max, averages)"]
        CURATED_DB -->|Read-Only (curated schema only)| DETERMINISTIC_CALC
        
        LOCAL_LLM["Local AI Agent\n(Strict grounding, citations by event_id)"]
        DETERMINISTIC_CALC -->|Pre-calculated Context| LOCAL_LLM
        
        GUARDRAIL{"Post-Generation Guardrail:\nValidate numbers & counts in LLM text\nagainst deterministic SQL metrics"}
        LOCAL_LLM --> GUARDRAIL
        GUARDRAIL -->|Passed / Corrected| WEB_UI
    end
```

---

## 3. Data Model & Layer Specifications

### 3.1 Raw Layer (Bronze)
* **Storage Location:** `/data/lakehouse/raw/year=YYYY/month=MM/day=DD/` (JSON raw records) and PostgreSQL table `raw.seismic_events_raw`.
* **Semantics:** Inmutable, append-only, Write Once Read Many (WORM). No transformations or schema coercions are applied.
* **Fields:**
  * `raw_id`: BigSerial Primary Key.
  * `source_id`: External ID from source (e.g. USGS `us7000xxxx`).
  * `payload`: Full original JSONB payload.
  * `ingested_at`: UTC timestamp of extraction.
  * `run_id`: Airflow DAG execution UUID.

### 3.2 Staging Layer (Silver)
* **Storage Location:** `/data/lakehouse/staging/` (Parquet) and table `staging.seismic_events`.
* **Pragmatic Pruning of Useless Fields:**
  * Raw APIs supply dozens of bloat attributes (`felt`, `cdi`, `mmi`, `dmin`, `rms`, `nst`, `sources`, etc.).
  * In the transition to Staging, **all unnecessary fields are eliminated immediately**. We only store the 7 essential business attributes:
    `event_id`, `event_time`, `latitude`, `longitude`, `depth`, `magnitude`, `place`, `status`.
* **Transformations & Gateway 1 Validation:**
  * Structural schema verification (all 7 core keys present and valid).
  * Data type coercion (numeric casting, ISO-8601 timestamp parsing).
  * Records with sensor read errors are routed to the **Sensor Diagnostics & Telemetry** module with code `ERR_SENSOR_PAYLOAD_CORRUPT`.

### 3.3 Curated Layer (Gold)
* **Storage Location:** PostgreSQL table `curated.seismic_events` (and analytical Parquet snapshots).
* **Gateway 2 Validation (Business & Domain Rules):**
  * $\text{magnitude} \in [-1.0, 10.0]$
  * $\text{depth} \ge 0.0 \text{ km}$
  * $\text{latitude} \in [-90.0, 90.0]$
  * $\text{longitude} \in [-180.0, 180.0]$
  * `place` is not empty.
  * Records failing business validation are diverted to `quarantine.rejected_events` with code `ERR_DOMAIN_RULE_VIOLATION`.
* **Schema Definition:**
  ```sql
  CREATE TABLE curated.seismic_events (
      event_id VARCHAR(64) PRIMARY KEY,
      event_time TIMESTAMPTZ NOT NULL,
      latitude NUMERIC(8, 4) NOT NULL,
      longitude NUMERIC(8, 4) NOT NULL,
      depth NUMERIC(8, 2) NOT NULL,
      magnitude NUMERIC(4, 2) NOT NULL,
      place VARCHAR(255) NOT NULL,
      status VARCHAR(32) NOT NULL DEFAULT 'reviewed',
      ingested_at TIMESTAMPTZ NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );
  ```

### 3.4 Operational Feature: Sensor Diagnostics & Telemetry (Operator View)
Rather than a passive quarantine, this serves as an active **operational monitoring feature** for the technical team to observe sensor health, detect physical sensor anomalies, and diagnose calibration drifts in real time.
* **Schema:**
  ```sql
  CREATE TABLE diagnostics.sensor_anomalies (
      diagnostic_id BIGSERIAL PRIMARY KEY,
      sensor_id VARCHAR(64),
      raw_reading JSONB,
      issue_code VARCHAR(64) NOT NULL,
      diagnostic_message TEXT NOT NULL,
      pipeline_stage VARCHAR(32) NOT NULL,
      run_id VARCHAR(64) NOT NULL,
      detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      sensor_status VARCHAR(32) NOT NULL DEFAULT 'NEEDS_CHECK' -- 'NEEDS_CHECK', 'RESOLVED'
  );
  ```

---

## 4. Architectural Decisions & Trade-Off Defenses

### 4.1 Medallion vs. Lambda Architecture
* **Decision:** We unified the processing topology under the Medallion Architecture rather than deploying a redundant Lambda speed layer.
* **Defense & Trade-off:**
  * In a traditional Lambda architecture, developers must maintain duplicate transformation logic: one codebase for batch (Spark/Hadoop) and another for streaming (Flink/Storm/Kafka).
  * By orchestrating a streamlined PySpark job with Airflow and serving data directly from a tuned PostgreSQL relational layer, we eliminate codebase duplication, conserve infrastructure resources, and ensure 100% consistent business logic across all stages.

### 4.2 Realistic SLA Definition & Freshness Measurement
* **Decision:** Explicit processing SLA of **$\le 5$ minutes**, defined strictly as:
  $$\text{Processing Latency} = \text{curated\_at} - \text{ingested\_at}$$
* **Defense & Trade-off:**
  * External seismic reporting stations exhibit varying ingestion delays outside our control. Measuring internal processing latency isolates pipeline performance.
  * Airflow scheduler cycle plus JVM/SparkSession initialization realistically requires 30–60 seconds. A 5-minute SLA is rigorous, reproducible in local/production environments, and continuously measured in `metrics_execution`.

### 4.3 Database Partitioning vs. Single Curated Table
* **Decision:** Partition raw/staging file storage by date (`year/month/day`), but keep PostgreSQL `curated.seismic_events` as an **unpartitioned table with a B-Tree Primary Key on `event_id`** and composite indices on `(event_time, magnitude)`.
* **Defense & Trade-off:**
  * PostgreSQL requires unique constraints on partitioned tables to contain all partition keys (`event_date, event_id`). Because seismic events can be revised across midnight UTC or updated without date changes, partitioning the database table introduces unnecessary complexity and breaks simple `ON CONFLICT (event_id)` upserts.

### 4.4 Real-Time Streaming: LISTEN/NOTIFY + SSE with Reconnection Catch-Up
* **Decision:** PostgreSQL `LISTEN / NOTIFY` combined with FastAPI Server-Sent Events (SSE) and `Last-Event-ID` cursor.
* **Defense & Trade-off:**
  * `NOTIFY` payloads are capped at 8,000 bytes. We send only lightweight change descriptors: `{"event_id": "us7000abc", "action": "UPSERT"}`.
  * To prevent event loss upon network drops or server restarts, the client sends `Last-Event-ID` (or `last_updated_at`). The backend queries `curated.seismic_events WHERE updated_at > :last_updated_at` before piping live push notifications.

### 4.5 AI Agent Anti-Hallucination Guardrails & Least-Privilege Security
* **Decision:** The Local AI Agent connects **strictly to the `curated` schema** via a read-only database user (`app_curated_reader`).
* **Defense & Trade-off:**
  * Large Language Models can hallucinate mathematical aggregates or invent nonexistent seismic events.
  * We enforce a dual-stage architecture:
    1. A deterministic SQL engine computes ground-truth statistics (total count, max magnitude, shallowest depth, regional distribution).
    2. The LLM receives pre-calculated metrics in its context, is mandated to cite verifiable `event_id`s, and a programmatic post-validator checks that numbers stated in the text match the database numbers. If a discrepancy occurs, the output is flagged or replaced with deterministic values.

---

## 5. Production Evolution Strategy

If migrating this architecture to high-throughput cloud production:
1. **Object Storage:** Replace local `/data/lakehouse/` with AWS S3 / Google Cloud Storage, leveraging Delta Lake or Apache Iceberg for ACID transactions on Parquet.
2. **Event-Driven Spark:** Transition Airflow batch triggers to Spark Structured Streaming on Kubernetes (EKS/GKE) with RocksDB state storage for sub-minute latency.
3. **Message Broker:** Introduce Apache Kafka or AWS Kinesis upstream of Raw storage to buffer burst events during major earthquake swarms.
4. **Metadata & Governance:** Integrate OpenMetadata automated lineage collectors to track schema drifts and dataset freshness in enterprise dashboards.
