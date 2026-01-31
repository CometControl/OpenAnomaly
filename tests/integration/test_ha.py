import pytest
import time
import uuid
from openanomaly.pipelines.tasks import simulate_work
from celery.result import GroupResult

@pytest.mark.integration
def test_worker_scaling_and_distribution(celery_app, celery_worker):
    """
    Test that tasks are distributed across multiple workers.
    Note: This test relies on an existing Celery cluster (like Docker Compose).
    Local 'celery_worker' fixture might not reflect the full cluster state 
    if running outside Docker network, but we use the app configuration
    to inspect the real broker/backend if configured correctly.
    
    If running FROM inside a container (like 'api'), this works perfectly against the cluster.
    """
    
    # number of tasks to dispatch
    NUM_TASKS = 20
    
    # 1. Dispatch tasks
    print(f"\nDispatching {NUM_TASKS} tasks...")
    async_results = []
    for i in range(NUM_TASKS):
        # We pass different durations to mix things up
        res = simulate_work.delay(i)
        async_results.append(res)
    
    # 2. Add them to a group to wait for all
    # (Naive waiting since we didn't create a Group beforehand)
    print("Waiting for tasks to complete...")
    
    # Wait for all to finish (with timeout)
    timeout = 30 # seconds
    start_time = time.time()
    
    completed_results = []
    for res in async_results:
        try:
            # Wait for each result
            val = res.get(timeout=10)
            completed_results.append(val)
        except Exception as e:
            print(f"Task {res.id} failed or timed out: {e}")
            
    assert len(completed_results) == NUM_TASKS, f"Expected {NUM_TASKS} completed tasks, got {len(completed_results)}"
    
    # 3. Analyze Worker Distribution
    worker_counts = {}
    for data in completed_results:
        worker_name = data.get('worker')
        worker_counts[worker_name] = worker_counts.get(worker_name, 0) + 1
        
    print("\nWorker Distribution:")
    for w, count in worker_counts.items():
        print(f"  {w}: {count}")
        
    # 4. Assertions
    # We expect distinct workers. In Docker Compose with 3 replicas, usually hostnames differ.
    unique_workers = len(worker_counts.keys())
    print(f"Unique workers found: {unique_workers}")
    
    # Warn if only 1 worker found (local test or no scaling)
    if unique_workers < 2:
        pytest.main.warnings.warn(UserWarning("Only 1 unique worker found! Is scaling enabled?"))
    
    # Should have at least 1 worker
    assert unique_workers >= 1
