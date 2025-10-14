# Development Tooling

This page covers the development tools used in the project and how to set them up.

## Package Manager: uv

The project uses **uv** instead of pip for Python package management.

### Installation

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Common Commands

```bash
# Install all dependencies
uv sync

# Install with optional dependencies
uv sync --extra test
uv sync --extra docs

# Add a new dependency
uv add package-name

# Add an optional dependency
uv add --optional test pytest-timeout

# Run a command in the environment
uv run python -m apps.cli.main --help

# Run tests
uv run pytest

# Update dependencies
uv sync --upgrade
```

### Why uv?

- **Faster**: 10-100x faster than pip
- **Reliable**: Deterministic dependency resolution
- **Modern**: Built with Rust for performance
- **Compatible**: Works with existing `pyproject.toml`

## Python Version Management

### Required Version

Python 3.12 or higher is required.

### Using pyenv (Recommended)

```bash
# Install pyenv
curl https://pyenv.run | bash

# Install Python 3.12
pyenv install 3.12.0

# Set as project version
pyenv local 3.12.0
```

### Verify Version

```bash
python --version
# Python 3.12.0
```

## Testing: pytest

### Installation

```bash
uv sync --extra test
```

### Running Tests

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest -m unit

# Integration tests
uv run pytest -m integration

# Specific file
uv run pytest tests/lib/opensearch/unit/test_client_initialization.py

# With coverage
uv run pytest --cov=lib --cov-report=html

# Verbose output
uv run pytest -vv

# Show print statements
uv run pytest -s
```

### Test Markers

The project uses pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_function():
    pass

@pytest.mark.integration
@pytest.mark.localhost
def test_opensearch_connection():
    pass

@pytest.mark.integration
@pytest.mark.aws
def test_aws_opensearch():
    pass

@pytest.mark.slow
def test_large_dataset():
    pass
```

### Configuration

See `pyproject.toml` for pytest configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "localhost: Localhost only tests",
    "aws: AWS only tests",
    "slow: Slow running tests",
]
```

## Docker

### Installation

Follow the official installation guide: [Docker Installation](https://docs.docker.com/engine/install/)

### Usage

```bash
# Start local OpenSearch
docker compose up -d

# View logs
docker compose logs -f opensearch

# Stop services
docker compose down

# Remove volumes (clean slate)
docker compose down -v

# Rebuild containers
docker compose up -d --build
```

### Docker Compose Services

The `docker-compose.yaml` defines:

- **opensearch**: OpenSearch 3.1.0 on port 9200
- **opensearch-dashboards**: Dashboards UI on port 5601

## Terraform

The project provides a Docker-based Terraform wrapper for consistent deployments.

### Using the Wrapper

```bash
# Initialize
./terraform init

# Plan changes
./terraform plan

# Apply changes
./terraform apply

# Destroy infrastructure
./terraform destroy

# View outputs
./terraform output
```

### Direct Terraform

If you have Terraform installed locally:

```bash
cd deployment
terraform init
terraform plan
terraform apply
```

### Required Version

Terraform 1.12 or higher.

## AWS CLI

### Installation

```bash
# macOS
brew install awscli

# Linux
pip install awscli

# Or download from AWS
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Configuration

```bash
# Configure default profile
aws configure

# Configure named profile
aws configure --profile my-profile

# Test configuration
aws sts get-caller-identity
```

### Profiles

The project supports AWS profiles for multi-account workflows:

```bash
# Use profile in CLI commands
uv run python -m apps.cli.main setup --profile my-profile ...

# Set default profile
export AWS_PROFILE=my-profile
```

## Documentation: MkDocs

### Installation

```bash
uv sync --extra docs
```

### Local Development

```bash
# Serve documentation locally
uv run mkdocs serve

# Open http://127.0.0.1:8000 in your browser

# Build static site
uv run mkdocs build

# Output in site/ directory
```

### Writing Documentation

- Documentation is in `docs/` directory
- Use Markdown format
- Follow existing structure
- Add code examples
- Use admonitions for important notes

Example admonitions:

```markdown
!!! note
    This is a note

!!! tip
    This is a helpful tip

!!! warning
    This is a warning

!!! danger
    This is dangerous!
```

## Code Quality Tools

### Linting with Ruff

The project uses **Ruff** for fast Python linting and formatting. Ruff is configured in `pyproject.toml` and runs automatically in CI/CD.

#### Installation

Ruff is included in the `dev` optional dependencies:

```bash
uv sync --extra dev
```

#### Running Linting Checks

```bash
# Check for linting errors
uv run ruff check lib/ apps/ tests/

# Check and auto-fix errors
uv run ruff check --fix lib/ apps/ tests/

# Check specific file or directory
uv run ruff check lib/bedrock/
```

#### Code Formatting

Ruff also handles code formatting:

```bash
# Format code
uv run ruff format lib/ apps/ tests/

# Check formatting without making changes
uv run ruff format --check lib/ apps/ tests/
```

#### Configuration

Ruff configuration is in `pyproject.toml` under `[tool.ruff]`. Key settings:

- **Line length**: 100 characters
- **Target Python**: 3.12+
- **Rule sets**: pycodestyle, pyflakes, isort, flake8-bugbear, and more
- **Auto-fix**: Enabled for all fixable rules

See `pyproject.toml` for the complete configuration.

### Type Checking with Pyright

The project uses **Pyright** for static type checking with strict mode enabled.

#### Installation

Pyright is included in the `dev` optional dependencies:

```bash
uv sync --extra dev
```

#### Running Type Checks

```bash
# Check all code
uv run pyright lib/ apps/

# Check specific directory
uv run pyright lib/

# Check with verbose output
uv run pyright lib/ --verbose
```

#### Configuration

Pyright configuration is in `pyrightconfig.json`:

- **Type checking mode**: Strict
- **Includes**: `lib/` and `apps/`
- **Excludes**: `.venv/` and `.test/`

### Pre-commit Hooks

The project includes pre-commit hooks to automatically run linting and type checking before commits.

#### Setup

```bash
# Install pre-commit
uv add --optional dev pre-commit

# Install git hooks
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files
```

#### What Runs

Pre-commit hooks automatically run:

- **Ruff linting** (with auto-fix)
- **Ruff formatting**
- **Pyright type checking**

Hooks run automatically on `git commit`. To skip hooks (not recommended):

```bash
git commit --no-verify
```

### CI/CD Integration

Linting and type checking run automatically in GitHub Actions on:

- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

See `.github/workflows/lint.yml` for the CI configuration.

### IDE Integration

#### VS Code

Recommended extensions:

- **Ruff** - Official Ruff extension for linting and formatting
- **Pylance** - Type checking (uses Pyright)

Settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "ruff.enable": true,
  "ruff.organizeImports": true
}
```

#### PyCharm

1. Install Ruff plugin: Settings → Plugins → Search "Ruff"
2. Configure Ruff: Settings → Tools → Ruff
   - Enable "Run Ruff on save"
   - Set executable path to `.venv/bin/ruff`
3. Configure Pyright: Settings → Languages & Frameworks → Python
   - Set type checker to Pyright

## IDE Setup

### VS Code

Recommended extensions:

- **Python** - Microsoft
- **Pylance** - Microsoft
- **Terraform** - HashiCorp
- **Docker** - Microsoft
- **AWS Toolkit** - Amazon

Settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "ruff.enable": true,
  "ruff.organizeImports": true
}
```

### PyCharm

1. Open project in PyCharm
2. Configure Python interpreter:
   - Settings → Project → Python Interpreter
   - Add interpreter from `.venv/`
3. Configure pytest:
   - Settings → Tools → Python Integrated Tools
   - Default test runner: pytest
4. Enable AWS integration:
   - Install AWS Toolkit plugin
   - Configure AWS credentials

## Environment Management

### Virtual Environment

uv automatically creates and manages the virtual environment:

```bash
# Location: .venv/ in project root

# Activate manually (usually not needed)
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Deactivate
deactivate
```

### Dependencies

Dependencies are defined in `pyproject.toml`:

```toml
[project]
dependencies = [
    "aioboto3>=15.5.0",
    "boto3>=1.40.56",
    "opensearch-py>=3.0.0",
    # ...
]

[project.optional-dependencies]
test = ["pytest>=9.0.0", ...]
docs = ["mkdocs>=1.6.0", ...]
```

### Lock File

`uv.lock` contains exact versions:

- **Commit** the lock file to version control
- **Update** with `uv sync --upgrade`
- **Reproducible** builds across environments

## Debugging

### Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: CLI",
      "type": "python",
      "request": "launch",
      "module": "apps.cli.main",
      "args": ["search", "--opensearch-host", "localhost", "--opensearch-port", "9200", "--index", "loinc_data"],
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-m", "unit"],
      "console": "integratedTerminal"
    }
  ]
}
```

### OpenSearch Debugging

```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# List indices
curl http://localhost:9200/_cat/indices?v

# Check index mapping
curl http://localhost:9200/loinc_data/_mapping?pretty

# View index settings
curl http://localhost:9200/loinc_data/_settings?pretty

# Check ML models
curl http://localhost:9200/_plugins/_ml/models/_search?pretty
```

## Performance Profiling

### Python Profiling

```python
import cProfile
import pstats

# Profile a function
cProfile.run('main()', 'output.prof')

# View results
stats = pstats.Stats('output.prof')
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Memory Profiling

```bash
# Install memory profiler
uv add --optional dev memory-profiler

# Profile memory usage
uv run python -m memory_profiler apps/cli/main.py
```

## Useful Scripts

### Development Scripts

Create a `scripts/` directory for common tasks:

```bash
# scripts/reset-opensearch.sh
#!/bin/bash
docker compose down -v
docker compose up -d
sleep 10
curl http://localhost:9200/_cluster/health

# scripts/run-tests.sh
#!/bin/bash
uv run pytest -m unit --cov=lib --cov-report=html

# scripts/build-docs.sh
#!/bin/bash
uv run mkdocs build
```

Make them executable:

```bash
chmod +x scripts/*.sh
```

## Next Steps

- [Environment Configuration](environment.md) - Set up environment variables
- [Testing Guide](testing.md) - Write and run tests
- [Deployment](deployment.md) - Deploy infrastructure

