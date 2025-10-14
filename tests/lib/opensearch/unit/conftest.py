"""Pytest fixtures for OpenSearchClient tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from botocore.credentials import Credentials

from lib.null_reporter import NullReporter
from lib.opensearch.client import OpenSearchClient


@pytest.fixture
def mock_credentials() -> Credentials:
    """Create mock AWS credentials."""
    return Credentials(
        access_key="test-access-key",
        secret_key="test-secret-key",
        token="test-token",
    )


@pytest.fixture
def mock_opensearch_client(mock_credentials: Credentials) -> Generator[MagicMock, None, None]:
    """Create a mock OpenSearch client."""
    with patch("lib.opensearch.client.OpenSearch") as mock_opensearch_class:
        mock_client_instance = MagicMock()
        mock_opensearch_class.return_value = mock_client_instance

        # Mock the info() call that happens during connection
        mock_client_instance.info.return_value = {"cluster_name": "test-cluster"}

        # Mock the http attribute for HTTP operations
        mock_client_instance.http = MagicMock()

        # Mock the indices attribute for index operations
        mock_client_instance.indices = MagicMock()

        # Mock the bulk method
        mock_client_instance.bulk = MagicMock()

        # Mock the count method
        mock_client_instance.count = MagicMock()

        # Mock the search method
        mock_client_instance.search = MagicMock()

        yield mock_client_instance


@pytest.fixture
def opensearch_client(mock_credentials: Credentials, mock_opensearch_client: MagicMock) -> Generator[OpenSearchClient, None, None]:
    """Create an OpenSearchClient instance with mocked dependencies."""
    with patch("lib.opensearch.client.OpenSearch") as mock_opensearch_class, \
         patch("lib.opensearch.client.SearchService"):
        mock_opensearch_class.return_value = mock_opensearch_client

        client = OpenSearchClient(
            credentials=mock_credentials,
            host="test-host.example.com",
            port=443,
            region="us-east-1",
            reporter=NullReporter(),
        )

        # Replace the internal client with our mock
        client._client = mock_opensearch_client

        yield client


@pytest.fixture
def mock_boto3_bedrock() -> Generator[MagicMock, None, None]:
    """Mock boto3 bedrock-runtime client."""
    with patch("boto3.client") as mock_boto3_client:
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        # Mock invoke_model response
        mock_response = MagicMock()
        mock_response.get.return_value.read.return_value = (
            b'{"embedding": [0.1, 0.2, 0.3]}'
        )
        mock_bedrock.invoke_model.return_value = {
            "body": mock_response.get.return_value
        }

        yield mock_bedrock
