# OpenAnomaly
> **Zero-shot anomaly detection for Prometheus-compatible TSDBs using Time Series Foundation Models.**

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![UV](https://img.shields.io/badge/managed%20by-uv-purple)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Vision

OpenAnomaly brings **real-time anomaly detection** to any **Prometheus-compatible TSDB** (VictoriaMetrics, Thanos, Mimir, Cortex) using **Time Series Foundation Models (TSFMs)**.

**No training required.** The system uses pre-trained models for **zero-shot forecasting**. It continuously queries your TSDB, runs inference, and writes anomaly scores back—just like VMAnomaly.

---

## How It Works

```
Scheduler (Celery Beat)
    │
    ▼
Fetch Data (Prometheus Query API)
    │
    ▼
Run TSFM (Local or Remote)
    │
    ▼
Calculate Anomaly Score (Optional)
    │
    ▼
Write Results (Remote Write)
```

---

## Features

*   **Leading TSFMs**: Use the latest Time Series Foundation Models from HuggingFace (Chronos, TimesFM, TOTO, Moirai).
*   **Local or Remote Models**: Run models locally or call external inference endpoints.
*   **Flexible Modes**: Forecast-only, Anomaly Detection, or both.
*   **Rich Configuration**: Step size, covariates, confidence techniques, per-pipeline settings.
*   **JSON Schema**: API and config validated with JSON Schema for easy integration.

---

## Quick Start

### 1. Install
```bash
uv sync
```

### 2. Configure (`config.yaml`)
```yaml
# Infrastructure
prometheus_url: "http://localhost:8428"
# ...
```

### 3. Bootstrap (Light Mode / SQLite)
To run without MongoDB/Redis, use SQLite and seed the database from your YAML:
```bash
# Set DB to SQLite
export OPENANOMALY_DATABASE_TYPE="sqlite"
export CELERY_BROKER_URL="sqla+sqlite:///celery.db"

# Create DB Schema
python manage.py migrate

# Seed pipelines from YAML
python manage.py seed_pipelines
```

### 3. Run
```bash
# Set broker (SQLite for standalone)
export CELERY_BROKER_URL="sqla+sqlite:///celery.db"

# Run worker with beat (using the new Django app)
celery -A openanomaly.config worker -B -l info
```

---

## Architecture

| Port | Responsibility | Adapters |
| :--- | :--- | :--- |
| **TSDBClient** | Read/Write to TSDB | `PrometheusAdapter` |
| **ModelEngine** | Run inference | Local adapters, `RemoteAdapter` |
| **ConfigStore** | Load pipelines | `YamlAdapter`, `MongoAdapter` |
| **Scheduler** | Trigger jobs | `CeleryBeatAdapter` |

---

## Development

```bash
# Option A: uv
uv sync

# Option B: nix
nix develop
```

---

## Deployment

*   **Standalone**: Single process with SQLite Beat.
*   **Distributed**: Redis broker + multiple workers.
*   **Kubernetes**: Helm chart with Beat/Worker/API pods.

---

## License
[Apache 2.0](LICENSE)
