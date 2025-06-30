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

# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {}
}

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

# Create Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = "${var.project_name}${var.environment}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Premium"
  admin_enabled       = true

  georeplications {
    location                = "East US"
    zone_redundancy_enabled = true
    tags = {
      Environment = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create Azure Kubernetes Service
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${var.project_name}-${var.environment}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${var.project_name}-${var.environment}"

  default_node_pool {
    name                = "default"
    node_count          = var.node_count
    vm_size             = var.node_vm_size
    auto_scaling_enabled = true
    min_count          = 2
    max_count          = 10
    os_disk_size_gb    = 30
    type               = "VirtualMachineScaleSets"

    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
  }

  # Enable monitoring
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create additional node pool for GPU workloads
resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  name                  = "gpu"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size              = "Standard_NC6s_v3"
  node_count           = 1
  auto_scaling_enabled = true
  min_count           = 0
  max_count           = 5
  os_disk_size_gb     = 30
  node_taints         = ["nvidia.com/gpu=true:NoSchedule"]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-${var.environment}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${var.project_name}-${var.environment}-appinsights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create Storage Account for ML artifacts
resource "azurerm_storage_account" "ml_storage" {
  name                     = "${var.project_name}${var.environment}mlstorage"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  
  blob_properties {
    versioning_enabled = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create blob containers
resource "azurerm_storage_container" "models" {
  name                 = "models"
  storage_account_id   = azurerm_storage_account.ml_storage.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "datasets" {
  name                 = "datasets"  
  storage_account_id   = azurerm_storage_account.ml_storage.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "artifacts" {
  name                 = "artifacts"
  storage_account_id   = azurerm_storage_account.ml_storage.id
  container_access_type = "private"
}

# Grant AKS access to ACR
resource "azurerm_role_assignment" "aks_acr" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                           = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# Create Virtual Network for AKS
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-${var.environment}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "${var.project_name}-${var.environment}-aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Create Network Security Group
resource "azurerm_network_security_group" "aks" {
  name                = "${var.project_name}-${var.environment}-aks-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowHTTP"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Associate Network Security Group to Subnet
resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}

# Create Key Vault for secrets
resource "azurerm_key_vault" "main" {
  name                        = "${var.project_name}-${var.environment}-kv"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get",
    ]

    secret_permissions = [
      "Get",
      "Set",
    ]

    storage_permissions = [
      "Get",
    ]
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Data source for current client configuration
data "azurerm_client_config" "current" {}

# Random string for unique naming
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}