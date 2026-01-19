"""
Shared fixtures for OpenAnomaly tests.
"""
import pytest
import sys
from pathlib import Path

# Ensure the root directory is in the path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Mock heavy ML dependencies to avoid installing them for unit tests
from unittest.mock import MagicMock
sys.modules["torch"] = MagicMock()
sys.modules["chronos"] = MagicMock()

