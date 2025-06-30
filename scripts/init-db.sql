-- Initialize databases for MLflow and application
CREATE DATABASE IF NOT EXISTS mlflow;
GRANT ALL PRIVILEGES ON DATABASE mlflow TO postgres;

-- Create tables for the ML application (if needed)
\c mldb;

CREATE TABLE IF NOT EXISTS model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    input_features TEXT NOT NULL,
    prediction TEXT NOT NULL,
    processing_time_ms FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_metrics_name ON model_metrics(model_name);
CREATE INDEX idx_model_metrics_timestamp ON model_metrics(timestamp);
CREATE INDEX idx_predictions_model ON predictions(model_name);
CREATE INDEX idx_predictions_timestamp ON predictions(timestamp);
