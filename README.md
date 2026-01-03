# OpenAnomaly
> **A distributed, scalable anomaly detection system for Prometheus-compatible Time Series Databases.**

![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)
![UV](https://img.shields.io/badge/managed%20by-uv-purple)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Vision
OpenAnomaly is a production-grade platform designed to bring advanced **Forecasting and Anomaly Detection** to any **Prometheus-compatible TSDB** (VictoriaMetrics, Thanos, Mimir, etc.).

It utilizes a **Hexagonal Architecture (Ports & Adapters)** to completely isolate the core anomaly detection logic (`Trainer`, `Inferencer`) from the infrastructure, allowing you to **mix and match** components to fit any environment—from a laptop to a global cluster.

## Domain Logic
The core engine is split into two specialized workers that handle the anomaly detection lifecycle:

### 1. The Trainer
*   **Trigger**: On-demand or Low-frequency schedules (e.g., Weekly).
*   **Workflow**:
    1.  Fetch historical data from TSDB (Prometheus API).
    2.  Fit complex models using the active **ModelEngine** (Nixtla, Darts, etc.).
    3.  Serialize and save the model artifact to `ArtifactStore`.
    4.  Update the Model Registry in `ConfigStore`.

### 2. The Inferencer
*   **Trigger**: High-frequency schedules (e.g., Every 5m).
*   **Workflow**:
    1.  Download the "Active" model artifact from `ArtifactStore`.
    2.  Fetch recent "context" window from TSDB.
    3.  Generate predictions and anomaly_score.
    4.  Write results back to TSDB (Remote Write).

---

## Architecture: Ports & Adapters
The system defines standard interfaces ("Ports") that can be satisfied by different plugins ("Adapters"):

| Port | Responsibility | Adapters (Plugins) |
| :--- | :--- | :--- |
| **ConfigStore** | Storing Pipelines & Rules | `MongoAdapter` (DB), `YamlAdapter` (File) |
| **ArtifactStore** | Storing Model Binaries | `S3Adapter`, `LocalAdapter`, `NoOpAdapter` (Disabled/Stat-Only) |
| **JobDispatcher** | Running Async Tasks | `CeleryAdapter` (Redis, SQLite, RabbitMQ, etc.) |
| **UserInterface** | Management & Plots | `StreamlitAdapter` (Optional, swappable) |

---

## Configuration (Mix & Match)
Control the architecture at runtime using **Environment Variables**.

### Preset A: "Standalone" (Single Node)
*Default single-node setup using files and SQLite. suitable for local dev or small-scale production.*
```bash
export OA_CONFIG_STORE="yaml"
export OA_ARTIFACT_STORE="local"
export OA_CELERY_BROKER="sqla+sqlite:///celery.db"
```

### Preset B: "Cluster" (Enterprise)
*Full distributed setup using Databases and Object Storage.*
```bash
export OA_CONFIG_STORE="mongo"
export OA_ARTIFACT_STORE="s3"
export OA_CELERY_BROKER="redis://redis:6379/0"
```

---

## Tech Stack
| Component | Choice | Rationale |
| :--- | :--- | :--- |
| **Engine (Port)** | **Pluggable** | `NixtlaAdapter` (Default), `DartsAdapter`, etc. |
| **Architecture** | **Hexagonal** | Maximum flexibility via Ports & Adapters |
| **Compatible TSDBs** | **Prometheus API** | Connects to VictoriaMetrics, Thanos, Mimir, Cortex, etc. |
| **Object Storage** | **MinIO / S3** | Standard ArtifactStore for model binaries. |
| **API** | **FastAPI** | Modern dependency injection system |
| **UI** | **Streamlit** | Interactive UI (Optional Port) |

## 🛠️ Development Workflow

### 1. Environment Setup (Choose One)

#### Option A: `uv` (Recommended for Speed)
```bash
# Initialize and sync
uv sync
```

#### Option B: `nix` (Recommended for Hermeticity)
Uses Nix Flakes to provide Python, UV, and system dependencies in an isolated shell.
```bash
nix develop
# or if using direnv:
direnv allow
```

### 2. Running Locally (Standalone Mode)
After setting up the environment:
```bash
# Run the API (Uses YAML config by default)
uv run uvicorn api.main:app --reload

# Run the Worker (Uses SQLite broker by default)
uv run celery -A workers.celery_worker worker -l info --pool=solo
```

---

## 🚀 Deployment Options (Future)
*This section will detail how to deploy OpenAnomaly to production environments.*

*   **Docker Images**: Official builds for Controller and Workers.
*   **Helm Chart**: Kubernetes-native deployment.
*   **Binary**: Self-contained executable (via PyInstaller/Nuitka).

## License
[MIT](LICENSE)
