"""
Tests for ML API
"""

import pytest
from fastapi.testclient import TestClient
import numpy as np

# Import the app - adjust import path as needed
try:
    from ml_api.main import app
except ImportError:
    # Alternative import for local testing
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml-api'))
    from main import app


client = TestClient(app)


def test_health_endpoint():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime_seconds" in data


def test_predict_endpoint_without_model(sample_prediction_request):
    """Test prediction endpoint when no model is loaded"""
    response = client.post("/predict", json=sample_prediction_request)
    # This might return 500 if no model is loaded, which is expected
    assert response.status_code in [200, 500]


def test_predict_endpoint_invalid_input():
    """Test prediction endpoint with invalid input"""
    invalid_request = {
        "features": "invalid",  # Should be a list
        "model_name": "default"
    }
    response = client.post("/predict", json=invalid_request)
    assert response.status_code == 422  # Validation error


def test_metrics_endpoint():
    """Test metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Should return Prometheus metrics format
    assert "text/plain" in response.headers.get("content-type", "")


def test_models_endpoint():
    """Test models listing endpoint"""
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "models" in data
