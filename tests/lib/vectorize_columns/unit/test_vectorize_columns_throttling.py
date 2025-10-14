"""
Tests for vectorize_columns with simulated throttling exceptions.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from botocore.exceptions import ClientError

from lib.bedrock import (
    BedrockClient,
    EmbeddingType,
    InvokeEmbeddingModelCommand,
    InvokeModelCommand,
)
from lib.null_reporter import NullReporter
from lib.vectorize_columns import vectorize_columns


@pytest.mark.unit
class TestVectorizeColumnsThrottling:
    """Test vectorize_columns behavior with throttling exceptions."""

    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        """Create a sample DataFrame for testing."""
        return pd.DataFrame(
            {
                "name": [
                    "Product A",
                    "Product B",
                    "Product C",
                ],
                "description": [f"Description {i}" for i in range(3)],
            }
        )

    @pytest.fixture
    def mock_bedrock_client(self) -> MagicMock:
        """Create a mock BedrockClient."""
        return MagicMock(spec=BedrockClient)

    @pytest.fixture
    def mock_invoke_model_command(self, mock_bedrock_client: MagicMock) -> MagicMock:
        """Create a mock InvokeModelCommand."""
        mock_command = MagicMock(spec=InvokeModelCommand)
        mock_command.client = mock_bedrock_client
        mock_command.get_tokens_count = MagicMock(return_value=(100, 200))
        return mock_command

    @pytest.fixture
    def mock_invoke_embedding_model_command(self, mock_invoke_model_command: MagicMock) -> MagicMock:
        """Create a mock InvokeEmbeddingModelCommand."""
        mock_command = MagicMock(spec=InvokeEmbeddingModelCommand)
        mock_command.get_tokens_count = MagicMock(return_value=(100, 200))
        return mock_command

    def test_vectorize_columns_throttling_retries(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
    ) -> None:
        """
        Test that vectorize_columns retries on throttling exceptions.
        """
        columns = ["name"]
        max_attempts = 5
        num_rows = len(sample_df)

        # Create a ThrottlingException
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "An error occurred (ThrottlingException) when calling the InvokeModel operation: Rate exceeded",
            }
        }
        throttling_error = ClientError(error_response, "InvokeModel")

        # Always raise ThrottlingException
        mock_invoke_embedding_model_command.execute = AsyncMock(side_effect=throttling_error)

        with (
            patch(
                "lib.vectorize_columns.InvokeModelCommand",
                return_value=MagicMock(client=mock_bedrock_client),
            ),
            patch(
                "lib.vectorize_columns.InvokeEmbeddingModelCommand",
                return_value=mock_invoke_embedding_model_command,
            ),
        ):
            # We expect the ThrottlingException to propagate after retries
            with pytest.raises(ClientError) as exc_info:
                vectorize_columns(
                    bedrock_model_id="amazon.titan-embed-text-v2:0",
                    client=mock_bedrock_client,
                    columns=columns,
                    embedding_column_suffix="_emb",
                    embedding_type=EmbeddingType.FLOAT,
                    df=sample_df.copy(),
                    max_attempts=max_attempts,
                    output_dimension=1024,
                    strategy="per-column",
                    reporter=NullReporter(),
                )

            assert exc_info.value.response["Error"]["Code"] == "ThrottlingException"
            # Verify that retries happened (more than initial attempts)
            # and are bounded (at most max_attempts per row)
            call_count = mock_invoke_embedding_model_command.execute.call_count
            assert call_count > num_rows, (
                f"Expected retries, but got {call_count} calls for {num_rows} rows"
            )
            assert call_count <= num_rows * max_attempts, (
                f"Too many retries: {call_count} calls (max: {num_rows * max_attempts})"
            )
