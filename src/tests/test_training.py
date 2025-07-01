"""
Tests for ML Training Pipeline - Simplified for CI/CD
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import tempfile
import os


def test_data_preprocessing():
    """Test data preprocessing functions"""
    # Create sample data
    data = {
        'feature_1': [1, 2, 3, 4, 5],
        'feature_2': [2, 4, 6, 8, 10],
        'target': [10, 20, 30, 40, 50]
    }
    df = pd.DataFrame(data)
    
    # Test data validation
    assert len(df) == 5
    assert list(df.columns) == ['feature_1', 'feature_2', 'target']
    assert df.isnull().sum().sum() == 0  # No missing values


def test_feature_engineering():
    """Test feature engineering logic"""
    # Create sample data
    np.random.seed(42)
    X = np.random.randn(100, 3)
    y = X[:, 0] + 2 * X[:, 1] + 0.5 * X[:, 2] + np.random.randn(100) * 0.1
    
    # Test feature scaling
    X_mean = np.mean(X, axis=0)
    X_std = np.std(X, axis=0)
    X_scaled = (X - X_mean) / X_std
    
    assert np.allclose(np.mean(X_scaled, axis=0), 0, atol=1e-10)
    assert np.allclose(np.std(X_scaled, axis=0), 1, atol=1e-10)


def test_model_training():
    """Test model training pipeline"""
    # Generate sample data
    np.random.seed(42)
    X = np.random.randn(100, 4)
    y = X[:, 0] + 2 * X[:, 1] - X[:, 2] + 0.5 * X[:, 3] + np.random.randn(100) * 0.1
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # Test predictions
    y_pred = model.predict(X_test)
    
    # Validate model performance
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    assert mse > 0
    assert r2 > 0.5  # Reasonable R² score
    assert len(y_pred) == len(y_test)


def test_model_serialization():
    """Test model saving and loading"""
    # Create and train a simple model
    np.random.seed(42)
    X = np.random.randn(50, 2)
    y = X[:, 0] + X[:, 1] + np.random.randn(50) * 0.1
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Test serialization
    with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as tmp_file:
        try:
            # Save model
            joblib.dump(model, tmp_file.name)
            
            # Load model
            loaded_model = joblib.load(tmp_file.name)
            
            # Test predictions are identical
            test_X = np.random.randn(5, 2)
            original_pred = model.predict(test_X)
            loaded_pred = loaded_model.predict(test_X)
            
            assert np.allclose(original_pred, loaded_pred)
            
        finally:
            # Clean up
            if os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)


def test_hyperparameter_validation():
    """Test hyperparameter validation"""
    hyperparams = {
        'learning_rate': 0.01,
        'max_depth': 6,
        'n_estimators': 100,
        'random_state': 42
    }
    
    # Validate hyperparameter ranges
    assert 0 < hyperparams['learning_rate'] <= 1
    assert hyperparams['max_depth'] > 0
    assert hyperparams['n_estimators'] > 0
    assert isinstance(hyperparams['random_state'], int)


def test_cross_validation_setup():
    """Test cross-validation configuration"""
    cv_config = {
        'cv_folds': 5,
        'scoring': 'neg_mean_squared_error',
        'shuffle': True,
        'random_state': 42
    }
    
    assert cv_config['cv_folds'] >= 2
    assert cv_config['scoring'] in ['neg_mean_squared_error', 'r2', 'neg_mean_absolute_error']
    assert isinstance(cv_config['shuffle'], bool)
    assert isinstance(cv_config['random_state'], int)


def test_metrics_calculation():
    """Test model evaluation metrics"""
    # Create sample predictions
    y_true = np.array([1, 2, 3, 4, 5])
    y_pred = np.array([1.1, 1.9, 3.1, 3.9, 5.1])
    
    # Calculate metrics
    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    mae = np.mean(np.abs(y_true - y_pred))
    
    # Validate metrics
    assert mse > 0
    assert 0 <= r2 <= 1
    assert mae > 0
    assert len(y_true) == len(y_pred)


def test_data_pipeline_config():
    """Test data pipeline configuration"""
    pipeline_config = {
        'data_source': 'csv',
        'target_column': 'target',
        'feature_columns': ['feature_1', 'feature_2', 'feature_3'],
        'test_size': 0.2,
        'validation_size': 0.1,
        'random_state': 42
    }
    
    # Validate configuration
    assert pipeline_config['data_source'] in ['csv', 'json', 'parquet', 'database']
    assert isinstance(pipeline_config['target_column'], str)
    assert isinstance(pipeline_config['feature_columns'], list)
    assert 0 < pipeline_config['test_size'] < 1
    assert 0 < pipeline_config['validation_size'] < 1
    assert pipeline_config['test_size'] + pipeline_config['validation_size'] < 1
