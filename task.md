# OpenAnomaly Development Tasks

## Phase 1: Core Engine
- [x] **Environment Setup** <!-- id: 0 -->
    - [x] **Nix**: Create `flake.nix` for Python 3.11+ <!-- id: 100 -->
    - [x] **UV**: Update dependencies (per-model libraries as needed) <!-- id: 101 -->
    - [x] `docker-compose.yml`: Redis + VictoriaMetrics for testing <!-- id: 1 -->
- [x] **Core Ports & Adapters** <!-- id: 3 -->
    - [x] **TSDBClient Port**: Interface for Prometheus Query + Remote Write <!-- id: 4 -->
    - [x] **PrometheusAdapter**: Implementation using `requests` <!-- id: 5 -->
    - [x] **ModelEngine Port**: Interface for `predict(context) -> forecast` (local or remote) <!-- id: 6 -->
    - [x] **RemoteModelAdapter**: HTTP client for external inference endpoints <!-- id: 7 -->
    - [x] **ConfigStore Port**: Interface for loading pipeline definitions <!-- id: 8 -->
    - [x] **YamlAdapter**: Implementation for file-based config <!-- id: 9 -->
    - [x] **Scheduler Port**: Interface for Celery Beat <!-- id: 10 -->
    - [x] **CeleryBeatAdapter**: Implementation with SQLite/Redis backend <!-- id: 11 -->
- [x] **Domain Models** <!-- id: 12 -->
    - [x] **Pipeline dataclass**: Full schema (mode, schedules, covariates, anomaly config) <!-- id: 13 -->
    - [x] **JSON Schema**: Generate `pipeline.schema.json` from Pydantic model <!-- id: 14 -->
- [x] **Inference Loop Service** <!-- id: 15 -->
    - [x] Implement `InferenceLoop` in `core/services/` <!-- id: 16 -->
    - [x] Logic: Fetch Data -> Run TSFM -> Score Anomaly (if enabled) -> Write Results <!-- id: 17 -->

## Phase 1.5: Testing (In Progress)
- [x] **Test Infrastructure** <!-- id: 200 -->
    - [x] Setup `pytest` and `tests/` directory <!-- id: 201 -->
- [x] **Unit Tests** <!-- id: 202 -->
    - [x] `core/domain`: Pipeline & Config validation <!-- id: 203 -->
    - [x] `adapters/models`: ChronosAdapter (Mocked) <!-- id: 204 -->
    - [x] `adapters/tsdb`: PrometheusAdapter (Mocked) <!-- id: 205 -->
    - [x] `services`: InferenceLoop logic <!-- id: 206 -->

## Phase 2: Productionize
- [x] Setup pytest and basic fixtures <!-- id: 18 -->
- [x] Create integration test suite (`tests/integration`) <!-- id: 19 -->
	- [x] Test Prometheus Adapter with Real VM <!-- id: 20 -->
	- [x] Test Chronos Adapter with Model Download <!-- id: 21 -->
	- [x] Test End-to-End Inference Loop (Dockerized) <!-- id: 22 -->
- [x] Implement CI/CD pipeline (Optional) <!-- id: 23 -->

## Phase 3: Management & UI
- [x] **Data Integration** (User Request) <!-- id: 24 -->
    - [x] Integrate CSV loader into `test_e2e.py` <!-- id: 25 -->
    - [x] Create sample BOOM-like dataset (`data/boom_sample.csv`) <!-- id: 26 -->

- [ ] **API** <!-- id: 27 -->
    - [ ] FastAPI service with JSON Schema validation <!-- id: 28 -->
    - [ ] CRUD for pipelines (requires `MongoAdapter`) <!-- id: 29 -->
- [ ] **UI** <!-- id: 37 -->
    - [ ] Streamlit Playground for ad-hoc forecasting <!-- id: 38 -->
    - [ ] Visualization of anomaly scores over time <!-- id: 39 -->

## Phase 4: Model Adapters (Research Required)
- [x] **TSFM Research Guide** <!-- id: 50 -->
    - [x] Create `research/TSFM_GUIDE.md` covering models, benchmarks (TAB/TOTO), and datasets (BOOM) <!-- id: 51 -->
- [ ] **Chronos Adapter** <!-- id: 30 -->
    - [x] Research official documentation and best practices <!-- id: 31 -->
    - [x] Implement `adapters/models/chronos/` <!-- id: 32 -->
- [ ] **TimesFM Adapter** <!-- id: 33 -->
    - [x] Research official documentation and best practices <!-- id: 34 -->
    - [ ] Implement `adapters/models/timesfm/` <!-- id: 35 -->
- [ ] **Additional Adapters** (as needed) <!-- id: 36 -->
