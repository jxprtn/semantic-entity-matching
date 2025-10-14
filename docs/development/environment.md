# Environment Configuration

This page covers environment variables, configuration files, and secrets management.

## Environment Files

The project uses environment files for configuration across different environments.

### Main Environment File: `.env`

Create from the example:

```bash
cp .env.example .env
```

Edit with your values:

```bash
# AWS Configuration
AWS_PROFILE=default
AWS_REGION=us-east-1
ASSUME_ROLE=arn:aws:iam::ACCOUNT:role/opensearch-master-role

# OpenSearch Configuration
ENDPOINT=localhost:9200  # or AWS endpoint
INDEX=loinc_data
PIPELINE_NAME=embedding-pipeline

# Bedrock Configuration
BEDROCK_MODEL_ID=amazon.titan-embed-text-v2:0
ML_CONNECTOR_ROLE=arn:aws:iam::ACCOUNT:role/ml-connector-role

# Data Configuration
FILE=/path/to/data.csv
VECTORIZE_COLUMNS=LONG_COMMON_NAME COMPONENT
SEARCH_COLUMN=LONG_COMMON_NAME
SEARCH_QUERY=glucose

# Vector Search Configuration (HNSW)
VECTOR_DIMENSION=1024
ENGINE=faiss
SPACE_TYPE=l2
M=48
EF_CONSTRUCTION=512
EF_SEARCH=512

# Processing Configuration
BATCH_SIZE=50
LIMIT_ROWS=1000
SKIP_ROWS=0
WAIT_TIME=0.1
MAX_ATTEMPTS=5
```

### Test Environment Files

The tests directory contains environment files for different backends:

#### `tests/localhost.env`

For local OpenSearch testing:

```bash
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
AWS_PROFILE=default
AWS_REGION=us-east-1
ML_CONNECTOR_ROLE=arn:aws:iam::ACCOUNT:role/ml-connector-role
```

#### `tests/aws.env`

For AWS OpenSearch testing:

```bash
AWS_OPENSEARCH_HOST=search-domain.us-east-1.es.amazonaws.com
AWS_OPENSEARCH_PORT=443
AWS_PROFILE=default
AWS_ASSUME_ROLE=arn:aws:iam::ACCOUNT:role/opensearch-master-role
AWS_ML_CONNECTOR_ROLE=arn:aws:iam::ACCOUNT:role/ml-connector-role
```

!!! warning "Never Commit"
    These files contain sensitive information. They are in `.gitignore` and should **never** be committed to version control.

## Loading Environment Variables

### In Shell

```bash
# Source the .env file
source .env

# Verify variables are loaded
echo $OPENSEARCH_ENDPOINT
echo $AWS_PROFILE
```

### In Python

```python
import os
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

# Access variables
endpoint = os.getenv('ENDPOINT')
region = os.getenv('AWS_REGION', 'us-east-1')  # with default
```

### In Tests

pytest-dotenv automatically loads environment files:

```python
# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def opensearch_host():
    return os.getenv("OPENSEARCH_HOST", "localhost")
```

## Configuration Hierarchy

The project uses this configuration precedence (highest to lowest):

1. **Command-line arguments** - `--opensearch-host localhost --opensearch-port 9200`
2. **Environment variables** - `export ENDPOINT=localhost:9200`
3. **Environment files** - `.env`, `tests/*.env`
4. **Default values** - Built into the code

Example:

```python
def main(
    *,
    endpoint: str = None,
    region: str = "us-east-1"  # Default value
):
    # 1. Check CLI argument
    if not endpoint:
        # 2. Check environment variable
        endpoint = os.getenv('ENDPOINT')
    
    if not endpoint:
        raise ValueError("Endpoint is required")
```

## AWS Credentials

### AWS Profile Configuration

Configure AWS profiles in `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY

[dev]
aws_access_key_id = DEV_ACCESS_KEY
aws_secret_access_key = DEV_SECRET_KEY

[prod]
aws_access_key_id = PROD_ACCESS_KEY
aws_secret_access_key = PROD_SECRET_KEY
```

And in `~/.aws/config`:

```ini
[default]
region = us-east-1
output = json

[profile dev]
region = us-east-1
output = json

[profile prod]
region = us-west-2
output = json
```

### Using Profiles

```bash
# Set profile for current session
export AWS_PROFILE=dev

# Or pass to commands
uv run python -m apps.cli.main setup --profile dev ...

# Verify active profile
aws sts get-caller-identity
```

### IAM Role Assumption

For cross-account or enhanced permissions:

```bash
# In .env
ASSUME_ROLE=arn:aws:iam::123456789012:role/opensearch-master-role

# The CLI automatically assumes this role
uv run python -m apps.cli.main setup --assume-role $ASSUME_ROLE ...
```

The `lib.utils.get_aws_credentials()` function handles this:

```python
from lib.utils import get_aws_credentials

credentials = get_aws_credentials(
    assume_role="arn:aws:iam::ACCOUNT:role/MyRole",
    profile="my-profile",
    region="us-east-1"
)
```

## Streamlit Secrets

For the web UI, create `.streamlit/secrets.toml`:

```toml
# OpenSearch Configuration
opensearch_endpoint = "search-domain.us-east-1.es.amazonaws.com"
opensearch_iam_role = "arn:aws:iam::ACCOUNT:role/opensearch-master-role"

# AWS Configuration
aws_profile = "default"
aws_region = "us-east-1"

# Search Configuration
opensearch_indices = {loinc_data = "embedding-pipeline"}
opensearch_fields = ["LONG_COMMON_NAME", "COMPONENT"]
```

Access in Streamlit:

```python
import streamlit as st

endpoint = st.secrets["opensearch_endpoint"]
indices = st.secrets["opensearch_indices"]
```

## Terraform Variables

### `terraform.tfvars`

Create from example:

```bash
cp deployment/terraform.tfvars.example deployment/terraform.tfvars
```

Edit with your values:

```hcl
aws_region             = "us-east-1"
bucket_name            = "my-unique-bucket-name"
opensearch_domain_name = "my-opensearch-domain"

# Optional
instance_type          = "m8g.large.search"
instance_count         = 1
ebs_volume_size        = 40

tags = {
  Environment = "dev"
  Project     = "opensearch-ingest"
  Owner       = "your-team"
}
```

!!! warning "Never Commit"
    The `terraform.tfvars` file contains environment-specific values and should not be committed. Use `terraform.tfvars.example` as a template.

## Lambda Environment Variables

Lambda functions receive environment variables through Terraform:

```hcl
# In deployment/modules/lambda-ingest/main.tf
resource "aws_lambda_function" "ingest" {
  environment {
    variables = {
      OPENSEARCH_ENDPOINT = var.opensearch_endpoint
      OPENSEARCH_ROLE_ARN = var.opensearch_master_role_arn
    }
  }
}
```

Access in Lambda:

```python
import os

endpoint = os.environ['OPENSEARCH_ENDPOINT']
role_arn = os.environ['OPENSEARCH_ROLE_ARN']
```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.development
ENDPOINT=localhost:9200
LOG_LEVEL=DEBUG
BATCH_SIZE=10
LIMIT_ROWS=100
```

### Production Environment

```bash
# .env.production
ENDPOINT=search-prod.us-east-1.es.amazonaws.com
LOG_LEVEL=WARNING
BATCH_SIZE=100
LIMIT_ROWS=
```

### Loading Specific Environment

```bash
# Load specific environment
source .env.development

# Or use environment-specific file
export ENV=development
source .env.$ENV
```

## Secrets Management

### Local Development

For local development, use `.env` files (not committed).

### AWS Secrets Manager (Production)

For production, consider AWS Secrets Manager:

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
secrets = get_secret('prod/opensearch/credentials')
endpoint = secrets['endpoint']
```

### Environment Variable Injection

For CI/CD pipelines:

```yaml
# GitHub Actions example
env:
  OPENSEARCH_ENDPOINT: ${{ secrets.OPENSEARCH_ENDPOINT }}
  AWS_PROFILE: ${{ secrets.AWS_PROFILE }}
```

## Configuration Validation

### Validating Required Variables

```python
def validate_config():
    """Validate required environment variables are set."""
    required = [
        'ENDPOINT',
        'INDEX',
        'ML_CONNECTOR_ROLE'
    ]
    
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
```

### Environment Check Script

Create `scripts/check-env.sh`:

```bash
#!/bin/bash

required_vars=(
    "ENDPOINT"
    "INDEX"
    "ML_CONNECTOR_ROLE"
    "AWS_PROFILE"
)

missing=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing+=("$var")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo "Missing required environment variables:"
    printf '  - %s\n' "${missing[@]}"
    exit 1
else
    echo "All required environment variables are set"
fi
```

## Best Practices

### 1. Never Commit Secrets

Add to `.gitignore`:

```gitignore
.env
.env.*
!.env.example
terraform.tfvars
tests/*.env
.streamlit/secrets.toml
```

### 2. Use Example Files

Provide templates:

- `.env.example`
- `terraform.tfvars.example`
- `.streamlit/secrets.toml.example`

### 3. Document Variables

Comment each variable:

```bash
# AWS region for all resources
AWS_REGION=us-east-1

# OpenSearch endpoint (without https://)
ENDPOINT=localhost:9200
```

### 4. Use Defaults

Provide sensible defaults:

```python
batch_size = int(os.getenv('BATCH_SIZE', '50'))
region = os.getenv('AWS_REGION', 'us-east-1')
```

### 5. Validate Early

Check configuration at startup:

```python
def main():
    validate_config()  # Check required vars first
    # ... rest of application
```

## Troubleshooting

### Variables Not Loading

```bash
# Verify file exists
ls -la .env

# Check for syntax errors
cat .env | grep -v '^#' | grep -v '^$'

# Source explicitly
source .env
echo $ENDPOINT
```

### AWS Credentials Not Working

```bash
# Verify AWS configuration
aws configure list

# Test credentials
aws sts get-caller-identity

# Check profile
echo $AWS_PROFILE
```

### Permission Errors

```bash
# Check IAM permissions
aws iam get-user

# Verify role assumption works
aws sts assume-role \
    --role-arn arn:aws:iam::ACCOUNT:role/MyRole \
    --role-session-name test
```

## Next Steps

- [Testing](testing.md) - Configure test environments
- [Deployment](deployment.md) - Production configuration
- [Tooling](tooling.md) - Development tools

