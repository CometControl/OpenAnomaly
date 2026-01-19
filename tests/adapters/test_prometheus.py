"""
Tests for PrometheusAdapter.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from openanomaly.adapters.tsdb.prometheus import PrometheusAdapter

@pytest.fixture
def mock_exporter():
    """Mock the OpenTelemetry exporter."""
    with patch("openanomaly.adapters.tsdb.prometheus.PrometheusRemoteWriteMetricsExporter") as MockExporter:
        # Mock instance
        instance = MockExporter.return_value
        instance.export.return_value = None # Success
        yield instance

@pytest.fixture
def adapter(mock_exporter):
    return PrometheusAdapter(read_url="http://localhost:9090", write_url="http://localhost:9090/write")

@pytest.mark.asyncio
async def test_write_conversion(adapter, mock_exporter):
    """Test DataFrame to OTel metric conversion."""
    
    # Input DataFrame with unique_id formatted as labels
    # e.g. "metric_name{label1=v1}"
    df = pd.DataFrame({
        "unique_id": ["test_metric{env=prod}", "test_metric{env=prod}"],
        "ds": [pd.Timestamp("2024-01-01 10:00:00"), pd.Timestamp("2024-01-01 10:01:00")],
        "y": [1.0, 2.0]
    })
    
    # Force _exporter initialization
    adapter._exporter = mock_exporter
    
    # Execute
    await adapter.write(df)
    
    # Assertions
    mock_exporter.export.assert_called_once()
    assert mock_exporter.export.called

@pytest.mark.asyncio
async def test_query_range_mock(adapter):
    """Test query logic (mocking the HTTP client)."""
    with patch("openanomaly.adapters.tsdb.prometheus.httpx.AsyncClient") as MockClient:
        # The adapter creates an instance: client = httpx.AsyncClient(...)
        client_instance = MockClient.return_value
        
        # Configure get method to be async
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {"__name__": "up", "instance": "loc"},
                        "values": [[1704096000, "1"], [1704096060, "1"]]
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        # Assign AsyncMock to .get
        client_instance.get = AsyncMock(return_value=mock_response)
        
        # Execute
        from datetime import datetime
        start_dt = datetime(2024, 1, 1, 10, 0)
        end_dt = datetime(2024, 1, 1, 10, 1)
        
        df = await adapter.query_range("up", start=start_dt, end=end_dt, step="1m")
        
        assert len(df) == 2
        assert "unique_id" in df.columns
        assert df["unique_id"].iloc[0] == 'up{instance="loc"}'
        assert "y" in df.columns
