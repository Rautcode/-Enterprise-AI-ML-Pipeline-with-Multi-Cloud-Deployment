"""
ML Training Pipeline
Handles model training, validation, and deployment
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import argparse

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLTrainingPipeline:
    """ML Training Pipeline for enterprise deployment"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.scaler = None
        self.metrics = {}
        
        # Initialize MLflow
        if config.get('mlflow_tracking_uri'):
            mlflow.set_tracking_uri(config['mlflow_tracking_uri'])
        
        # Create directories
        self.model_dir = Path(config.get('model_output_path', '/app/models'))
        self.data_dir = Path(config.get('data_path', '/app/data'))
        self.artifacts_dir = Path(config.get('artifacts_path', '/app/artifacts'))
        
        for directory in [self.model_dir, self.artifacts_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def load_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Load training data"""
        logger.info("Loading training data")
        
        # Example: Load from CSV (replace with your data loading logic)
        data_file = self.data_dir / 'training_data.csv'
        
        if not data_file.exists():
            # Generate synthetic data for demonstration
            logger.warning("Training data not found, generating synthetic data")
            return self._generate_synthetic_data()
        
        try:
            df = pd.read_csv(data_file)
            
            # Assume last column is target
            X = df.iloc[:, :-1]
            y = df.iloc[:, -1]
            
            logger.info(f"Loaded data: {X.shape[0]} samples, {X.shape[1]} features")
            return X, y
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _generate_synthetic_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Generate synthetic data for demonstration"""
        np.random.seed(42)
        n_samples = 1000
        n_features = 10
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        
        # Create synthetic target with some correlation to features
        y = pd.Series(
            (X.sum(axis=1) > 0).astype(int),
            name='target'
        )
        
        logger.info(f"Generated synthetic data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y
    
    def preprocess_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess the data"""
        logger.info("Preprocessing data")
        
        # Handle missing values
        X_clean = X.fillna(X.mean())
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_clean)
        
        logger.info("Data preprocessing completed")
        return X_scaled, y.values
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """Train the ML model"""
        logger.info("Training model")
        
        # Get model parameters from config
        model_params = self.config.get('model_params', {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42
        })
        
        # Initialize model
        self.model = RandomForestClassifier(**model_params)
        
        # Train model
        start_time = time.time()
        self.model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        self.metrics['training_time'] = training_time
        logger.info(f"Model training completed in {training_time:.2f} seconds")
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate the trained model"""
        logger.info("Evaluating model")
        
        # Make predictions
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        
        # Cross-validation score
        cv_scores = cross_val_score(self.model, X_test, y_test, cv=5)
        
        evaluation_metrics = {
            'accuracy': accuracy,
            'cv_mean_score': cv_scores.mean(),
            'cv_std_score': cv_scores.std(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        self.metrics.update(evaluation_metrics)
        
        logger.info(f"Model evaluation completed. Accuracy: {accuracy:.4f}")
        return evaluation_metrics
    
    def save_model(self, model_name: str = "production_model") -> None:
        """Save the trained model and artifacts"""
        logger.info(f"Saving model: {model_name}")
        
        # Save model
        model_path = self.model_dir / f"{model_name}.pkl"
        joblib.dump(self.model, model_path)
        
        # Save scaler
        scaler_path = self.model_dir / f"{model_name}_scaler.pkl"
        joblib.dump(self.scaler, scaler_path)
        
        # Save metadata
        metadata = {
            'model_name': model_name,
            'model_type': type(self.model).__name__,
            'version': self.config.get('model_version', '1.0.0'),
            'created_at': time.time(),
            'metrics': self.metrics,
            'config': self.config,
            'input_shape': self.scaler.n_features_in_,
            'output_shape': len(np.unique(self.metrics.get('y_true', [0, 1])))
        }
        
        metadata_path = self.model_dir / f"{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        logger.info(f"Metadata saved to {metadata_path}")
    
    def log_to_mlflow(self, model_name: str = "production_model") -> None:
        """Log training run to MLflow"""
        logger.info("Logging to MLflow")
        
        with mlflow.start_run():
            # Log parameters
            model_params = self.config.get('model_params', {})
            for param, value in model_params.items():
                mlflow.log_param(param, value)
            
            # Log metrics
            for metric, value in self.metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(metric, value)
            
            # Log model
            mlflow.sklearn.log_model(
                self.model,
                "model",
                registered_model_name=model_name
            )
            
            # Log artifacts
            mlflow.log_artifacts(str(self.artifacts_dir))
            
            logger.info("MLflow logging completed")
    
    def run_training_pipeline(self, model_name: str = "production_model") -> Dict[str, Any]:
        """Run the complete training pipeline"""
        logger.info("Starting ML training pipeline")
        
        try:
            # Load data
            X, y = self.load_data()
            
            # Preprocess data
            X_processed, y_processed = self.preprocess_data(X, y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_processed, y_processed,
                test_size=0.2,
                random_state=42,
                stratify=y_processed
            )
            
            # Train model
            self.train_model(X_train, y_train)
            
            # Evaluate model
            evaluation_metrics = self.evaluate_model(X_test, y_test)
            
            # Save model
            self.save_model(model_name)
            
            # Log to MLflow if configured
            if self.config.get('mlflow_tracking_uri'):
                self.log_to_mlflow(model_name)
            
            logger.info("Training pipeline completed successfully")
            return {
                'status': 'success',
                'model_name': model_name,
                'metrics': evaluation_metrics
            }
            
        except Exception as e:
            logger.error(f"Training pipeline failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }


def load_config(config_path: str) -> Dict[str, Any]:
    """Load training configuration"""
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    
    # Default configuration
    return {
        'model_params': {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42
        },
        'model_version': '1.0.0',
        'data_path': '/app/data',
        'model_output_path': '/app/models',
        'artifacts_path': '/app/artifacts',
        'mlflow_tracking_uri': os.getenv('MLFLOW_TRACKING_URI')
    }


def main():
    """Main training function"""
    parser = argparse.ArgumentParser(description='ML Training Pipeline')
    parser.add_argument('--config', type=str, default='config.json', help='Configuration file path')
    parser.add_argument('--model-name', type=str, default='production_model', help='Model name')
    parser.add_argument('--environment', type=str, default='development', help='Environment')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    config['environment'] = args.environment
    
    # Initialize and run pipeline
    pipeline = MLTrainingPipeline(config)
    result = pipeline.run_training_pipeline(args.model_name)
    
    # Print results
    print(f"Training completed with status: {result['status']}")
    if result['status'] == 'success':
        print(f"Model: {result['model_name']}")
        print(f"Accuracy: {result['metrics']['accuracy']:.4f}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
