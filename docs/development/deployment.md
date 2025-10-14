# Deployment

This page covers deploying infrastructure using Terraform and the Docker-based deployment workflow.

## Deployment Overview

The project uses Terraform for infrastructure as code, with a Docker-based wrapper for consistent deployments across environments.

## Terraform Docker Wrapper

### The `terraform` Script

The project includes a `terraform` wrapper script that runs Terraform in a Docker container:

```bash
#!/usr/bin/env bash

docker run --rm -it \
  -v "$(pwd)/deployment:/workspace" \
  -v "$HOME/.aws:/root/.aws:ro" \
  -w /workspace \
  $(docker build -q -f terraform.Dockerfile .) \
  "$@"
```

This ensures:

- Consistent Terraform version (1.12.x)
- No local Terraform installation needed
- Same deployment environment for all users

### The `terraform.Dockerfile`

The Dockerfile builds a container with Terraform and required tools:

```dockerfile
# Build stage
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y gnupg wget lsb-release && \
    wget -O- https://apt.releases.hashicorp.com/gpg | \
    gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/hashicorp.list > /dev/null && \
    wget -O- https://download.docker.com/linux/debian/gpg | \
    gpg --dearmor -o /usr/share/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y terraform=1.12.* docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Final stage
FROM python:3.12-slim

COPY --from=builder /usr/bin/terraform /usr/bin/terraform
COPY --from=builder /usr/share/keyrings/hashicorp-archive-keyring.gpg /usr/share/keyrings/
COPY --from=builder /usr/bin/docker /usr/bin/docker
COPY --from=builder /usr/share/keyrings/docker.gpg /usr/share/keyrings/

RUN apt-get update && apt-get install -y build-essential git && \
    pip install --no-cache-dir awscli

ENTRYPOINT ["/usr/bin/terraform"]
```

Key components:

- **Terraform 1.12.x**: Infrastructure provisioning
- **Docker CLI**: For building Lambda deployment packages
- **AWS CLI**: For AWS operations
- **Python 3.12**: For running build scripts

## Deployment Workflow

### 1. Initial Setup

Configure Terraform variables:

```bash
# Copy example configuration
cp deployment/terraform.tfvars.example deployment/terraform.tfvars

# Edit with your values
vim deployment/terraform.tfvars
```

Required variables:

```hcl
aws_region             = "us-east-1"
bucket_name            = "my-unique-bucket"
opensearch_domain_name = "my-domain"

tags = {
  Environment = "dev"
  Project     = "opensearch-ingest"
  Owner       = "your-team"
}
```

### 2. Initialize Terraform

```bash
# Initialize Terraform (download providers, modules)
./terraform init
```

This creates:

- `.terraform/` directory with providers
- `.terraform.lock.hcl` lock file

### 3. Plan Changes

```bash
# Preview what will be created/changed
./terraform plan

# Save plan to file
./terraform plan -out=tfplan
```

Review the plan carefully before applying.

### 4. Apply Changes

```bash
# Apply changes (will prompt for confirmation)
./terraform apply

# Apply without confirmation (CI/CD)
./terraform apply -auto-approve

# Apply saved plan
./terraform apply tfplan
```

### 5. View Outputs

```bash
# Show all outputs
./terraform output

# Get specific output
./terraform output opensearch_domain_endpoint

# Get output in JSON
./terraform output -json
```

## Deployment Structure

### Root Configuration

#### `deployment/main.tf`

Main Terraform configuration:

```hcl
terraform {
  required_version = ">= 1.12"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "opensearch" {
  source = "./modules/opensearch"
  
  domain_name    = var.opensearch_domain_name
  instance_type  = var.instance_type
  instance_count = var.instance_count
  # ...
}

module "lambda_ingest" {
  source = "./modules/lambda-ingest"
  
  function_name         = "${var.opensearch_domain_name}-ingest"
  opensearch_endpoint   = module.opensearch.endpoint
  opensearch_master_role = module.opensearch.master_role_arn
  # ...
}
```

#### `deployment/variables.tf`

Input variable definitions:

```hcl
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "opensearch_domain_name" {
  description = "Name of the OpenSearch domain"
  type        = string
}

# ... more variables
```

#### `deployment/outputs.tf`

Output values:

```hcl
output "opensearch_domain_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = module.opensearch.endpoint
}

output "opensearch_master_role_arn" {
  description = "ARN of the OpenSearch master role"
  value       = module.opensearch.master_role_arn
}

# ... more outputs
```

### Terraform Modules

#### OpenSearch Module

`deployment/modules/opensearch/`:

Creates:

- OpenSearch domain
- Master IAM role for CLI access
- ML connector IAM role for Bedrock
- Domain access policies

#### Lambda Ingest Module

`deployment/modules/lambda-ingest/`:

Creates:

- Lambda function for S3 ingestion
- IAM execution role
- Deployment package from source code
- CloudWatch log group

## Lambda Deployment

### Building Lambda Package

The Lambda module builds a deployment package:

```hcl
# In deployment/modules/lambda-ingest/main.tf
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.root}/../apps/lambda/ingest"
  output_path = "${path.module}/builds/lambda.zip"
  
  excludes = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache"
  ]
}

resource "aws_lambda_function" "ingest" {
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  # ...
}
```

### Updating Lambda Code

After modifying Lambda code:

```bash
# Rebuild and deploy
./terraform apply -target=module.lambda_ingest

# Or full apply
./terraform apply
```

### Lambda Layers (Optional)

For large dependencies, use Lambda layers:

```hcl
resource "aws_lambda_layer_version" "dependencies" {
  filename            = "lambda-dependencies.zip"
  layer_name          = "opensearch-dependencies"
  compatible_runtimes = ["python3.12"]
}

resource "aws_lambda_function" "ingest" {
  layers = [aws_lambda_layer_version.dependencies.arn]
  # ...
}
```

## State Management

### Local State (Development)

By default, Terraform stores state locally:

```
deployment/
├── terraform.tfstate
└── terraform.tfstate.backup
```

!!! danger "Never Commit State"
    State files contain sensitive information. They are in `.gitignore`.

### Remote State (Production)

For production, use remote state with S3:

```hcl
# In deployment/main.tf
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "opensearch/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

Initialize remote state:

```bash
./terraform init -backend-config="bucket=my-terraform-state"
```

## Multi-Environment Deployments

### Using Workspaces

```bash
# Create workspace for each environment
./terraform workspace new dev
./terraform workspace new staging
./terraform workspace new prod

# Switch workspace
./terraform workspace select dev

# List workspaces
./terraform workspace list
```

Use workspace in configuration:

```hcl
locals {
  env = terraform.workspace
  
  instance_count = {
    dev     = 1
    staging = 2
    prod    = 3
  }
}

resource "aws_opensearch_domain" "main" {
  cluster_config {
    instance_count = local.instance_count[local.env]
  }
}
```

### Using Separate Variable Files

```bash
# deployment/terraform.tfvars.dev
opensearch_domain_name = "opensearch-dev"
instance_count = 1

# deployment/terraform.tfvars.prod
opensearch_domain_name = "opensearch-prod"
instance_count = 3

# Deploy to environment
./terraform apply -var-file=terraform.tfvars.dev
./terraform apply -var-file=terraform.tfvars.prod
```

## Resource Targeting

### Deploy Specific Resources

```bash
# Deploy only OpenSearch
./terraform apply -target=module.opensearch

# Deploy only Lambda
./terraform apply -target=module.lambda_ingest

# Deploy multiple targets
./terraform apply -target=module.opensearch -target=module.lambda_ingest
```

### Refresh State

```bash
# Update state without making changes
./terraform refresh

# Plan with refresh
./terraform plan -refresh=true
```

## Troubleshooting

### Domain Creation Failed

```
Error: Error creating OpenSearch Domain: LimitExceededException
```

Solutions:

- Check service limits in AWS console
- Request limit increase
- Use smaller instance types

### IAM Permission Denied

```
Error: error creating OpenSearch Domain: AccessDeniedException
```

Solutions:

- Verify AWS credentials have necessary permissions
- Check IAM user/role has `es:CreateDomain` permission
- Review AWS Organizations SCPs

### State Lock Error

```
Error: Error acquiring the state lock
```

Solutions:

```bash
# Force unlock (use carefully)
./terraform force-unlock LOCK_ID

# Or wait for lock to expire
```

### Lambda Upload Too Large

```
Error: RequestEntityTooLargeException: Request must be smaller than 69905067 bytes
```

Solutions:

- Use Lambda layers for dependencies
- Remove unnecessary files from package
- Upload to S3 first, reference in Terraform

## Best Practices

### 1. Version Control

Commit to git:

- Terraform configuration (`.tf` files)
- Variable definitions
- Module code
- `.terraform.lock.hcl`

Don't commit:

- `terraform.tfvars` (contains secrets)
- `terraform.tfstate` (contains sensitive data)
- `.terraform/` directory

### 2. Code Review

Review Terraform plans:

```bash
# Generate plan
./terraform plan -out=tfplan

# Convert to JSON for review
./terraform show -json tfplan > plan.json

# Review in pull request
```

### 3. Incremental Changes

Make small, focused changes:

```bash
# Add one resource at a time
./terraform apply -target=aws_s3_bucket.new_bucket

# Verify before proceeding
```

### 4. Backup State

Before major changes:

```bash
# Backup current state
cp deployment/terraform.tfstate deployment/terraform.tfstate.backup.$(date +%Y%m%d)

# Make changes
./terraform apply
```

### 5. Use Modules

Organize code into reusable modules:

```
deployment/modules/
├── opensearch/
├── lambda-ingest/
└── s3-bucket/
```

### 6. Validate Configuration

```bash
# Validate syntax
./terraform validate

# Format code
./terraform fmt -recursive
```

## Cleanup

### Destroy Resources

```bash
# Preview what will be destroyed
./terraform plan -destroy

# Destroy all resources
./terraform destroy

# Destroy specific resource
./terraform destroy -target=module.lambda_ingest
```

### Prevent Accidental Destruction

```hcl
resource "aws_opensearch_domain" "main" {
  lifecycle {
    prevent_destroy = true
  }
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Terraform

on:
  push:
    branches: [main]
    paths: ['deployment/**']

jobs:
  terraform:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Terraform Init
        run: ./terraform init
      
      - name: Terraform Plan
        run: ./terraform plan
      
      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: ./terraform apply -auto-approve
```

## Next Steps

- [Getting Started](../getting-started.md) - Deploy your first instance
- [Deploy on AWS](../deploy-aws.md) - Detailed AWS deployment guide
- [Environment Configuration](environment.md) - Configure Terraform variables

