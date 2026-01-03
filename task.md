# OpenAnomaly Development Tasks

## Phase 1: Foundation (Infrastructure)
- [ ] **Environment Setup** <!-- id: 0 -->
    - [x] **Nix**: Create `flake.nix` for Latest Supported Python (e.g. 3.14+) + system tools <!-- id: 100 -->
    - [/] **UV**: Initialize project with `uv init`, add dependencies (`fastapi`, `celery`, `pymongo`, `nixtla`, `streamlit`) <!-- id: 101 -->
    - [x] `docker-compose.yml`: Add MongoDB, MinIO (S3), **VictoriaMetrics (Single)** <!-- id: 1 -->
- [ ] **Core Modules** <!-- id: 3 -->
    - [ ] **Config**: Implement `ConfigStore` Interface + `MongoStore` (Prod) + `FileStore` (Lite-JSON) <!-- id: 4 -->
    - [ ] **Dispatcher**: Implement `Dispatcher` Interface + `CeleryDispatcher` (Prod) + `LocalDispatcher` (Lite) <!-- id: 5 -->
    - [ ] **Artifacts**: Implement `ArtifactStore` Interface + `S3Store` (Prod) + `FileStore` (Lite) <!-- id: 6 -->
    - [ ] **TSDB**: Implement `PrometheusReader` and `PrometheusRemoteWriter` (Compatible with VM) <!-- id: 7 -->

## Phase 2: The Workers (The Engine)
- [ ] **Model Engine (Generic)** <!-- id: 8 -->
    - [ ] Implement `NixtlaAdapter` (Supports `Stats/ML/Neural` via config) <!-- id: 9 -->
- [ ] **Training Worker** <!-- id: 10 -->
    - [ ] Create `services/trainer/main.py` entrypoint <!-- id: 11 -->
    - [ ] Logic: Consume Job -> Fetch VM Data -> Fit Model -> Save to S3 -> Update Mongo <!-- id: 12 -->
- [ ] **Inference Worker** <!-- id: 13 -->
    - [ ] Create `services/inferencer/main.py` entrypoint <!-- id: 14 -->
    - [ ] Logic: Consume Job -> Load S3 Model (Cache) -> Fetch Context -> Predict -> Write VM <!-- id: 15 -->
- [ ] **Dockerization** <!-- id: 16 -->
    - [ ] **Dockerfile**: Create multi-stage Dockerfile (Agent/Worker/API) <!-- id: 25 -->
    - [ ] **Compose**: Update `docker-compose.yml` to run full "Cluster Mode" (API + Worker + Scheduler services) <!-- id: 26 -->

## Phase 3: Controller & UI
- [ ] **Controller Services** <!-- id: 16 -->
    - [ ] **Scheduler**: Setup **Celery Beat** with `celerybeat-mongo` for dynamic scheduling <!-- id: 17 -->
    - [ ] **API**: Stateless FastAPI service for managing config <!-- id: 19 -->
- [ ] **Interactive UI (Streamlit)** <!-- id: 20 -->
    - [ ] Setup `ui/app.py` <!-- id: 21 -->
    - [ ] **Playground**: Graph component using `plotly` <!-- id: 22 -->
    - [ ] **Management**: Streamlit Forms for Mongo CRUD (Pipelines/Schedules) <!-- id: 23 -->
