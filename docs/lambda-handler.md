# Lambda Handler

The project includes an AWS Lambda function for automated S3-to-OpenSearch data ingestion.

## Overview

The Lambda handler enables automated data processing workflows:

1. Upload CSV/Excel files to S3
2. S3 triggers Lambda function
3. Lambda reads file and ingests to OpenSearch
4. OpenSearch generates embeddings via Bedrock
5. Data becomes searchable immediately

## Event Structure

The Lambda function accepts events with the following structure:

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

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `s3_uri` | string | S3 URI of the file to ingest (e.g., `s3://bucket/file.csv`) |
| `index_name` | string | Name of the OpenSearch index to ingest into |
| `opensearch_endpoint` | string | OpenSearch domain endpoint (without https://) |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `batch_size` | integer | 50 | Number of documents to process in each batch |
| `delete` | boolean | false | Delete existing index before ingestion |
| `limit_rows` | integer | null | Limit the number of rows to process |
| `region` | string | us-east-1 | AWS region |
| `wait_time` | float | 5.0 | Wait time in seconds between batches |

## Invocation Methods

### Manual Invocation

Invoke the Lambda function directly with the AWS CLI:

```bash
aws lambda invoke \
    --function-name opensearch-ingest-function \
    --payload '{
        "s3_uri": "s3://my-bucket/data.csv",
        "index_name": "loinc_data",
        "opensearch_endpoint": "search-domain.us-east-1.es.amazonaws.com",
        "batch_size": 50,
        "wait_time": 1.0
    }' \
    response.json

# View response
cat response.json
```

### S3 Event Trigger

Configure S3 to automatically trigger Lambda on file uploads:

#### Using AWS Console

1. Go to S3 bucket properties
2. Navigate to "Event notifications"
3. Create notification:
   - Event type: "All object create events"
   - Destination: Lambda function
   - Select your ingestion function

#### Using Terraform

```hcl
resource "aws_s3_bucket_notification" "lambda_trigger" {
  bucket = aws_s3_bucket.data_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "data/"
    filter_suffix       = ".csv"
  }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_bucket.arn
}
```

With S3 trigger configured, simply upload files:

```bash
aws s3 cp data.csv s3://my-bucket/data/data.csv
```

The Lambda function will automatically process the file.

### Step Functions Integration

Use AWS Step Functions for complex workflows:

```json
{
  "Comment": "Multi-file ingestion workflow",
  "StartAt": "IngestFile",
  "States": {
    "IngestFile": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:ingest-function",
      "Parameters": {
        "s3_uri.$": "$.s3_uri",
        "index_name": "loinc_data",
        "opensearch_endpoint": "search-domain.region.es.amazonaws.com",
        "batch_size": 100
      },
      "End": true
    }
  }
}
```

## Lambda Configuration

### Function Settings

The deployed Lambda function uses:

- **Runtime**: Python 3.12
- **Memory**: 512 MB (adjustable based on file size)
- **Timeout**: 900 seconds (15 minutes)
- **Architecture**: x86_64

### Environment Variables

The Lambda function uses these environment variables (set by Terraform):

| Variable | Description |
|----------|-------------|
| `AWS_EXECUTION_ENV` | Indicates Lambda environment (set automatically) |

The function detects Lambda environment and skips connection tests for faster execution.

### IAM Permissions

The Lambda execution role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "es:ESHttp*"
      ],
      "Resource": "arn:aws:es:region:account:domain/your-domain/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole"
      ],
      "Resource": "arn:aws:iam::account:role/opensearch-master-role"
    }
  ]
}
```

## Monitoring

### CloudWatch Logs

Lambda automatically logs to CloudWatch Logs:

```bash
# View recent logs
aws logs tail /aws/lambda/opensearch-ingest-function --follow

# Filter for errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/opensearch-ingest-function \
    --filter-pattern "ERROR"
```

### CloudWatch Metrics

Monitor Lambda performance:

- **Invocations**: Total number of invocations
- **Duration**: Execution time per invocation
- **Errors**: Number of failed invocations
- **Throttles**: Number of throttled invocations

### Custom Metrics

The Lambda function logs progress:

```
Processing file: s3://bucket/data.csv
Will read 1000 rows total
Processing batch 1/20 (rows 1-50)
  Successfully indexed batch 1
Processing batch 2/20 (rows 51-100)
  Successfully indexed batch 2
...
Data import completed successfully. Processed 1000 rows.
```

## Error Handling

### Common Errors

**S3 Access Denied**

```
Error: An error occurred (403) when calling the GetObject operation: Forbidden
```

Solution: Verify Lambda execution role has `s3:GetObject` permission.

**OpenSearch Access Denied**

```
Error: AuthorizationException: User is not authorized to perform: es:ESHttpPost
```

Solution: Ensure Lambda can assume the OpenSearch master role.

**File Format Error**

```
Error: Unsupported file format: .txt
```

Solution: Only CSV and Excel (.xlsx, .xls) files are supported.

**Timeout**

```
Error: Task timed out after 900.00 seconds
```

Solutions:

- Increase Lambda timeout (up to 15 minutes)
- Reduce batch size
- Use `limit_rows` to process file in chunks
- Increase Lambda memory (improves CPU)

### Retry Logic

The Lambda function includes built-in retry logic:

- Retries failed batches up to 5 times
- Exponential backoff between retries
- Continues processing remaining batches on failure

### Error Responses

On error, Lambda returns:

```json
{
  "statusCode": 500,
  "error": "Error message",
  "traceback": "Full stack trace"
}
```

On success:

```json
{
  "statusCode": 200,
  "message": "Successfully processed 1000 rows",
  "rows_processed": 1000,
  "batches_processed": 20
}
```

## Advanced Usage

### Processing Large Files

For files larger than 100K rows:

1. **Split into chunks**:
   ```bash
   split -l 10000 large_file.csv chunk_
   ```

2. **Upload chunks**:
   ```bash
   for file in chunk_*; do
       aws s3 cp $file s3://bucket/data/$file
   done
   ```

3. **Lambda processes each automatically**

### Parallel Processing

Process multiple files simultaneously:

```python
import boto3
import json

lambda_client = boto3.client('lambda')

files = [
    's3://bucket/file1.csv',
    's3://bucket/file2.csv',
    's3://bucket/file3.csv'
]

for s3_uri in files:
    payload = {
        's3_uri': s3_uri,
        'index_name': 'loinc_data',
        'opensearch_endpoint': 'search-domain.region.es.amazonaws.com'
    }
    
    lambda_client.invoke(
        FunctionName='opensearch-ingest-function',
        InvocationType='Event',  # Async invocation
        Payload=json.dumps(payload)
    )
```

### Custom Transformations

To add data transformations, modify `apps/lambda/ingest/main.py`:

```python
def transform_data(df):
    """Apply custom transformations to DataFrame."""
    # Add computed columns
    df['full_name'] = df['first_name'] + ' ' + df['last_name']
    
    # Clean data
    df['email'] = df['email'].str.lower()
    
    # Filter rows
    df = df[df['status'] == 'active']
    
    return df

# In handler function
df = read_data_file(local_file_path)
df = transform_data(df)  # Apply transformations
await ingest(df, ...)
```

## Cost Optimization

### Lambda Costs

- **Invocations**: $0.20 per 1M requests
- **Duration**: $0.0000166667 per GB-second

Example (512MB, 2 min per file, 1000 files/month):

```
Invocations: 1000 * $0.0000002 = $0.20
Duration: 1000 * 120s * 0.5GB * $0.0000166667 = $1.00
Total: ~$1.20/month
```

### Optimization Tips

1. **Increase memory**: More memory = more CPU = faster execution
2. **Batch efficiently**: Larger batches reduce API calls
3. **Use provisioned concurrency**: For predictable workloads
4. **Optimize wait time**: Balance throughput vs rate limiting

## Testing

### Local Testing

Test the Lambda handler locally:

```bash
cd apps/lambda/ingest
python main.py
```

### Integration Testing

Test with actual AWS services:

```bash
# Create test event
cat > test_event.json <<EOF
{
  "s3_uri": "s3://test-bucket/test-data.csv",
  "index_name": "test_index",
  "opensearch_endpoint": "localhost:9200",
  "batch_size": 10,
  "limit_rows": 100
}
EOF

# Invoke Lambda
aws lambda invoke \
    --function-name opensearch-ingest-function \
    --payload file://test_event.json \
    response.json
```

## Next Steps

- [CLI Reference](cli-reference.md) - Direct CLI ingestion
- [Deploy on AWS](deploy-aws.md) - Infrastructure setup
- [Development Guide](development/index.md) - Customize Lambda function

