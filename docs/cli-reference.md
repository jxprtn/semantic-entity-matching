# CLI Reference

Complete reference for all CLI commands in the Entity Matching toolkit.

## Usage

```bash
uv run python -m apps.cli.main <command> [options]
```

## Common Options

These options are available for all commands:

- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}` - Set logging level (default: WARNING)
- `--no-timestamp` - Disable timestamps in log output

## Commands

### vectorize

Generate embeddings for CSV/Excel files offline (without OpenSearch).

```bash
uv run python -m apps.cli.main vectorize [options]
```

**Required Options:**

- `--bedrock-model-id BEDROCK_MODEL_ID` - Bedrock embedding model (e.g., amazon.titan-embed-text-v2:0)
- `--columns COLUMNS [COLUMNS ...]` - Columns to generate embeddings for
- `--file FILE` - Input file (CSV or Excel)

**Optional Options:**

- `--embedding-column-suffix EMBEDDING_COLUMN_SUFFIX` - Suffix to append to column names for embedding columns (default: _embedding)
- `--limit-rows LIMIT_ROWS` - Limit rows to process (after skipping rows)
- `--max-attempts MAX_ATTEMPTS` - Maximum retry attempts for failed batches (default: 5)
- `--output OUTPUT` - Custom output file path (default: <input_file>_vectorized.csv)
- `--overwrite` - Automatically overwrite existing output file without prompting
- `--profile PROFILE` - AWS profile to use
- `--region REGION` - AWS region (default: us-east-1)
- `--skip-rows SKIP_ROWS` - Skip rows at beginning (for resuming)
- `--vector-dimension VECTOR_DIMENSION` - Vector dimension for embeddings (default: 1024)
- `--vectorize-strategy {per-column,combined}` - Vectorization strategy: 'per-column' (default) creates separate embedding columns, 'combined' creates a single combined embedding

**Example:**

```bash
uv run python -m apps.cli.main vectorize \
    --bedrock-model-id amazon.titan-embed-text-v2:0 \
    --columns LONG_COMMON_NAME COMPONENT \
    --file /path/to/input.csv \
    --output /path/to/output.csv \
    --vectorize-strategy per-column \
    --profile default
```

**Output:**

```
Input file: /path/to/input.csv
Output file: /path/to/output.csv
Columns to vectorize: ['LONG_COMMON_NAME', 'COMPONENT']
Strategy: per-column
Model: amazon.titan-embed-text-v2:0
Vector dimension: 1024

Writing output to: /path/to/output.csv
Successfully wrote 1000 rows to /path/to/output.csv

Embedding columns created: ['LONG_COMMON_NAME_embedding', 'COMPONENT_embedding']
```

---

### setup

Configure OpenSearch index for vector search.

```bash
uv run python -m apps.cli.main setup [options]
```

**Required Options:**

- `--columns COLUMNS [COLUMNS ...]` - List of columns to use for ingestion
- `--index INDEX` - Index name to create

**Optional Options:**

- `--assume-role ASSUME_ROLE` - AWS role to assume for OpenSearch operations
- `--delete` - Delete existing index before setup
- `--ef-construction EF_CONSTRUCTION` - HNSW ef_construction parameter (default: 512)
- `--ef-search EF_SEARCH` - HNSW ef_search parameter (default: 512)
- `--engine ENGINE` - Vector search engine (default: faiss)
- `--m M` - HNSW m parameter (default: 48)
- `--no-confirm` - Skip confirmation prompts
- `--opensearch-host OPENSEARCH_HOST` - OpenSearch host (default: localhost)
- `--opensearch-port OPENSEARCH_PORT` - OpenSearch port (default: 9200)
- `--profile PROFILE` - AWS profile to use
- `--region REGION` - AWS region (default: us-east-1)
- `--space-type SPACE_TYPE` - Space type for vector similarity (default: l2)
- `--vector-dimension VECTOR_DIMENSION` - Vector dimension for embeddings (default: 1024)

**Example:**

```bash
uv run python -m apps.cli.main setup \
    --assume-role arn:aws:iam::123456789012:role/opensearch-master-role \
    --columns LONG_COMMON_NAME COMPONENT \
    --index loinc_data \
    --opensearch-host search-domain.us-east-1.es.amazonaws.com \
    --opensearch-port 443 \
    --profile default \
    --region us-east-1
```

---

### ingest

Ingest data from CSV or Excel files into OpenSearch.

```bash
uv run python -m apps.cli.main ingest [options]
```

**Required Options:**

- `--file FILE` - Excel (.xlsx, .xls) or CSV (.csv) file to import
- `--index INDEX` - Index name to ingest into
- `--knn-columns KNN_COLUMNS [KNN_COLUMNS ...]` - Columns to ingest as vectors for KNN search

**Optional Options:**

- `--assume-role ASSUME_ROLE` - AWS role to assume for OpenSearch operations
- `--delete` - Delete existing index before ingestion
- `--limit-rows LIMIT_ROWS` - Limit rows to process (after skipping rows)
- `--max-attempts MAX_ATTEMPTS` - Maximum retry attempts for ingestion (default: 5)
- `--opensearch-host OPENSEARCH_HOST` - OpenSearch host (default: localhost)
- `--opensearch-port OPENSEARCH_PORT` - OpenSearch port (default: 9200)
- `--profile PROFILE` - AWS profile to use
- `--region REGION` - AWS region (default: us-east-1)
- `--skip-rows SKIP_ROWS` - Rows to skip at beginning (for resuming)

**Example:**

```bash
uv run python -m apps.cli.main ingest \
    --assume-role arn:aws:iam::123456789012:role/opensearch-master-role \
    --file /path/to/data.csv \
    --index loinc_data \
    --knn-columns LONG_COMMON_NAME COMPONENT \
    --limit-rows 1000 \
    --opensearch-host search-domain.us-east-1.es.amazonaws.com \
    --opensearch-port 443 \
    --profile default \
    --region us-east-1
```

**Resuming Ingestion:**

If ingestion is interrupted, resume from where you left off:

```bash
# If interrupted at row 500, resume from there
uv run python -m apps.cli.main ingest \
    --file /path/to/data.csv \
    --index loinc_data \
    --knn-columns LONG_COMMON_NAME COMPONENT \
    --skip-rows 500 \
    --opensearch-host localhost \
    --opensearch-port 9200
```

---

### search

Perform vector-based semantic search on indexed data with reranking.

```bash
uv run python -m apps.cli.main search [options]
```

**Required Options:**

- `--column COLUMN` - Column to search on
- `--index INDEX` - Index name to search
- `--query QUERY` - Search query text

**Optional Options:**

- `--assume-role ASSUME_ROLE` - AWS role to assume for OpenSearch operations
- `--embedding-column-suffix EMBEDDING_COLUMN_SUFFIX` - Suffix appended to column names for embedding columns (default: _embedding)
- `--filter-field FILTER_FIELD` - Field name for filtering search results (e.g., 'CLASS')
- `--filter-value FILTER_VALUE` - Value for filtering search results (e.g., 'MICRO')
- `--opensearch-host OPENSEARCH_HOST` - OpenSearch host (default: localhost)
- `--opensearch-port OPENSEARCH_PORT` - OpenSearch port (default: 9200)
- `--profile PROFILE` - AWS profile to use
- `--region REGION` - AWS region (default: us-east-1)

**Example:**

```bash
uv run python -m apps.cli.main search \
    --assume-role arn:aws:iam::123456789012:role/opensearch-master-role \
    --column LONG_COMMON_NAME \
    --index loinc_data \
    --opensearch-host search-domain.us-east-1.es.amazonaws.com \
    --opensearch-port 443 \
    --profile default \
    --query "blood glucose measurement"
```

**Output:**

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

---

### evaluate

Evaluate search performance against a test dataset of queries.

```bash
uv run python -m apps.cli.main evaluate [options]
```

**Required Options:**

- `--column COLUMN` - Column to search on
- `--file FILE` - CSV/Excel file with test queries
- `--index INDEX` - Index name to search

**Optional Options:**

- `--assume-role ASSUME_ROLE` - AWS role to assume for OpenSearch operations
- `--batch-size BATCH_SIZE` - Number of documents to process in each batch (default: 50)
- `--display-field DISPLAY_FIELD` - Field name in OpenSearch index to display in results (default: LONG_COMMON_NAME)
- `--evaluation-columns EVALUATION_COLUMNS [EVALUATION_COLUMNS ...]` - List of columns to combine for evaluation query text (default: ['department name', 'test description'])
- `--limit-rows LIMIT_ROWS` - Limit queries to process (after skipping rows)
- `--match-column MATCH_COLUMN` - Column name in test dataset to match against (default: 'loinc code')
- `--match-field MATCH_FIELD` - Field name in OpenSearch index to match against (default: LOINC_NUM)
- `--opensearch-host OPENSEARCH_HOST` - OpenSearch host (default: localhost)
- `--opensearch-port OPENSEARCH_PORT` - OpenSearch port (default: 9200)
- `--profile PROFILE` - AWS profile to use
- `--region REGION` - AWS region (default: us-east-1)
- `--skip-rows SKIP_ROWS` - Skip rows at beginning

**Example:**

```bash
uv run python -m apps.cli.main evaluate \
    --assume-role arn:aws:iam::123456789012:role/opensearch-master-role \
    --batch-size 50 \
    --column LONG_COMMON_NAME \
    --file test_queries.csv \
    --index loinc_data \
    --limit-rows 100 \
    --opensearch-host search-domain.us-east-1.es.amazonaws.com \
    --opensearch-port 443 \
    --profile default
```

**Output:**

```
================================================================================
Evaluating search performance
Dataset: test_queries.csv
Index: loinc_data
Target field: LONG_COMMON_NAME
Total queries to run: 100
Batch size: 50
================================================================================
  Row 1: 1/15 | 0.8234 | Blood glucose measurement
  Row 2: 3/8 | 0.7891 | Cholesterol, total
...

================================================================================
EVALUATION SUMMARY
Total queries processed:	100
Successful queries:	98
Failed queries:		2
Top-5 accuracy:		85.7%
Top-10 accuracy:		91.8%
Top-25 accuracy:		96.9%
Top-100 accuracy:		98.0%
================================================================================
```

---

### tokens

Estimate token counts for files to predict Bedrock API costs.

```bash
uv run python -m apps.cli.main tokens [options]
```

**Required Options:**

- `--file FILE` - Excel (.xlsx, .xls) or CSV (.csv) file to analyze

**Example:**

```bash
uv run python -m apps.cli.main tokens \
    --file /path/to/data.csv
```

**Output:**

```

Token estimation for: /path/to/data.csv
==================================================
Method: tiktoken (cl100k_base)
Estimated tokens: 45,230
File size: 234,567 bytes
Tokens per byte: 0.1927
Note: Token count is an estimate based on file content
File extension: .csv
```

---

### dev

Interactive OpenSearch request console for testing and debugging.

```bash
uv run python -m apps.cli.main dev [options]
```

**Optional Options:**

- `--assume-role ASSUME_ROLE` - AWS role to assume for OpenSearch operations
- `--opensearch-host OPENSEARCH_HOST` - OpenSearch host (default: localhost)
- `--opensearch-port OPENSEARCH_PORT` - OpenSearch port (default: 9200)
- `--profile PROFILE` - AWS profile to use
- `--region REGION` - AWS region (default: us-east-1)

**Example:**

```bash
uv run python -m apps.cli.main dev \
    --opensearch-host search-domain.us-east-1.es.amazonaws.com \
    --opensearch-port 443 \
    --assume-role arn:aws:iam::123456789012:role/opensearch-master-role \
    --profile default
```

**Usage:**

```
OpenSearch Dev Console
==================================================
Enter your request in the format:
HTTP_METHOD /path
{
  "json": "body"
}

Press Ctrl+C to exit
==================================================

Enter your request (press Enter twice when done):
GET /_cluster/health

Response:
{
  "cluster_name": "123456789012:my-opensearch-domain",
  "status": "green",
  "timed_out": false,
  "number_of_nodes": 1,
  "number_of_data_nodes": 1,
  ...
}
```

**Example Requests:**

```
# Get cluster health
GET /_cluster/health

# List all indices
GET /_cat/indices?v

# Search with custom query
POST /loinc_data/_search
{
  "query": {
    "match": {
      "LONG_COMMON_NAME": "glucose"
    }
  }
}

# Update index mapping
PUT /loinc_data/_mapping
{
  "properties": {
    "new_field": {
      "type": "text"
    }
  }
}
```

---

## Environment Variables

You can use environment variables to simplify command invocation:

```bash
# Set in .env file
export AWS_PROFILE=default
export AWS_REGION=us-east-1
export OPENSEARCH_HOST=search-domain.us-east-1.es.amazonaws.com
export OPENSEARCH_PORT=443
export OPENSEARCH_ASSUME_ROLE=arn:aws:iam::123456789012:role/opensearch-master-role

# Then use in commands
uv run python -m apps.cli.main search \
    --opensearch-host $OPENSEARCH_HOST \
    --opensearch-port $OPENSEARCH_PORT \
    --assume-role $OPENSEARCH_ASSUME_ROLE \
    --index loinc_data \
    --column LONG_COMMON_NAME \
    --query "glucose"
```

## Tips and Best Practices

### Batch Size Tuning

- **Small files (<10K rows)**: Use larger batches (100-200)
- **Large files (>100K rows)**: Use smaller batches (25-50) to avoid timeouts
- **AWS OpenSearch**: Add `--wait-time 0.1` to avoid rate limiting

### Error Recovery

If a command fails midway:

1. Note the last successful row number
2. Use `--skip-rows` to resume from that point
3. Use `--limit-rows` to process in smaller chunks

### Performance Optimization

- Use `--vectorize-strategy combined` to create a single embedding for multiple columns
- Use `--limit-rows` for testing before processing full datasets
- Adjust `--max-attempts` for retry behavior during vectorization

### Cost Management

- Use `tokens` command to estimate costs before vectorization
- Process samples first with `--limit-rows 100`
- Monitor token usage in command output

## Next Steps

- [Getting Started](getting-started.md) - Step-by-step tutorial
- [Deploy on AWS](deploy-aws.md) - Production deployment
- [Development Guide](development/index.md) - Customization and extension

