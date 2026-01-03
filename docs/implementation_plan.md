# OpenAnomaly: Distributed, Scalable Anomaly Detection

## 1. Vision & Architecture
A production-grade, distributed anomaly detection system for Prometheus-compatible TSDBs.
**Key Tenets:**
- **TSDB Agnostic**: Prometheus standards for I/O.
- **Distributed & Asynchronous**: Heavy lifting (Training) explicitly separated from Inference.
- **Stateful Management**: MongoDB for configuration/metadata, S3 for model artifacts.
- **Queue-Based**: Celery (Mongo Broker) for reliable job dispatching.
- **Pluggable Engine**: Nixtla (`StatsForecast`, `MLForecast`, `NeuralForecast`) as the core.

---

## 2. System Components
**Strategy**: Monorepo. Architecture uses **Dependency Injection** to swap backends based on `RUN_MODE`.

### A. Core Interfaces (The Abstractions)
To support both "Enterprise Cluster" and "Local Light Mode", we code against interfaces:
-   **`ConfigStore`**: Abstract CRUD for Pipelines.
    -   *Impl 1 (Default)*: **MongoDB**.
    -   *Impl 2 (Light)*: **SQLite** or **YAML Files**.
-   **`ArtifactStore`**: Abstract Save/Load for models.
    -   *Impl 1 (Default)*: **S3 (MinIO)**.
    -   *Impl 2 (Light)*: **Local Filesystem**.
-   **`JobDispatcher`**: Abstract "Run this Job".
    -   *Impl 1 (Default)*: **Celery** (Distributed).
    -   *Impl 2 (Light)*: **In-Process ThreadPool** (No Broker needed).

### B. The Services (Deployables)

#### 1. The "Controller" (Agent)
-   In **Cluster Mode**: Connects to Mongo/Redpanda, dispatches to Celery.
-   In **Light Mode**: Runs as a single process, using SQLite/LocalDisk, spawns threads for work.

#### 2. The "Worker" (Trainer/Inferencer)
-   In **Cluster Mode**: Standalone container consuming from Celery.
-   In **Light Mode**: Embedded as a generic python module imported by the Controller.

---

## 3. Data Flow (Modes)

### A. Cluster Mode (Production)
1.  **Schedule**: `celerybeat-mongo` triggers task.
2.  **Dispatch**: Task -> Mongo Broker.
3.  **Train**: Worker -> S3 Save -> Mongo Update.

### B. Light Mode (Laptop/Dev)
1.  **Schedule**: In-process `APScheduler`.
2.  **Dispatch**: Call function `train_model(pipeline_id)`.
3.  **Train**: Thread -> Local File Save -> SQLite Update.

---

## 4. Technology Stack

| Component | Choice | Rationale |
| :--- | :--- | :--- |
| **Language** | **Python** | Unified DS and Backend stack. |
| **Engine** | **Nixtla** | StatsForecast, MLForecast, NeuralForecast. |
| **Config/State** | **MongoDB** | Flexible document store for configs and registry. |
| **Messaging** | **Celery (Mongo Broker)** | Simplified stack (no Redis). |
| **Artifacts** | **S3 (MinIO)** | Shared storage for model binaries. |
| **Web** | **FastAPI** | Backend API. |
| **Frontend** | **Streamlit** | Interactive UI. |

---

## 5. Development Roadmap

1.  **Phase 1: Foundation (The Skeleton)**
    - Setup Docker Compose: Mongo, MinIO, **VictoriaMetrics (Single)** (Infra only).
    - Create `db` module (Mongo) and `queue` module (Celery).
    - Implement `S3Client` for artifact storage.

2.  **Phase 2: The Workers (Train & Infer)**
    - Implement `Trainer`: VMRead -> Fit -> S3Write.
    - Implement `Inferencer`: S3Read -> VMRead -> Predict -> VMWrite.
    - Integrate `GenericNixtlaEngine`.
    - **Docker**: Add App Services to `docker-compose` to simulate Cluster Mode.

3.  **Phase 3: The Controller & UI**
    - Build Scheduler to dispatch jobs.
    - Build Streamlit UI to manage Mongo entries and trigger "Playground" runs.
