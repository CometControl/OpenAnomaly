# OpenAnomaly: Real-Time Anomaly Detection with Time Series Foundation Models

## 1. Vision

OpenAnomaly is a lightweight, zero-shot anomaly detection system for **Prometheus-compatible TSDBs** (VictoriaMetrics, Thanos, Mimir, Cortex, etc.).

It leverages **Time Series Foundation Models (TSFMs)** from the HuggingFace ecosystem—such as **Chronos**, **TimesFM**, and **TOTO**—to perform inference without any prior training on your specific data.

### Key Tenets
1.  **Zero Training Required**: Uses pre-trained foundation models. No model fitting, no weight storage.
2.  **Real-Time Scoring**: Continuously queries the TSDB, runs inference, and writes anomaly scores back.
3.  **TSDB Agnostic**: Speaks standard Prometheus Query API and Remote Write protocol.
4.  **Pluggable Models**: Swap foundation models via configuration (HuggingFace model IDs).

---

## 2. How It Works (The Loop)

OpenAnomaly operates in a simple, continuous loop, similar to VMAnomaly:

```
┌──────────────────────────────────────────────────────────────────┐
│                        THE INFERENCE LOOP                        │
│                                                                  │
│  ┌─────────────────┐                                             │
│  │   1. SCHEDULER  │  (Triggers job every N minutes)             │
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
│  │ 4. SCORE ANOMALY│  (Compare prediction vs. actual)            │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                             │
│  │ 5. WRITE RESULTS│  (Remote Write: prediction, anomaly_score)  │
│  └─────────────────┘                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture: Hexagonal (Ports & Adapters)

We retain the **Hexagonal Architecture** for flexibility, but the ports are simplified.

### Core Ports

| Port | Responsibility | Adapters |
| :--- | :--- | :--- |
| **`TSDBClient`** | Read (Query) and Write (Remote Write) to TSDB | `PrometheusAdapter` |
| **`ModelEngine`** | Run zero-shot forecast inference | `ChronosAdapter`, `TimesFMAdapter`, `HuggingFaceAdapter` |
| **`ConfigStore`** | Persist pipeline definitions (queries, schedules) | `YamlAdapter` (File), `MongoAdapter` (DB) |
| **`Scheduler`** | Trigger inference jobs on a schedule | `APSchedulerAdapter`, `CeleryBeatAdapter` |

### Removed Ports (vs. Previous Design)
*   ~~`ArtifactStore`~~: No model weights to store.
*   ~~`TrainerWorker`~~: No training happens.

---

## 4. Supported Foundation Models

Models are loaded via HuggingFace `transformers` or dedicated libraries. The user specifies a model ID.

| Model | Provider | HuggingFace ID | Notes |
| :--- | :--- | :--- | :--- |
| **Chronos** | Amazon | `amazon/chronos-t5-*` | T5-based, zero-shot probabilistic forecasting. |
| **Chronos-Bolt** | Amazon | `amazon/chronos-bolt-*` | Faster variant of Chronos. |
| **TimesFM** | Google | `google/timesfm-*` | 200M param decoder-only model. |
| **TOTO** | Datadog | `Datadog/toto` | Trained on 1T observability data points. |

*Configuration*: `OA_MODEL_ID="amazon/chronos-t5-small"`

---

## 5. Configuration

### Environment Variables

| Env Var | Description | Example |
| :--- | :--- | :--- |
| `OA_MODEL_ID` | HuggingFace model ID for the TSFM. | `amazon/chronos-t5-small` |
| `OA_TSDB_READ_URL` | Prometheus Query API endpoint. | `http://victoria:8428` |
| `OA_TSDB_WRITE_URL` | Prometheus Remote Write endpoint. | `http://victoria:8428/api/v1/write` |
| `OA_CONFIG_STORE` | Where to load pipeline definitions. | `yaml` or `mongo` |
| `OA_CONFIG_PATH` | Path to YAML config (if `yaml`). | `./config/pipelines.yaml` |

### Pipeline Definition (YAML Example)

```yaml
pipelines:
  - name: "cpu_anomaly"
    query: 'avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)'
    context_window: "1h"      # Fetch 1 hour of history for context
    prediction_horizon: "5m"  # Predict the next 5 minutes
    schedule: "*/5 * * * *"   # Run every 5 minutes
    model_id: "amazon/chronos-t5-small" # Override global model per-pipeline
```

---

## 6. Technology Stack

| Component | Choice | Rationale |
| :--- | :--- | :--- |
| **Language** | Python | Standard for ML/DS. |
| **Model Engine** | HuggingFace Transformers / Chronos | Access to leading TSFMs. |
| **TSDB Interface** | Prometheus API | Universal compatibility. |
| **Scheduler** | APScheduler / Celery Beat | Lightweight or distributed scheduling. |
| **API** | FastAPI | For optional management API. |
| **UI** | Streamlit | For optional playground/visualization. |

---

## 7. Project Structure

```text
openanomaly/
├── core/
│   ├── ports/
│   │   ├── tsdb_client.py      # Interface for Prometheus Read/Write
│   │   ├── model_engine.py     # Interface for TSFM inference
│   │   ├── config_store.py     # Interface for loading pipelines
│   │   └── scheduler.py        # Interface for scheduling jobs
│   ├── domain/
│   │   └── pipeline.py         # Pipeline, AnomalyResult data classes
│   └── services/
│       └── inference_loop.py   # Core business logic (the loop)
│
├── adapters/
│   ├── models/
│   │   ├── chronos.py          # ChronosAdapter
│   │   └── huggingface.py      # Generic HuggingFaceAdapter
│   ├── tsdb/
│   │   └── prometheus.py       # PrometheusAdapter (Query + Remote Write)
│   ├── config/
│   │   ├── yaml_store.py
│   │   └── mongo_store.py
│   └── schedulers/
│       └── apscheduler.py
│
├── api/                        # Optional FastAPI management
│   └── main.py
│
└── cli/                        # Main entrypoint
    └── main.py                 # `python -m openanomaly`
```

---

## 8. Deployment

### A. Standalone (Single Process)
Run as a single Python process. Ideal for small-scale or local testing.
```bash
# Set environment variables
export OA_MODEL_ID="amazon/chronos-t5-small"
export OA_TSDB_READ_URL="http://localhost:8428"
export OA_TSDB_WRITE_URL="http://localhost:8428/api/v1/write"
export OA_CONFIG_PATH="./config/pipelines.yaml"

# Run
python -m openanomaly
```

### B. Docker
```bash
docker run -e OA_MODEL_ID="amazon/chronos-t5-small" \
           -e OA_TSDB_READ_URL="..." \
           -v ./config:/app/config \
           openanomaly:latest
```

### C. Kubernetes (Helm)
The Helm chart deploys OpenAnomaly as a **Deployment** (not a CronJob, since it runs its own internal scheduler).
*   **No external dependencies required** (unlike previous design with Redis/Mongo/MinIO).
*   Optionally connect to an external MongoDB for dynamic pipeline management via API.

---

## 9. Scaling Strategy

### A. Vertical Scaling (Scale Up)
*   **CPU**: Sufficient for smaller models like `chronos-t5-tiny` or `chronos-t5-small`.
*   **GPU**: Recommended for larger models (`chronos-t5-large`, `timesfm`). The model engine auto-detects CUDA.

### B. Horizontal Scaling (Scale Out)
For many pipelines, run multiple OpenAnomaly instances, each responsible for a subset of pipelines (sharding by pipeline name or label).

---

## 10. Development Roadmap

1.  **Phase 1: Core Engine**
    *   Implement `TSDBClient` Port + `PrometheusAdapter`.
    *   Implement `ModelEngine` Port + `ChronosAdapter`.
    *   Implement `ConfigStore` Port + `YamlAdapter`.
    *   Implement the main `InferenceLoop` service.

2.  **Phase 2: Productionize**
    *   Add `APSchedulerAdapter` for scheduling.
    *   Dockerize the application.
    *   Create Helm chart.

3.  **Phase 3: Management & UI**
    *   Add FastAPI for CRUD on pipelines (requires `MongoAdapter`).
    *   Add Streamlit UI for visualization and playground.
