"""
Test configuration
"""

import pytest
from pathlib import Path


@pytest.fixture
def test_data_path():
    """Path to test data"""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_features():
    """Sample features for testing"""
    return [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]


@pytest.fixture
def sample_prediction_request():
    """Sample prediction request"""
    return {
        "features": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        "model_name": "default",
        "metadata": {"test": True}
    }
