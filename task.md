# OpenAnomaly Development Tasks

## Phase 1: Core Engine
- [ ] **Environment Setup** <!-- id: 0 -->
    - [x] **Nix**: Create `flake.nix` for Python 3.11+ (required for Chronos) <!-- id: 100 -->
    - [ ] **UV**: Update dependencies (`chronos-forecasting`, `torch`, `transformers`) <!-- id: 101 -->
    - [ ] `docker-compose.yml`: Simplify to VictoriaMetrics only (for testing) <!-- id: 1 -->
- [ ] **Core Ports & Adapters** <!-- id: 3 -->
    - [ ] **TSDBClient Port**: Interface for Prometheus Query + Remote Write <!-- id: 4 -->
    - [ ] **PrometheusAdapter**: Implementation using `requests` <!-- id: 5 -->
    - [ ] **ModelEngine Port**: Interface for `predict(context) -> forecast` <!-- id: 6 -->
    - [ ] **ChronosAdapter**: Implementation using `chronos-forecasting` library <!-- id: 7 -->
    - [ ] **ConfigStore Port**: Interface for loading pipeline definitions <!-- id: 8 -->
    - [ ] **YamlAdapter**: Implementation for file-based config <!-- id: 9 -->
- [ ] **Inference Loop Service** <!-- id: 10 -->
    - [ ] Implement `InferenceLoop` in `core/services/` <!-- id: 11 -->
    - [ ] Logic: Fetch Data -> Run TSFM -> Score Anomaly -> Write Results <!-- id: 12 -->

## Phase 2: Productionize
- [ ] **Scheduling** <!-- id: 13 -->
    - [ ] **Scheduler Port**: Interface for triggering jobs <!-- id: 14 -->
    - [ ] **APSchedulerAdapter**: Implementation for standalone mode <!-- id: 15 -->
- [ ] **Dockerization** <!-- id: 16 -->
    - [ ] **Dockerfile**: Create multi-stage Dockerfile (GPU optional) <!-- id: 17 -->
    - [ ] **Compose**: Update `docker-compose.yml` for local testing <!-- id: 18 -->
- [ ] **Helm Chart** <!-- id: 19 -->
    - [ ] Create `charts/openanomaly` <!-- id: 20 -->
    - [ ] Configure `values.yaml` for TSDB connection and model selection <!-- id: 21 -->

## Phase 3: Management & UI
- [ ] **API (Optional)** <!-- id: 22 -->
    - [ ] FastAPI service for CRUD on pipelines <!-- id: 23 -->
    - [ ] Requires `MongoAdapter` for `ConfigStore` <!-- id: 24 -->
- [ ] **UI (Optional)** <!-- id: 25 -->
    - [ ] Streamlit Playground for ad-hoc forecasting <!-- id: 26 -->
    - [ ] Visualization of anomaly scores over time <!-- id: 27 -->
