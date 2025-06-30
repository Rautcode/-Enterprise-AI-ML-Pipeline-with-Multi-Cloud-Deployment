"""
Monitoring and metrics for ML API service
Provides Prometheus metrics and health monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import structlog

logger = structlog.get_logger()


class MetricsCollector:
    """Collects and manages Prometheus metrics"""
    
    def __init__(self):
        # Request metrics
        self.prediction_requests_total = Counter(
            'ml_api_prediction_requests_total',
            'Total number of prediction requests'
        )
        
        self.prediction_errors_total = Counter(
            'ml_api_prediction_errors_total',
            'Total number of prediction errors',
            ['error_type']
        )
        
        self.prediction_duration_seconds = Histogram(
            'ml_api_prediction_duration_seconds',
            'Time spent processing predictions',
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.predictions_total = Counter(
            'ml_api_predictions_total',
            'Total number of successful predictions',
            ['model_name']
        )
        
        # Model metrics
        self.models_loaded_total = Gauge(
            'ml_api_models_loaded_total',
            'Number of models currently loaded'
        )
        
        self.model_load_duration_seconds = Histogram(
            'ml_api_model_load_duration_seconds',
            'Time spent loading models',
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.model_memory_usage_bytes = Gauge(
            'ml_api_model_memory_usage_bytes',
            'Memory usage of loaded models',
            ['model_name']
        )
        
        # System metrics
        self.active_connections = Gauge(
            'ml_api_active_connections',
            'Number of active connections'
        )
        
        self.response_size_bytes = Histogram(
            'ml_api_response_size_bytes',
            'Size of API responses in bytes',
            buckets=[100, 1000, 10000, 100000, 1000000]
        )
        
        # Info metrics
        self.app_info = Info(
            'ml_api_app_info',
            'Application information'
        )
        
        logger.info("Metrics collector initialized")
    
    def update_model_count(self, count: int):
        """Update the number of loaded models"""
        self.models_loaded_total.set(count)
    
    def record_model_load(self, duration: float):
        """Record model loading duration"""
        self.model_load_duration_seconds.observe(duration)
    
    def record_prediction(self, model_name: str, duration: float, success: bool = True):
        """Record prediction metrics"""
        if success:
            self.predictions_total.labels(model_name=model_name).inc()
        self.prediction_duration_seconds.observe(duration)
    
    def record_error(self, error_type: str):
        """Record an error"""
        self.prediction_errors_total.labels(error_type=error_type).inc()
    
    def set_app_info(self, version: str, environment: str):
        """Set application information"""
        self.app_info.info({
            'version': version,
            'environment': environment
        })


# Global metrics instance
metrics = MetricsCollector()


def setup_monitoring():
    """Setup monitoring and metrics collection"""
    import os
    
    # Set application info
    version = os.getenv('APP_VERSION', '1.0.0')
    environment = os.getenv('ENVIRONMENT', 'development')
    
    metrics.set_app_info(version, environment)
    
    logger.info("Monitoring setup completed", version=version, environment=environment)
