# OpenAnomaly Helm Chart

Zero-shot anomaly detection for Prometheus-compatible TSDBs using Time Series Foundation Models.

## TL;DR

```bash
helm install openanomaly ./helm/openanomaly \
  --set image.registry=your-registry \
  --set image.repository=openanomaly \
  --set secrets.secretKey="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
```

---

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- MongoDB (if not using bundled dependency)
- Redis (if not using bundled dependency)

---

## Installing the Chart

### 1. Build Docker Images

OpenAnomaly supports **two build modes**:

**Light Mode** (~500MB) - No ML models, uses remote inference:
```bash
docker build --build-arg INSTALL_ML=false -t your-registry/openanomaly:0.1.0-light .
docker push your-registry/openanomaly:0.1.0-light
```

**Heavy Mode** (~5-8GB) - Includes ML models for local inference:
```bash
docker build --build-arg INSTALL_ML=true -t your-registry/openanomaly:0.1.0-heavy .
docker push your-registry/openanomaly:0.1.0-heavy
```

### 2. Install with Helm

```bash
helm install openanomaly ./helm/openanomaly \
  --set image.registry=your-registry \
  --set image.repository=openanomaly \
  --set image.tag=0.1.0 \
  --set secrets.secretKey="YOUR-SECRET-KEY"
```

### 3. Install with Custom Values

```bash
# Create custom values file
cat > my-values.yaml <<EOF
image:
  registry: docker.io
  repository: myorg/openanomaly
  tag: 0.1.0

buildMode:
  api: light
  worker: heavy
  beat: light

api:
  replicaCount: 3
  service:
    type: LoadBalancer

worker:
  replicaCount: 5
  autoscaling:
    maxReplicas: 15

config:
  mongo:
    url: mongodb://my-external-mongo:27017
  redis:
    url: redis://my-external-redis:6379/0

secrets:
  secretKey: "my-generated-secret-key"
EOF

# Install
helm install openanomaly ./helm/openanomaly -f my-values.yaml
```

---

## Configuration

The following table lists the configurable parameters and their default values.

### Image Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.registry` | Image registry | `docker.io` |
| `image.repository` | Image repository | `your-org/openanomaly` |
| `image.tag` | Image tag | `""` (chart appVersion) |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### Build Modes

| Parameter | Description | Default |
|-----------|-------------|---------|
| `buildMode.api` | API image mode (light/heavy) | `light` |
| `buildMode.worker` | Worker image mode (light/heavy) | `heavy` |
| `buildMode.beat` | Beat image mode (light/heavy) | `light` |

### API Component

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.enabled` | Enable API deployment | `true` |
| `api.replicaCount` | Number of API replicas | `2` |
| `api.service.type` | Kubernetes service type | `LoadBalancer` |
| `api.service.port` | Service port | `8000` |
| `api.resources.requests.memory` | Memory request | `512Mi` |
| `api.resources.requests.cpu` | CPU request | `250m` |

### Worker Component

| Parameter | Description | Default |
|-----------|-------------|---------|
| `worker.enabled` | Enable worker deployment | `true` |
| `worker.replicaCount` | Number of worker replicas | `3` |
| `worker.autoscaling.enabled` | Enable HPA | `true` |
| `worker.autoscaling.minReplicas` | Minimum replicas | `3` |
| `worker.autoscaling.maxReplicas` | Maximum replicas | `10` |
| `worker.resources.requests.memory` | Memory request | `2Gi` |
| `worker.resources.requests.cpu` | CPU request | `1` |

### Beat (Scheduler) Component

| Parameter | Description | Default |
|-----------|-------------|---------|
| `beat.enabled` | Enable beat deployment | `true` |
| `beat.replicaCount` | Number of beat replicas (HA) | `2` |
| `beat.resources.requests.memory` | Memory request | `256Mi` |
| `beat.resources.requests.cpu` | CPU request | `100m` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.django.debug` | Enable Django debug mode | `false` |
| `config.mongo.url` | MongoDB connection URL | `mongodb://mongodb:27017` |
| `config.mongo.dbName` | MongoDB database name | `openanomaly` |
| `config.redis.url` | Redis connection URL | `redis://redis:6379/0` |
| `config.prometheus.url` | Prometheus query URL | `http://prometheus:9090` |

### Secrets

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.secretKey` | Django secret key | `CHANGE_ME_IN_PRODUCTION` |

---

## Upgrading

```bash
helm upgrade openanomaly ./helm/openanomaly -f my-values.yaml
```

---

## Uninstalling

```bash
helm uninstall openanomaly
```

---

## Architecture

OpenAnomaly deploys as 3 microservices:

- **API** (2 replicas) - Django REST API with Swagger UI
- **Worker** (3-10 replicas) - Celery workers for ML inference (auto-scales)
- **Beat** (2 replicas) - Celery Beat scheduler with RedBeat (HA active-passive)

All components share configuration via ConfigMap and communicate through Redis.

---

## Build Modes Explained

### Why Two Modes?

| Feature | Light Mode | Heavy Mode |
|---------|-----------|------------|
| **Image Size** | ~500MB | ~5-8GB |
| **Startup Time** | Fast (~10s) | Slower (~30s) |
| **Model Location** | Remote API | Local (in-memory) |
| **Use Case** | Cost-effective, scalable | Low-latency, offline |
| **RAM Required** | 512MB | 2-8GB |
| **Best For** | API, Beat | Workers |

### Recommended Configuration

```yaml
buildMode:
  api: light      # API doesn't need ML models
  worker: heavy   # Workers run inference locally
  beat: light     # Scheduler doesn't need ML models
```

---

## Examples

### Minimal Installation

```bash
helm install openanomaly ./helm/openanomaly \
  --set secrets.secretKey="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
```

### Production Installation

```bash
helm install openanomaly ./helm/openanomaly \
  --set image.registry=myregistry.io \
  --set image.repository=openanomaly \
  --set api.replicaCount=3 \
  --set worker.autoscaling.maxReplicas=20 \
  --set config.mongo.url=mongodb://prod-mongo:27017 \
  --set secrets.secretKey="$PROD_SECRET_KEY"
```

### Development Installation

```bash
helm install openanomaly ./helm/openanomaly \
  --set config.django.debug=true \
  --set api.service.type=NodePort \
  --set worker.replicaCount=1
```

---

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -l app.kubernetes.io/name=openanomaly
```

### View Logs
```bash
# API logs
kubectl logs -l app.kubernetes.io/component=api

# Worker logs
kubectl logs -l app.kubernetes.io/component=worker

# Beat logs
kubectl logs -l app.kubernetes.io/component=beat
```

### Verify Configuration
```bash
kubectl get configmap openanomaly-config -o yaml
```
