"""
Seed Data Script for OpenAnomaly Integration Testing.
Generates synthetic metrics and pushes them to VictoriaMetrics.
"""
import asyncio
import time
import math
import random
from datetime import datetime
import httpx

VM_URL = "http://localhost:8428"

async def seed_metrics(metric_name="test_metric", history_minutes=60, future_minutes=15, anomaly_at=50):
    """
    Seed metrics with both history (for model context) and future (for ground truth).
    """
    duration_minutes = history_minutes + future_minutes
    print(f"Seeding {metric_name}: -{history_minutes}m (History) to +{future_minutes}m (Future)...")
    
    # Generate data points
    lines = []
    now = int(time.time())
    start_time = now - (history_minutes * 60)
    
    # Generate points from start_time up to start_time + duration
    for i in range(duration_minutes):
        t = start_time + (i * 60)
        
        # Sine wave base
        val = 10 + 5 * math.sin(i / 10.0)
        
        # Add noise
        val += random.uniform(-0.5, 0.5)
        
        # Inject anomaly (if within range)
        if i == anomaly_at:
            val += 20  # SPIKE
            
        # Prometheus text format: metric_name{label="val"} value timestamp_ms
        lines.append(f'{metric_name}{{env="test"}} {val:.2f} {t * 1000}')

    payload = "\n".join(lines)
    
    async with httpx.AsyncClient() as client:
        # VictoriaMetrics allows import via /api/v1/import/prometheus
        url = f"{VM_URL}/api/v1/import/prometheus"
        print(f"Pushing to {url}...")
        
        response = await client.post(url, content=payload)
        
        if response.status_code == 204:
            print("Successfully seeded data.")
        else:
            print(f"Failed to seed: {response.status_code} {response.text}")

if __name__ == "__main__":
    asyncio.run(seed_metrics())
