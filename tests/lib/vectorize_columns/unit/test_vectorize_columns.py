"""
Unit tests for vectorize_columns function.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from lib.bedrock import (
    BedrockClient,
    EmbeddingModelId,
    EmbeddingModelOutput,
    EmbeddingType,
    InputType,
    InvokeEmbeddingModelCommand,
    InvokeModelCommand,
)
from lib.null_reporter import NullReporter
from lib.vectorize_columns import vectorize_columns


@pytest.mark.unit
class TestVectorizeColumns:
    """Test vectorize_columns functionality."""

    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        """Create a sample DataFrame for testing."""
        return pd.DataFrame(
            {
                "name": ["Product A", "Product B", "Product C"],
                "description": ["Description A", "Description B", "Description C"],
                "price": [10.0, 20.0, 30.0],
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

        # Mock execute method to return list[EmbeddingModelOutput]
        async def mock_execute(*args: Any, **kwargs: Any) -> list[EmbeddingModelOutput]:
            # Return a list of EmbeddingModelOutput (one per input)
            inputs = kwargs.get("inputs", [])
            return [
                EmbeddingModelOutput(
                    embeddings={EmbeddingType.FLOAT: [0.1, 0.2, 0.3, 0.4] * 256}  # 1024 dims
                )
                for _ in inputs
            ]

        mock_command.execute = AsyncMock(side_effect=mock_execute)
        return mock_command

    @pytest.fixture
    def mock_get_model_id(self) -> Generator[MagicMock, None, None]:
        """Mock the get_model_id static method."""
        with patch.object(
            InvokeEmbeddingModelCommand,
            "get_model_id",
            return_value=EmbeddingModelId.TITAN,
        ) as mock:
            yield mock

    def test_vectorize_columns_per_column_strategy(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test vectorization with per-column strategy."""
        columns = ["name", "description"]

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
            result_df = vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        # Verify original columns are preserved
        assert "name" in result_df.columns
        assert "description" in result_df.columns
        assert "price" in result_df.columns

        # Verify embedding columns are added
        assert "name_emb" in result_df.columns
        assert "description_emb" in result_df.columns

        # Verify embeddings are lists
        assert isinstance(result_df["name_emb"].iloc[0], list)
        assert isinstance(result_df["description_emb"].iloc[0], list)

        # Verify number of rows is preserved
        assert len(result_df) == len(sample_df)

        # Verify execute was called for each row
        assert mock_invoke_embedding_model_command.execute.call_count == len(sample_df)

    def test_vectorize_columns_combined_strategy(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test vectorization with combined strategy."""
        columns = ["name", "description"]

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
            result_df = vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="combined",
                reporter=NullReporter(),
            )

        # Verify original columns are preserved
        assert "name" in result_df.columns
        assert "description" in result_df.columns
        assert "price" in result_df.columns

        # Verify combined embedding column is added
        assert "name_description_emb" in result_df.columns
        assert "name_emb" not in result_df.columns
        assert "description_emb" not in result_df.columns

        # Verify embeddings are lists
        assert isinstance(result_df["name_description_emb"].iloc[0], list)

        # Verify number of rows is preserved
        assert len(result_df) == len(sample_df)

    def test_vectorize_columns_single_column(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test vectorization with a single column."""
        columns = ["name"]

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
            result_df = vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        # Verify embedding column is added
        assert "name_emb" in result_df.columns
        assert "description_emb" not in result_df.columns

    def test_vectorize_columns_missing_column_error(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
    ) -> None:
        """Test that ValueError is raised when columns don't exist."""
        columns = ["nonexistent_column"]

        with pytest.raises(ValueError) as exc_info:
            vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        assert "Columns not found in file" in str(exc_info.value)
        assert "nonexistent_column" in str(exc_info.value)

    def test_vectorize_columns_multiple_missing_columns_error(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
    ) -> None:
        """Test that ValueError lists all missing columns."""
        columns = ["name", "nonexistent1", "nonexistent2"]

        with pytest.raises(ValueError) as exc_info:
            vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        assert "Columns not found in file" in str(exc_info.value)
        assert "nonexistent1" in str(exc_info.value)
        assert "nonexistent2" in str(exc_info.value)

    def test_vectorize_columns_empty_dataframe(
        self,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test vectorization with empty DataFrame."""
        empty_df = pd.DataFrame({"name": [], "description": []})
        columns = ["name"]

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
            result_df = vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=empty_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        # Verify empty DataFrame is returned with embedding column
        assert len(result_df) == 0
        assert "name_emb" in result_df.columns
        # Execute should not be called for empty DataFrame
        assert mock_invoke_embedding_model_command.execute.call_count == 0

    def test_vectorize_columns_different_embedding_types(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test vectorization with different embedding types."""
        columns = ["name"]

        # Test with INT8 embedding type
        async def mock_execute_int8(*args: Any, **kwargs: Any) -> list[EmbeddingModelOutput]:
            inputs = kwargs.get("inputs", [])
            return [
                EmbeddingModelOutput(embeddings={EmbeddingType.INT8: [1, 2, 3, 4] * 256})
                for _ in inputs
            ]

        mock_invoke_embedding_model_command.execute = AsyncMock(side_effect=mock_execute_int8)

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
            result_df = vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.INT8,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        assert "name_emb" in result_df.columns
        assert isinstance(result_df["name_emb"].iloc[0], list)

    def test_vectorize_columns_calls_execute_with_correct_parameters(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test that execute is called with correct parameters."""
        columns = ["name", "description"]

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
            vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        # Verify execute was called for each row
        assert mock_invoke_embedding_model_command.execute.call_count == len(sample_df)

        # Verify each call has correct parameters
        for call in mock_invoke_embedding_model_command.execute.call_args_list:
            kwargs = call.kwargs
            assert "embedding_types" in kwargs
            assert kwargs["embedding_types"] == [EmbeddingType.FLOAT]
            assert "input_type" in kwargs
            assert kwargs["input_type"] == InputType.CLASSIFICATION
            assert "model_id" in kwargs
            assert "output_dimension" in kwargs
            assert kwargs["output_dimension"] == 1024
            assert "inputs" in kwargs
            # Verify inputs is a list of values from the columns
            assert isinstance(kwargs["inputs"], list)

    def test_vectorize_columns_preserves_original_data(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test that original DataFrame data is preserved."""
        columns = ["name"]
        original_data = sample_df.copy()

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
            result_df = vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )

        # Verify original columns and data are preserved
        for col in original_data.columns:
            assert col in result_df.columns
            pd.testing.assert_series_equal(result_df[col], original_data[col], check_names=True)

    def test_vectorize_columns_token_count_tracking(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test that token count is tracked and retrieved."""
        columns = ["name"]

        mock_reporter = MagicMock()
        
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
            vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=mock_reporter,
            )

        # Verify get_tokens_count was called
        assert mock_invoke_embedding_model_command.get_tokens_count.called

        # Verify token usage is reported via reporter.on_message
        token_message_calls = [
            call for call in mock_reporter.on_message.call_args_list 
            if "Token usage" in str(call)
        ]
        assert len(token_message_calls) > 0

    def test_vectorize_columns_api_error_propagation(
        self,
        sample_df: pd.DataFrame,
        mock_bedrock_client: Any,
        mock_invoke_embedding_model_command: Any,
        mock_get_model_id: Any,
    ) -> None:
        """Test that API errors are propagated."""
        columns = ["name"]

        # Mock execute to raise an exception
        mock_invoke_embedding_model_command.execute = AsyncMock(
            side_effect=Exception("Bedrock API Error")
        )

        with (
            patch(
                "lib.vectorize_columns.InvokeModelCommand",
                return_value=MagicMock(client=mock_bedrock_client),
            ),
            patch(
                "lib.vectorize_columns.InvokeEmbeddingModelCommand",
                return_value=mock_invoke_embedding_model_command,
            ),
            pytest.raises(Exception, match="Bedrock API Error"),
        ):
            vectorize_columns(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                client=mock_bedrock_client,
                columns=columns,
                embedding_column_suffix="_emb",
                embedding_type=EmbeddingType.FLOAT,
                df=sample_df.copy(),
                max_attempts=5,
                output_dimension=1024,
                strategy="per-column",
                reporter=NullReporter(),
            )
