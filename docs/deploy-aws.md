# Deploy on AWS

This guide covers deploying the complete infrastructure stack to AWS using Terraform.

## Infrastructure Overview

The Terraform deployment creates:

- **OpenSearch Domain**: Single-node cluster with vector search capabilities
- **Lambda Function**: Automated S3-to-OpenSearch data ingestion
- **S3 Bucket**: Storage for data files to be processed
- **IAM Roles**: Proper permissions for cross-service communication
- **Security Configuration**: IAM-based access control

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform 1.12+ (or use the provided Docker wrapper)
- AWS account with permissions to create:
    - OpenSearch domains
    - Lambda functions
    - S3 buckets
    - IAM roles and policies

## Deployment Structure

```
deployment/
├── main.tf                    # Main Terraform configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars.example   # Example configuration
└── modules/
    ├── lambda-ingest/         # Lambda function module
    └── opensearch/            # OpenSearch domain module
```

## Step 1: Configure Terraform Variables

Copy the example configuration:

```bash
cp deployment/terraform.tfvars.example deployment/terraform.tfvars
```

Edit `terraform.tfvars` with your specific values:

```hcl
aws_region = "us-east-1"
bucket_name = "my-unique-opensearch-bucket"  # Must be globally unique
opensearch_domain_name = "my-opensearch-domain"

tags = {
  Environment = "dev"
  Project     = "opensearch-ingest"
  Owner       = "your-team"
}
```

!!! warning "S3 Bucket Names"
    S3 bucket names must be globally unique across all AWS accounts. Choose a unique name for your bucket.

## Step 2: Deploy Infrastructure

Use the provided Terraform wrapper script:

```bash
# Initialize Terraform
./terraform init

# Preview changes
./terraform plan

# Deploy infrastructure
./terraform apply
```

The wrapper script uses a Docker container with Terraform pre-installed, ensuring consistent deployments across environments.

!!! tip "Direct Terraform"
    You can also use Terraform directly if you have it installed:
    ```bash
    cd deployment
    terraform init
    terraform plan
    terraform apply
    ```

## Step 3: Capture Outputs

After deployment, Terraform provides important values you'll need:

```bash
# View all outputs
./terraform output

# Get specific values
./terraform output opensearch_domain_endpoint
./terraform output opensearch_master_role_arn
./terraform output s3_bucket_id
```

Save these values for CLI and Lambda configuration:

| Output | Usage |
|--------|-------|
| `opensearch_domain_endpoint` | Use for CLI `--opensearch-host` parameter (extract hostname) |
| `opensearch_master_role_arn` | Use for CLI `--assume-role` parameter |
| `s3_bucket_id` | Upload files here for Lambda processing |
| `lambda_function_name` | For S3 event triggers |

## OpenSearch Domain Configuration

The deployed OpenSearch domain includes:

### Version and Compute

- **Version**: OpenSearch 2.19
- **Instance Type**: m8g.large.search (2 vCPU, 8 GB RAM)
- **Instance Count**: 1 (single-node for development)

### Storage

- **Volume Type**: GP3 (General Purpose SSD)
- **Volume Size**: 40 GB
- **IOPS**: 3000
- **Throughput**: 125 MB/s

### Security

- **Network**: Public endpoint with IAM authentication
- **Encryption**: At-rest and in-transit encryption enabled
- **Access Control**: IAM-based (no username/password)
- **Fine-grained Access**: Disabled (IAM only)

### Plugins

The domain includes the ML Commons plugin for Bedrock integration, enabling vector search with automatic embedding generation.

## IAM Permissions

### Master Role

The deployment creates a master IAM role with permissions for:

- Full OpenSearch domain access (`es:*`)
- Amazon Bedrock model access (`bedrock:InvokeModel`)
- S3 bucket read access (for Lambda ingestion)

This role can be assumed by:

- Your AWS user/role (for CLI operations)
- The Lambda execution role (for automated ingestion)
- OpenSearch service (for Bedrock calls)

### ML Connector Role

A separate role is created specifically for ML operations:

- Bedrock model invocation (`bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`)
- Used by OpenSearch ML connectors to generate embeddings

## Lambda Function

The deployed Lambda function automates S3-to-OpenSearch ingestion:

### Configuration

- **Runtime**: Python 3.12
- **Memory**: 512 MB
- **Timeout**: 900 seconds (15 minutes)
- **Architecture**: x86_64

### Trigger

The Lambda can be triggered by:

- S3 event notifications (automatic)
- Direct invocation with event payload
- AWS Step Functions
- API Gateway

### Event Structure

```json
{
  "batch_size": 50,
  "delete": false,
  "index_name": "your-index",
  "limit_rows": 1000,
  "opensearch_endpoint": "https://your-domain.region.es.amazonaws.com",
  "region": "us-east-1",
  "s3_uri": "s3://bucket-name/path/to/file.csv",
  "wait_time": 5.0
}
```

See [Lambda Handler](lambda-handler.md) for complete documentation.

## Step 4: Set Up OpenSearch

After infrastructure is deployed, configure OpenSearch:

```bash
# Update your .env file with the outputs
export OPENSEARCH_HOST=$(./terraform output -raw opensearch_domain_endpoint | sed 's|https\?://||' | sed 's|:.*||')
export OPENSEARCH_PORT=443
export ASSUME_ROLE=$(./terraform output -raw opensearch_master_role_arn)

# Run setup
uv run python -m apps.cli.main setup \
    --assume-role $ASSUME_ROLE \
    --columns LONG_COMMON_NAME COMPONENT \
    --index loinc_data \
    --opensearch-host $OPENSEARCH_HOST \
    --opensearch-port $OPENSEARCH_PORT \
    --profile default \
    --region us-east-1
```

## Step 5: Ingest Data

Upload data directly via CLI:

```bash
uv run python -m apps.cli.main ingest \
    --assume-role $ASSUME_ROLE \
    --file /path/to/data.csv \
    --index loinc_data \
    --knn-columns LONG_COMMON_NAME COMPONENT \
    --opensearch-host $OPENSEARCH_HOST \
    --opensearch-port $OPENSEARCH_PORT \
    --profile default \
    --region us-east-1
```

Or upload to S3 to trigger Lambda:

```bash
# Upload file to S3
aws s3 cp /path/to/data.csv s3://your-bucket/data.csv

# Invoke Lambda manually
aws lambda invoke \
    --function-name $(./terraform output -raw lambda_function_name) \
    --payload '{
        "s3_uri": "s3://your-bucket/data.csv",
        "index_name": "loinc_data",
        "opensearch_endpoint": "your-endpoint.es.amazonaws.com"
    }' \
    response.json
```

## Production Considerations

For production deployments, consider these enhancements:

### High Availability

```hcl
# In terraform.tfvars
opensearch_instance_count = 3
zone_awareness_enabled = true
zone_awareness_availability_zone_count = 3
```

### Dedicated Masters

```hcl
dedicated_master_enabled = true
dedicated_master_type = "m8g.large.search"
dedicated_master_count = 3
```

### Larger Instances

```hcl
instance_type = "m8g.xlarge.search"  # 4 vCPU, 16 GB RAM
instance_count = 3
```

### VPC Deployment

```hcl
vpc_enabled = true
vpc_id = "vpc-xxxxx"
subnet_ids = ["subnet-xxxxx", "subnet-yyyyy"]
security_group_ids = ["sg-xxxxx"]
```

### Enhanced Storage

```hcl
ebs_volume_size = 100
ebs_volume_type = "gp3"
ebs_iops = 6000
ebs_throughput = 250
```

### Monitoring

Enable CloudWatch logs and metrics:

```hcl
log_publishing_options = {
  index_slow_logs = {
    enabled = true
    log_group_name = "/aws/opensearch/index-slow-logs"
  }
  search_slow_logs = {
    enabled = true
    log_group_name = "/aws/opensearch/search-slow-logs"
  }
}
```

### Automated Snapshots

```hcl
automated_snapshot_start_hour = 3  # 3 AM UTC
```

## Teardown

To remove all infrastructure:

```bash
./terraform destroy
```

!!! danger "Data Loss"
    This will permanently delete your OpenSearch domain and all data. Make sure you have backups of any important data.

## Cost Estimation

Approximate monthly costs (us-east-1):

| Resource | Configuration | Estimated Cost |
|----------|--------------|----------------|
| OpenSearch | 1x m8g.large.search, 40GB | ~$120/month |
| Lambda | 512MB, 1M invocations | ~$5/month |
| S3 | 10GB storage, 1M requests | ~$1/month |
| **Total** | | **~$126/month** |

Costs will vary based on:

- Instance types and counts
- Storage size and IOPS
- Data transfer
- Bedrock API usage
- Lambda execution time

## Troubleshooting

### IAM Access Denied

If you get access denied errors:

1. Verify the master role trust policy allows your user/role
2. Check the OpenSearch domain access policy
3. Ensure you're using `--assume-role` with the correct ARN

### OpenSearch Domain Creation Failed

Common causes:

1. Invalid instance type for the region
2. Service limits exceeded
3. IAM permission issues
4. Invalid VPC configuration

Check CloudFormation events for details:

```bash
aws cloudformation describe-stack-events \
    --stack-name opensearch-stack
```

### Lambda Function Timeout

If Lambda times out during ingestion:

1. Increase Lambda timeout (up to 15 minutes)
2. Reduce batch size in event payload
3. Increase Lambda memory (improves CPU)
4. Process file in chunks with multiple invocations

## Next Steps

- [Configure CLI](cli-reference.md) with AWS endpoints
- [Set up Lambda triggers](lambda-handler.md) for S3 events
- [Test search](getting-started.md#step-6-search-the-data) with the deployed infrastructure

