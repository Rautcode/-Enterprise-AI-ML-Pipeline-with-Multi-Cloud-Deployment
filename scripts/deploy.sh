#!/bin/bash

# Enterprise ML Pipeline Deployment Script
# Automates the deployment of ML infrastructure and applications

set -e

# Configuration
PROJECT_NAME="aimlpipeline"
ENVIRONMENT=${1:-dev}
CLOUD_PROVIDER=${2:-azure}
REGION=${3:-"West US 2"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local tools=("docker" "kubectl" "terraform" "helm")
    
    for tool in "${tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            log_error "$tool is not installed"
            exit 1
        fi
    done
    
    # Check cloud CLI tools
    if [ "$CLOUD_PROVIDER" = "azure" ] || [ "$CLOUD_PROVIDER" = "both" ]; then
        if ! command -v az &> /dev/null; then
            log_error "Azure CLI is not installed"
            exit 1
        fi
    fi
    
    if [ "$CLOUD_PROVIDER" = "aws" ] || [ "$CLOUD_PROVIDER" = "both" ]; then
        if ! command -v aws &> /dev/null; then
            log_error "AWS CLI is not installed"
            exit 1
        fi
    fi
    
    log_success "Prerequisites check completed"
}

# Validate environment variables
validate_environment() {
    log_info "Validating environment variables..."
    
    case $CLOUD_PROVIDER in
        azure|both)
            if [ -z "$AZURE_CLIENT_ID" ] || [ -z "$AZURE_CLIENT_SECRET" ] || [ -z "$AZURE_TENANT_ID" ]; then
                log_error "Azure credentials not set. Please set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID"
                exit 1
            fi
            ;;
        aws|both)
            if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
                log_error "AWS credentials not set. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
                exit 1
            fi
            ;;
    esac
    
    log_success "Environment validation completed"
}

# Deploy infrastructure using Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure for $CLOUD_PROVIDER..."
    
    case $CLOUD_PROVIDER in
        azure)
            deploy_azure_infrastructure
            ;;
        aws)
            deploy_aws_infrastructure
            ;;
        both)
            deploy_azure_infrastructure
            deploy_aws_infrastructure
            ;;
        *)
            log_error "Invalid cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
}

deploy_azure_infrastructure() {
    log_info "Deploying Azure infrastructure..."
    
    cd terraform/azure
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan \
        -var="project_name=$PROJECT_NAME" \
        -var="environment=$ENVIRONMENT" \
        -var="location=$REGION" \
        -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Get outputs
    AKS_CLUSTER_NAME=$(terraform output -raw aks_cluster_name)
    RESOURCE_GROUP_NAME=$(terraform output -raw resource_group_name)
    ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
    
    # Configure kubectl
    az aks get-credentials --resource-group $RESOURCE_GROUP_NAME --name $AKS_CLUSTER_NAME
    
    cd ../..
    log_success "Azure infrastructure deployed successfully"
}

deploy_aws_infrastructure() {
    log_info "Deploying AWS infrastructure..."
    
    cd terraform/aws
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan \
        -var="project_name=$PROJECT_NAME" \
        -var="environment=$ENVIRONMENT" \
        -var="region=$REGION" \
        -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Get outputs
    EKS_CLUSTER_NAME=$(terraform output -raw eks_cluster_name)
    ECR_ML_API_URL=$(terraform output -raw ecr_ml_api_repository_url)
    ECR_ML_TRAINING_URL=$(terraform output -raw ecr_ml_training_repository_url)
    
    # Configure kubectl
    aws eks update-kubeconfig --region $REGION --name $EKS_CLUSTER_NAME
    
    cd ../..
    log_success "AWS infrastructure deployed successfully"
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Build ML API image
    log_info "Building ML API image..."
    docker build -t ml-api:$ENVIRONMENT-$(git rev-parse --short HEAD) docker/ml-api/
    
    # Build ML Training image
    log_info "Building ML Training image..."
    docker build -t ml-training:$ENVIRONMENT-$(git rev-parse --short HEAD) docker/ml-training/
    
    # Tag and push images based on cloud provider
    case $CLOUD_PROVIDER in
        azure)
            push_to_azure_registry
            ;;
        aws)
            push_to_aws_registry
            ;;
        both)
            push_to_azure_registry
            push_to_aws_registry
            ;;
    esac
    
    log_success "Docker images built and pushed successfully"
}

push_to_azure_registry() {
    log_info "Pushing images to Azure Container Registry..."
    
    # Login to ACR
    az acr login --name ${PROJECT_NAME}${ENVIRONMENT}acr
    
    # Tag and push images
    docker tag ml-api:$ENVIRONMENT-$(git rev-parse --short HEAD) ${PROJECT_NAME}${ENVIRONMENT}acr.azurecr.io/ml-api:latest
    docker tag ml-training:$ENVIRONMENT-$(git rev-parse --short HEAD) ${PROJECT_NAME}${ENVIRONMENT}acr.azurecr.io/ml-training:latest
    
    docker push ${PROJECT_NAME}${ENVIRONMENT}acr.azurecr.io/ml-api:latest
    docker push ${PROJECT_NAME}${ENVIRONMENT}acr.azurecr.io/ml-training:latest
}

push_to_aws_registry() {
    log_info "Pushing images to Amazon ECR..."
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Login to ECR
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    # Tag and push images
    docker tag ml-api:$ENVIRONMENT-$(git rev-parse --short HEAD) $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/$ENVIRONMENT/ml-api:latest
    docker tag ml-training:$ENVIRONMENT-$(git rev-parse --short HEAD) $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/$ENVIRONMENT/ml-training:latest
    
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/$ENVIRONMENT/ml-api:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/$ENVIRONMENT/ml-training:latest
}

# Deploy Kubernetes applications
deploy_applications() {
    log_info "Deploying Kubernetes applications..."
    
    # Create namespace
    kubectl apply -f kubernetes/base/storage.yaml
    
    # Update image references in manifests
    export IMAGE_TAG="$ENVIRONMENT-$(git rev-parse --short HEAD)"
    
    case $CLOUD_PROVIDER in
        azure)
            export REGISTRY="${PROJECT_NAME}${ENVIRONMENT}acr.azurecr.io"
            ;;
        aws)
            AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
            export REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/$ENVIRONMENT"
            ;;
    esac
    
    # Deploy applications with blue-green strategy
    envsubst < kubernetes/base/ml-api.yaml | kubectl apply -f -
    envsubst < kubernetes/base/ml-training.yaml | kubectl apply -f -
    
    # Wait for deployments to be ready
    kubectl rollout status deployment/ml-api -n ml-pipeline --timeout=600s
    
    log_success "Applications deployed successfully"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring stack..."
    
    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Install Prometheus Operator
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set grafana.adminPassword=admin123 \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false
    
    log_success "Monitoring stack deployed successfully"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=ml-api -n ml-pipeline --timeout=300s
    
    # Get service endpoint
    if [ "$CLOUD_PROVIDER" = "azure" ]; then
        ENDPOINT=$(kubectl get service ml-api-service -n ml-pipeline -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    else
        ENDPOINT=$(kubectl get service ml-api-service -n ml-pipeline -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    
    # Test health endpoint
    if curl -f http://$ENDPOINT/health; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi
}

# Main deployment function
main() {
    log_info "Starting ML Pipeline deployment for environment: $ENVIRONMENT, cloud: $CLOUD_PROVIDER"
    
    check_prerequisites
    validate_environment
    deploy_infrastructure
    build_and_push_images
    deploy_applications
    setup_monitoring
    run_health_checks
    
    log_success "ML Pipeline deployment completed successfully!"
    log_info "Access your services:"
    kubectl get services -n ml-pipeline
}

# Show usage information
show_usage() {
    echo "Usage: $0 [ENVIRONMENT] [CLOUD_PROVIDER] [REGION]"
    echo ""
    echo "Arguments:"
    echo "  ENVIRONMENT     Environment to deploy to (dev, staging, prod) [default: dev]"
    echo "  CLOUD_PROVIDER  Cloud provider (azure, aws, both) [default: azure]"
    echo "  REGION          Cloud region [default: West US 2]"
    echo ""
    echo "Examples:"
    echo "  $0 dev azure \"West US 2\""
    echo "  $0 prod aws us-west-2"
    echo "  $0 staging both"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_usage
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
