"""
End-to-End Integration Test for OpenAnomaly.
Runs against the Docker stack (localhost ports).
Uses real BOOM benchmark data from HuggingFace.
"""
import pytest
import httpx
import pandas as pd
from pathlib import Path
import time
from celery import Celery

# Config
VM_READ_URL = "http://localhost:8428"
VM_IMPORT_URL = "http://localhost:8428/api/v1/import/prometheus"
VM_DELETE_URL = "http://localhost:8428/api/v1/admin/tsdb/delete_series"
REDIS_URL = "redis://localhost:6379/0"

@pytest.mark.asyncio
async def test_e2e_pipeline_execution():
    """
    1. Clear VictoriaMetrics
    2. Seed BOOM Data
    3. Write Pipeline Config
    4. Trigger Worker
    5. Verify Results
    """
    
    # --- 0. Clear VictoriaMetrics ---
    print("\n[0] Clearing VictoriaMetrics data...")
    async with httpx.AsyncClient() as client:
        # Delete all boom_* and openanomaly_* metrics
        for match_query in ["boom_.*", "openanomaly_.*", "e2e_.*"]:
            resp = await client.post(
                VM_DELETE_URL,
                params={"match[]": f'{{{__name__}=~"{match_query}"}}'}
            )
            print(f"  Deleted {match_query}: {resp.status_code}")
    
    # Wait for deletion to propagate
    time.sleep(1)
    
    # --- 1. Seed BOOM Data ---
    csv_path = Path("data/boom_sample.csv")
    assert csv_path.exists(), f"BOOM sample not found at {csv_path}. Run scripts/fetch_boom_sample.py first."
    
    print(f"\n[1] Seeding BOOM data from {csv_path}...")
    df = pd.read_csv(csv_path)
    df['dt'] = pd.to_datetime(df['timestamp'])
    
    # Shift time to end at 'now' (UTC to match worker)
    last_ts = df['dt'].max()
    # Use tz-naive UTC
    now_pd = pd.Timestamp.now(tz='UTC').tz_localize(None)
    # Make last_ts tz-naive if needed
    if last_ts.tzinfo is not None:
        last_ts = last_ts.tz_localize(None)
    delta = now_pd - last_ts
    df['dt'] += delta
    
    # Get unique series
    series_ids = df['item_id'].unique()
    print(f"  Found {len(series_ids)} series: {list(series_ids)}")
    
    # Build Prometheus text format lines
    lines = []
    for _, row in df.iterrows():
        ts_millis = int(row['dt'].timestamp() * 1000)
        val = row['value']
        metric_name = row['item_id']  # e.g., boom_0
        lines.append(f'{metric_name}{{source="boom"}} {val} {ts_millis}')
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(VM_IMPORT_URL, content="\n".join(lines))
        assert resp.status_code == 204, f"Seed failed: {resp.text}"
    
    print(f"  Seeded {len(lines)} points across {len(series_ids)} series.")
    
    # --- 2. Write Pipeline Config ---
    # Use the first BOOM series for the pipeline
    target_metric = series_ids[0]  # e.g., boom_0
    print(f"\n[2] Creating pipelines.yaml for {target_metric}...")
    
    pipeline_yaml = f"""
pipelines:
  - name: boom_pipeline
    query: {target_metric}{{source="boom"}}
    step: 1m
    context_window: 1h
    prediction_horizon: 15m
    model:
      type: local
      id: autogluon/chronos-2-small
    output:
       metric_prefix: openanomaly_
"""
    with open("pipelines.yaml", "w") as f:
        f.write(pipeline_yaml)
        
    # --- 3. Trigger Task ---
    print("\n[3] Triggering Celery Task...")
    celery = Celery("e2e_test", broker=REDIS_URL, backend=REDIS_URL)
    
    task = celery.send_task("openanomaly.tasks.run_inference", args=["boom_pipeline"])
    
    print(f"Task ID: {task.id}. Waiting for result...")
    try:
        result = task.get(timeout=60)  # Longer timeout for model loading
        print(f"Task Result: {result}")
        assert "Success" in str(result)
    except Exception as e:
        pytest.fail(f"Task failed or timed out: {e}")

    # --- 4. Verify Results in TSDB ---
    print("\n[4] Verifying Forecast Metrics in VictoriaMetrics...")
    
    expected_metric = 'openanomaly_boom_pipeline_forecast'
    
    found = False
    async with httpx.AsyncClient() as client:
        for attempt in range(10):
            now_ts = time.time()
            params = {
                "query": expected_metric,
                "start": now_ts - 3600,
                "end": now_ts + 3600,
                "step": "1m"
            }
            resp = await client.get(f"{VM_READ_URL}/api/v1/query_range", params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                if data["status"] == "success" and data["data"]["result"]:
                    series_count = len(data['data']['result'])
                    points_count = len(data['data']['result'][0]['values'])
                    print(f"Found forecast metrics: {series_count} series, {points_count} points")
                    found = True
                    break
                else:
                    print(f"Query returned empty result.")
            else:
                print(f"Query failed: {resp.status_code}")
            
            print(f"Attempt {attempt+1}: Metric not found yet...")
            time.sleep(2)
            
    assert found, "Forecast metric was not found in VictoriaMetrics after task execution!"
    print("\n[SUCCESS] E2E Integration Test Passed!")
