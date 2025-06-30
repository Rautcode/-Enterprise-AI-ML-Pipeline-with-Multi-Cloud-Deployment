# Deployment Guide

This guide provides step-by-step instructions for deploying the Enterprise AI/ML Pipeline to Azure and/or AWS cloud platforms.

## Prerequisites

### Software Requirements
- **Docker Desktop** (version 4.0+)
- **kubectl** (version 1.28+)
- **Terraform** (version 1.6+)
- **Helm** (version 3.12+)
- **Git** (version 2.30+)

### Cloud CLI Tools
- **Azure CLI** (if deploying to Azure)
- **AWS CLI** (if deploying to AWS)

### System Requirements
- **OS**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB free space
- **Network**: High-speed internet connection

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AIML-Pipeline-Implementation
```

### 2. Set Environment Variables

#### For Azure Deployment
```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
```

#### For AWS Deployment
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"
```

### 3. Run Deployment Script

#### Linux/macOS
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh dev azure "West US 2"
```

#### Windows PowerShell
```powershell
.\scripts\deploy.ps1 dev azure "West US 2"
```

## Detailed Deployment Steps

### Step 1: Infrastructure Deployment

#### Azure Infrastructure
```bash
cd terraform/azure

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="project_name=aimlpipeline" \
  -var="environment=dev" \
  -var="location=West US 2"

# Apply deployment
terraform apply
```

#### AWS Infrastructure
```bash
cd terraform/aws

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="project_name=aimlpipeline" \
  -var="environment=dev" \
  -var="region=us-west-2"

# Apply deployment
terraform apply
```

### Step 2: Container Images

#### Build Images
```bash
# Build ML API image
docker build -t ml-api:latest docker/ml-api/

# Build ML Training image
docker build -t ml-training:latest docker/ml-training/
```

#### Push to Azure Container Registry
```bash
# Login to ACR
az acr login --name aimlpipelinedevacr

# Tag and push images
docker tag ml-api:latest aimlpipelinedevacr.azurecr.io/ml-api:latest
docker tag ml-training:latest aimlpipelinedevacr.azurecr.io/ml-training:latest

docker push aimlpipelinedevacr.azurecr.io/ml-api:latest
docker push aimlpipelinedevacr.azurecr.io/ml-training:latest
```

#### Push to Amazon ECR
```bash
# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com

# Tag and push images
docker tag ml-api:latest $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/aimlpipeline/dev/ml-api:latest
docker tag ml-training:latest $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/aimlpipeline/dev/ml-training:latest

docker push $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/aimlpipeline/dev/ml-api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/aimlpipeline/dev/ml-training:latest
```

### Step 3: Kubernetes Configuration

#### Configure kubectl for Azure
```bash
az aks get-credentials \
  --resource-group aimlpipeline-dev-rg \
  --name aimlpipeline-dev-aks
```

#### Configure kubectl for AWS
```bash
aws eks update-kubeconfig \
  --region us-west-2 \
  --name aimlpipeline-dev-eks
```

### Step 4: Application Deployment

#### Create Namespace and Storage
```bash
kubectl apply -f kubernetes/base/storage.yaml
```

#### Deploy ML API
```bash
kubectl apply -f kubernetes/base/ml-api.yaml
```

#### Deploy ML Training
```bash
kubectl apply -f kubernetes/base/ml-training.yaml
```

#### Verify Deployment
```bash
# Check pod status
kubectl get pods -n ml-pipeline

# Check services
kubectl get services -n ml-pipeline

# Check deployment status
kubectl rollout status deployment/ml-api -n ml-pipeline
```

### Step 5: Monitoring Setup

#### Install Prometheus and Grafana
```bash
# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus Operator
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=admin123
```

#### Access Monitoring Dashboards
```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Access Grafana at http://localhost:3000
# Username: admin, Password: admin123
```

## Environment-Specific Configurations

### Development Environment
- **Resources**: Minimal resource allocation
- **Scaling**: 1-3 pods
- **Monitoring**: Basic metrics
- **Storage**: Standard storage classes

### Staging Environment
- **Resources**: Production-like resource allocation
- **Scaling**: 2-10 pods
- **Monitoring**: Full monitoring stack
- **Storage**: Performance storage classes

### Production Environment
- **Resources**: High resource allocation
- **Scaling**: 3-20 pods
- **Monitoring**: Full monitoring with alerting
- **Storage**: Premium storage classes
- **Security**: Enhanced security policies

## Blue-Green Deployment

### Overview
Blue-Green deployment ensures zero-downtime deployments by maintaining two identical production environments.

### Implementation Steps

1. **Deploy Green Environment**
```bash
# Update image tag to new version
export NEW_IMAGE_TAG="v2.0.0"

# Apply updated manifests
envsubst < kubernetes/base/ml-api.yaml | kubectl apply -f -

# Wait for green deployment
kubectl rollout status deployment/ml-api-green -n ml-pipeline
```

2. **Health Check Green Environment**
```bash
# Test green environment
kubectl port-forward svc/ml-api-green-service 8080:80 -n ml-pipeline
curl http://localhost:8080/health
```

3. **Switch Traffic to Green**
```bash
# Update service selector to point to green deployment
kubectl patch service ml-api-service -n ml-pipeline \
  -p '{"spec":{"selector":{"version":"green"}}}'
```

4. **Cleanup Blue Environment**
```bash
# After verification, remove blue deployment
kubectl delete deployment ml-api-blue -n ml-pipeline
```

## Multi-Cloud Deployment

### Active-Active Configuration
Deploy to both Azure and AWS simultaneously with traffic distribution.

```bash
# Deploy to Azure
./scripts/deploy.sh prod azure "West US 2"

# Deploy to AWS
./scripts/deploy.sh prod aws "us-west-2"

# Configure DNS for load balancing
# Use Route 53 or Azure DNS for geographic routing
```

### Primary-Secondary Configuration
Use one cloud as primary and another as disaster recovery.

```bash
# Primary deployment (Azure)
./scripts/deploy.sh prod azure "West US 2"

# Secondary deployment (AWS) - standby mode
./scripts/deploy.sh prod aws "us-west-2"

# Configure failover mechanisms
```

## Troubleshooting

### Common Issues

#### 1. Pod Startup Issues
```bash
# Check pod logs
kubectl logs -f deployment/ml-api -n ml-pipeline

# Check pod events
kubectl describe pod <pod-name> -n ml-pipeline

# Check resource constraints
kubectl top pods -n ml-pipeline
```

#### 2. Image Pull Issues
```bash
# Check image pull secrets
kubectl get secrets -n ml-pipeline

# Check registry credentials
kubectl describe secret registry-secret -n ml-pipeline

# Manual image pull test
docker pull <image-name>
```

#### 3. Network Connectivity Issues
```bash
# Check service endpoints
kubectl get endpoints -n ml-pipeline

# Test service connectivity
kubectl run test-pod --image=busybox -it --rm -- /bin/sh
# Inside pod: wget -qO- http://ml-api-service.ml-pipeline.svc.cluster.local/health
```

#### 4. Resource Constraints
```bash
# Check cluster resources
kubectl top nodes

# Check resource quotas
kubectl describe resourcequota -n ml-pipeline

# Scale down if needed
kubectl scale deployment ml-api --replicas=1 -n ml-pipeline
```

### Rollback Procedures

#### Application Rollback
```bash
# Rollback to previous version
kubectl rollout undo deployment/ml-api -n ml-pipeline

# Rollback to specific revision
kubectl rollout undo deployment/ml-api --to-revision=2 -n ml-pipeline

# Check rollback status
kubectl rollout status deployment/ml-api -n ml-pipeline
```

#### Infrastructure Rollback
```bash
# Terraform rollback
cd terraform/azure
terraform plan -destroy
terraform apply -destroy

# Or rollback to previous state
terraform apply -target=<specific-resource>
```

## Performance Tuning

### Resource Optimization
```yaml
# Update resource requests/limits
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "1000m"
    memory: "2Gi"
```

### Auto-scaling Tuning
```yaml
# Update HPA configuration
spec:
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Storage Performance
```yaml
# Use faster storage class
storageClassName: premium-ssd
```

## Security Hardening

### Network Policies
```bash
# Apply network policies
kubectl apply -f kubernetes/security/network-policies.yaml
```

### Pod Security Standards
```bash
# Apply pod security policies
kubectl apply -f kubernetes/security/pod-security-policies.yaml
```

### Secret Management
```bash
# Use external secret management
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace
```

## Monitoring and Alerting

### Custom Metrics
```bash
# Deploy custom metrics
kubectl apply -f monitoring/custom-metrics.yaml
```

### Alerting Rules
```bash
# Configure alert rules
kubectl apply -f monitoring/alert-rules.yaml
```

### Dashboard Import
```bash
# Import Grafana dashboards
kubectl apply -f monitoring/dashboards/
```

## Backup and Disaster Recovery

### Database Backups
```bash
# Configure automated backups
kubectl apply -f backup/database-backup.yaml
```

### Persistent Volume Backups
```bash
# Setup volume snapshots
kubectl apply -f backup/volume-snapshots.yaml
```

### Cross-Region Replication
```bash
# Configure cross-region backup
kubectl apply -f backup/cross-region-backup.yaml
```
