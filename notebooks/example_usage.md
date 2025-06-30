# ML Pipeline Example Notebook

This notebook demonstrates the basic usage of the ML Pipeline API.

## Setup

```python
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
API_BASE_URL = "http://localhost:8000"
```

## 1. Check API Health

```python
response = requests.get(f"{API_BASE_URL}/health")
print("API Health:", response.json())
```

## 2. Generate Sample Data

```python
# Generate sample features
features = np.random.randn(10).tolist()
print("Sample features:", features)
```

## 3. Make Predictions

```python
prediction_request = {
    "features": features,
    "model_name": "default",
    "metadata": {"experiment": "notebook_test"}
}

response = requests.post(f"{API_BASE_URL}/predict", json=prediction_request)
result = response.json()
print("Prediction result:", result)
```

## 4. Batch Predictions

```python
# Generate multiple samples
batch_requests = []
for i in range(5):
    features = np.random.randn(10).tolist()
    batch_requests.append({
        "features": features,
        "model_name": "default"
    })

response = requests.post(f"{API_BASE_URL}/batch_predict", json=batch_requests)
batch_results = response.json()
print(f"Batch predictions completed: {len(batch_results['predictions'])} results")
```

## 5. Visualize Results

```python
# Extract predictions for visualization
predictions = [pred['prediction'][0] for pred in batch_results['predictions']]
processing_times = [pred['processing_time_ms'] for pred in batch_results['predictions']]

plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.hist(predictions, bins=10, alpha=0.7)
plt.title('Distribution of Predictions')
plt.xlabel('Prediction Value')
plt.ylabel('Frequency')

plt.subplot(1, 2, 2)
plt.bar(range(len(processing_times)), processing_times)
plt.title('Processing Time per Request')
plt.xlabel('Request Number')
plt.ylabel('Processing Time (ms)')

plt.tight_layout()
plt.show()
```

## 6. Monitor API Metrics

```python
# Get Prometheus metrics
response = requests.get(f"{API_BASE_URL}/metrics")
print("API Metrics (first 500 chars):")
print(response.text[:500])
```
