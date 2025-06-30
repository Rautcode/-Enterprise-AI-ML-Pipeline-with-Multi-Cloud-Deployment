"""
Sample data generator for training and testing
"""

import pandas as pd
import numpy as np
from sklearn.datasets import make_classification


def generate_sample_data(n_samples=1000, n_features=10, n_classes=2, random_state=42):
    """Generate sample classification data"""
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_informative=n_features//2,
        n_redundant=n_features//4,
        n_classes=n_classes,
        random_state=random_state
    )
    
    # Create feature names
    feature_names = [f'feature_{i}' for i in range(n_features)]
    
    # Create DataFrame
    df = pd.DataFrame(X, columns=feature_names)
    df['target'] = y
    
    return df


if __name__ == "__main__":
    # Generate sample data
    df = generate_sample_data()
    
    # Save to CSV
    df.to_csv('sample_data.csv', index=False)
    print(f"Generated sample data with shape: {df.shape}")
    print(f"Features: {df.columns.tolist()[:-1]}")
    print(f"Target distribution: {df['target'].value_counts().to_dict()}")
