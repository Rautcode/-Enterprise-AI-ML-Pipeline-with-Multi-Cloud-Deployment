"""
Configuration management for ML API service
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""
    
    # Application settings
    app_name: str = Field(default="ML Pipeline API", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    
    # Model settings
    model_path: str = Field(default="/app/models", env="MODEL_PATH")
    default_model: str = Field(default="default", env="DEFAULT_MODEL")
    model_cache_size: int = Field(default=10, env="MODEL_CACHE_SIZE")
    model_timeout: int = Field(default=300, env="MODEL_TIMEOUT")
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security settings
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    
    # Storage settings
    storage_backend: str = Field(default="local", env="STORAGE_BACKEND")  # local, s3, azure
    aws_bucket: Optional[str] = Field(default=None, env="AWS_BUCKET")
    azure_container: Optional[str] = Field(default=None, env="AZURE_CONTAINER")
    
    # Database settings (if needed)
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # External services
    mlflow_tracking_uri: Optional[str] = Field(default=None, env="MLFLOW_TRACKING_URI")
    prometheus_gateway: Optional[str] = Field(default=None, env="PROMETHEUS_GATEWAY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
