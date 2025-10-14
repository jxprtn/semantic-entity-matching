# Getting Started

This guide will help you set up a local development environment and run the CLI application with OpenSearch running in Docker.

## Prerequisites

Before you begin, ensure you have the following installed:

- **uv** - Python package manager: [Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
- **Docker** - Container platform: [Installation Guide](https://docs.docker.com/engine/install/)
- **AWS Account** - For Bedrock access (embeddings)

## Step 1: Install Dependencies

Clone the repository and install Python dependencies:

```bash
# Install all dependencies
uv sync

# Install with test dependencies (optional)
uv sync --extra test

# Install with documentation dependencies (optional)
uv sync --extra docs
```

## Step 2: Start OpenSearch with Docker Compose

The project includes a Docker Compose configuration that starts:

- OpenSearch 3.1.0 (vector search enabled)
- OpenSearch Dashboards (web UI on port 5601)

Start the services:

```bash
docker compose up -d
```

Verify OpenSearch is running:

```bash
curl http://localhost:9200/_cluster/health
```

You should see a response indicating the cluster is up and running.

!!! tip "OpenSearch Dashboards"
    Access OpenSearch Dashboards at [http://localhost:5601](http://localhost:5601) to explore your data visually.

## Step 3: Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```bash
# AWS Configuration
AWS_PROFILE=your-aws-profile
AWS_REGION=us-east-1
ASSUME_ROLE=  # Leave empty for localhost

# OpenSearch Configuration
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
INDEX=loinc_data

# Data Configuration
FILE=/path/to/your/data.csv
VECTORIZE_COLUMNS=LONG_COMMON_NAME COMPONENT
SEARCH_COLUMN=LONG_COMMON_NAME
SEARCH_QUERY=glucose

# Vector Search Configuration (HNSW parameters)
VECTOR_DIMENSION=1024
ENGINE=faiss
SPACE_TYPE=l2
M=48
EF_CONSTRUCTION=512
EF_SEARCH=512

# Processing Configuration
BATCH_SIZE=50
LIMIT_ROWS=1000  # Remove or set to higher value for full dataset
SKIP_ROWS=0
WAIT_TIME=0.1
MAX_ATTEMPTS=5
```


Source the environment file:

```bash
source .env
```

## Step 4: Set Up OpenSearch Index

Run the setup command to create the index:

```bash
uv run python -m apps.cli.main setup \
    --columns $VECTORIZE_COLUMNS \
    --ef-construction $EF_CONSTRUCTION \
    --ef-search $EF_SEARCH \
    --engine $ENGINE \
    --index $INDEX \
    --m $M \
    --opensearch-host $OPENSEARCH_HOST \
    --opensearch-port $OPENSEARCH_PORT \
    --profile $PROFILE \
    --space-type $SPACE_TYPE \
    --vector-dimension $VECTOR_DIMENSION
```

Expected output:

```
Creating new index 'loinc_data'... Done
Setup completed successfully!
```

## Step 5: Ingest Data

Load data from a CSV or Excel file:

```bash
uv run python -m apps.cli.main ingest \
    --file $FILE \
    --index $INDEX \
    --knn-columns $VECTORIZE_COLUMNS \
    --limit-rows $LIMIT_ROWS \
    --max-attempts $MAX_ATTEMPTS \
    --opensearch-host $OPENSEARCH_HOST \
    --opensearch-port $OPENSEARCH_PORT \
    --profile $PROFILE \
    --skip-rows $SKIP_ROWS
```

The ingestion process will:

1. Read the CSV/Excel file
2. Process data in batches
3. Send each batch to OpenSearch
4. Store documents in the index

Expected output:

```
Processing file: /path/to/data.csv
Will read 1000 rows total (skip 0, process 1000)
Detected CSV file format
Read 1000 rows from file
Processing batch 1/25 (file rows 1-40)
  Successfully indexed batch 1
Processing batch 2/25 (file rows 41-80)
  Successfully indexed batch 2
...
Data import completed successfully. Processed 1000 rows.
```

!!! tip "Resumable Ingestion"
    Use `--skip-rows` and `--limit-rows` to resume interrupted ingestions or process data in chunks.

## Step 6: Search the Data

Perform a vector search:

```bash
uv run python -m apps.cli.main search \
    --column $SEARCH_COLUMN \
    --index $INDEX \
    --opensearch-host $OPENSEARCH_HOST \
    --opensearch-port $OPENSEARCH_PORT \
    --profile $PROFILE \
    --query "blood glucose measurement"
```

Expected output:

```
================================================================================
1000 documents in index loinc_data

Target field:  LONG_COMMON_NAME
Searching for: blood glucose measurement
Found 50 results:

Reranking 50 documents...
Query: What is the most relevant description to 'blood glucose measurement'
==================================================
Reranked Results:
1. Score: 0.892 | Index: 1
    LOINC_NUM: 1558-6
Glucose [Mass/volume] in Blood

2. Score: 0.867 | Index: 2
    LOINC_NUM: 2345-7
Glucose [Moles/volume] in Blood
...
```

## Step 7: Evaluate Search Performance (Optional)

Test search quality with a test dataset:

```bash
uv run python -m apps.cli.main evaluate \
    --batch-size 50 \
    --column $SEARCH_COLUMN \
    --file test_queries.csv \
    --index $INDEX \
    --limit-rows 100 \
    --opensearch-host $OPENSEARCH_HOST \
    --opensearch-port $OPENSEARCH_PORT \
    --profile $PROFILE
```

The evaluation will run each query in the test file and provide statistics.

## Next Steps

- **Explore the Web UI**: See [Web UI](web-ui.md) for the Streamlit interface
- **Deploy to AWS**: Follow [Deploy on AWS](deploy-aws.md) for production deployment
- **Learn all CLI commands**: Check [CLI Reference](cli-reference.md)
- **Understand development**: Read [Development Guide](development/index.md)

## Common Issues

### OpenSearch Connection Failed

If you get connection errors:

1. Verify Docker containers are running: `docker ps`
2. Check OpenSearch health: `curl http://localhost:9200/_cluster/health`
3. Review container logs: `docker logs opensearch`

### Bedrock Access Denied

If you get Bedrock permission errors:

1. Ensure your AWS profile has Bedrock access
2. Verify the ML connector role has `bedrock:InvokeModel` permission
3. Check you're in a region where Bedrock is available (e.g., us-east-1)

### Out of Memory

If OpenSearch crashes:

1. Increase Docker memory allocation (Settings → Resources)
2. Reduce `OPENSEARCH_JAVA_OPTS` in `docker-compose.yaml`
3. Process smaller batches with `--limit-rows`

