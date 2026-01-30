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
| **`ModelEngine`** | Run zero-shot forecast inference | Local or Remote adapters |
| **`ConfigStore`** | Persist pipeline definitions | `DjangoConfigStore` (ORM-based) |
| **`Scheduler`** | Trigger inference jobs on a schedule | `DjangoSchedulerAdapter` (Syncs to Redbeat) |

### Independent Tasks
The scheduler triggers three distinct tasks:
1.  **Forecast**: Runs the inference loop (Fetch -> Predict -> Write).
2.  **Anomaly**: Checks for anomalies (Actuals vs Forecast).
3.  **Train**: Retrains the model (if applicable).


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
```json
POST /execute/inference (Stateless)
{
  ...Pipeline Configuration Object...
}
Response:
{
  "status": "success",
  "message": "Inference executed and results written to TSDB"
}

POST /execute/train (Stateless)
{
  ...Pipeline Configuration Object...
}
Response:
{
  "status": "success",
  "model_id": "model_v2_123"
}
```


```json
POST http://remote-host/custom/predict

{
  "context": [1.2, 3.4, ...],
  "prediction_length": 12,
  "quantiles": [0.1, 0.5, 0.9]
}
...

POST http://remote-host/custom/train
{
  "data": [...],
  "parameters": {...}
}
```

*Configuration*: 
- Prediction: `model.endpoint` = "http://remote-host/custom/predict"
- Training: `training.endpoint` = "http://remote-host/custom/train"
- Format: `model.serialization_format` = "json" | "arrow"
  - `arrow` sends Arrow IPC (Feather) via `multipart/form-data`.




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
      id: null                          
      endpoint: "http://gpu-server/predict" # Full prediction URL
      serialization_format: "arrow"         # "json" (default) or "arrow"
      parameters:                       
        num_samples: 20                 

        temperature: 1.0                # Sampling temperature
        top_k: 50                       # Top-k sampling
        top_p: 1.0                      # Top-p (nucleus) sampling

    # --- Training Configuration (Optional) ---
      enabled: true
      schedule: "0 0 * * *"             
      window: "30d"                     
      endpoint: "http://gpu-server/train" # Full training URL
      parameters:                       
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
| **Persistence** | **Django + Mongo/SQLite** | Supports MongoDB (Prod) or SQLite (Light Mode). |
| **Scheduler** | **Celery + Redbeat** | Distributed scheduling (requires Redis) or Standalone. |
| **API** | FastAPI + JSON Schema | OpenAPI spec with schema validation for integration. |
| **UI** | Streamlit | For optional playground/visualization. |

---

## 7. Project Structure

```text

openanomaly/
├── common/                     # Shared components
│   ├── config/
│   │   └── django_store.py     # Database-agnostic ConfigStore using Django ORM
│   ├── adapters/
│   │   ├── models/             # Model Engine Adapters (Chronos, Remote)
│   │   ├── schedulers/         # Scheduler Adapters (Django, Celery Beat)
│   │   └── tsdb/               # TSDB Clients (Prometheus)
│   ├── interfaces/             # Core Interfaces (Ports)
│   └── dataclasses.py          # Shared Data Models
│
├── config/                     # Configuration & Settings
│   ├── settings.py             # Django Settings (django-environ)
│   ├── urls.py                 # Root URLConf
│   ├── celery.py               # Celery App Entrypoint
│   ├── wsgi.py                 # WSGI Entry Point
│   └── asgi.py                 # ASGI Entry Point
│
├── pipelines/                  # Core Domain App (Django App)
│   ├── models.py               # Pipeline Model (MongoDB)
│   ├── views.py                # HTTP Entry Points (Trigger/Execute)
│   ├── tasks.py                # Celery Tasks (Forecast, Anomaly, Train)
│   ├── signals.py              # Scheduler Logic (Sync to Redbeat)
│   ├── inference.py            # Business Logic (Fetch->Predict->Write)
│   └── urls.py                 # App URLs
│
├── manage.py                   # Django CLI
├── config.yaml.example         # Example Config
└── scripts/                    # Utilities
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
