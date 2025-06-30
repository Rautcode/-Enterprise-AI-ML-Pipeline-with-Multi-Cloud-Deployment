"""
Model management for ML API service
Handles loading, caching, and lifecycle management of ML models
"""

import os
import json
import asyncio
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import joblib
import numpy as np
import structlog

logger = structlog.get_logger()


class ModelManager:
    """Manages ML models loading, caching, and lifecycle"""
    
    def __init__(self, model_path: str, cache_size: int = 10):
        self.model_path = Path(model_path)
        self.cache_size = cache_size
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
    async def load_models(self):
        """Load all available models from the model directory"""
        if not self.model_path.exists():
            logger.warning(f"Model path {self.model_path} does not exist")
            return
            
        for model_file in self.model_path.glob("*.pkl"):
            model_name = model_file.stem
            try:
                await self.load_model(model_name)
                logger.info(f"Loaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
    
    async def load_model(self, model_name: str) -> bool:
        """Load a specific model"""
        async with self._lock:
            if model_name in self.loaded_models:
                logger.info(f"Model {model_name} already loaded")
                return True
                
            model_file = self.model_path / f"{model_name}.pkl"
            metadata_file = self.model_path / f"{model_name}_metadata.json"
            
            if not model_file.exists():
                logger.error(f"Model file not found: {model_file}")
                return False
                
            try:
                # Load model
                model = joblib.load(model_file)
                
                # Load metadata
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                
                # Store model info
                self.loaded_models[model_name] = {
                    "model": model,
                    "loaded_at": time.time(),
                    "metadata": metadata,
                    "version": metadata.get("version", "unknown"),
                    "type": metadata.get("type", "unknown"),
                    "input_shape": metadata.get("input_shape"),
                    "output_shape": metadata.get("output_shape"),
                    "access_count": 0,
                    "last_accessed": time.time()
                }
                
                # Manage cache size
                await self._manage_cache()
                
                logger.info(f"Successfully loaded model: {model_name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                return False
    
    async def unload_model(self, model_name: str) -> bool:
        """Unload a specific model"""
        async with self._lock:
            if model_name in self.loaded_models:
                del self.loaded_models[model_name]
                logger.info(f"Unloaded model: {model_name}")
                return True
            return False
    
    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get a loaded model"""
        if model_name in self.loaded_models:
            model_info = self.loaded_models[model_name]
            model_info["access_count"] += 1
            model_info["last_accessed"] = time.time()
            return model_info
        return None
    
    async def list_available_models(self) -> List[str]:
        """List all available models in the model directory"""
        if not self.model_path.exists():
            return []
            
        models = []
        for model_file in self.model_path.glob("*.pkl"):
            models.append(model_file.stem)
        return models
    
    def is_ready(self) -> bool:
        """Check if the model manager is ready"""
        return len(self.loaded_models) > 0
    
    async def _manage_cache(self):
        """Manage model cache size by removing least recently used models"""
        if len(self.loaded_models) <= self.cache_size:
            return
            
        # Sort models by last accessed time
        sorted_models = sorted(
            self.loaded_models.items(),
            key=lambda x: x[1]["last_accessed"]
        )
        
        # Remove oldest models
        models_to_remove = len(self.loaded_models) - self.cache_size
        for i in range(models_to_remove):
            model_name = sorted_models[i][0]
            del self.loaded_models[model_name]
            logger.info(f"Removed model from cache: {model_name}")
    
    async def cleanup(self):
        """Cleanup resources"""
        async with self._lock:
            self.loaded_models.clear()
            logger.info("Model manager cleaned up")
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded models"""
        stats = {
            "total_loaded": len(self.loaded_models),
            "cache_size": self.cache_size,
            "models": {}
        }
        
        for name, info in self.loaded_models.items():
            stats["models"][name] = {
                "version": info["version"],
                "type": info["type"],
                "loaded_at": info["loaded_at"],
                "access_count": info["access_count"],
                "last_accessed": info["last_accessed"]
            }
            
        return stats


class ModelValidator:
    """Validates model inputs and outputs"""
    
    @staticmethod
    def validate_input(features: List[float], expected_shape: Optional[int] = None) -> bool:
        """Validate input features"""
        if not isinstance(features, list):
            return False
            
        if not all(isinstance(f, (int, float)) for f in features):
            return False
            
        if expected_shape is not None and len(features) != expected_shape:
            return False
            
        return True
    
    @staticmethod
    def validate_prediction(prediction: np.ndarray) -> bool:
        """Validate model prediction"""
        if not isinstance(prediction, np.ndarray):
            return False
            
        if prediction.size == 0:
            return False
            
        return True
