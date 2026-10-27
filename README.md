# SismoWatch 🌍⚡
### Advanced Seismic Event Monitoring Platform & AI Intelligence Engine

[![Architecture: Medallion](https://img.shields.io/badge/Architecture-Medallion-blue.svg)](ARQUITECTURA.md)
[![Orchestration: Airflow](https://img.shields.io/badge/Orchestrator-Apache%20Airflow%202.8-orange.svg)](https://airflow.apache.org/)
[![Engine: PySpark](https://img.shields.io/badge/Processing-Apache%20Spark-red.svg)](https://spark.apache.org/)
[![Database: PostgreSQL 16](https://img.shields.io/badge/Database-PostgreSQL%2016-blue.svg)](https://www.postgresql.org/)
[![Real-Time: SSE](https://img.shields.io/badge/Streaming-Server--Sent%20Events-green.svg)](#real-time-serving)
[![Security: Least Privilege](https://img.shields.io/badge/Security-RBAC%20%7C%20JWT-brightgreen.svg)](#security-in-depth)

---

## 1. Project Overview & Business Epics

**SismoWatch** is an enterprise data engineering and AI automation platform built to monitor, process, and analyze real-time seismic events worldwide with special focus on tectonic monitoring (USGS / Colombian Geological Service - SGC data).

### Core Capabilities:
1. **Medallion Architecture (Raw $\rightarrow$ Staging $\rightarrow$ Curated):** Pure WORM append-only raw storage, strict structural normalization in staging, and high-performance analytical storage in curated PostgreSQL tables.
2. **Audited Lateral Quarantine (Dead-Letter Store):** Failed records are routed laterally to `quarantine.rejected_events` preserving the raw payload, violated rule code, and pipeline execution ID for reprocessing.
3. **Idempotent UPSERT & Backfill:** Guaranteed idempotency on `event_id`. Historical backfill of 30 days updates revised magnitudes and coordinates with zero duplicate records.
4. **Deterministic AI Agent:** The AI agent operates **strictly over the `curated` schema** via a read-only database user. Statistical calculations are computed deterministically in code/SQL and cross-validated against model outputs to mitigate hallucinations.
5. **Real-Time Streaming without Polling:** Database-driven `LISTEN / NOTIFY` events stream lightweight update notifications (`< 100 bytes`) to connected clients via Server-Sent Events (SSE) with `Last-Event-ID` cursor recovery.

---

## 2. System Architecture

For a detailed technical breakdown, trade-off defenses, and data models, please refer to [ARQUITECTURA.md](ARQUITECTURA.md).

```
                      +---------------------------------------+
                      |       USGS / SGC Seismic API          |
                      +---------------------------------------+
                                          |
                              [Airflow Ingestion DAG]
                                          v
+---------------------------------------------------------------------------------+
| RAW LAYER (Bronze)                                                              |
| Filesystem: /data/lakehouse/raw/YYYY/MM/DD/*.json (Append-only)                 |
| PostgreSQL: raw.seismic_events_raw                                              |
+---------------------------------------------------------------------------------+
                                          |
                              [Stage 1: Schema & Typing]
                                   /             \
                             (Failed)          (Passed)
                                 /                 \
                                v                   v
          +-----------------------------+     +-----------------------------------+
          | LATERAL QUARANTINE          |     | STAGING LAYER (Silver)            |
          | quarantine.rejected_events  |     | Filesystem: /staging/*.parquet    |
          | (Payload, Rule, Run ID)     |     | PostgreSQL: staging.seismic_events|
          +-----------------------------+     +-----------------------------------+
                                 ^                  |
                             (Failed)     [Stage 2: Domain Rules]
                                 \                  |
                                  \------------ (Passed)
                                                    v
                                      +-------------------------------------------+
                                      | CURATED LAYER (Gold)                      |
                                      | PostgreSQL: curated.seismic_events        |
                                      | Atomic UPSERT ON CONFLICT (event_id)      |
                                      +-------------------------------------------+
                                                    |
                                      [Trigger: LISTEN/NOTIFY]
                                                    v
                                      +-------------------------------------------+
                                      | FASTAPI CONSUMPTION & SSE STREAM          |
                                      | (User Role: app_curated_reader)           |
                                      +-------------------------------------------+
                                            /                       \
                                           v                         v
                           +----------------------+   +---------------------------+
                           | Dashboard & Map UI   |   | Local AI Agent            |
                           | Real-time alerts/SSE |   | Deterministic Guardrail   |
                           +----------------------+   +---------------------------+
```

---

## 3. Data Quality & SLA Framework

* **SLA Target:** Internal processing latency $\le 5$ minutes:
  $$\text{Processing Latency} = \text{curated\_at} - \text{ingested\_at}$$
* **Data Quality Score ($Q_s$):**
  $$Q_s = \left(\frac{\text{Records Curated}}{\text{Records Ingested}}\right) \times 100\%$$
* **Domain Validation Rules:**
  * Magnitude: $-1.0 \le \text{mag} \le 10.0$
  * Depth: $\text{depth} \ge 0.0\text{ km}$
  * Latitude: $-90.0 \le \text{lat} \le 90.0$
  * Longitude: $-180.0 \le \text{lon} \le 180.0$

---

## 4. Security in Depth

1. **Principle of Least Privilege:**
   * PostgreSQL role `app_curated_reader` has read-only access (`SELECT`) exclusively on `curated` schema.
   * Access is explicitly denied on `raw`, `staging`, and `quarantine`.
2. **Zero Hardcoded Secrets:**
   * All credentials and keys are loaded through `.env` and external environment variables.
3. **Prompt Injection Mitigation:**
   * User prompts to the AI Agent are sanitized and structured as parameterized tool arguments; the agent cannot execute ungrounded arbitrary SQL statements.

---

## 5. Quickstart & Deployment

### 5.1 Prerequisites
* Docker Engine 24+ & Docker Compose v2+
* Python 3.11+
* Git

### 5.2 Environment Setup
1. Clone the repository and prepare `.env`:
   ```bash
   cp .env.example .env
   ```
2. Build and start services via Docker Compose:
   ```bash
   docker compose up -d --build
   ```
3. Verify running containers:
   ```bash
   docker compose ps
   ```

### 5.3 Service Endpoints
* **Web Application & Dashboard:** [http://localhost:8000](http://localhost:8000)
* **API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Airflow Web UI:** [http://localhost:8080](http://localhost:8080) (Default: `admin` / `admin`)
* **PostgreSQL Database:** `localhost:5432` (`sismowatch_db`)

---

## 6. Test Suite Execution

Run all automated unit, transformation, schema, and API tests with a single command:
```bash
pytest tests/ -v
```

---

## 7. Project Structure

```text
SismoWatch-PruebaDesempe-o/
├── ARQUITECTURA.md            # Comprehensive architecture specification & trade-offs
├── README.md                  # Project documentation in English
├── docker-compose.yml         # Container orchestration (Airflow, Postgres, WebApp)
├── .env.example               # Template for environment configuration
├── .gitignore                 # Version control exclusion rules
├── dags/                      # Airflow DAGs (TaskFlow API, backfills, alerts)
├── spark/                     # PySpark transformation jobs and schemas
│   ├── jobs/                  # Modular PySpark medallion jobs
│   └── schemas/               # PySpark StructType schemas
├── quality/                   # Data quality verification rules & quarantine routing
├── agent/                     # Local AI Agent, versioned prompts, and guardrails
│   ├── prompts/               # Versioned system & user prompts
│   └── tools/                 # Deterministic query and telemetry tools
├── webapp/                    # Full-stack consumption platform
│   ├── backend/               # FastAPI backend (REST, SSE, JWT security)
│   ├── frontend/              # Interactive dashboard, maps, charts, chat
│   └── Dockerfile             # Container definition for web app
├── sql/                       # DDL initialization scripts (schemas, roles, triggers)
│   └── init.sql               # PostgreSQL multi-schema setup & LISTEN/NOTIFY
├── data/                      # Lakehouse filesystem volumes
│   └── lakehouse/             # Raw, staging, curated, quarantine storage
└── tests/                     # Pytest automated test suite
```
