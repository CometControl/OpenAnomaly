"""
Script to load ALL Datadog/BOOM datasets into VictoriaMetrics as live metrics.

All series share the same metric name 'boom' with labels:
  - series: Original BOOM series ID (e.g., ds_0_T)
  - domain: Domain from taxonomy (Infrastructure, Networking, etc.)
  - metric_type: Type from taxonomy (count, rate, gauge, distribution)
  - freq: Sampling frequency (T=1min, 5T=5min, 10S=10sec)

Usage:
    # Load first N series (default: 50)
    python scripts/load_boom_to_victoria.py --limit 50
    
    # Load all series
    python scripts/load_boom_to_victoria.py --all
    
    # Clear existing data first
    python scripts/load_boom_to_victoria.py --clear --limit 20
"""

import argparse
import asyncio
import json
import time
from pathlib import Path
import pandas as pd
import httpx
from huggingface_hub import hf_hub_download, list_repo_files
import pyarrow as pa

# Config
REPO_ID = "Datadog/BOOM"
DATA_DIR = Path("data/boom_raw")
VM_IMPORT_URL = "http://localhost:8428/api/v1/import/prometheus"
VM_DELETE_URL = "http://localhost:8428/api/v1/admin/tsdb/delete_series"
METRIC_NAME = "boom"  # Single metric name for all series

async def clear_vm_data():
    """Delete all existing boom metrics from VictoriaMetrics."""
    print("Clearing existing BOOM data from VictoriaMetrics...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            VM_DELETE_URL,
            params={"match[]": f'{METRIC_NAME}'}
        )
        print(f"  Deleted {METRIC_NAME}: {resp.status_code}")
        
        # Also clear forecast metrics
        resp = await client.post(
            VM_DELETE_URL,
            params={"match[]": 'openanomaly_boom.*'}
        )
        print(f"  Deleted openanomaly_boom.*: {resp.status_code}")
    time.sleep(1)

async def load_all_boom(limit: int = 50, clear: bool = False):
    """Load BOOM datasets into VictoriaMetrics."""
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if clear:
        await clear_vm_data()
    
    # 1. Download taxonomy
    print("\n=== Downloading BOOM Taxonomy ===")
    taxonomy_path = hf_hub_download(
        repo_id=REPO_ID,
        filename="dataset_taxonomy.json",
        repo_type="dataset",
        local_dir=str(DATA_DIR)
    )
    
    with open(taxonomy_path) as f:
        taxonomy = json.load(f)
    
    print(f"Loaded taxonomy for {len(taxonomy)} series.")
    
    # 2. List Arrow files
    print("\n=== Listing Arrow Files ===")
    files = list_repo_files(REPO_ID, repo_type="dataset")
    arrow_files = [f for f in files if f.endswith(".arrow")]
    folders = sorted(set(f.split("/")[0] for f in arrow_files))
    
    # Limit if specified
    if limit > 0:
        folders = folders[:limit]
    print(f"Will process {len(folders)} series.")
    
    # 3. Process each series
    total_points = 0
    failed = []
    
    # Shift timestamps to end at 'now' (UTC)
    now_utc = pd.Timestamp.now(tz='UTC').tz_localize(None)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, folder in enumerate(folders):
            series_id = folder
            target_file = f"{folder}/data-00000-of-00001.arrow"
            
            # Get taxonomy info
            meta = taxonomy.get(series_id, {})
            domains = meta.get("domain", ["Unknown"])
            types = meta.get("type", ["Unknown"])
            freq_suffix = series_id.split("-")[-1]  # T, 5T, 10S
            
            # Use first domain/type for primary label
            domain = domains[0] if domains else "Unknown"
            mtype = types[0] if types else "Unknown"
            
            try:
                print(f"\n[{i+1}/{len(folders)}] {series_id}: {domain} / {mtype} / {freq_suffix}")
                
                # Download Arrow file
                local_arrow = hf_hub_download(
                    repo_id=REPO_ID,
                    filename=target_file,
                    repo_type="dataset",
                    local_dir=str(DATA_DIR)
                )
                
                # Load Arrow via IPC stream
                with pa.OSFile(local_arrow, 'rb') as f:
                    reader = pa.ipc.open_stream(f)
                    table = reader.read_all()
                    df = table.to_pandas()
                
                if len(df) == 0:
                    print("  Empty, skipping.")
                    continue
                
                # Extract first variate (row)
                row = df.iloc[0]
                start_ts = pd.to_datetime(row['start'])
                values = row['target']
                
                # Map freq suffix to pandas freq
                freq_map = {"T": "min", "5T": "5min", "10S": "10s", "H": "h"}
                pd_freq = freq_map.get(freq_suffix, "min")
                
                # Create timestamps
                timestamps = pd.date_range(start=start_ts, periods=len(values), freq=pd_freq)
                
                # Position "now" at 80% of the series (80% past, 20% future)
                # This allows forecasts to be compared against actual future data
                if len(timestamps) > 0:
                    split_idx = int(len(timestamps) * 0.8)
                    reference_ts = timestamps[split_idx]  # This will become "now"
                    delta = now_utc - reference_ts
                    timestamps = timestamps + delta
                
                # Build Prometheus lines
                # Format: metric_name{label1="val1",...} value timestamp_ms
                metric_id = series_id.replace("-", "_")
                lines = []
                for ts, val in zip(timestamps, values):
                    ts_ms = int(ts.timestamp() * 1000)
                    # Escape quotes in labels
                    domain_safe = domain.replace('"', '\\"')
                    mtype_safe = mtype.replace('"', '\\"')
                    line = f'{METRIC_NAME}{{series="{metric_id}",domain="{domain_safe}",metric_type="{mtype_safe}",freq="{freq_suffix}"}} {val} {ts_ms}'
                    lines.append(line)
                
                # Push to VM
                resp = await client.post(VM_IMPORT_URL, content="\n".join(lines))
                if resp.status_code == 204:
                    print(f"  Loaded {len(lines)} points.")
                    total_points += len(lines)
                else:
                    print(f"  Push failed: {resp.status_code}")
                    failed.append(series_id)
                    
            except Exception as e:
                print(f"  ERROR: {e}")
                failed.append(series_id)
    
    # Summary
    print("\n" + "="*60)
    print(f"=== SUMMARY ===")
    print(f"Total series processed: {len(folders)}")
    print(f"Total points loaded: {total_points:,}")
    print(f"Failed: {len(failed)}")
    if failed:
        print(f"Failed series: {failed[:10]}...")
    print("="*60)
    print(f"\nQuery example:")
    print(f'  boom{{series="ds_0_T"}}')
    print(f'  boom{{domain="Infrastructure"}}')
    print(f'  boom{{metric_type="gauge"}}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load BOOM datasets to VictoriaMetrics")
    parser.add_argument("--limit", type=int, default=50, help="Number of series to load (0 for all)")
    parser.add_argument("--all", action="store_true", help="Load all series (overrides --limit)")
    parser.add_argument("--clear", action="store_true", help="Clear existing boom data first")
    
    args = parser.parse_args()
    
    limit = 0 if args.all else args.limit
    
    asyncio.run(load_all_boom(limit=limit, clear=args.clear))
