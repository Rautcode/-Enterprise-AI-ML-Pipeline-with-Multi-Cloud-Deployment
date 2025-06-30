# Enterprise ML Pipeline Deployment Script for Windows
# PowerShell script for deploying ML infrastructure and applications

param(
    [Parameter(Position=0)]
    [string]$Environment = "dev",
    
    [Parameter(Position=1)]
    [string]$CloudProvider = "azure",
    
    [Parameter(Position=2)]
    [string]$Region = "West US 2",
    
    [switch]$Help
)

# Configuration
$ProjectName = "aimlpipeline"
$ErrorActionPreference = "Stop"

# Function to write colored output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Show-Usage {
    Write-Host @"
Enterprise ML Pipeline Deployment Script

Usage: .\deploy.ps1 [Environment] [CloudProvider] [Region]

Parameters:
  Environment     Environment to deploy to (dev, staging, prod) [default: dev]
  CloudProvider   Cloud provider (azure, aws, both) [default: azure]
  Region          Cloud region [default: West US 2]

Examples:
  .\deploy.ps1 dev azure "West US 2"
  .\deploy.ps1 prod aws us-west-2
  .\deploy.ps1 staging both

Switches:
  -Help           Show this help message
"@
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    $tools = @("docker", "kubectl", "terraform", "helm")
    
    foreach ($tool in $tools) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            Write-Error "$tool is not installed or not in PATH"
            exit 1
        }
    }
    
    # Check cloud CLI tools
    if ($CloudProvider -eq "azure" -or $CloudProvider -eq "both") {
        if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
            Write-Error "Azure CLI is not installed"
            exit 1
        }
    }
    
    if ($CloudProvider -eq "aws" -or $CloudProvider -eq "both") {
        if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
            Write-Error "AWS CLI is not installed"
            exit 1
        }
    }
    
    Write-Success "Prerequisites check completed"
}

function Test-Environment {
    Write-Info "Validating environment variables..."
    
    switch ($CloudProvider) {
        { $_ -eq "azure" -or $_ -eq "both" } {
            if (-not ($env:AZURE_CLIENT_ID -and $env:AZURE_CLIENT_SECRET -and $env:AZURE_TENANT_ID)) {
                Write-Error "Azure credentials not set. Please set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID"
                exit 1
            }
        }
        { $_ -eq "aws" -or $_ -eq "both" } {
            if (-not ($env:AWS_ACCESS_KEY_ID -and $env:AWS_SECRET_ACCESS_KEY)) {
                Write-Error "AWS credentials not set. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
                exit 1
            }
        }
    }
    
    Write-Success "Environment validation completed"
}

function Deploy-Infrastructure {
    Write-Info "Deploying infrastructure for $CloudProvider..."
    
    switch ($CloudProvider) {
        "azure" { Deploy-AzureInfrastructure }
        "aws" { Deploy-AWSInfrastructure }
        "both" { 
            Deploy-AzureInfrastructure
            Deploy-AWSInfrastructure
        }
        default {
            Write-Error "Invalid cloud provider: $CloudProvider"
            exit 1
        }
    }
}

function Deploy-AzureInfrastructure {
    Write-Info "Deploying Azure infrastructure..."
    
    Push-Location "terraform\azure"
    
    try {
        # Initialize Terraform
        terraform init
        
        # Plan deployment
        terraform plan `
            -var="project_name=$ProjectName" `
            -var="environment=$Environment" `
            -var="location=$Region" `
            -out=tfplan
        
        # Apply deployment
        terraform apply tfplan
        
        # Get outputs
        $script:AKSClusterName = terraform output -raw aks_cluster_name
        $script:ResourceGroupName = terraform output -raw resource_group_name
        $script:ACRLoginServer = terraform output -raw acr_login_server
        
        # Configure kubectl
        az aks get-credentials --resource-group $ResourceGroupName --name $AKSClusterName
        
        Write-Success "Azure infrastructure deployed successfully"
    }
    finally {
        Pop-Location
    }
}

function Deploy-AWSInfrastructure {
    Write-Info "Deploying AWS infrastructure..."
    
    Push-Location "terraform\aws"
    
    try {
        # Initialize Terraform
        terraform init
        
        # Plan deployment
        terraform plan `
            -var="project_name=$ProjectName" `
            -var="environment=$Environment" `
            -var="region=$Region" `
            -out=tfplan
        
        # Apply deployment
        terraform apply tfplan
        
        # Get outputs
        $script:EKSClusterName = terraform output -raw eks_cluster_name
        $script:ECRMLApiURL = terraform output -raw ecr_ml_api_repository_url
        $script:ECRMLTrainingURL = terraform output -raw ecr_ml_training_repository_url
        
        # Configure kubectl
        aws eks update-kubeconfig --region $Region --name $EKSClusterName
        
        Write-Success "AWS infrastructure deployed successfully"
    }
    finally {
        Pop-Location
    }
}

function Build-AndPushImages {
    Write-Info "Building and pushing Docker images..."
    
    # Get git commit hash
    $GitHash = git rev-parse --short HEAD
    
    # Build ML API image
    Write-Info "Building ML API image..."
    docker build -t "ml-api:$Environment-$GitHash" docker\ml-api\
    
    # Build ML Training image
    Write-Info "Building ML Training image..."
    docker build -t "ml-training:$Environment-$GitHash" docker\ml-training\
    
    # Tag and push images based on cloud provider
    switch ($CloudProvider) {
        "azure" { Push-ToAzureRegistry -GitHash $GitHash }
        "aws" { Push-ToAWSRegistry -GitHash $GitHash }
        "both" { 
            Push-ToAzureRegistry -GitHash $GitHash
            Push-ToAWSRegistry -GitHash $GitHash
        }
    }
    
    Write-Success "Docker images built and pushed successfully"
}

function Push-ToAzureRegistry {
    param([string]$GitHash)
    
    Write-Info "Pushing images to Azure Container Registry..."
    
    # Login to ACR
    az acr login --name "$ProjectName$Environment" + "acr"
    
    # Tag and push images
    $acrName = "$ProjectName$Environment" + "acr.azurecr.io"
    docker tag "ml-api:$Environment-$GitHash" "$acrName/ml-api:latest"
    docker tag "ml-training:$Environment-$GitHash" "$acrName/ml-training:latest"
    
    docker push "$acrName/ml-api:latest"
    docker push "$acrName/ml-training:latest"
}

function Push-ToAWSRegistry {
    param([string]$GitHash)
    
    Write-Info "Pushing images to Amazon ECR..."
    
    # Get AWS account ID
    $AWSAccountId = aws sts get-caller-identity --query Account --output text
    
    # Login to ECR
    $loginToken = aws ecr get-login-password --region $Region
    $loginToken | docker login --username AWS --password-stdin "$AWSAccountId.dkr.ecr.$Region.amazonaws.com"
    
    # Tag and push images
    $ecrBase = "$AWSAccountId.dkr.ecr.$Region.amazonaws.com/$ProjectName/$Environment"
    docker tag "ml-api:$Environment-$GitHash" "$ecrBase/ml-api:latest"
    docker tag "ml-training:$Environment-$GitHash" "$ecrBase/ml-training:latest"
    
    docker push "$ecrBase/ml-api:latest"
    docker push "$ecrBase/ml-training:latest"
}

function Deploy-Applications {
    Write-Info "Deploying Kubernetes applications..."
    
    # Create namespace and storage
    kubectl apply -f kubernetes\base\storage.yaml
    
    # Get git commit hash
    $GitHash = git rev-parse --short HEAD
    
    # Set environment variables for manifest substitution
    $env:IMAGE_TAG = "$Environment-$GitHash"
    
    switch ($CloudProvider) {
        "azure" {
            $env:REGISTRY = "$ProjectName$Environment" + "acr.azurecr.io"
        }
        "aws" {
            $AWSAccountId = aws sts get-caller-identity --query Account --output text
            $env:REGISTRY = "$AWSAccountId.dkr.ecr.$Region.amazonaws.com/$ProjectName/$Environment"
        }
    }
    
    # Deploy applications with environment variable substitution
    # Note: PowerShell doesn't have envsubst, so we'll use a simple replacement
    $apiManifest = Get-Content kubernetes\base\ml-api.yaml -Raw
    $apiManifest = $apiManifest -replace '\$\{REGISTRY\}', $env:REGISTRY
    $apiManifest = $apiManifest -replace '\$\{IMAGE_TAG\}', $env:IMAGE_TAG
    $apiManifest | kubectl apply -f -
    
    $trainingManifest = Get-Content kubernetes\base\ml-training.yaml -Raw
    $trainingManifest = $trainingManifest -replace '\$\{REGISTRY\}', $env:REGISTRY
    $trainingManifest = $trainingManifest -replace '\$\{IMAGE_TAG\}', $env:IMAGE_TAG
    $trainingManifest | kubectl apply -f -
    
    # Wait for deployments to be ready
    kubectl rollout status deployment/ml-api -n ml-pipeline --timeout=600s
    
    Write-Success "Applications deployed successfully"
}

function Setup-Monitoring {
    Write-Info "Setting up monitoring stack..."
    
    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Install Prometheus Operator
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack `
        --namespace monitoring `
        --create-namespace `
        --set grafana.adminPassword=admin123 `
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false `
        --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false
    
    Write-Success "Monitoring stack deployed successfully"
}

function Test-HealthChecks {
    Write-Info "Running health checks..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=ml-api -n ml-pipeline --timeout=300s
    
    # Get service endpoint
    if ($CloudProvider -eq "azure") {
        $endpoint = kubectl get service ml-api-service -n ml-pipeline -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
    } else {
        $endpoint = kubectl get service ml-api-service -n ml-pipeline -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
    }
    
    # Test health endpoint
    try {
        $response = Invoke-RestMethod -Uri "http://$endpoint/health" -TimeoutSec 30
        Write-Success "Health check passed"
    }
    catch {
        Write-Error "Health check failed: $($_.Exception.Message)"
        exit 1
    }
}

function Main {
    if ($Help) {
        Show-Usage
        return
    }
    
    Write-Info "Starting ML Pipeline deployment for environment: $Environment, cloud: $CloudProvider"
    
    Test-Prerequisites
    Test-Environment
    Deploy-Infrastructure
    Build-AndPushImages
    Deploy-Applications
    Setup-Monitoring
    Test-HealthChecks
    
    Write-Success "ML Pipeline deployment completed successfully!"
    Write-Info "Access your services:"
    kubectl get services -n ml-pipeline
}

# Run main function
Main
