# OpenAnomaly: Distributed, Scalable Anomaly Detection

## 1. Vision & Domain Logic
OpenAnomaly is a production-grade platform designed to bring advanced **Forecasting and Anomaly Detection** to any **Prometheus-compatible TSDB**.

### Key Tenets
1.  **TSDB Agnostic**: We speak standard Prometheus API. Compatible with VictoriaMetrics, Thanos, Cortex, Mimir, etc.
2.  **Distributed & Asynchronous**: Heavy lifting (Training) is explicitly decoupled from lightweight tasks (Inference).
3.  **Pluggable Engine**: Powered by **Nixtla** (`StatsForecast`, `MLForecast`, `NeuralForecast`) for state-of-the-art time series logic.

---

## 2. Architecture: Hexagonal (Ports & Adapters)
To achieve maximum flexibility, we follow the **Hexagonal Architecture**.
The **Core Domain** (Anomaly Detection) is isolated from **Infrastructure**. We define **Ports** (Interfaces) and provide plug-and-play **Adapters**.

### A. The Core Ports
*   **`ConfigStore` Port**: Persistence of Pipelines.
    *   *Adapters*: `MongoAdapter` (DB), `YamlAdapter` (File).
*   **`ArtifactStore` Port**: Storage of Model Binaries.
    *   *Adapters*: `S3Adapter` (Cloud), `LocalAdapter` (Disk), `NoOpAdapter` (No Operation / Disabled).
*   **`JobDispatcher` Port**: Async execution.
    *   *Adapters*: `CeleryAdapter` (supports Redis, SQLite, RabbitMQ brokers).

### B. The Worker Roles (Domain Logic)
The core logic is split into two specialized workers that use these ports:

#### 1. The Trainer
*   **Goal**: Fit complex models on historical data.
*   **Flow**:
    1.  Fetch Data from TSDB (Prometheus Range Query).
    2.  Fit Model (Nixtla).
    3.  Save Artifact to `ArtifactStore`.
    4.  Update Metadata in `ConfigStore`.

#### 2. The Inferencer
*   **Goal**: High-frequency scoring.
*   **Flow**:
    1.  Load Artifact from `ArtifactStore`.
    2.  Fetch Context from TSDB.
    3.  Generates Prediction and anomaly_score.
    4.  Write Result to TSDB (Remote Write).

### D. `ModelEngine` Port
*Responsibility*: The "Brain". Generic interface for Training and Inference.
*   **Adapter 1: `NixtlaAdapter`** - Wrapper for `StatsForecast`, `MLForecast`, `NeuralForecast`.
*   **Adapter 2: `DartsAdapter`** - Wrapper for `Darts` library.
*   **Adapter 3: `SklearnAdapter`** - Wrapper for standard Scikit-Learn pipelines.

---

## 3. Configuration (Dependency Injection)
Select adapters at runtime via **Environment Variables**:

| Port | Env Var | Example Values |
| :--- | :--- | :--- |
| **Engine** | `OA_MODEL_ENGINE` | `nixtla`, `darts` |
| **Config** | `OA_CONFIG_STORE` | `mongo`, `yaml` |
| **Artifacts** | `OA_ARTIFACT_STORE` | `s3`, `local` |
| **Dispatcher** | `OA_DISPATCHER` | `celery` |
| **Broker** | `OA_CELERY_BROKER` | `redis://...`, `sqla+sqlite:///...` |

---

## 4. Presets (Common Modes)

### A. Protocol: "Standalone" (Single Node)
*   **Config**: YAML Files (`./config/pipelines.yaml`).
*   **Infrastructure**: None (SQLite/Local).
*   `OA_CONFIG_STORE=yaml`, `OA_ARTIFACT_STORE=local`, `OA_CELERY_BROKER=sqla+sqlite:///celery.db`

### B. Protocol: "Enterprise" (Cluster)
*   **Config**: MongoDB (Dynamic API).
*   **Infrastructure**: Docker/K8s (Redis, Mongo, MinIO).
*   `OA_CONFIG_STORE=mongo`, `OA_ARTIFACT_STORE=s3`, `OA_CELERY_BROKER=redis://...`

---

## 5. Technology Stack

| Component | Choice | Rationale |
| :--- | :--- | :--- |
| **Language** | **Python** | Unified DS and Backend stack. |
| **Engine (Port)** | **Pluggable** | `NixtlaAdapter` (Default), `DartsAdapter`, etc. |
| **Architecture** | **Hexagonal** | Ports & Adapters for ultimate flexibility. |
| **Framework** | **FastAPI** | Dependency Injection System. |
| **Compatible TSDBs** | **Prometheus API** | Connects to VictoriaMetrics, Thanos, Mimir, Cortex, etc. |
| **UI** | **Streamlit** | Optional UI Port (swappable in future). |

---

## 6. Deployment Strategy: From Hexagon to Microservices
How does one codebase become many microservices? **Role-Based Deployment**.

We build a **Single Docker Image** containing the entire Hexagon (Code + Adapters).
Reference architecture for Kubernetes/Helm:

1.  **Deployment A (API)**:
    *   *Role*: HTTP Server.
    *   *Env*: `OA_CONFIG_STORE=mongo`.
    *   *Command*: `uvicorn api.main:app`.
2.  **Deployment B (Trainer Worker)**:
    *   *Role*: Heavy Model Training (Scaled independently).
    *   *Env*: `OA_DISPATCHER=celery`, `OA_MODEL_ENGINE=nixtla`.
    *   *Command*: `celery worker -Q training`.
3.  **Deployment C (Inference Worker)**:
    *   *Role*: Fast Anomaly Scoring (Scaled independently).
    *   *Env*: `OA_DISPATCHER=celery`, `OA_MODEL_ENGINE=nixtla`.
    *   *Command*: `celery worker -Q inference`.

**Result**: The logic is shared, but the runtime behavior and scaling characteristics are decoupled.

### Helm Strategy: "Batteries Included but Removable"
Our Helm chart will include **Redis, MongoDB, and MinIO** as *optional dependencies* (Subcharts).
*   **Dev/POV**: `helm install openanomaly --set tags.infrastructure=true` (Deploys everything).
*   **Prod**: `helm install openanomaly --set tags.infrastructure=false` (Connects to your managed AWS S3 / Atlas / Elasticache).

---

## 7. Scaling Strategy: Up, Out, or Elsewhere

### A. Vertical Scaling (Scale Up) - **The Simple Path**
**No external cluster required.**
*   **CPU Mode**: Run the worker on a standard machine. Ideal for light statistical models (ARIMA) or small-scale Deep Learning.
*   **GPU Mode**: Run the worker on a GPU node (`nvidia-docker`). Ideal for accelerating `NeuralForecast`.

### B. Horizontal Scaling (Scale Out) - **The Big Data Path**
For massive datasets (1M+ series) where a single machine's RAM/CPU is insufficient.
*   **`NixtlaAdapter`**: Automatically handles distribution based on configuration.
    *   *StatsForecast*: Utilizes **Fugue** to distribute across Spark/Dask/Ray.
    *   *MLForecast*: Utilizes native **DistributedMLForecast** on Spark/Dask/Ray.
    *   *NeuralForecast*: Utilizes **Spark** (Data Parallel) or **Ray** (Hyperopt).
*   **Benefits**: The complexity of which class to use (`Fugue` vs `DistributedMLForecast`) is hidden inside the Adapter.

### C. External Dispatching (Delegate) - **The Managed Path**
Since `JobDispatcher` is a Port, we can implement adapters that don't run code locally at all, but submit jobs to managed clouds.
*   **`RemoteJobAdapter`**: Submits a training job to an external compute cluster (Cloud or On-Prem).

This allows OpenAnomaly to be a lightweight "Control Plane" while heavy lifting happens on ephemeral infrastructure.

---

## 8. Development Roadmap

1.  **Phase 1: Foundation (The Skeleton)**
    - Define Ports & Implement Adapters.
    - Setup Bootstrap loader (Dependency Injection Factory).

2.  **Phase 2: The Workers**
    - Implement generic `Trainer` and `Inferencer` tasks.
    - Integrate Nixtla engine.

3.  **Phase 3: Controller & UI**
    - Build API to manage pipelines.

## 8. Project Structure (Modular Monolith)
This layout ensures separation of concerns while keeping the codebase unified.

```text
openanomaly/
├── core/                   # 🧠 PURE PYTHON (No external deps like Mongo/S3)
│   ├── ports/              # Interfaces (Abstract Base Classes)
│   │   ├── config_store.py
│   │   ├── artifact_store.py
│   │   ├── model_engine.py # Interface for ML (fit, predict)
│   │   └── tsdb_client.py  # <--- [NEW] Interface for Prometheus/VM
│   ├── domain/             # Data Classes (Job, Pipeline, AnomalyResult)
│   └── services/           # Business Logic (Trainer/Inferencer orchestration)
│
├── adapters/               # 🔌 THE PLUGINS (External Libs live here)
│   ├── engines/            # ML Libraries
│   │   ├── nixtla/         # <--- [Package] Complex logic goes here
│   │   │   ├── __init__.py
│   │   │   └── adapter.py
│   │   └── darts/
│   ├── tsdb/               # <--- [NEW] TSDB Drivers
│   │   └── prometheus.py   # Implementation using requests/prom-api client
│   ├── stores/
│   │   ├── mongo.py
│   │   └── s3.py
│   └── ui/
│       └── streamlit.py
│
├── api/                    # 🌐 REST API (FastAPI)
│   └── main.py             # Entrypoint for API Pod
│
└── workers/                # 👷 WORKERS (Celery)
    └── celery_worker.py    # Entrypoint for Worker Pods
```
