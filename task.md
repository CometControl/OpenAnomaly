# OpenAnomaly Development Tasks

## Phase 1: Core Engine
- [ ] **Environment Setup** <!-- id: 0 -->
    - [x] **Nix**: Create `flake.nix` for Python 3.11+ <!-- id: 100 -->
    - [ ] **UV**: Update dependencies (per-model libraries as needed) <!-- id: 101 -->
    - [ ] `docker-compose.yml`: Redis + VictoriaMetrics for testing <!-- id: 1 -->
- [ ] **Core Ports & Adapters** <!-- id: 3 -->
    - [ ] **TSDBClient Port**: Interface for Prometheus Query + Remote Write <!-- id: 4 -->
    - [ ] **PrometheusAdapter**: Implementation using `requests` <!-- id: 5 -->
    - [ ] **ModelEngine Port**: Interface for `predict(context) -> forecast` (local or remote) <!-- id: 6 -->
    - [ ] **RemoteModelAdapter**: HTTP client for external inference endpoints <!-- id: 7 -->
    - [ ] **ConfigStore Port**: Interface for loading pipeline definitions <!-- id: 8 -->
    - [ ] **YamlAdapter**: Implementation for file-based config <!-- id: 9 -->
    - [ ] **Scheduler Port**: Interface for Celery Beat <!-- id: 10 -->
    - [ ] **CeleryBeatAdapter**: Implementation with SQLite/Redis backend <!-- id: 11 -->
- [ ] **Domain Models** <!-- id: 12 -->
    - [ ] **Pipeline dataclass**: Full schema (mode, schedules, covariates, anomaly config) <!-- id: 13 -->
    - [ ] **JSON Schema**: Generate `pipeline.schema.json` from Pydantic model <!-- id: 14 -->
- [ ] **Inference Loop Service** <!-- id: 15 -->
    - [ ] Implement `InferenceLoop` in `core/services/` <!-- id: 16 -->
    - [ ] Logic: Fetch Data -> Run TSFM -> Score Anomaly (if enabled) -> Write Results <!-- id: 17 -->

## Phase 2: Productionize
- [ ] **Dockerization** <!-- id: 18 -->
    - [ ] **Dockerfile**: Multi-stage build (GPU optional) <!-- id: 19 -->
    - [ ] **Compose**: Local testing stack <!-- id: 20 -->
- [ ] **Helm Chart** <!-- id: 21 -->
    - [ ] Create `charts/openanomaly` <!-- id: 22 -->
    - [ ] Beat Pod, Worker Pods, API Pod (optional) <!-- id: 23 -->

## Phase 3: Management & UI
- [ ] **API** <!-- id: 24 -->
    - [ ] FastAPI service with JSON Schema validation <!-- id: 25 -->
    - [ ] CRUD for pipelines (requires `MongoAdapter`) <!-- id: 26 -->
- [ ] **UI** <!-- id: 27 -->
    - [ ] Streamlit Playground for ad-hoc forecasting <!-- id: 28 -->
    - [ ] Visualization of anomaly scores over time <!-- id: 29 -->

## Phase 4: Model Adapters (Research Required)
- [ ] **Chronos Adapter** <!-- id: 30 -->
    - [ ] Research official documentation and best practices <!-- id: 31 -->
    - [ ] Implement `adapters/models/chronos/` <!-- id: 32 -->
- [ ] **TimesFM Adapter** <!-- id: 33 -->
    - [ ] Research official documentation and best practices <!-- id: 34 -->
    - [ ] Implement `adapters/models/timesfm/` <!-- id: 35 -->
- [ ] **Additional Adapters** (as needed) <!-- id: 36 -->
