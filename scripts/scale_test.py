import os
import sys
import time
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'openanomaly.config.settings')
os.environ['OPENANOMALY_CONFIG_FILE'] = 'config.docker.yaml' # Use docker config

import django
django.setup()

from openanomaly.pipelines.tasks import simulate_work

def main():
    print("Dispatching 20 tasks to test worker scaling...")
    task_ids = []
    for i in range(20):
        # We don't wait for result here, just dispatch
        res = simulate_work.delay(i)
        task_ids.append(res.id)
        print(f"Dispatched task {i}: {res.id}")
    
    print("All tasks dispatched. Check worker logs to see distribution.")
    print("Command: docker compose logs -f worker")

if __name__ == "__main__":
    main()
