"""Pytest fixtures for OpenSearchClient integration tests."""

import os
import uuid
from typing import Any

import pytest

from lib.null_reporter import NullReporter
from lib.opensearch.client import OpenSearchClient
from lib.utils import get_aws_credentials


@pytest.fixture(scope="session")
def opensearch_host() -> str:
    """Get OpenSearch host from environment."""
    host = os.getenv("OPENSEARCH_HOST")
    if not host:
        raise ValueError(
            "OPENSEARCH_HOST environment variable is not set. "
            "Please export it before running tests."
        )
    return host


@pytest.fixture(scope="session")
def opensearch_port() -> int:
    """Get OpenSearch port from environment."""
    port_str = os.getenv("OPENSEARCH_PORT")
    if not port_str:
        raise ValueError(
            "OPENSEARCH_PORT environment variable is not set. "
            "Please export it before running tests."
        )
    try:
        return int(port_str)
    except ValueError:
        raise ValueError(f"OPENSEARCH_PORT must be a valid integer, got: {port_str}")


@pytest.fixture(scope="session")
def aws_credentials() -> Any:
    """Fixture that provides credentials for OpenSearch client."""
    assume_role = os.getenv("ASSUME_ROLE")
    if not assume_role:
        raise ValueError(
            "ASSUME_ROLE environment variable is not set. Please export it before running tests."
        )
    profile = os.getenv("AWS_PROFILE")
    if not profile:
        raise ValueError(
            "AWS_PROFILE environment variable is not set. Please export it before running tests."
        )

    return get_aws_credentials(
        assume_role=assume_role,
        profile=profile,
        region=os.getenv("AWS_REGION"),
        role_session_name="pytest-integration-test",
    )


@pytest.fixture(scope="session")
def connector_auth(opensearch_backend: str, request: Any) -> dict[str, Any]:
    """
    Fixture that provides connector authentication based on backend.

    - AWS: Returns dict with iam_role
    - Localhost: Returns dict with access_key, secret_key, session_token
    """
    if opensearch_backend == "aws":
        role_arn = os.getenv("ML_CONNECTOR_ROLE")
        if not role_arn:
            raise ValueError(
                "ML_CONNECTOR_ROLE environment variable is not set. "
                "Please export it before running tests."
            )
        return {"iam_role": role_arn}
    profile = os.getenv("AWS_PROFILE")
    if not profile:
        raise ValueError(
            "AWS_PROFILE environment variable is not set. Please export it before running tests."
        )
    credentials = get_aws_credentials(
        profile=profile,
        region=os.getenv("AWS_REGION"),
        role_session_name="pytest-integration-test",
    )
    return {
        "access_key": credentials.access_key,
        "secret_key": credentials.secret_key,
        "session_token": getattr(credentials, "token", None),
    }


@pytest.fixture(scope="session")
def opensearch_backend(opensearch_host: str) -> str:
    """Fixture that checks if the OpenSearch host is an AWS domain."""
    return "aws" if "amazonaws.com" in opensearch_host else "localhost"


@pytest.fixture(scope="module")
def opensearch(
    request: Any,
    opensearch_backend: str,
    opensearch_host: str,
    opensearch_port: int,
) -> OpenSearchClient:
    """
    Create a real OpenSearchClient instance for integration tests.

    This fixture creates an actual OpenSearchClient that connects to a real
    OpenSearch instance (default: localhost:9200). It does NOT use mocks.

    The client will attempt to connect during initialization and will raise
    an exception if the connection fails.
    """
    credentials = (
        request.getfixturevalue("aws_credentials") if opensearch_backend == "aws" else None
    )

    # Create client WITHOUT any mocking - this is a real connection
    client = OpenSearchClient(
        host=opensearch_host,
        port=opensearch_port,
        credentials=credentials,
        reporter=NullReporter(),
    )

    # Verify we're using a real client, not a mock
    # Check that the internal client is actually an OpenSearch instance
    internal_client = client._client
    assert hasattr(internal_client, "info"), (
        "Client should be a real OpenSearch instance, not a mock"
    )

    # Verify connection by getting cluster info
    cluster_info = internal_client.info()
    assert "cluster_name" in cluster_info, "Should be able to get cluster info from real OpenSearch"

    print(
        f"\n[Integration Test] Connected to OpenSearch instance at {opensearch_host}:{opensearch_port}"
    )
    print(f"[Integration Test] Cluster: {cluster_info.get('cluster_name', 'unknown')}")

    return client


@pytest.fixture(scope="function")
def index_name(opensearch: OpenSearchClient) -> str:
    """Create a test index and return its name.

    The index is automatically created before the test and deleted after.
    """
    index_name = f"test-index-{opensearch._host}-{uuid.uuid4().hex[:8]}"
    opensearch.indexes.create(
        index=index_name,
        fields=["title", "description"],
        vector_dimension=1024,
        embedding_column_suffix="_embedding",
    )

    yield index_name

    try:
        idx = opensearch.indexes.get(index=index_name)
        idx.delete()
    except Exception:
        pass


@pytest.fixture(scope="module")
def model_group(opensearch: OpenSearchClient) -> dict[str, str]:
    """Create and cleanup a model group.

    Returns:
        Dict with model_group_id and model_group_name
    """
    unique_id = uuid.uuid4().hex[:8]
    model_group_name = f"test-model-group-{unique_id}"
    model_group = opensearch.model_groups.create(model_group_name=model_group_name)

    result = {"model_group_id": model_group.id, "model_group_name": model_group_name}

    yield result

    # Cleanup
    try:
        mg = opensearch.model_groups.find(field_name="name", field_value=result["model_group_name"])
        if mg:
            mg[0].delete()
    except Exception:
        pass


@pytest.fixture(scope="module")
def connector(opensearch: OpenSearchClient, connector_auth: dict[str, Any]) -> dict[str, str]:
    """Create and cleanup a connector.

    Returns:
        Dict with connector_id and connector_name
    """
    unique_id = uuid.uuid4().hex[:8]
    connector_name = f"test-connector-{unique_id}"
    connector = opensearch.connectors.create(
        name=connector_name,
        description="Test connector for ML integration tests",
        model_id="amazon.titan-embed-text-v2:0",
        dimensions=1024,
        region=opensearch._region or "us-east-1",
        **connector_auth,
    )

    result = {"connector_id": connector.id, "connector_name": connector_name}

    yield result

    # Cleanup
    try:
        conn = opensearch.connectors.get(connector_id=result["connector_id"])
        conn.delete()
    except Exception:
        pass


@pytest.fixture(scope="module")
def model(
    opensearch: OpenSearchClient, model_group: dict[str, str], connector: dict[str, str]
) -> dict[str, str]:
    """Create and cleanup a model.

    Args:
        model_group: Model group dict from model_group fixture
        connector: Connector dict from connector fixture

    Returns:
        Dict with model information merged with model_group and connector info
    """
    unique_id = uuid.uuid4().hex[:8]
    model_name = f"test-model-{unique_id}"
    model = opensearch.models.create(
        name=model_name,
        model_group_id=model_group["model_group_id"],
        connector_id=connector["connector_id"],
    )

    model.deploy()

    result = {"model_id": model.id, "model_name": model_name} | model_group | connector

    yield result

    # Cleanup
    try:
        model.delete()
    except Exception:
        pass


@pytest.fixture(scope="module")
def pipelines(opensearch: OpenSearchClient, model: dict[str, str]) -> dict[str, str]:
    """Create and cleanup ingestion and search pipelines.

    Args:
        model: Model dict from model fixture

    Returns:
        Dict with all ML stack info including pipelines, model, connector, and model_group
    """
    unique_id = uuid.uuid4().hex[:8]
    pipeline_name = f"test-pipeline-{unique_id}"

    # Create ingestion pipeline
    ingestion_pipeline_name = f"{pipeline_name}-ingest"
    opensearch.ingest_pipelines.create(
        model_id=model["model_id"],
        pipeline_name=ingestion_pipeline_name,
        fields=["title"],
    )

    # Create search pipeline
    search_pipeline_name = f"{pipeline_name}-search"
    opensearch.search_pipelines.create(
        model_id=model["model_id"],
        pipeline_name=search_pipeline_name,
        field="title",
    )

    result = {
        "ingestion_pipeline_name": ingestion_pipeline_name,
        "search_pipeline_name": search_pipeline_name,
    } | model

    yield result

    # Cleanup in reverse order
    try:
        from lib.opensearch.entities.pipeline import SearchPipeline

        pipeline = SearchPipeline(
            name=result["search_pipeline_name"],
            model_id="",
            field="",
            _repository=opensearch.search_pipelines,
        )
        pipeline.delete()
    except Exception:
        pass
    try:
        from lib.opensearch.entities.pipeline import IngestPipeline

        pipeline = IngestPipeline(
            name=result["ingestion_pipeline_name"],
            model_id="",
            fields=[],
            _repository=opensearch.ingest_pipelines,
        )
        pipeline.delete()
    except Exception:
        pass
