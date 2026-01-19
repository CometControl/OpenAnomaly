# OpenAnomaly
> **Zero-shot anomaly detection for Prometheus-compatible TSDBs using Time Series Foundation Models.**

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![UV](https://img.shields.io/badge/managed%20by-uv-purple)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Vision

OpenAnomaly brings **real-time anomaly detection** to any **Prometheus-compatible TSDB** (VictoriaMetrics, Thanos, Mimir, Cortex) using **Time Series Foundation Models (TSFMs)** like Chronos, TimesFM, and TOTO.

**No training required.** The system uses pre-trained models from HuggingFace for **zero-shot forecasting**. It continuously queries your TSDB, runs inference, and writes anomaly scores back—just like VMAnomaly.

---

## How It Works

```
┌────────────────────────────────────────────────────────┐
│                  THE INFERENCE LOOP                    │
│                                                        │
│   Scheduler (every N min)                              │
│        │                                               │
│        ▼                                               │
│   Fetch Data (Prometheus Query API)                    │
│        │                                               │
│        ▼                                               │
│   Run TSFM (Chronos/TimesFM/TOTO)                      │
│        │                                               │
│        ▼                                               │
│   Calculate Anomaly Score (Prediction vs Actual)       │
│        │                                               │
│        ▼                                               │
│   Write Results (Remote Write)                         │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## Supported Models

| Model | Provider | HuggingFace ID |
| :--- | :--- | :--- |
| **Chronos** | Amazon | `amazon/chronos-t5-small` |
| **Chronos-Bolt** | Amazon | `amazon/chronos-bolt-small` |
| **TimesFM** | Google | `google/timesfm-1.0-200m` |
| **TOTO** | Datadog | `Datadog/toto` |

---

## Quick Start

### 1. Install
```bash
uv sync
```

### 2. Configure (Environment Variables)
```bash
export OA_MODEL_ID="amazon/chronos-t5-small"
export OA_TSDB_READ_URL="http://localhost:8428"
export OA_TSDB_WRITE_URL="http://localhost:8428/api/v1/write"
export OA_CONFIG_PATH="./config/pipelines.yaml"
```

### 3. Define Pipelines (`config/pipelines.yaml`)
```yaml
pipelines:
  - name: "cpu_anomaly"
    query: 'avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)'
    context_window: "1h"
    prediction_horizon: "5m"
    schedule: "*/5 * * * *"
```

### 4. Run
```bash
python -m openanomaly
```

---

## Architecture

| Port | Responsibility | Adapters |
| :--- | :--- | :--- |
| **TSDBClient** | Read/Write to TSDB | `PrometheusAdapter` |
| **ModelEngine** | Run zero-shot inference | `ChronosAdapter`, `HuggingFaceAdapter` |
| **ConfigStore** | Load pipeline definitions | `YamlAdapter`, `MongoAdapter` |
| **Scheduler** | Trigger inference jobs | `APSchedulerAdapter` |

---

## Development

### Option A: `uv`
```bash
uv sync
```

### Option B: `nix`
```bash
nix develop
```

---

## Deployment

*   **Docker**: Single container, no external dependencies.
*   **Kubernetes (Helm)**: Deployment with configurable model and TSDB settings.

---

## License
[MIT](LICENSE)
