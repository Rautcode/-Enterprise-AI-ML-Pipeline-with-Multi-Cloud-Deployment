 # GitHub Secrets Configuration Guide

## Step-by-Step Instructions

### 1. Navigate to Repository Settings
- Go to: `https://github.com/Rautcode/-Enterprise-AI-ML-Pipeline-with-Multi-Cloud-Deployment`
- Click the **Settings** tab

### 2. Access Secrets Section
- In left sidebar: **Secrets and variables** → **Actions**

### 3. Add Each Secret
Click **"New repository secret"** and add:

## For Azure:
| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AZURE_REGISTRY` | Container registry URL | `myregistry.azurecr.io` |
| `AZURE_CLIENT_ID` | Service principal app ID | `12345678-1234-1234-1234-123456789012` |
| `AZURE_CLIENT_SECRET` | Service principal password | `your-generated-password` |
| `AZURE_CREDENTIALS` | Full JSON from `az ad sp create-for-rbac` | `{"clientId":"...","clientSecret":"...","subscriptionId":"...","tenantId":"..."}` |

## For AWS:
| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ACCESS_KEY_ID` | IAM user access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ACCOUNT_ID` | 12-digit account ID | `123456789012` |

## 4. Test the Setup
After adding secrets, trigger the workflow:
- Go to **Actions** tab
- Click **"Multi-Cloud ML Pipeline CI/CD"**
- Click **"Run workflow"**
- Select environment and cloud provider
- Click **"Run workflow"**

## 5. Verification
The workflow will now:
- ✅ Build and push Docker images to your registries
- ✅ Deploy infrastructure using Terraform
- ✅ Show success messages instead of credential warnings
