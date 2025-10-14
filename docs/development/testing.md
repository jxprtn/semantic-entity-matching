# Testing

This page covers how to run tests, write new tests, and understand the testing infrastructure.

## Test Organization

The project uses pytest with tests organized by type and scope:

```
tests/
├── conftest.py              # Root pytest configuration
├── localhost.env            # Localhost test environment
├── aws.env                  # AWS test environment
├── apps/                    # Application tests
│   └── cli/
│       └── commands/
│           └── test_vectorize_command.py
└── lib/                     # Library tests
    ├── batch_processor/
    │   └── test_batch_processor.py
    └── opensearch/
        ├── unit/            # Unit tests (fast, no external dependencies)
        │   ├── conftest.py
        │   ├── test_client_initialization.py
        │   └── test_client_settings.py
        └── integration/     # Integration tests (require OpenSearch)
            ├── conftest.py
            ├── test_client_bulk_integration.py
            ├── test_client_connection_integration.py
            ├── test_client_index_integration.py
            ├── test_client_ml_integration.py
            └── test_client_search_integration.py
```

## Test Types

### Unit Tests

Fast tests that don't require external services:

```python
import pytest
from lib.opensearch.client import OpenSearchClient

@pytest.mark.unit
def test_client_initialization():
    """Test client can be initialized with basic parameters."""
    client = OpenSearchClient(
        host="localhost",
        port=9200
    )
    assert client is not None
```

**Run unit tests:**

```bash
uv run pytest -m unit
```

### Integration Tests

Tests that require actual OpenSearch instances:

```python
import pytest
from lib.opensearch.client import OpenSearchClient

@pytest.mark.integration
@pytest.mark.localhost
def test_opensearch_connection(opensearch_client):
    """Test connecting to OpenSearch."""
    info = opensearch_client.get_cluster_info()
    assert info["cluster_name"] is not None
```

**Run integration tests:**

```bash
# Localhost
uv run pytest -m integration -m localhost

# AWS
uv run pytest -m integration -m aws
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
uv sync --extra test

# Run all unit tests (default)
uv run pytest -m unit

# Run specific test file
uv run pytest tests/lib/opensearch/unit/test_client_initialization.py

# Run specific test function
uv run pytest tests/lib/opensearch/unit/test_client_initialization.py::test_client_creation
```

### Test Markers

Filter tests by markers:

```bash
# Unit tests only
uv run pytest -m unit

# Integration tests
uv run pytest -m integration

# Localhost integration tests
uv run pytest -m "integration and localhost"

# AWS integration tests  
uv run pytest -m "integration and aws"

# Slow tests
uv run pytest -m slow

# Everything except slow tests
uv run pytest -m "not slow"
```

### Verbose Output

```bash
# Very verbose (-vv)
uv run pytest -vv

# Show print statements (-s)
uv run pytest -s

# Both
uv run pytest -vv -s

# Show full traceback
uv run pytest --tb=long
```

### Coverage Reports

```bash
# Run with coverage
uv run pytest -m unit --cov=lib

# Generate HTML report
uv run pytest -m unit --cov=lib --cov-report=html

# Open report
open htmlcov/index.html
```

## Test Fixtures

### Common Fixtures

Defined in `tests/conftest.py`:

```python
import pytest
import os
from lib.opensearch.client import OpenSearchClient
from lib.utils import get_aws_credentials

@pytest.fixture(scope="session")
def opensearch_host():
    """Get OpenSearch host from environment."""
    return os.getenv("OPENSEARCH_HOST", "localhost")

@pytest.fixture(scope="session")
def opensearch_client(opensearch_host):
    """Create OpenSearch client for tests."""
    return OpenSearchClient(
        host=opensearch_host,
        port=9200
    )
```

### Using Fixtures

```python
def test_with_fixture(opensearch_client):
    """opensearch_client is automatically provided."""
    info = opensearch_client.get_cluster_info()
    assert info is not None
```

### Fixture Scopes

- `function` - New instance per test (default)
- `class` - New instance per test class
- `module` - New instance per test module
- `session` - One instance for entire test session

```python
@pytest.fixture(scope="session")
def expensive_resource():
    """Created once per test session."""
    resource = create_expensive_resource()
    yield resource
    resource.cleanup()
```

## Writing Tests

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_bulk_index(opensearch_client, test_index):
    # Arrange: Set up test data
    documents = [
        {"id": "1", "name": "Document 1"},
        {"id": "2", "name": "Document 2"}
    ]
    
    # Act: Perform the operation
    result = opensearch_client.bulk_index(
        index=test_index,
        documents=documents
    )
    
    # Assert: Verify the result
    assert result["errors"] is False
    assert result["items"] is not None
    assert len(result["items"]) == 2
```

### Async Tests

Use `pytest-asyncio` for async tests:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    result = await some_async_function()
    assert result is not None
```

### Mocking

Use `pytest-mock` for mocking:

```python
def test_with_mock(mocker):
    """Test with mocked dependency."""
    # Mock a function
    mock_bedrock = mocker.patch('lib.bedrock.Bedrock.invoke')
    mock_bedrock.return_value = {"result": "mocked"}
    
    # Test code that uses the mocked function
    result = my_function()
    
    # Verify mock was called
    mock_bedrock.assert_called_once()
```

### Parametrized Tests

Test multiple scenarios:

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("world", 5),
    ("", 0),
    (None, 0)
])
def test_length(input, expected):
    """Test with multiple inputs."""
    assert len(input or "") == expected
```

### Exception Testing

Test error handling:

```python
import pytest
from opensearchpy.exceptions import NotFoundError

def test_delete_nonexistent_index(opensearch_client):
    """Test deleting non-existent index raises error."""
    with pytest.raises(NotFoundError):
        opensearch_client.delete_index("nonexistent-index")
```

## Integration Test Setup

### Localhost Integration Tests

1. **Start OpenSearch**:
   ```bash
   docker compose up -d
   ```

2. **Configure environment**:
   ```bash
   # Edit tests/localhost.env
   OPENSEARCH_HOST=localhost
   OPENSEARCH_PORT=9200
   AWS_PROFILE=default
   ML_CONNECTOR_ROLE=arn:aws:iam::ACCOUNT:role/ml-connector-role
   ```

3. **Run tests**:
   ```bash
   uv run pytest -m "integration and localhost"
   ```

### AWS Integration Tests

1. **Deploy infrastructure**:
   ```bash
   ./terraform apply
   ```

2. **Configure environment**:
   ```bash
   # Edit tests/aws.env
   AWS_OPENSEARCH_HOST=search-domain.us-east-1.es.amazonaws.com
   AWS_OPENSEARCH_PORT=443
   AWS_PROFILE=default
   AWS_ASSUME_ROLE=arn:aws:iam::ACCOUNT:role/opensearch-master-role
   AWS_ML_CONNECTOR_ROLE=arn:aws:iam::ACCOUNT:role/ml-connector-role
   ```

3. **Run tests**:
   ```bash
   uv run pytest -m "integration and aws"
   ```

## Test Configuration

### pytest Configuration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "-vv",
    "-s",
    "--tb=long",
    "-l",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "localhost: Localhost only tests",
    "aws: AWS only tests",
    "slow: Slow running tests",
]
```

### Coverage Configuration

```toml
[tool.coverage.run]
source = ["lib"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__init__.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install uv
        run: pip install uv
      
      - name: Install dependencies
        run: uv sync --extra test
      
      - name: Run unit tests
        run: uv run pytest -m unit --cov=lib --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Test Isolation

### Cleanup Between Tests

```python
import pytest

@pytest.fixture
def test_index(opensearch_client):
    """Create test index and clean up after."""
    index_name = "test-index"
    
    # Setup
    opensearch_client.create_index(index_name)
    
    yield index_name
    
    # Teardown
    try:
        opensearch_client.delete_index(index_name)
    except Exception:
        pass  # Index might not exist
```

### Parallel Test Execution

Use unique identifiers:

```python
import uuid

def test_with_unique_index(opensearch_client):
    """Use unique index name for parallel tests."""
    index_name = f"test-{uuid.uuid4()}"
    
    try:
        opensearch_client.create_index(index_name)
        # ... test code ...
    finally:
        opensearch_client.delete_index(index_name)
```

## Debugging Tests

### Run Single Test

```bash
uv run pytest tests/lib/opensearch/unit/test_client_initialization.py::test_client_creation -vv
```

### Use Debugger

```python
def test_with_debugger():
    import pdb; pdb.set_trace()
    # ... test code ...
```

### Print Debug Info

```bash
# Show print statements
uv run pytest -s

# Show local variables on failure
uv run pytest -l
```

### Keep Test Artifacts

```python
@pytest.fixture
def test_index_no_cleanup(opensearch_client):
    """Leave test index for inspection."""
    index_name = "debug-test-index"
    opensearch_client.create_index(index_name)
    return index_name
    # No cleanup - inspect manually
```

## Best Practices

### 1. Test Names

Use descriptive names:

```python
# Good
def test_bulk_index_creates_documents_in_opensearch():
    pass

# Bad
def test_bulk():
    pass
```

### 2. One Assert Per Test

Focus tests on single behaviors:

```python
# Good
def test_create_index_returns_success():
    result = client.create_index("test")
    assert result["acknowledged"] is True

def test_create_index_creates_index():
    client.create_index("test")
    assert client.index_exists("test")

# Bad (multiple unrelated asserts)
def test_create_index():
    result = client.create_index("test")
    assert result["acknowledged"] is True
    assert client.index_exists("test")
    assert result["shards_acknowledged"] is True
```

### 3. Clean Up Resources

Always clean up:

```python
@pytest.fixture
def resource():
    r = create_resource()
    yield r
    r.cleanup()  # Always cleanup
```

### 4. Mark Slow Tests

```python
@pytest.mark.slow
def test_large_dataset():
    """Test with large dataset (slow)."""
    pass
```

### 5. Use Meaningful Test Data

```python
# Good
test_documents = [
    {"id": "1", "name": "Alice", "age": 30},
    {"id": "2", "name": "Bob", "age": 25}
]

# Bad
test_documents = [
    {"id": "1", "name": "test1", "age": 1},
    {"id": "2", "name": "test2", "age": 2}
]
```

## Troubleshooting

### Tests Hanging

- Check for infinite loops
- Verify async tests use `@pytest.mark.asyncio`
- Check for missing timeouts

### Import Errors

```bash
# Verify pythonpath is set
uv run pytest --collect-only

# Check for missing dependencies
uv sync --extra test
```

### Fixture Not Found

- Verify fixture is defined in `conftest.py`
- Check fixture name spelling
- Ensure `conftest.py` is in correct location

### Integration Tests Failing

- Verify OpenSearch is running
- Check environment variables are set
- Test connection manually with curl

## Next Steps

- [Tooling](tooling.md) - Set up development tools
- [Environment](environment.md) - Configure test environments
- [Deployment](deployment.md) - Deploy test infrastructure

