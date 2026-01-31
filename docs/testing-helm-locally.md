# Testing OpenAnomaly Helm Chart Locally

## Quick Start

```powershell
# Run the automated test script
.\scripts\test-helm-local.ps1
```

## Prerequisites

1. **Enable Kubernetes in Docker Desktop**
   - Open Docker Desktop
   - Settings → Kubernetes
   - Check "Enable Kubernetes"
   - Apply & Restart

2. **Install Helm** (if not already installed)
   ```powershell
   choco install kubernetes-helm  # or download from helm.sh
   ```

## Manual Testing Steps

### 1. Build Images

```powershell
# Build light image (API, Beat)
docker build --build-arg INSTALL_ML=false -t openanomaly:0.1.0-light .

# Build heavy image (Worker)
docker build --build-arg INSTALL_ML=true -t openanomaly:0.1.0-heavy .
```

### 2. Deploy Dependencies

```powershell
# Add Bitnami repo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install Redis (no persistence for testing)
helm install redis bitnami/redis `
  --set auth.enabled=false `
  --set master.persistence.enabled=false

# Install MongoDB (no persistence for testing)
helm install mongodb bitnami/mongodb `
  --set auth.enabled=false `
  --set persistence.enabled=false
```

### 3. Deploy OpenAnomaly

```powershell
# Install with test values
helm install openanomaly ./helm/openanomaly -f ./helm/test-values.yaml

# Watch pods start
kubectl get pods -w
```

### 4. Access the API

```powershell
# Check service
kubectl get svc

# Access on localhost (Docker Desktop auto-exposes LoadBalancer)
# Visit: http://localhost:8000/api/docs/

# Or port-forward if needed
kubectl port-forward svc/openanomaly-api 8000:8000
```

### 5. Test Endpoints

```powershell
# Health check
curl http://localhost:8000/health

# Swagger UI
start http://localhost:8000/api/docs/

# List pipelines
curl http://localhost:8000/pipelines/
```

## Debugging

```powershell
# View pod status
kubectl get pods

# View logs
kubectl logs -l app.kubernetes.io/component=api
kubectl logs -l app.kubernetes.io/component=worker
kubectl logs -l app.kubernetes.io/component=beat

# Describe pod
kubectl describe pod -l app.kubernetes.io/name=openanomaly

# View events
kubectl get events --sort-by='.lastTimestamp'
```

## Cleanup

```powershell
# Using the script
.\scripts\test-helm-local.ps1 -Cleanup

# Or manually
helm uninstall openanomaly
helm uninstall redis
helm uninstall mongodb
```

## Script Options

```powershell
# Skip Docker build (use existing images)
.\scripts\test-helm-local.ps1 -SkipBuild

# Clean up only
.\scripts\test-helm-local.ps1 -Cleanup
```

## Troubleshooting

### Pods not starting?

```powershell
# Check pod status
kubectl describe pod <pod-name>

# Check if images exist locally
docker images | findstr openanomaly
```

### Can't access API?

```powershell
# Check service
kubectl get svc openanomaly-api

# Try port-forward
kubectl port-forward svc/openanomaly-api 8000:8000
```

### Out of resources?

Edit `helm/test-values.yaml` to reduce resource requests:
```yaml
api:
  resources:
    requests:
      memory: 128Mi
      cpu: 50m
```
