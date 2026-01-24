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

- [x] **Training Support** (User Request) <!-- id: 40 -->
    - [x] Update `Pipeline` domain model with `TrainingConfig` (`schedule`, `window`, `parameters`) <!-- id: 41 -->
    - [x] Update `ModelEngine` interface with `train()` abstract method <!-- id: 42 -->
    - [x] Register `openanomaly.tasks.train_model` in `main.py` <!-- id: 43 -->
    - [x] Implement `run_training_task` logic (fetch data -> train -> log) <!-- id: 44 -->
    - [x] Create `RemoteTrainableAdapter` (Implemented in `RemoteModelAdapter`) <!-- id: 45 -->

- [x] **Flexible Serialization** (User Request) <!-- id: 50 -->
    - [x] Update `ModelConfig` with `serialization_format` field (json/arrow) <!-- id: 51 -->
    - [x] Update `RemoteModelAdapter` to handle arrow (Feather) serialization <!-- id: 52 -->
    - [x] Update `technical_design.md` with arrow capabilities <!-- id: 53 -->

- [x] **API Triggers** (User Request) <!-- id: 54 -->
    - [x] `POST /pipelines/{name}/inference` (Renamed from trigger) <!-- id: 55 -->
    - [x] `POST /pipelines/{name}/train` (Training) <!-- id: 56 -->
    - [x] `POST /execute/inference` (Stateless Ad-hoc, Writes to TSDB) <!-- id: 57 -->
    - [x] `POST /execute/train` (Stateless Ad-hoc) <!-- id: 60 -->

- [x] **System Configuration (YAML)** (User Request) <!-- id: 61 -->
    - [x] Create `SystemSettings` domain model <!-- id: 62 -->
    - [x] Create `load_settings` adapter (YAML loader) <!-- id: 63 -->
    - [x] Integrate `load_settings` into `main.py` <!-- id: 64 -->
    - [x] Create default `config.yaml` <!-- id: 65 -->

- [x] **Verification & Testing** (User Request) <!-- id: 66 -->
    - [x] Unit Test: `SystemSettings` & `load_settings` <!-- id: 67 -->
    - [x] API Test: `POST /pipelines/{name}/inference` & `/train` <!-- id: 68 -->
    - [x] API Test: `POST /execute/inference` & `/train` <!-- id: 69 -->

- [x] **MongoDB Config Store** (User Request) <!-- id: 70 -->
    - [x] Update `SystemSettings` with Mongo fields <!-- id: 71 -->
    - [x] Implement `MongoConfigStore` adapter (Motor) <!-- id: 72 -->
    - [x] Implement `get_config_store` factory in `main.py` <!-- id: 73 -->
    - [x] Update Celery tasks to use factory <!-- id: 74 -->
    - [x] Add unit/integration tests for Mongo Store <!-- id: 75 -->

- [ ] **Management API (MongoDB + FastAPI)** <!-- id: 3 -->
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
