"""Pytest fixtures for integration tests."""

import os

import pytest

from lib.bedrock import BedrockClient


@pytest.fixture(scope="module")
def bedrock_client() -> BedrockClient:
    """Create a BedrockClient instance for integration tests."""
    return BedrockClient(
        region=os.getenv("AWS_REGION", "us-east-1"),
        profile=os.getenv("AWS_PROFILE", None),
    )
