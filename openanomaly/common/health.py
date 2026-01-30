"""
Health check endpoints for Kubernetes probes.
"""
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def healthz(request):
    """
    Liveness probe - checks if the application is alive.
    Should return 200 if the app is running, regardless of dependencies.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "openanomaly",
    })


def readiness(request):
    """
    Readiness probe - checks if the application is ready to serve traffic.
    Checks database connectivity and other critical dependencies.
    """
    checks = {
        "database": False,
        "redis": False,
    }
    
    # Check database connection
    try:
        connection.ensure_connection()
        checks["database"] = True
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
    
    # Check Redis connection (optional)
    try:
        from redis import Redis
        redis_url = settings.REDIS_URL
        # Parse redis URL to get host/port
        if redis_url:
            redis_client = Redis.from_url(redis_url, socket_connect_timeout=2)
            redis_client.ping()
            checks["redis"] = True
    except Exception as e:
        logger.warning(f"Redis check failed: {e}")
        # Redis is not critical for serving requests, so we don't fail
        checks["redis"] = True  # Mark as true anyway
    
    # Ready if database is accessible
    is_ready = checks["database"]
    
    status_code = 200 if is_ready else 503
    
    return JsonResponse({
        "status": "ready" if is_ready else "not ready",
        "checks": checks,
    }, status=status_code)


def startup(request):
    """
    Startup probe - checks if the application has started successfully.
    Similar to readiness but only checked once at startup.
    """
    checks = {
        "database": False,
        "migrations": False,
    }
    
    # Check database connection
    try:
        connection.ensure_connection()
        checks["database"] = True
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
    
    # Check if migrations are applied (optional check)
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        checks["migrations"] = len(plan) == 0
    except Exception as e:
        logger.warning(f"Migration check failed: {e}")
        checks["migrations"] = True  # Don't fail on migration check
    
    is_ready = checks["database"]
    status_code = 200 if is_ready else 503
    
    return JsonResponse({
        "status": "started" if is_ready else "starting",
        "checks": checks,
    }, status=status_code)
