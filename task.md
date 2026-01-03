# OpenAnomaly Development Tasks

## Phase 1: Foundation (Infrastructure)
- [ ] **Environment Setup** <!-- id: 0 -->
    - [x] **Nix**: Create `flake.nix` for Latest Supported Python (e.g. 3.14+) + system tools <!-- id: 100 -->
    - [x] **UV**: Initialize project with `uv init`, add dependencies (`fastapi`, `celery`, `pymongo`, `nixtla`, `streamlit`) <!-- id: 101 -->
    - [x] `docker-compose.yml`: Add MongoDB, MinIO (S3), **VictoriaMetrics (Single)** <!-- id: 1 -->
- [ ] **Core Modules** <!-- id: 3 -->
    - [ ] **Config**: Implement `ConfigStore` Interface + `MongoStore` (Prod) + `YamlStore` (Dev-File) <!-- id: 4 -->
    - [ ] **Dispatcher**: Implement `JobDispatcher` Interface + `CeleryDispatcher` (Redis/SQLite) <!-- id: 5 -->
    - [ ] **Artifacts**: Implement `ArtifactStore` Interface + `S3Store` (MinIO) + `FileStore` (Local) + `NoOpStore` (Stat-Only) <!-- id: 6 -->
    - [ ] **TSDB**: Implement `PrometheusReader` and `PrometheusRemoteWriter` (Compatible with VM) <!-- id: 7 -->

## Phase 2: The Workers (The Engine)
- [ ] **Model Engine (Port)** <!-- id: 8 -->
    - [ ] Implement `ModelEngine` Interface <!-- id: 9 -->
    - [ ] Implement `NixtlaAdapter` (Stats/ML/Neural) <!-- id: 9a -->
    - [ ] Implement `DartsAdapter` (Optional/Future) <!-- id: 9b -->
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
- [ ] **UserInterface (Port)** <!-- id: 20 -->
    - [ ] Implement `UserInterface` Interface <!-- id: 21 -->
    - [ ] **StreamlitAdapter**: Implement default UI <!-- id: 21a -->
        - [ ] **Playground**: Graph component using `plotly` <!-- id: 22 -->
        - [ ] **Management**: CRUD for Mongo/YAML Pipelines <!-- id: 23 -->

## Phase 4: Deployment (Production)
- [ ] **Helm Chart** <!-- id: 27 -->
    - [ ] Create `charts/openanomaly` <!-- id: 28 -->
    - [ ] **Dependencies**: Add `redis`, `mongodb`, `minio` as optional subcharts (Bitnami) <!-- id: 29 -->
    - [ ] **Values**: Configure `values.yaml` to toggle between internal (subchart) and external infra <!-- id: 30 -->
