#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test OpenAnomaly Helm chart on Docker Desktop Kubernetes
.DESCRIPTION
    This script automates the deployment and testing of OpenAnomaly on local K8s:
    1. Checks if Kubernetes is enabled
    2. Builds Docker images locally
    3. Deploys Redis and MongoDB
    4. Installs OpenAnomaly with Helm
    5. Waits for pods to be ready
    6. Port-forwards and tests the API
.EXAMPLE
    .\test-helm-local.ps1
    .\test-helm-local.ps1 -SkipBuild  # Skip docker build
    .\test-helm-local.ps1 -Cleanup     # Clean up only
#>

param(
    [switch]$SkipBuild,
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n===> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Cleanup function
function Cleanup-Deployment {
    Write-Step "Cleaning up existing deployments..."
    
    helm uninstall openanomaly 2>$null
    if ($?) { Write-Success "Uninstalled openanomaly" }
    
    helm uninstall redis 2>$null
    if ($?) { Write-Success "Uninstalled redis" }
    
    helm uninstall mongodb 2>$null
    if ($?) { Write-Success "Uninstalled mongodb" }
    
    Write-Success "Cleanup complete"
}

if ($Cleanup) {
    Cleanup-Deployment
    exit 0
}

# Check if kubectl is available
Write-Step "Checking prerequisites..."
try {
    kubectl version --client --short 2>$null | Out-Null
    Write-Success "kubectl is installed"
} catch {
    Write-Error "kubectl not found. Please enable Kubernetes in Docker Desktop."
    exit 1
}

# Check if Kubernetes is running
try {
    kubectl cluster-info 2>$null | Out-Null
    Write-Success "Kubernetes cluster is running"
} catch {
    Write-Error "Kubernetes cluster not accessible. Please enable Kubernetes in Docker Desktop (Settings -> Kubernetes -> Enable Kubernetes)"
    exit 1
}

# Check if Helm is installed
try {
    helm version --short 2>$null | Out-Null
    Write-Success "Helm is installed"
} catch {
    Write-Error "Helm not found. Install from: https://helm.sh/docs/intro/install/"
    exit 1
}

# Build Docker images
if (-not $SkipBuild) {
    Write-Step "Building Docker images..."
    
    Write-Host "Building light image (API, Beat)..."
    docker build --build-arg INSTALL_ML=false -t openanomaly:0.1.0-light .
    if (-not $?) {
        Write-Error "Failed to build light image"
        exit 1
    }
    Write-Success "Built openanomaly:0.1.0-light"
    
    Write-Host "Building heavy image (Worker)..."
    docker build --build-arg INSTALL_ML=true -t openanomaly:0.1.0-heavy .
    if (-not $?) {
        Write-Error "Failed to build heavy image"
        exit 1
    }
    Write-Success "Built openanomaly:0.1.0-heavy"
} else {
    Write-Warning "Skipping Docker build (using existing images)"
}

# Add Bitnami repo
Write-Step "Adding Helm repositories..."
helm repo add bitnami https://charts.bitnami.com/bitnami 2>$null
helm repo update
Write-Success "Helm repos updated"

# Clean up any existing deployments
Write-Step "Cleaning up any existing deployments..."
Cleanup-Deployment

# Deploy Redis
Write-Step "Deploying Redis..."
helm install redis bitnami/redis `
    --set auth.enabled=false `
    --set master.persistence.enabled=false `
    --wait --timeout 2m
if (-not $?) {
    Write-Error "Failed to deploy Redis"
    exit 1
}
Write-Success "Redis deployed"

# Deploy MongoDB
Write-Step "Deploying MongoDB..."
helm install mongodb bitnami/mongodb `
    --set auth.enabled=false `
    --set persistence.enabled=false `
    --wait --timeout 2m
if (-not $?) {
    Write-Error "Failed to deploy MongoDB"
    Cleanup-Deployment
    exit 1
}
Write-Success "MongoDB deployed"

# Deploy OpenAnomaly
Write-Step "Deploying OpenAnomaly..."
helm install openanomaly ./helm/openanomaly `
    -f ./helm/test-values.yaml `
    --wait --timeout 5m
if (-not $?) {
    Write-Error "Failed to deploy OpenAnomaly"
    Cleanup-Deployment
    exit 1
}
Write-Success "OpenAnomaly deployed"

# Wait for all pods to be ready
Write-Step "Waiting for all pods to be ready..."
Start-Sleep -Seconds 10

$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $notReady = kubectl get pods -o json | ConvertFrom-Json | 
        Select-Object -ExpandProperty items | 
        Where-Object { $_.status.phase -ne "Running" -or $_.status.conditions.status -contains "False" }
    
    if (-not $notReady) {
        Write-Success "All pods are ready"
        break
    }
    
    $attempt++
    Write-Host "Waiting for pods... ($attempt/$maxAttempts)"
    Start-Sleep -Seconds 5
}

if ($attempt -eq $maxAttempts) {
    Write-Warning "Some pods may not be ready yet"
}

# Show deployment status
Write-Step "Deployment Status"
kubectl get pods
kubectl get svc

# Get the API service
Write-Step "Accessing the API..."
$apiService = kubectl get svc -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}'

if ($apiService) {
    Write-Host "`nAPI Service: $apiService"
    
    # Check if LoadBalancer is assigned
    $serviceType = kubectl get svc $apiService -o jsonpath='{.spec.type}'
    
    if ($serviceType -eq "LoadBalancer") {
        Write-Host "Waiting for LoadBalancer IP..."
        Start-Sleep -Seconds 5
        $externalIP = kubectl get svc $apiService -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
        
        if ($externalIP) {
            Write-Success "API available at: http://$externalIP:8000"
            Write-Success "Swagger UI: http://$externalIP:8000/api/docs/"
        } else {
            Write-Host "LoadBalancer IP not assigned yet, using localhost (Docker Desktop exposes on localhost)"
            Write-Success "API available at: http://localhost:8000"
            Write-Success "Swagger UI: http://localhost:8000/api/docs/"
        }
    } else {
        Write-Host "Setting up port-forward..."
        Write-Host "Run in another terminal:"
        Write-Host "  kubectl port-forward svc/$apiService 8000:8000" -ForegroundColor Yellow
    }
    
    # Test the API
    Write-Step "Testing API endpoints..."
    Start-Sleep -Seconds 5
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Success "Health check: OK"
        }
    } catch {
        Write-Warning "Health check failed. API may still be starting up."
        Write-Host "Try manually: http://localhost:8000/health"
    }
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/docs/" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Success "Swagger UI: OK"
        }
    } catch {
        Write-Warning "Swagger UI not accessible yet."
        Write-Host "Try manually: http://localhost:8000/api/docs/"
    }
}

Write-Step "Deployment Complete!"
Write-Host @"

📊 Next Steps:
  1. View pods:        kubectl get pods
  2. View logs:        kubectl logs -l app.kubernetes.io/component=api
  3. Access Swagger:   http://localhost:8000/api/docs/
  4. Test API:         curl http://localhost:8000/health

🧹 Cleanup:
  .\scripts\test-helm-local.ps1 -Cleanup

"@ -ForegroundColor Green
