"""
ML API Service - FastAPI application for serving ML models
Provides REST API endpoints for model inference with monitoring and logging
"""

import os
import logging
import time
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
import asyncio

import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
import joblib
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST
import structlog

from models import ModelManager
from monitoring import setup_monitoring, metrics
from config import Settings


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# Pydantic models for request/response
class PredictionRequest(BaseModel):
    """Request model for predictions"""
    features: List[float] = Field(..., description="Input features for prediction")
    model_name: Optional[str] = Field(default="default", description="Model name to use")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class PredictionResponse(BaseModel):
    """Response model for predictions"""
    prediction: List[float] = Field(..., description="Model prediction")
    probability: Optional[List[float]] = Field(None, description="Prediction probabilities")
    model_name: str = Field(..., description="Name of the model used")
    model_version: str = Field(..., description="Version of the model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    request_id: str = Field(..., description="Unique request identifier")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    models_loaded: List[str] = Field(..., description="List of loaded models")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")


# Global variables
model_manager: ModelManager = None
settings: Settings = None
start_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global model_manager, settings
    
    # Startup
    logger.info("Starting ML API service")
    settings = Settings()
    model_manager = ModelManager(settings.model_path)
    
    # Load default models
    await model_manager.load_models()
    setup_monitoring()
    
    logger.info("ML API service started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down ML API service")
    await model_manager.cleanup()


# Create FastAPI application
app = FastAPI(
    title="ML Pipeline API",
    description="Enterprise ML API for model inference and management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Dependency to get settings
def get_settings() -> Settings:
    return settings


# Health check endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    import psutil
    
    uptime = time.time() - start_time
    memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=uptime,
        models_loaded=list(model_manager.loaded_models.keys()) if model_manager else [],
        memory_usage_mb=memory_usage
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    if not model_manager or not model_manager.is_ready():
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    from fastapi import Response
    
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Model management endpoints
@app.get("/models")
async def list_models():
    """List all available models"""
    if not model_manager:
        raise HTTPException(status_code=503, detail="Model manager not initialized")
    
    return {
        "loaded_models": list(model_manager.loaded_models.keys()),
        "available_models": await model_manager.list_available_models()
    }


@app.post("/models/{model_name}/load")
async def load_model(model_name: str, background_tasks: BackgroundTasks):
    """Load a specific model"""
    if not model_manager:
        raise HTTPException(status_code=503, detail="Model manager not initialized")
    
    background_tasks.add_task(model_manager.load_model, model_name)
    return {"message": f"Loading model {model_name}"}


@app.delete("/models/{model_name}")
async def unload_model(model_name: str):
    """Unload a specific model"""
    if not model_manager:
        raise HTTPException(status_code=503, detail="Model manager not initialized")
    
    await model_manager.unload_model(model_name)
    return {"message": f"Model {model_name} unloaded"}


# Prediction endpoints
@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, settings: Settings = Depends(get_settings)):
    """Make predictions using the specified model"""
    if not model_manager:
        raise HTTPException(status_code=503, detail="Model manager not initialized")
    
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000000)}"
    
    try:
        # Record metrics
        metrics.prediction_requests_total.inc()
        
        # Get model
        model_info = model_manager.get_model(request.model_name)
        if not model_info:
            metrics.prediction_errors_total.labels(error_type="model_not_found").inc()
            raise HTTPException(
                status_code=404, 
                detail=f"Model {request.model_name} not found"
            )
        
        # Validate input
        if len(request.features) != model_info.get("input_shape", len(request.features)):
            metrics.prediction_errors_total.labels(error_type="invalid_input").inc()
            raise HTTPException(
                status_code=400,
                detail="Invalid input shape"
            )
        
        # Make prediction
        features = np.array(request.features).reshape(1, -1)
        prediction = model_info["model"].predict(features)
        
        # Get probabilities if available
        probabilities = None
        if hasattr(model_info["model"], "predict_proba"):
            probabilities = model_info["model"].predict_proba(features)[0].tolist()
        
        processing_time = (time.time() - start_time) * 1000
        
        # Record metrics
        metrics.prediction_duration_seconds.observe(processing_time / 1000)
        metrics.predictions_total.labels(model_name=request.model_name).inc()
        
        logger.info(
            "Prediction completed",
            request_id=request_id,
            model_name=request.model_name,
            processing_time_ms=processing_time
        )
        
        return PredictionResponse(
            prediction=prediction.tolist(),
            probability=probabilities,
            model_name=request.model_name,
            model_version=model_info.get("version", "unknown"),
            processing_time_ms=processing_time,
            request_id=request_id
        )
        
    except Exception as e:
        metrics.prediction_errors_total.labels(error_type="prediction_error").inc()
        logger.error(
            "Prediction failed",
            request_id=request_id,
            error=str(e),
            model_name=request.model_name
        )
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/predict/batch")
async def predict_batch(requests: List[PredictionRequest]):
    """Make batch predictions"""
    if not model_manager:
        raise HTTPException(status_code=503, detail="Model manager not initialized")
    
    results = []
    for request in requests:
        try:
            result = await predict(request)
            results.append(result)
        except HTTPException as e:
            results.append({"error": e.detail, "status_code": e.status_code})
    
    return {"results": results}


# Model information endpoints
@app.get("/models/{model_name}/info")
async def get_model_info(model_name: str):
    """Get information about a specific model"""
    if not model_manager:
        raise HTTPException(status_code=503, detail="Model manager not initialized")
    
    model_info = model_manager.get_model(model_name)
    if not model_info:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    return {
        "name": model_name,
        "version": model_info.get("version", "unknown"),
        "type": model_info.get("type", "unknown"),
        "input_shape": model_info.get("input_shape"),
        "output_shape": model_info.get("output_shape"),
        "loaded_at": model_info.get("loaded_at"),
        "metadata": model_info.get("metadata", {})
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
