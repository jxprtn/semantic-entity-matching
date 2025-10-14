"""Pytest fixtures for Bedrock integration tests."""

import os

import pytest
import pytest_asyncio

from lib.bedrock import (
    BedrockClient,
    InvokeEmbeddingModelCommand,
    InvokeModelCommand,
)


@pytest_asyncio.fixture(scope="function")
async def bedrock_client() -> BedrockClient:
    """Create a BedrockClient instance for integration tests."""
    region = os.getenv("AWS_REGION") or "us-east-1"
    client = BedrockClient(
        region=region,
        profile=os.getenv("AWS_PROFILE", None),
    )
    yield client
    await client.close()


@pytest.fixture(scope="function")
def invoke_embedding_model_command(
    bedrock_client: BedrockClient,
) -> InvokeEmbeddingModelCommand:
    """Create a BedrockClientForTextEmbeddings instance for integration tests."""
    return InvokeEmbeddingModelCommand(InvokeModelCommand(client=bedrock_client))


@pytest.fixture(scope="function")
def test_text() -> str:
    """Sample text for embedding generation."""
    return "This is a test sentence for generating embeddings."
