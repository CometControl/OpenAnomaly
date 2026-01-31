"""
Pytest configuration for adapter tests - Skip database for unit tests
"""
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require database"
    )
