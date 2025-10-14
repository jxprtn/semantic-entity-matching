# Web UI

The project includes a Streamlit-based web interface for interactive search and OpenSearch API exploration.

## Overview

The web UI provides:

- **Interactive Search**: Perform semantic and keyword searches
- **Real-time Results**: View search results with scores and details
- **Dev Console**: Send raw OpenSearch API requests
- **Visual Interface**: User-friendly alternative to CLI commands

## Running the Web UI

### Prerequisites

Ensure you have:

1. OpenSearch running (local or AWS)
2. Python dependencies installed: `uv sync`
3. Streamlit secrets configured (see below)

### Configuration

Create `.streamlit/secrets.toml` in the project root:

```toml
# OpenSearch Configuration
opensearch_endpoint = "https://your-domain.region.es.amazonaws.com"
opensearch_iam_role = "arn:aws:iam::ACCOUNT:role/opensearch-master-role"

# AWS Configuration
aws_profile = "default"
aws_region = "us-east-1"

# Search Configuration
opensearch_indices = {loinc_data = "embedding-pipeline"}
opensearch_fields = ["LONG_COMMON_NAME", "COMPONENT"]
```

For localhost OpenSearch:

```toml
opensearch_endpoint = "localhost:9200"
opensearch_iam_role = ""  # Empty for localhost
aws_profile = "default"
aws_region = "us-east-1"
opensearch_indices = {loinc_data = "embedding-pipeline"}
opensearch_fields = ["LONG_COMMON_NAME", "COMPONENT"]
```

### Start the Web UI

```bash
uv run streamlit run apps/web/main.py
```

The app will open automatically in your browser at `http://localhost:8501`.

## Features

### Search Tab

The search tab provides an intuitive interface for querying your data.

#### Search Configuration

Use the sidebar to configure your search:

1. **Index Selection**: Choose which OpenSearch index to search
2. **Search Field**: Select the field to search against
3. **Search Type**: 
   - **Semantic Search**: Vector-based similarity search
   - **Keyword Search**: Traditional text matching
4. **Result Fields**: Customize which fields appear in results

#### Performing Searches

1. Enter your query in the search box
2. Press Enter or click the "Go" button
3. Results appear below with:
   - Relevance score
   - Configured display fields
   - Expandable details showing all fields

#### Search Example

```
Query: "blood glucose measurement"

Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▼ 10-234-5 | 0.892 | Glucose [Mass/volume] in Blood
  LOINC_NUM: 10-234-5
  LONG_COMMON_NAME: Glucose [Mass/volume] in Blood
  COMPONENT: Glucose
  SYSTEM: Blood
  ...

▼ 10-567-8 | 0.867 | Glucose [Moles/volume] in Blood
  LOINC_NUM: 10-567-8
  LONG_COMMON_NAME: Glucose [Moles/volume] in Blood
  ...
```

### Dev Console Tab

The dev console allows you to send raw OpenSearch API requests directly from the web interface.

#### Features

- HTTP method selection (GET, POST, PUT, DELETE)
- URL path input
- JSON body editor with syntax highlighting
- Full response display
- Error handling and debugging

#### Example Requests

**Get Cluster Health**

```
Method: GET
Path: /_cluster/health
Body: (empty)
```

**Search with Custom Query**

```
Method: POST
Path: /loinc_data/_search
Body:
{
  "query": {
    "match": {
      "LONG_COMMON_NAME": "glucose"
    }
  },
  "size": 10
}
```

**Update Index Mapping**

```
Method: PUT
Path: /loinc_data/_mapping
Body:
{
  "properties": {
    "new_field": {
      "type": "text"
    }
  }
}
```

**Get Index Statistics**

```
Method: GET
Path: /loinc_data/_stats
Body: (empty)
```

## Customization

### Adding New Indices

Edit `.streamlit/secrets.toml`:

```toml
opensearch_indices = {
    loinc_data = "embedding-pipeline",
    products = "product-embedding-pipeline",
    documents = "document-embedding-pipeline"
}
```

### Customizing Result Display

Modify the result field inputs in the sidebar:

- **Result Field 1**: Primary identifier (e.g., ID, code)
- **Result Field 2**: Description or name field

These fields determine what appears in the collapsed result summary.

### Styling and Branding

The web UI uses Streamlit's theming system. Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#4F46E5"  # Indigo
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F3F4F6"
textColor = "#1F2937"
font = "sans serif"
```

## Deployment

### Deploy to Streamlit Cloud

1. Push your code to GitHub
2. Sign in to [Streamlit Cloud](https://streamlit.io/cloud)
3. Create a new app pointing to your repository
4. Configure secrets in the Streamlit Cloud dashboard
5. Deploy!

### Deploy to AWS (EC2 or ECS)

#### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["uv", "run", "streamlit", "run", "apps/web/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:

```bash
docker build -t opensearch-web-ui .
docker run -p 8501:8501 opensearch-web-ui
```

### Environment Variables

Alternatively, use environment variables instead of secrets file:

```python
# In apps/web/main.py, add:
import os

opensearch_endpoint = os.getenv("OPENSEARCH_ENDPOINT", st.secrets.get("opensearch_endpoint"))
opensearch_iam_role = os.getenv("OPENSEARCH_IAM_ROLE", st.secrets.get("opensearch_iam_role"))
```

## Troubleshooting

### Connection Refused

If the app can't connect to OpenSearch:

1. Verify `opensearch_endpoint` in secrets
2. Check OpenSearch is running: `curl http://localhost:9200`
3. Ensure firewall/security groups allow access
4. Verify IAM role permissions (for AWS)

### Authentication Failed

For AWS OpenSearch:

1. Verify `opensearch_iam_role` is correct
2. Check the role trust policy allows your credentials
3. Ensure your AWS profile has `sts:AssumeRole` permission
4. Test CLI access first to isolate the issue

### Missing Secrets Error

If you see "Missing secret: X" error:

1. Create `.streamlit/secrets.toml` in project root
2. Add all required secrets (see Configuration section)
3. Restart the Streamlit app

### Slow Search Performance

If searches are slow:

1. Check OpenSearch cluster health
2. Verify index settings (HNSW parameters)
3. Consider reducing search result size
4. Monitor OpenSearch metrics

## Advanced Features

### Custom Search Pipelines

The web UI uses the pipeline name from the indices configuration. To use different pipelines:

```toml
opensearch_indices = {
    loinc_data = "custom-pipeline-name",
    products = "another-pipeline"
}
```

### Field Filtering

The web UI automatically excludes `*_embedding` fields from results to keep the display clean. Embedding vectors are large and not human-readable.

### Caching

The OpenSearch client is cached using `@st.cache_resource` for better performance. Clear cache with:

```python
st.cache_resource.clear()
```

## Best Practices

1. **Use HTTPS**: Always use HTTPS endpoints for production
2. **Secure Secrets**: Never commit secrets to version control
3. **Monitor Usage**: Track search patterns and performance
4. **Set Limits**: Configure result size limits to prevent overload
5. **Test Locally**: Verify changes locally before deploying

## Next Steps

- Learn about [CLI commands](cli-reference.md) for programmatic access
- Explore [Lambda integration](lambda-handler.md) for automated workflows
- Review [development guide](development/index.md) for customization

