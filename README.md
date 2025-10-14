# Semantic Entity Matching

This project provides an end-to-end automated pipeline for **semantic entity matching**.

It leverages OpenSearch as a vector store and search engine, combined with embedding models (Amazon Titan and Cohere) accessed through Amazon Bedrock, to enable semantic matching and discovery of related entities across datasets.

## Overview

### What is Semantic Entity Matching?

Also reffered to as *entity resolution*, *entity mapping*, *record matching*, *record linkage*, or more broadly *ontology alignment*, **Semantic Entity Matching** is the process of identifying when different representations of data refer to the same real-world entity, even when they use different terminology, codes, or formats.

### Concrete example in healthcare

1. LOINC Code Mapping

[LOINC](https://loinc.org/) is a universal standard for identifying medical laboratory observations. Different healthcare systems often describe the same test differently:
- **Problem**: A hospital needs to map their internal lab test names to LOINC codes.
  - Hospital A uses: *"Blood sugar, fasting"*
  - Hospital B uses: *"FBS - Fasting Blood Glucose"*
  - Lab C uses: *"GLU-F"*
  - Standard LOINC:
    - code: *"1558-6"* 
    - description: *"Fasting glucose [Mass/volume] in Serum or Plasma"*
- **Solution**: Instead of manually mapping thousands of test names, this system automates the process using semantic search:
  1. **Index**: Generate embeddings for all LOINC codes and store them in OpenSearch (one-time setup)
  2. **Search**: When a user searches for *"Blood sugar, fasting"*, generate an embedding for the query
  3. **Match**: Find the most semantically similar LOINC descriptions using k-NN vector search
  4. **Return**: Present ranked results with confidence scores:
     - `1558-6` | Score: 0.95 | *"Fasting glucose [Mass/volume] in Serum or Plasma"*
     - `2345-7` | Score: 0.89 | *"Glucose [Mass/volume] in Blood"*
  
  The system understands that "blood sugar" and "glucose" are synonymous, eliminating the need for manual mapping rules.

## Key Features

- **Vector Search**: HNSW-based similarity search for fast entity matching
- **Amazon Bedrock Integration**: Embedding generation and reranking with Cohere models
- **CLI Tools**: Complete command-line interface for all operations
- **Web UI**: Streamlit-based interactive search interface
- **Infrastructure as Code**: Terraform deployment for AWS infrastructure
- **Batch Processing**: Efficient handling of large datasets with resumability
- **Comprehensive Testing**: Unit and integration test suites

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) - Python package manager
- [Docker](https://docs.docker.com/engine/install/) - For local OpenSearch
- AWS Account with Bedrock access

### 1. Install Dependencies

```bash
uv sync
```

### 2. Start Local OpenSearch

```bash
docker compose up -d
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
source .env
```

### 4. Set Up OpenSearch

```bash
uv run python -m apps.cli.main setup \
    --columns LONG_COMMON_NAME COMPONENT \
    --index loinc_data \
    --opensearch-host localhost \
    --opensearch-port 9200
```

### 5. Ingest Data

```bash
uv run python -m apps.cli.main ingest \
    --file /path/to/data.csv \
    --index loinc_data \
    --knn-columns LONG_COMMON_NAME COMPONENT \
    --opensearch-host localhost \
    --opensearch-port 9200
```

### 6. Search

```bash
uv run python -m apps.cli.main search \
    --column LONG_COMMON_NAME \
    --index loinc_data \
    --query "blood glucose measurement" \
    --opensearch-host localhost \
    --opensearch-port 9200
```

## Available Commands

| Command | Description |
|---------|-------------|
| `setup` | Configure OpenSearch index for vector search |
| `ingest` | Load data from CSV/Excel files into OpenSearch |
| `search` | Perform vector-based semantic searches |
| `evaluate` | Test search performance against test datasets |
| `dev` | Interactive OpenSearch request console |
| `tokens` | Estimate token counts for files |
| `vectorize` | Generate embeddings for CSV/Excel files offline |

## Project Structure

```
├── apps/           # Applications (CLI, Lambda, Web)
├── lib/            # Core libraries
├── deployment/     # Terraform infrastructure
├── docs/           # Documentation
└── tests/          # Test suites
```

## Documentation

📚 **[Full Documentation](https://your-docs-site.com)** (or run `uv run mkdocs serve` locally)

- [Getting Started](docs/getting-started.md) - Local development setup
- [Deploy on AWS](docs/deploy-aws.md) - Production deployment
- [CLI Reference](docs/cli-reference.md) - Complete command documentation
- [Web UI](docs/web-ui.md) - Web interface guide
- [Lambda Handler](docs/lambda-handler.md) - Automated ingestion
- [Development](docs/development/index.md) - Developer documentation

## Technology Stack

- **Language**: Python 3.12+
- **Package Manager**: uv
- **Vector Database**: OpenSearch 3.1+
- **ML Embeddings**: AWS Bedrock (Titan, Cohere models)
- **Infrastructure**: Terraform
- **Testing**: pytest
- **Web Framework**: Streamlit

## Running Tests

```bash
# Unit tests
uv run pytest -m unit

# Integration tests (requires OpenSearch)
uv run pytest -m integration --envfile tests/localhost.env
```

## Deployment

### Deploy AWS Infrastructure

```bash
# Configure Terraform
cp deployment/terraform.tfvars.example deployment/terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy
./terraform init
./terraform plan
./terraform apply
```

### View Deployment Outputs

```bash
./terraform output opensearch_domain_endpoint
./terraform output opensearch_master_role_arn
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## License

This project is provided as-is for educational and commercial use.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/your-org/entity-matching-with-embeddings/issues)
- 💬 [Discussions](https://github.com/your-org/entity-matching-with-embeddings/discussions)
