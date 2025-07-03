# AWS Credentials Setup Guide

## 1. Create IAM User for GitHub Actions

### Via AWS Console:
1. Go to AWS IAM Console → Users → Create User
2. User name: `github-actions-user`
3. Select "Attach policies directly"
4. Add these policies:
   - `AmazonEC2ContainerRegistryFullAccess`
   - `AmazonEKSClusterPolicy` (if using EKS)
   - `IAMFullAccess` (for Terraform)
   - `AmazonS3FullAccess` (for Terraform state)

### Via AWS CLI:
```bash
# Create IAM user
aws iam create-user --user-name github-actions-user

# Attach policies
aws iam attach-user-policy --user-name github-actions-user --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess

# Create access keys
aws iam create-access-key --user-name github-actions-user
```

## 2. The command will output:
```json
{
    "AccessKey": {
        "UserName": "github-actions-user",
        "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
        "Status": "Active",
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    }
}
```

## 3. GitHub Secrets Configuration:

**AWS_ACCESS_KEY_ID**: Use the `AccessKeyId` value
**AWS_SECRET_ACCESS_KEY**: Use the `SecretAccessKey` value
**AWS_REGION**: Your preferred region (e.g., `us-east-1`)
**AWS_ACCOUNT_ID**: Your 12-digit AWS account ID

## 4. Get your AWS Account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

## 5. Create ECR Repository (if needed):
```bash
# Create ECR repository for ml-api
aws ecr create-repository --repository-name aimlpipeline/ml-api

# Create ECR repository for ml-training  
aws ecr create-repository --repository-name aimlpipeline/ml-training
```
