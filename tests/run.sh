#!/bin/bash

# Remove any existing coverage data
rm -f .coverage .coverage.*
rm -rf htmlcov

# Run tests with different configs, appending coverage data
uv run pytest --envfile tests/locahost.env --capture=sys --cov --cov-append
uv run pytest --envfile tests/aws.env --capture=sys --cov --cov-append

# Generate combined coverage report
uv run coverage report
uv run coverage html
