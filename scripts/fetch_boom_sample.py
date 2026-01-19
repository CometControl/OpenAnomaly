"""
Script to fetch diverse samples from the Datadog/BOOM dataset on Hugging Face.
Downloads taxonomy info and selects series across different domains and types.
"""

import json
import pandas as pd
from huggingface_hub import hf_hub_download, list_repo_files
from pathlib import Path
import pyarrow as pa
from collections import defaultdict

DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "boom_sample.csv"
REPO_ID = "Datadog/BOOM"
POINTS_PER_SERIES = 200  # Points per series

# Target diversity: one series from each domain/type combo
TARGET_DOMAINS = ["Infrastructure", "Networking", "Database", "Application Usage", "Security"]
TARGET_TYPES = ["count", "rate", "gauge"]
MAX_SERIES = 10

def fetch_sample():
    DATA_DIR.mkdir(exist_ok=True)
    
    # 1. Download taxonomy file
    print("Downloading taxonomy...")
    taxonomy_path = hf_hub_download(
        repo_id=REPO_ID,
        filename="dataset_taxonomy.json",
        repo_type="dataset",
        local_dir=str(DATA_DIR / "boom_raw")
    )
    
    with open(taxonomy_path) as f:
        taxonomy = json.load(f)
    
    print(f"Loaded taxonomy for {len(taxonomy)} series.")
    
    # 2. Select diverse series
    # Group by domain -> type
    selected = []
    domain_type_seen = set()
    
    for series_id, meta in taxonomy.items():
        domains = meta.get("domain", ["Unknown"])
        types = meta.get("type", ["Unknown"])
        freq = series_id.split("-")[-1]  # e.g., "T", "5T", "10S"
        
        for domain in domains:
            for mtype in types:
                key = (domain, mtype)
                if key not in domain_type_seen and len(selected) < MAX_SERIES:
                    domain_type_seen.add(key)
                    selected.append({
                        "series_id": series_id,
                        "domain": domain,
                        "type": mtype,
                        "freq": freq,
                        "num_variates": meta.get("num_variates", 1)
                    })
    
    print(f"\nSelected {len(selected)} diverse series:")
    for s in selected:
        print(f"  - {s['series_id']}: {s['domain']} / {s['type']} / freq={s['freq']}")
    
    # 3. Download and extract each series
    all_rows = []
    for series_meta in selected:
        series_id = series_meta["series_id"]
        target_file = f"{series_id}/data-00000-of-00001.arrow"
        
        try:
            print(f"\nDownloading {series_id}...")
            local_arrow = hf_hub_download(
                repo_id=REPO_ID,
                filename=target_file,
                repo_type="dataset",
                local_dir=str(DATA_DIR / "boom_raw")
            )
            
            # Load Arrow file via IPC stream
            with pa.OSFile(local_arrow, 'rb') as f:
                reader = pa.ipc.open_stream(f)
                table = reader.read_all()
                df = table.to_pandas()
            
            if len(df) == 0:
                print(f"  Empty dataset, skipping.")
                continue
            
            # Extract first variate from this series
            row = df.iloc[0]
            start_ts = pd.to_datetime(row['start'])
            values = row['target'][:POINTS_PER_SERIES]
            
            # Map freq suffix to pandas freq
            freq_map = {"T": "min", "5T": "5min", "10S": "10s", "H": "h"}
            freq_suffix = series_meta["freq"]
            pd_freq = freq_map.get(freq_suffix, "min")
            
            timestamps = pd.date_range(start=start_ts, periods=len(values), freq=pd_freq)
            
            # Use sanitized series_id as metric name
            metric_name = series_id.replace("-", "_")
            
            series_df = pd.DataFrame({
                'timestamp': timestamps,
                'value': values,
                'item_id': metric_name,
                'domain': series_meta["domain"],
                'metric_type': series_meta["type"],
                'freq': freq_suffix
            })
            all_rows.append(series_df)
            print(f"  Extracted {metric_name}: {len(values)} points")
            
        except Exception as e:
            print(f"  Failed: {e}")
            continue
    
    if all_rows:
        export_df = pd.concat(all_rows, ignore_index=True)
        export_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n=== Saved {len(export_df)} total points ({len(all_rows)} series) to {OUTPUT_FILE} ===")
        
        # Print summary
        print("\nSeries Summary:")
        summary = export_df.groupby(['item_id', 'domain', 'metric_type', 'freq']).size()
        print(summary.to_string())
    else:
        print("No data extracted!")

if __name__ == "__main__":
    fetch_sample()
