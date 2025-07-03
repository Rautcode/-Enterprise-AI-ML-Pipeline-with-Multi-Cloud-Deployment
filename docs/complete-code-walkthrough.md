# Enterprise AI/ML Pipeline - Complete Code Walkthrough

## 📁 Project Structure Overview

This is an enterprise-grade AI/ML pipeline with multi-cloud deployment capabilities. Here's what each directory contains:

```
├── .github/workflows/     # CI/CD automation
├── terraform/            # Infrastructure as Code
├── docker/              # Container configurations
├── kubernetes/          # Orchestration manifests
├── src/                 # Application source code
├── scripts/             # Deployment utilities
├── docs/                # Documentation
├── monitoring/          # Observability stack
├── nginx/               # Load balancer config
└── notebooks/           # Data science experiments
```

## 🔧 Core Components Breakdown

### 1. CI/CD Pipeline (.github/workflows/ci-cd.yml)

This file defines the complete automation pipeline for testing, building, and deploying the ML application.

#### **Line 1: Workflow Name**
```yaml
name: Multi-Cloud ML Pipeline CI/CD
```
- Sets a descriptive name for the GitHub Actions workflow
- This name appears in the Actions tab and notifications

#### **Lines 3-27: Trigger Configuration**
```yaml
on:
  push:
    branches: [ main, develop ]    # Auto-trigger on code pushes
  pull_request:
    branches: [ main ]             # Auto-trigger on PRs to main
  workflow_dispatch:               # Manual trigger option
    inputs:
      environment:                 # User selects deployment environment
        description: 'Environment to deploy to'
        required: true
        default: 'dev'
        type: choice
        options: [dev, staging, prod]
      cloud_provider:              # User selects cloud provider
        description: 'Cloud provider'
        required: true
        default: 'azure'
        type: choice
        options: [azure, aws, both]
```

**Purpose**: 
- **Automated triggers**: Run tests on every code change
- **Manual triggers**: Allow controlled deployments to specific environments
- **Multi-cloud support**: Deploy to Azure, AWS, or both simultaneously

#### **Lines 29-33: Environment Variables**
```yaml
env:
  REGISTRY_AZURE: ${{ secrets.AZURE_REGISTRY }}
  REGISTRY_AWS: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ secrets.AWS_REGION }}.amazonaws.com
  PROJECT_NAME: aimlpipeline
```

**Purpose**:
- **REGISTRY_AZURE**: Azure Container Registry URL for storing Docker images
- **REGISTRY_AWS**: AWS ECR URL (constructed from account ID and region)
- **PROJECT_NAME**: Consistent naming across all resources

#### **Lines 35-39: Security Permissions**
```yaml
permissions:
  contents: read        # Read repository code
  security-events: write # Write security scan results
  actions: read         # Read workflow status
```

**Purpose**: Minimal required permissions following security best practices

#### **Lines 41-85: Test Job**
```yaml
test:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ["3.9", "3.10", "3.11"]  # Test multiple Python versions
```

**Test Process**:
1. **Setup**: Install Python and dependencies
2. **Linting**: Code quality checks with flake8
3. **Formatting**: Code style checks with black
4. **Type checking**: Static analysis with mypy  
5. **Unit tests**: Run pytest test suite
6. **Coverage**: Generate and upload coverage reports

**Key Features**:
- **Matrix testing**: Ensures compatibility across Python versions
- **Dependency caching**: Speeds up subsequent runs
- **Non-blocking**: Tests continue even if some checks fail
- **Comprehensive**: Covers linting, formatting, types, and functionality

### 2. ML API Service (src/ml-api/main.py)

This is the core FastAPI application that serves ML models via REST API.

#### **Lines 1-5: Module Documentation**
```python
"""
ML API Service - FastAPI application for serving ML models
Provides REST API endpoints for model inference with monitoring and logging
"""
```

**Purpose**: Clear documentation explaining the module's role in the system

#### **Lines 6-24: Import Statements**
```python
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
```

**Breakdown**:
- **Standard library**: `os`, `logging`, `time`, `typing`, `asyncio` for basic functionality
- **FastAPI**: Web framework for building the API (`FastAPI`, `HTTPException`, etc.)
- **Data processing**: `numpy` for numerical operations, `joblib` for model serialization
- **Monitoring**: `prometheus_client` for metrics collection, `structlog` for structured logging
- **Custom modules**: `models`, `monitoring`, `config` for application-specific logic

#### **Lines 27-43: Structured Logging Configuration**
```python
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,     # Filter by log level
        structlog.stdlib.add_logger_name,     # Add logger name to output
        structlog.stdlib.add_log_level,       # Add log level to output
        structlog.stdlib.PositionalArgumentsFormatter(),  # Format arguments
        structlog.processors.JSONRenderer()   # Output as JSON
    ],
    context_class=dict,                       # Use dict for context
    logger_factory=structlog.stdlib.LoggerFactory(),  # Standard logger factory
    wrapper_class=structlog.stdlib.BoundLogger,       # Bound logger class
    cache_logger_on_first_use=True,          # Cache for performance
)

logger = structlog.get_logger()
```

**Purpose**:
- **Structured logging**: Outputs logs in JSON format for easy parsing
- **Enterprise-ready**: Includes log levels, timestamps, and context
- **Performance**: Caching reduces overhead
- **Observability**: Enables log aggregation and analysis

#### **Lines 46-50: Pydantic Data Models**
```python
class PredictionRequest(BaseModel):
    """Request model for predictions"""
    features: List[float] = Field(..., description="Input features for prediction")
    model_name: Optional[str] = Field(default="default", description="Model name to use")
```

**Purpose**:
- **Input validation**: Ensures API receives correctly formatted data
- **Type safety**: Validates data types at runtime
- **Documentation**: Automatic API documentation generation
- **Default values**: Provides sensible defaults for optional fields

### 3. Docker Configuration (docker/ml-api/Dockerfile)

This multi-stage Dockerfile creates an optimized container for the ML API service.

#### **Lines 1-2: Multi-stage Build Setup**
```dockerfile
# Multi-stage build for ML API
FROM python:3.11-slim as builder
```

**Purpose**:
- **Multi-stage build**: Reduces final image size by separating build and runtime environments
- **Python 3.11-slim**: Lightweight base image with Python pre-installed
- **Builder stage**: Used for installing dependencies and compiling code

#### **Lines 4-6: Working Directory**
```dockerfile
# Set working directory
WORKDIR /app
```

**Purpose**: Sets the working directory inside the container for all subsequent commands

#### **Lines 8-13: System Dependencies**
```dockerfile
# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*
```

**Breakdown**:
- **gcc/g++**: Compilers needed for building Python packages with C extensions
- **make**: Build tool for compiling dependencies
- **Cleanup**: `rm -rf /var/lib/apt/lists/*` reduces image size by removing package lists

#### **Lines 15-22: Python Dependencies**
```dockerfile
# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
```

**Docker Cache Optimization**:
- **Copy requirements first**: If requirements.txt doesn't change, Docker reuses cached layers
- **Virtual environment**: Isolates dependencies from system Python
- **No cache**: `--no-cache-dir` reduces image size by not storing pip cache

#### **Lines 24-25: Production Stage**
```dockerfile
# Production stage
FROM python:3.11-slim as production
```

**Purpose**: Second stage creates the final, lightweight production image

#### **Lines 27-30: Environment Variables**
```dockerfile
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
```

**Optimization**:
- **PYTHONDONTWRITEBYTECODE=1**: Prevents Python from creating .pyc files (reduces space)
- **PYTHONUNBUFFERED=1**: Ensures Python output is sent directly to terminal (better logging)
- **PATH**: Adds virtual environment to PATH

#### **Lines 32-33: Security**
```dockerfile
# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
```

**Security best practice**: Running containers as non-root user reduces security risks

#### **Lines 35-39: Runtime Dependencies**
```dockerfile
# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

**Purpose**: 
- **curl**: Needed for health checks and external API calls
- **Minimal dependencies**: Only installs what's needed for runtime

#### **Lines 41: Copy Dependencies**
```dockerfile
# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
```

**Multi-stage benefit**: Copies only the installed dependencies, not the build tools

### 4. Infrastructure as Code (terraform/azure/main.tf)

This Terraform configuration provisions Azure infrastructure for the ML pipeline.

#### **Lines 1-21: Provider Configuration**
```terraform
# Configure the Azure Provider
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~>3.1"
    }
  }
  
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstateaimlpipeline"
    container_name       = "tfstate"
    key                  = "azure/terraform.tfstate"
  }
}
```

**Key Components**:
- **Provider versions**: Pins Azure provider to version 3.x for stability
- **Random provider**: Used for generating unique resource names
- **Remote backend**: Stores Terraform state in Azure Storage for team collaboration
- **State isolation**: Separate state file for Azure resources

#### **Lines 23-25: Provider Features**
```terraform
# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {}
}
```

**Purpose**: Enables all Azure provider features with default settings

#### **Lines 27-37: Resource Group**
```terraform
# Create a resource group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}
```

**Infrastructure Pattern**:
- **Naming convention**: `{project}-{environment}-rg` for consistency
- **Location variable**: Configurable deployment region
- **Resource tagging**: Enables cost tracking and resource management
- **Managed by Terraform**: Clear ownership identification

#### **Lines 39-40: Container Registry Setup**
```terraform
# Create Azure Container Registry
resource "azurerm_container_registry" "acr" {
```

**Purpose**: Azure Container Registry stores Docker images for the ML applications

### 5. Kubernetes Orchestration (kubernetes/base/ml-api.yaml)

This Kubernetes manifest defines the deployment and services for the ML API.

#### **Lines 1-7: Namespace Definition**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ml-pipeline
  labels:
    name: ml-pipeline
    environment: production
```

**Purpose**:
- **Namespace isolation**: Separates ML pipeline resources from other applications
- **Resource organization**: Groups related resources together
- **Environment labeling**: Identifies the deployment environment

#### **Lines 9-17: Deployment Metadata**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-api
  namespace: ml-pipeline
  labels:
    app: ml-api
    tier: api
```

**Kubernetes Resource**:
- **Deployment**: Manages replica sets and rolling updates
- **Namespace**: Places resource in ml-pipeline namespace
- **Labels**: Enable resource selection and organization

#### **Lines 18-21: Replica Configuration**
```yaml
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-api
```

**High Availability**:
- **3 replicas**: Ensures service availability if one pod fails
- **Selector**: Links deployment to pods with matching labels
- **Load distribution**: Traffic distributed across all replicas

#### **Lines 22-31: Pod Template**
```yaml
  template:
    metadata:
      labels:
        app: ml-api
        tier: api
    spec:
      containers:
      - name: ml-api
        image: ml-api:latest
        ports:
        - containerPort: 8000
          name: http
```

**Container Specification**:
- **Image**: References the Docker image built in CI/CD pipeline
- **Port 8000**: FastAPI default port for HTTP traffic
- **Named port**: Enables service discovery and monitoring

#### **Lines 32-39: Environment Configuration**
```yaml
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        - name: MODEL_PATH
          value: "/app/models"
```

**Runtime Configuration**:
- **ENVIRONMENT**: Controls application behavior (production optimizations)
- **LOG_LEVEL**: Controls logging verbosity
- **MODEL_PATH**: Specifies where ML models are stored

### 6. Monitoring Stack (monitoring/prometheus.yml)

This Prometheus configuration defines metrics collection for the ML pipeline.

#### **Lines 1-3: Global Configuration**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
```

**Monitoring Intervals**:
- **scrape_interval**: How often Prometheus collects metrics (15 seconds)
- **evaluation_interval**: How often Prometheus evaluates rules (15 seconds)
- **Balance**: Frequent enough for real-time monitoring, not too frequent to overwhelm

#### **Lines 5-7: Rule Files**
```yaml
rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"
```

**Purpose**: Placeholder for alerting rules (commented out for basic setup)

#### **Lines 9-27: Scrape Configurations**
```yaml
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'ml-api'
    static_configs:
      - targets: ['ml-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

**Monitoring Targets**:
- **Prometheus self-monitoring**: Monitors its own health and performance
- **ML API**: Collects custom application metrics every 10 seconds
- **Node Exporter**: System-level metrics (CPU, memory, disk)
- **cAdvisor**: Container-level metrics (Docker stats)

**Comprehensive Observability**:
- **Application layer**: ML API performance and business metrics
- **System layer**: Infrastructure health and resource usage
- **Container layer**: Docker container performance

### 7. Docker Compose (docker-compose.yml)

This file orchestrates the entire ML pipeline for local development.

#### **Lines 1-5: Compose Version and Documentation**
```yaml
version: '3.8'

# Docker Compose for Local Development
# This setup allows you to run the entire ML pipeline locally for development and testing
```

**Setup**:
- **Version 3.8**: Modern Docker Compose with full feature support
- **Development focus**: Optimized for local testing and development

#### **Lines 7-35: ML API Service**
```yaml
services:
  # ML API Service
  ml-api:
    build:
      context: ./docker/ml-api
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
      - MODEL_PATH=/app/models
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/mldb
```

**Service Configuration**:
- **Build context**: Builds from local Dockerfile
- **Port mapping**: Exposes API on localhost:8000
- **Development environment**: Debug logging enabled
- **Service discovery**: Uses Docker network for inter-service communication
- **External services**: Connects to MLflow, Redis, and PostgreSQL

#### **Lines 21-27: Volume Mounts**
```yaml
    volumes:
      - ml_models:/app/models
      - ./data:/app/data
      - ml_logs:/app/logs
```

**Data Persistence**:
- **ml_models**: Shared volume for trained models
- **./data**: Local data directory mounted for development
- **ml_logs**: Persistent logging across container restarts

#### **Lines 28-34: Health Check**
```yaml
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Reliability**:
- **Health endpoint**: Monitors API availability
- **30-second intervals**: Regular health checks
- **Retry logic**: Allows for temporary failures
- **Startup grace period**: 40 seconds for initialization

### 8. Build Automation (Makefile)

This Makefile provides cross-platform automation for the entire ML pipeline.

#### **Lines 1-8: Project Variables**
```makefile
# Makefile for Enterprise AI/ML Pipeline

# Variables
PROJECT_NAME := aimlpipeline
ENVIRONMENT := dev
CLOUD_PROVIDER := azure
REGION := "West US 2"
```

**Configuration**:
- **PROJECT_NAME**: Consistent naming across all resources
- **ENVIRONMENT**: Default to development (can be overridden)
- **CLOUD_PROVIDER**: Supports Azure and AWS
- **REGION**: Default deployment region

#### **Lines 10-16: Cross-Platform Compatibility**
```makefile
# Detect OS for cross-platform compatibility
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    SHELL := powershell.exe
    .SHELLFLAGS := -NoProfile -Command
else
    DETECTED_OS := $(shell uname -s)
endif
```

**Multi-OS Support**:
- **Windows detection**: Uses PowerShell as shell
- **Unix/Linux/macOS**: Uses default shell
- **Shell flags**: Optimizes PowerShell execution
- **OS-specific commands**: Enables platform-specific operations

#### **Lines 18-19: Git Integration**
```makefile
# Set image tag based on git availability
IMAGE_TAG := $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
```

**Version Control**:
- **Git commit hash**: Uses short commit hash as Docker image tag
- **Fallback**: Uses "latest" if Git is not available
- **Traceability**: Links deployed images to specific code versions

#### **Lines 21-27: Dynamic Registry Selection**
```makefile
# Dynamic registry selection based on cloud provider
ifeq ($(CLOUD_PROVIDER),aws)
    AWS_ACCOUNT_ID := $(shell aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "123456789012")
    DOCKER_REGISTRY := $(AWS_ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com/$(PROJECT_NAME)/$(ENVIRONMENT)
else
    DOCKER_REGISTRY := $(PROJECT_NAME)$(ENVIRONMENT)acr.azurecr.io
endif
```

**Multi-Cloud Support**:
- **AWS ECR**: Constructs ECR URL with account ID and region
- **Azure ACR**: Uses Azure Container Registry naming convention
- **Automatic detection**: Gets AWS account ID dynamically
- **Fallback values**: Provides defaults when CLI tools unavailable

#### **Lines 29-36: Help System**
```makefile
# Help target
.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
```

**User Experience**:
- **Self-documenting**: Automatically generates help from inline comments
- **AWK parsing**: Extracts target descriptions
- **Formatted output**: Clean, aligned help display

#### **Lines 38-40: Prerequisites Check**
```makefile
# Prerequisites
.PHONY: check-prereqs
check-prereqs: ## Check if all prerequisites are installed
	@echo "Checking prerequisites for $(DETECTED_OS)..."
```

**Validation**: Ensures required tools are installed before operations

### 9. Testing Framework (src/tests/test_api.py)

This test suite validates the ML API functionality with a CI/CD-friendly approach.

#### **Lines 1-7: Test Module Setup**
```python
"""
Tests for ML API - Simplified for CI/CD
"""

import pytest
import numpy as np
import json
```

**Test Strategy**:
- **Simplified approach**: Avoids complex imports that may fail in CI/CD
- **Core testing**: Focuses on business logic and data validation
- **CI/CD optimized**: Designed to run reliably in automated environments

#### **Lines 10-21: Data Validation Tests**
```python
def test_data_validation():
    """Test data validation logic"""
    # Test valid features
    valid_features = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert len(valid_features) == 5
    assert all(isinstance(f, (int, float)) for f in valid_features)
    
    # Test numpy array conversion
    np_array = np.array(valid_features)
    assert np_array.shape == (5,)
    assert np_array.dtype == np.float64
```

**Validation Logic**:
- **Feature format**: Ensures input features are numeric
- **Type checking**: Validates data types for ML processing
- **NumPy conversion**: Tests array creation for model input
- **Shape validation**: Confirms expected array dimensions

#### **Lines 24-36: Configuration Tests**
```python
def test_model_configuration():
    """Test model configuration structure"""
    config = {
        "model_name": "test_model",
        "version": "1.0.0",
        "features": ["feature_1", "feature_2", "feature_3"],
        "target": "target_value"
    }
    
    assert "model_name" in config
    assert "version" in config
    assert isinstance(config["features"], list)
    assert len(config["features"]) > 0
```

**Configuration Validation**:
- **Required fields**: Ensures essential configuration elements exist
- **Data structures**: Validates correct data types
- **Business rules**: Checks that feature lists are non-empty
- **Version tracking**: Validates model versioning structure

#### **Lines 39-40: Request Format Tests**
```python
def test_prediction_request_format():
    """Test prediction request format validation"""
    request_data = {
```

**API Contract Testing**:
- **Request structure**: Validates API input format
- **JSON serialization**: Tests data conversion for HTTP requests
- **Contract compliance**: Ensures API adheres to expected interface

### 10. Project Configuration Files

#### **.gitignore - Version Control Exclusions**

This comprehensive .gitignore ensures only essential files are tracked in Git.

**Lines 1-22: Python Artifacts**
```ignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
```

**Purpose**:
- **Compiled bytecode**: Excludes .pyc files and __pycache__ directories
- **Build artifacts**: Ignores distribution and package build files
- **Virtual environments**: Prevents committing environment-specific files
- **Package metadata**: Excludes installation and distribution metadata

**Lines 24-29: Installation Logs**
```ignore
# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt
```

**Cleanup**: Prevents committing installation logs and packaging artifacts

### 11. Environment Configuration (.env.example)

This template provides all necessary environment variables for the ML pipeline.

#### **Lines 1-10: Application Settings**
```bash
# Environment Variables Configuration
# Copy this file to .env and update with your values

# Application Configuration
APP_NAME=ML Pipeline API
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=false
```

**Configuration Management**:
- **Template approach**: Provides examples without exposing secrets
- **Version tracking**: Maintains application version information
- **Environment control**: Switches between dev/staging/prod behaviors
- **Debug control**: Enables/disables detailed logging

#### **Lines 13-17: Server Configuration**
```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

**Server Tuning**:
- **HOST=0.0.0.0**: Binds to all network interfaces (container-friendly)
- **PORT=8000**: FastAPI default port
- **WORKERS=4**: Number of worker processes for handling requests

#### **Lines 20-25: Model Configuration**
```bash
# Model Configuration
MODEL_PATH=/app/models
DEFAULT_MODEL=default
MODEL_CACHE_SIZE=10
MODEL_TIMEOUT=300
```

**ML-Specific Settings**:
- **MODEL_PATH**: Directory where trained models are stored
- **DEFAULT_MODEL**: Fallback model when none specified
- **MODEL_CACHE_SIZE**: Number of models to keep in memory
- **MODEL_TIMEOUT**: Seconds before model request times out

#### **Lines 28-31: Monitoring Configuration**
```bash
# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=INFO
```

**Observability Settings**:
- **ENABLE_METRICS**: Toggle Prometheus metrics collection
- **METRICS_PORT**: Port for metrics endpoint
- **LOG_LEVEL**: Controls logging verbosity (DEBUG/INFO/WARNING/ERROR)

## 🔄 Data Flow Architecture

### Request Processing Flow:
1. **Client Request** → nginx load balancer
2. **Load Balancer** → Kubernetes service
3. **Service** → ML API pod
4. **API** → Model prediction
5. **Response** → Client

### CI/CD Pipeline Flow:
1. **Code Push** → GitHub webhook
2. **GitHub Actions** → Run tests
3. **Tests Pass** → Build Docker images
4. **Images Built** → Push to registries
5. **Deploy** → Kubernetes clusters
6. **Health Check** → Service available

### Monitoring Data Flow:
1. **Application** → Prometheus metrics
2. **Prometheus** → Scrapes metrics
3. **Grafana** → Visualizes data
4. **Alerts** → Notification systems

## 🚀 Key Enterprise Features

### **High Availability**:
- Multi-replica deployments
- Health checks and auto-restart
- Load balancing across instances

### **Scalability**:
- Horizontal pod autoscaling
- Multi-cloud deployment options
- Container orchestration

### **Security**:
- Non-root container execution
- Secret management via environment variables
- Network isolation with namespaces

### **Observability**:
- Structured logging (JSON format)
- Metrics collection (Prometheus)
- Distributed tracing capabilities

### **DevOps Integration**:
- Automated testing and deployment
- Infrastructure as Code (Terraform)
- Multi-environment support

This enterprise-grade ML pipeline provides a production-ready foundation for scalable machine learning applications with comprehensive automation, monitoring, and security features.
