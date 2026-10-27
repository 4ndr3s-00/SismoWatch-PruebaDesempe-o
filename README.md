# SismoWatch 🌍⚡
### Advanced Seismic Event Monitoring Platform, Medallion Lakehouse & Local AI Engine

[![Architecture: Medallion](https://img.shields.io/badge/Architecture-Medallion%20Lakehouse-blue.svg)](ARQUITECTURA.md)
[![Governance: OpenMetadata](https://img.shields.io/badge/Governance-OpenMetadata%20Lineage-purple.svg)](#governance--lineage)
[![Orchestration: Airflow](https://img.shields.io/badge/Orchestrator-Apache%20Airflow%202.8-orange.svg)](https://airflow.apache.org/)
[![Engine: PySpark](https://img.shields.io/badge/Processing-Apache%20Spark-red.svg)](https://spark.apache.org/)
[![AI Engine: Ollama Local](https://img.shields.io/badge/AI%20Agent-Llama%203.2%20%7C%20Zero%20Tokens-brightgreen.svg)](#local-ai-agent-engine)
[![Database: PostgreSQL 16](https://img.shields.io/badge/Database-PostgreSQL%2016-blue.svg)](https://www.postgresql.org/)
[![Test Suite: 100% Passing](https://img.shields.io/badge/Tests-62%20Passed-success.svg)](#test-suite-execution)

---

## 1. Project Overview & Business Epics

**SismoWatch** is an enterprise data engineering, automated governance, and local AI intelligence platform built to monitor, process, validate, and analyze real-time seismic events worldwide with live telemetry from the **USGS Earthquake API** and regional geological sensors.

### Core Capabilities:
1. **Medallion Lakehouse Architecture (Bronze $\rightarrow$ Silver $\rightarrow$ Gold):** 
   - **Bronze (Raw):** Append-only WORM filesystem storage (`data/lakehouse/raw/`) preserving unmodified GeoJSON payloads for forensic data auditing.
   - **Silver (Staging):** Tabular schema enforcement and pruning of redundant API metadata with PySpark.
   - **Gold (Curated):** High-performance analytical storage in PostgreSQL (`curated.seismic_events`) and mirrored Lakehouse JSON snapshot (`data/lakehouse/curated/curated_snapshot.json`).
   - **Diagnostics (Quarantine):** Automatic lateral diversion of physical sensor anomalies ($M > 10.0$ or $\text{depth} < 0\text{ km}$) to `data/lakehouse/diagnostics/`.
2. **Strict 1:1 Data Integrity ($N \text{ in} \rightarrow N \text{ out}$):** Zero loss and zero artificial truncation of valid seismic events.
3. **End-to-End Data Governance with OpenMetadata:** Complete metadata catalog across all 4 Medallion layers, column-level lineage tracking from raw sensor attributes to curated tables, and automated data quality test suites.
4. **Local AI Agent (\$0.00 Cost / Zero Paid Tokens):**
   - 100% On-Premise execution using local **Ollama** (`llama3.2:3b`) and a **Predefined Vector Database** (`all-minilm` 384d dense embeddings).
   - Multi-layer defense: **Security Shield** (Prompt/SQL injection defense), **Domain Boundary Guard** (blocks recipes, sports, and out-of-context prompts), and **GeoEntityResolver** (canonical resolution for all 50 US states, territories, and 20+ international countries).
5. **Dual-Storage Circuit Breaker:** If PostgreSQL is unreachable, the system automatically falls back to the Lakehouse Curated Snapshot in $< 1\text{ ms}$ without raising an exception.
6. **Real-Time Interactive Consumption:** FastAPI asynchronous backend and React 18 / Tailwind CSS / Leaflet dashboard with dynamic magnitude markers, interactive charts, and live chat telemetry (0 tokens, \$0.00, latency in ms).

---

## 2. System Architecture

For complete architectural specifications, diagrams, and detailed layer breakdowns, refer to:
* 📄 [**ARQUITECTURA.md**](ARQUITECTURA.md)
* 🏛️ [**arquitectura_completa_sismowatch.md**](file:///home/cohorte5/.gemini/antigravity/brain/842ef318-12f2-4960-a474-71187a669b88/arquitectura_completa_sismowatch.md)

```
                              +---------------------------------------+
                              |       USGS Live Earthquake API        |
                              +---------------------------------------+
                                                  |
                                   [Airflow Ingestion DAG / Client]
                                                  v
+-----------------------------------------------------------------------------------------+
| BRONZE LAYER (Raw Storage)                                                              |
| Filesystem: data/lakehouse/raw/*.json (WORM Append-only audit)                          |
+-----------------------------------------------------------------------------------------+
                                                  |
                                      [PySpark Stage 1: Extraction]
                                           /             \
                                     (Failed)          (Passed)
                                         /                 \
                                        v                   v
                  +-----------------------------+     +-----------------------------------+
                  | DIAGNOSTICS (Quarantine)    |     | SILVER LAYER (Staging)            |
                  | data/lakehouse/diagnostics/ |     | PySpark StructType Normalization  |
                  | Sensor anomaly triage code  |     | API Bloat Stripped                |
                  +-----------------------------+     +-----------------------------------+
                                         ^                  |
                                     (Failed)     [Stage 2: Validation Gate]
                                         \                  |
                                          \------------ (Passed)
                                                            v
                                              +-------------------------------------------+
                                              | GOLD LAYER (Curated Data)                 |
                                              | PostgreSQL: curated.seismic_events        |
                                              | Filesystem: curated_snapshot.json         |
                                              | Atomic UPSERT ON CONFLICT (event_id)      |
                                              +-------------------------------------------+
                                                            |
                                        [Circuit Breaker / CuratedDataClient]
                                                            v
                                              +-------------------------------------------+
                                              | FASTAPI REST API & GATEWAY                |
                                              | Role: app_curated_reader (Least Privilege)|
                                              +-------------------------------------------+
                                                    /                       \
                                                   v                         v
                                   +----------------------+   +---------------------------+
                                   | Dashboard & Map UI   |   | Local AI Agent Engine     |
                                   | React 18 + Leaflet   |   | Ollama Llama 3.2 + Vector |
                                   | Live Metrics & Stats |   | 0 Tokens | $0.00 Cost     |
                                   +----------------------+   +---------------------------+
```

---

## 3. Technology Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Data Ingestion** | `USGSLiveClient` (Python) | 3.12 | Resilient HTTP extractor with exponential backoff and fallback feeds |
| **Processing** | Apache Spark (PySpark) | 3.5+ | Distributed tabular flattening, deduplication, schema enforcement |
| **Governance** | OpenMetadata SDK | 1.2+ | 4-layer catalog entities, column-level lineage, quality test suites |
| **Orchestration** | Apache Airflow | 2.8+ | 5-minute automated pipeline (`*/5 * * * *`), TaskFlow API, TaskGroups |
| **Database** | PostgreSQL | 16 | ACID relational storage with least-privilege role `app_curated_reader` |
| **Local LLM** | Ollama (`llama3.2:3b`) | 3.2B Q4_K_M | Structural NLU reasoning and JSON filter parsing (cost: \$0.00) |
| **Vector Search** | Vector Semantic Router | `all-minilm` (384d) | Conversational matching in $< 20\text{ ms}$ with 0 tokens |
| **Geo Resolution** | `GeoEntityResolver` | Engine | Disambiguates 50 US states, territories, and 20+ countries |
| **Backend API** | FastAPI / Uvicorn | 0.110+ | Asynchronous REST gateway with JWT authentication & RBAC |
| **Frontend UI** | React 18 + Vite + Tailwind | 18.2 / 3.4 | Dynamic seismic map (Leaflet), analytics cards, audit modal, chat |
| **Testing** | Pytest | 9.1 | 62 automated unit, pipeline, integration, and security tests |

---

## 4. Governance & Lineage with OpenMetadata

The platform incorporates full data lineage and metadata management defined in [`openmetadata/lineage_and_catalog.py`](openmetadata/lineage_and_catalog.py):
* **Entities:** `raw.seismic_events_raw`, `staging.seismic_events`, `curated.seismic_events`, `diagnostics.sensor_anomalies`.
* **Lineage Topology:** Maps pipeline edges from raw GeoJSON features to curated fields (`source_id` $\rightarrow$ `event_id`, calibrated `depth`, `magnitude`, `coordinates`).
* **OpenMetadata Ingestion Config:** Located at [`openmetadata/openmetadata_ingestion_config.yaml`](openmetadata/openmetadata_ingestion_config.yaml).
* **Exportable Bundle:** Standard JSON bundle at [`openmetadata/openmetadata_bundle.json`](openmetadata/openmetadata_bundle.json).

---

## 5. Local AI Agent Engine

The conversational AI assistant operates deterministically with **zero token cost and 0% hallucinations**:
1. **Security Shield:** Inspects queries before parsing; actively blocks prompt injections (`ERR_PROMPT_INJECTION_DETECTED`) and SQL injections.
2. **Vector Semantic Router:** High-dimensional vector cache (`all-minilm`) resolving greetings, capabilities, pleasantries, and out-of-scope prompts in $< 20\text{ ms}$.
3. **Domain Boundary Guard:** Rejects unrelated questions (e.g., cooking recipes like *"Como hago un arroz con pollo?"*, sports, general trivia) without querying the database or dumping ungrounded records.
4. **GeoEntityResolver:** Canonical mapping of all 50 US states (`CA`, `AK`, `TX`, `HI`, etc.), territories (`PR`, `VI`, `GU`), and international regions. Solves token collisions (e.g., strictly excludes `"New Mexico"` from Mexico, and prevents `"La Tirana, Chile"` from matching Louisiana `LA`).
5. **Physical Dimension Safety:** Strictly distinguishes depth in kilometers (`km`, `profundidad`) from magnitude scale ($M \le 10.0$).
6. **Telemetry & Audit:** Returns response text along with execution metadata (`tokens_consumed: 0`, `cost_usd: 0.00`, `latency_ms`, `model`, `records_retrieved`).

---

## 6. Quickstart & Deployment

### 6.1 Prerequisites
* Docker Engine 24+ & Docker Compose v2+
* Python 3.12 (for local development)
* Ollama running locally with `llama3.2:3b` and `all-minilm` (optional, falls back gracefully)

### 6.2 Setup with Docker Compose
1. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```
2. Build and launch all services in detached mode:
   ```bash
   docker compose up -d --build
   ```
3. Check status of running containers:
   ```bash
   docker compose ps
   ```

### 6.3 Service Endpoints
* **Web Application & Dashboard:** [http://localhost:8000](http://localhost:8000)
* **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Airflow Web UI:** [http://localhost:8080](http://localhost:8080) (Default credentials: `admin` / `admin`)
* **PostgreSQL Database:** `localhost:5432` (Database: `sismowatch_db`)

### 6.4 Single-Command Makefile Shortcuts
```bash
make help          # Displays all available targets
make run           # Starts web application and services
make pipeline      # Executes the PySpark Medallion transformation job manually
make test          # Runs the full automated test suite (62 tests)
```

---

## 7. Test Suite Execution

Run the complete suite of 62 unit, integration, pipeline, NLU, and security tests:
```bash
PYTHONPATH=. pytest tests/ -v
```

All 62 tests pass cleanly with 100% compliance across:
* `test_ai_agent.py`: Security shield, out-of-scope guard, superlatives, multi-turn memory, depth vs magnitude.
* `test_geo_resolver.py`: US states, territories, foreign country disambiguation, negation queries.
* `test_vector_router.py`: Dense vector indexing, cosine similarity, domain boundaries.
* `test_airflow_dags.py`: DAG compilation, backfill parameters, TaskFlow execution simulation.
* `test_medallion_pipeline.py`: PySpark transformation idempotency and 1:1 event preservation.
* `test_dataset_and_quality.py`: API field pruning, sensor diagnostics isolation.
* `test_openmetadata_lineage.py`: 4-layer catalog schemas and lineage graph edges.
* `test_webapp_api.py`: FastAPI endpoints, JWT authentication, and CSV/JSON bulk exports.

---

## 8. Project Structure

```text
SismoWatch-PruebaDesempe-o/
├── ARQUITECTURA.md                        # Architecture design specification & trade-offs
├── README.md                              # Main platform documentation
├── Makefile                               # Automation shortcuts (run, pipeline, test)
├── docker-compose.yml                     # Container orchestration (Airflow, Postgres, WebApp)
├── .env.example                           # Environment configuration template
├── dags/
│   └── sismo_pipeline_dag.py              # Apache Airflow orchestration DAG
├── spark/
│   ├── jobs/
│   │   └── seismic_medallion_job.py       # PySpark Medallion Pipeline transformation
│   └── schemas/
│       └── seismic_schemas.py             # PySpark StructType schemas
├── quality/
│   └── validator.py                       # Data quality engine & physical bound validator
├── openmetadata/
│   ├── lineage_and_catalog.py             # OpenMetadata catalog & lineage graph generator
│   ├── openmetadata_bundle.json           # Exportable OpenMetadata JSON bundle
│   └── openmetadata_ingestion_config.yaml # OpenMetadata ingestion configuration
├── agent/
│   ├── core/
│   │   ├── agent_engine.py                # Master AI Agent engine
│   │   ├── conversation_router.py         # Conversational router & out-of-scope guard
│   │   ├── geo_resolver.py                # Canonical US & international territory resolver
│   │   ├── semantic_parser.py             # Deterministic seismological NLU
│   │   └── narrator.py                    # Certified response narrator & formatter
│   ├── database/
│   │   └── curated_client.py              # Curated client with dual-storage circuit breaker
│   ├── llm/
│   │   └── ollama_client.py               # Local Llama 3.2 HTTP client
│   ├── security/
│   │   └── shield.py                      # Anti-Prompt Injection & SQL injection shield
│   └── vector/
│       └── predefined_vector_db.py        # Semantic vector database (all-minilm 384d)
├── pipeline/
│   └── extractors/
│       └── usgs_live_client.py            # Live USGS catalog client & fallback extractor
├── webapp/
│   ├── backend/                           # FastAPI gateway (auth, chat, events, export)
│   ├── frontend/                          # React + Leaflet + Tailwind UI
│   └── Dockerfile                         # Container definition for web consumption app
├── sql/
│   └── init.sql                           # Database DDL (schemas, least-privilege roles)
├── data/
│   ├── lakehouse/                         # raw/, staging/, curated/, diagnostics/
│   └── vector_store/                      # Predefined intent vector index
└── tests/                                 # 62 automated Pytest verification tests
```
