# OpenAnomaly: Real-Time Anomaly Detection with Time Series Foundation Models

## 1. Vision

OpenAnomaly is a zero-shot anomaly detection system for **Prometheus-compatible TSDBs** (VictoriaMetrics, Thanos, Mimir, Cortex, etc.).

It leverages **Time Series Foundation Models (TSFMs)** from the HuggingFace ecosystem to perform inference without any prior training on your specific data.

### Key Tenets
1.  **Zero Training Required**: Uses pre-trained foundation models. No model fitting, no weight storage.
2.  **Real-Time Scoring**: Continuously queries the TSDB, runs inference, and writes results back.
3.  **TSDB Agnostic**: Speaks standard Prometheus Query API and Remote Write protocol.
4.  **Pluggable Models**: Any TSFM available on HuggingFace is a potential model.
5.  **Flexible Modes**: Forecast-only, Anomaly Detection, or both.

---

## 2. How It Works (The Loop)

OpenAnomaly operates in a continuous loop, similar to VMAnomaly:

```
┌──────────────────────────────────────────────────────────────────┐
│                        THE INFERENCE LOOP                        │
│                                                                  │
│  ┌─────────────────┐                                             │
│  │   1. SCHEDULER  │  (Celery Beat triggers job)                 │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │  2. FETCH DATA  │  (Prometheus Range Query -> Context Window) │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │ 3. RUN INFERENCE│  (TSFM predicts next N points)              │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │ 4. SCORE ANOMALY│  (Compare prediction vs. actual - Optional) │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │ 5. WRITE RESULTS│  (Remote Write: prediction, anomaly_score)  │
│  └─────────────────┘                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```
┌──────────────────────────────────────────────────────────────────┐
│                        THE INFERENCE LOOP                        │
│  (Existing loop components...)                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        THE TRAINING LOOP                         │
│                                                                  │
│  ┌─────────────────┐                                             │
│  │   1. SCHEDULER  │  (Celery Beat triggers job)                 │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │  2. FETCH DATA  │  (Long Range Query e.g. 30d)                │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │ 3. TRAIN/FIT    │  (Train model/Fit parameters)               │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │ 4. UPDATE CONFIG│  (Save new model ID/Artifact)               │
│  └─────────────────┘                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘


---

## 3. Architecture: Hexagonal (Ports & Adapters)

### Core Ports

| Port | Responsibility | Adapters |
| :--- | :--- | :--- |
| **`TSDBClient`** | Read (Query) and Write (Remote Write) to TSDB | `PrometheusAdapter` |
| **`ModelEngine`** | Run zero-shot forecast inference | Local or Remote adapters (see Section 4) |
| **`ConfigStore`** | Persist pipeline definitions | `YamlAdapter` (File), `MongoAdapter` (DB) |
| **`Scheduler`** | Trigger inference jobs on a schedule | `CeleryBeatAdapter` |

### Removed Ports (vs. Previous Design)
*   ~~`ArtifactStore`~~: No model weights to store (for pre-trained TSFMs). For trainable models, weights are managed by the Model Engine (Remote or Local).


---

## 4. Model Engine: Local & Remote

The `ModelEngine` Port supports two modes of operation:

### A. Local Model Adapters
Each TSFM requires its **dedicated library** and deep research on official documentation for capabilities and best practices.

**Implementation Pattern:**
```
adapters/models/
├── base.py              # Abstract ModelEngine interface
├── chronos/             # Amazon Chronos (uses `chronos-forecasting` lib)
│   ├── __init__.py
│   └── adapter.py       # ChronosAdapter - requires research on official guide
├── timesfm/             # Google TimesFM (uses `timesfm` lib)
│   └── adapter.py
└── ...                  # Each new model = new adapter package
```

### B. Remote Model Adapter
For models running on external infrastructure (e.g., dedicated GPU server, cloud endpoint).

**Interface Contract (HTTP/gRPC):**
```json
POST /predict
{
  "context": [1.2, 3.4, ...],
  "prediction_length": 12,
  "quantiles": [0.1, 0.5, 0.9]
}
Response:
{
  "forecast": [7.8, ...],
  "quantiles": {...}
}

POST /train (Optional)
{
  "data": [{"ds": "2024-01-01T00:00:00Z", "unique_id": "ts1", "y": 1.2}, ...],
  "parameters": {"epochs": 10}
}
Response:
{
  "model_id": "model_v2_123"
}
```


*Configuration*: `OA_MODEL_TYPE="remote"`, `OA_MODEL_ENDPOINT="http://gpu-server:8000/predict"`

---

## 5. Pipeline Configuration (JSON Schema)

Pipeline definitions follow a **JSON Schema** for validation and easy integration with other systems.

### Full Pipeline Schema

```yaml
pipelines:
  - name: "cpu_anomaly"
    description: "Detect anomalies in CPU idle time"
    enabled: true

    # --- Data Source ---
    query: 'avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)'
    step: "1m"                          # Resolution/step size for query

    # --- Time Windows ---
    context_window: "1h"                # History to fetch for model context
    prediction_horizon: "15m"           # How far ahead to predict

    # --- Mode ---
    mode: "forecast_and_anomaly"        # Options: "forecast_only", "anomaly_only", "forecast_and_anomaly"

    # --- Scheduling ---
    forecast_schedule: "*/5 * * * *"    # Cron for forecast job
    anomaly_schedule: "*/1 * * * *"     # Cron for anomaly scoring (can differ)

    # --- Series Type ---
    series_type: "univariate"           # Options: "univariate", "multivariate", "covariate"
    covariates:                         # Only if series_type includes covariates
      - query: 'node_memory_MemFree_bytes'
        name: "memory_free"

    # --- Model Configuration ---
    model:
      type: "local"                     # Options: "local", "remote"
      id: "amazon/chronos-t5-small"     # HuggingFace ID (if local)
      endpoint: null                    # URL (if remote)
      parameters:                       # Model-specific parameters
        num_samples: 20                 # Number of sample paths for probabilistic forecast
        temperature: 1.0                # Sampling temperature
        top_k: 50                       # Top-k sampling
        top_p: 1.0                      # Top-p (nucleus) sampling

    # --- Training Configuration (Optional) ---
    training:
      enabled: true
      schedule: "0 0 * * *"             # Daily at midnight
      window: "30d"                     # Training data history
      parameters:                       # Training-specific parameters
        epochs: 10
        batch_size: 32


    # --- Anomaly Detection ---
    anomaly:
      technique: "confidence_interval"  # Options: "confidence_interval", "z_score", "iqr", "isolation_forest"
      confidence_level: 0.95            # For confidence_interval
      threshold: 3.0                    # For z_score (number of std deviations)

    # --- Output ---
    output:
      write_forecast: true              # Write predicted values to TSDB
      write_anomaly_score: true         # Write anomaly scores to TSDB
      metric_prefix: "openanomaly_"     # Prefix for output metrics
```

---

## 6. Technology Stack

| Component | Choice | Rationale |
| :--- | :--- | :--- |
| **Language** | Python | Standard for ML/DS. |
| **Model Engine** | Per-model dedicated libraries | Each TSFM has its own library and API. |
| **TSDB Interface** | Prometheus API | Universal compatibility. |
| **Scheduler** | Celery Beat | Distributed scheduling with persistence. |
| **API** | FastAPI + JSON Schema | OpenAPI spec with schema validation for integration. |
| **UI** | Streamlit | For optional playground/visualization. |

---

## 7. Project Structure

```text
openanomaly/
├── core/
│   ├── ports/
│   │   ├── tsdb_client.py      # Interface for Prometheus Read/Write
│   │   ├── model_engine.py     # Interface for TSFM inference (local or remote)
│   │   ├── config_store.py     # Interface for loading pipelines
│   │   └── scheduler.py        # Interface for Celery Beat
│   ├── domain/
│   │   ├── pipeline.py         # Pipeline dataclass (matches JSON Schema)
│   │   └── result.py           # ForecastResult, AnomalyResult
│   └── services/
│       └── inference_loop.py   # Core business logic (the loop)
│
├── adapters/
│   ├── models/
│   │   ├── base.py             # Abstract base for all model adapters
│   │   ├── remote.py           # RemoteModelAdapter (HTTP client)
│   │   ├── chronos/            # ChronosAdapter (local, dedicated lib)
│   │   └── timesfm/            # TimesFMAdapter (local, dedicated lib)
│   ├── tsdb/
│   │   └── prometheus.py       # PrometheusAdapter (Query + Remote Write)
│   ├── config/
│   │   ├── yaml_store.py
│   │   └── mongo_store.py
│   └── schedulers/
│       └── celery_beat.py      # CeleryBeatAdapter
│
├── api/                        # FastAPI with JSON Schema
│   ├── main.py
│   └── schemas/                # Pydantic models (auto-generate JSON Schema)
│       └── pipeline.py
│
├── schemas/                    # JSON Schema definitions (for external use)
│   └── pipeline.schema.json
│
└── cli/                        # Main entrypoint
    └── main.py                 # `python -m openanomaly`
```

---

## 8. Deployment

### A. Standalone (Single Process + SQLite Beat)
```bash
export OA_CELERY_BROKER="sqla+sqlite:///celery.db"
export OA_CONFIG_PATH="./config/pipelines.yaml"

# Run worker + beat
celery -A openanomaly.worker worker -B -l info
```

### B. Distributed (Redis + MongoDB)
```bash
export OA_CELERY_BROKER="redis://redis:6379/0"
export OA_CONFIG_STORE="mongo"

# Separate processes for scaling
celery -A openanomaly.worker beat -l info          # Scheduler
celery -A openanomaly.worker worker -l info -Q inference  # Workers
```

### C. Kubernetes (Helm)
*   **Beat Pod**: Single replica running Celery Beat.
*   **Worker Pods**: Scaled based on pipeline count.
*   **API Pod**: Optional, for dynamic pipeline management.

---

## 9. Scaling Strategy

### A. Vertical Scaling (Scale Up)
*   **CPU**: Sufficient for smaller models.
*   **GPU**: Recommended for larger models. Model engine auto-detects CUDA.

### B. Horizontal Scaling (Scale Out)
*   Run multiple Worker pods, each pulling jobs from shared queue.
*   Celery handles load balancing automatically.

---

## 10. Development Roadmap

1.  **Phase 1: Core Engine**
    *   Implement `TSDBClient` Port + `PrometheusAdapter`.
    *   Implement `ModelEngine` Port + `RemoteAdapter` + one local adapter.
    *   Implement `ConfigStore` Port + `YamlAdapter`.
    *   Implement `Scheduler` Port + `CeleryBeatAdapter`.
    *   Implement the main `InferenceLoop` service.

2.  **Phase 2: Productionize**
    *   Define JSON Schema for pipelines.
    *   Dockerize the application.
    *   Create Helm chart.

3.  **Phase 3: Management & UI**
    *   Add FastAPI for CRUD on pipelines (with JSON Schema validation).
    *   Add Streamlit UI for visualization and playground.
