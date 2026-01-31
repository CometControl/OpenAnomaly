# OpenAnomaly: Technical Design Document

## 1. System Overview

OpenAnomaly is a modular, zero-shot anomaly detection system designed to integrate seamlessly with Prometheus-compatible Time Series Databases (TSDBs). It leverages Time Series Foundation Models (TSFMs) to forecast metrics and detect anomalies without requiring historical training on specific datasets.

### Core Philosophy
*   **Zero-Shot**: No per-series training. Uses pre-trained foundation models.
*   **Pull/Push**: Pulls data from PromQL, pushes results via Remote Write.
*   **Stateless Workers**: Scalable inference workers.
*   **High Availability**: Robust scheduling and execution.

---

## 2. Architecture: Hexagonal (Ports & Adapters)

The system follows a Hexagonal Architecture (Ports & Adapters) pattern to ensure loose coupling between business logic and infrastructure.

### 2.1 Ports (Interfaces)
| Port | Responsibility |
| :--- | :--- |
| **TSDBClient** | Interface for reading from and writing to the TSDB. |
| **ModelEngine** | Interface for running inference (Forecast/Anomaly). |
| **ConfigStore** | Interface for retrieving pipeline configurations. |
| **Scheduler** | Interface for triggering periodic tasks. |

### 2.2 Adapters (Implementations)
| Port | Current Adapter | Description |
| :--- | :--- | :--- |
| **TSDBClient** | `PrometheusAdapter` | Uses Prometheus HTTP API for queries and Remote Write for output. |
| **ModelEngine** | `LocalAdapter`, `RemoteAdapter` | Runs TSFMs locally or calls external inference endpoints. |
| **ConfigStore** | `MongoAdapter`, `YamlAdapter` | Loads pipelines from MongoDB (Prod) or local YAML (Test). |
| **Scheduler** | `CeleryRedBeatAdapter` | Uses Celery Beat with RedBeat backend for distributed scheduling. |

---

## 3. High Availability Strategy

A core requirement is ensuring reliable execution of anomaly detection pipelines, even at scale.

### 3.1 Scheduler HA (Active-Passive)
We use **RedBeat** (`redbeat.RedBeatScheduler`) to persist schedules in Redis and enable a High Availability setup.

*   **Mechanism**: Distributed Locking via Redis.
*   **Behavior**:
    *   Multiple `beat` instances start.
    *   One instance acquires the global lock and becomes the **Leader**.
    *   Other instances enter **Standby** mode, polling the lock.
    *   If the Leader crashes, the lock expires, and a Standby instance promotes itself to Leader.
*   **Benefit**: Eliminates the scheduler as a single point of failure.

### 3.2 Worker HA (Active-Active)
Inference tasks (`run_forecast`, `run_anomaly_check`) are stateless and idempotent within their time window.

*   **Mechanism**: Celery Worker Queues.
*   **Scaling**: You can run `N` worker containers.
*   **Behavior**: Tasks are load-balanced across all available workers by Redis.
*   **Benefit**: High throughput and fault tolerance. If a worker crashes, the task is redelivered (if acks_late is enabled) or retried.

---

## 4. Workflows

### 4.1 The Inference Loop
1.  **Trigger**: Scheduler pushes a task (e.g., `run_forecast`) to Redis.
2.  **Consume**: A Worker picks up the task.
3.  **Fetch**: Worker queries the TSDB for the context window (e.g., past 1 hour of data).
4.  **Inference**: Worker sends data to the `ModelEngine`.
    *   Model predicts the next `N` steps (Horizon).
5.  **Score** (Optional): If actual data is available (anomaly check), compare Actual vs. Forecast using a scoring technique (e.g., Z-Score, Confidence Interval).
6.  **Write**: Worker writes the Forecast and/or Anomaly Score back to the TSDB via Remote Write.

---

## 5. Configuration Management

Configuration is handled strictly through **Pydantic Models** and a single YAML file, ensuring type safety and validation at startup.

### 5.1 Structure (`config.yaml`)
*   **`django`**: Core web settings (Debug, Secret Key).
*   **`mongo`**: Database connection details.
*   **`redis`**: Broker connection details.
*   **`prometheus`**: TSDB endpoints (Query & Write).

### 5.2 Loading Process
1.  App starts.
2.  Reads `OPENANOMALY_CONFIG_FILE` env var (default: `config.yaml`).
3.  Parses YAML content.
4.  Validates against `openanomaly.config.schema.AppConfig` Pydantic model.
5.  Injects values into Django `settings.py`.

---

## 6. Deployment Topology

### Distributed (Docker Compose / K8s)
*   **`api`**: Serves the Admin UI and API. Stateless.
*   **`beat`** (x2): Scheduler. One active leader.
*   **`worker`** (xN): Inference workers. Scalable.
*   **`redis`**: Message Broker & Schedule Store.
*   **`mongo`**: Persistent storage for Pipelines and Users.
