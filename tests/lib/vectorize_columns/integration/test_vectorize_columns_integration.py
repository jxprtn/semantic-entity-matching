"""Integration tests for vectorize_columns function."""

import pandas as pd
import pytest

from lib.bedrock import BedrockClient
from lib.null_reporter import NullReporter
from lib.vectorize_columns import vectorize_columns


@pytest.mark.integration
@pytest.mark.aws
class TestVectorizeColumnsIntegration:
    """Integration tests for vectorize_columns."""

    def test_vectorize_columns_titan_v2(self, bedrock_client: BedrockClient) -> None:
        """Test vectorize_columns with Amazon Titan Text v2 model."""
        # Setup
        df = pd.DataFrame(
            {
                "text_col": [
                    "This is a test sentence for vectorization.",
                    "Another sentence to generate embeddings.",
                ],
                "other_col": [1, 2],
            }
        )
        columns = ["text_col"]
        model_id = "amazon.titan-embed-text-v2:0"

        # Execute
        result_df = vectorize_columns(
            bedrock_model_id=model_id,
            client=bedrock_client,
            columns=columns,
            df=df,
            embedding_column_suffix="_emb",
            strategy="per-column",
            reporter=NullReporter(),
        )

        # Verify
        assert "text_col_emb" in result_df.columns
        assert len(result_df) == 2

        # Check embedding structure and dimension
        first_embedding = result_df["text_col_emb"].iloc[0]
        assert isinstance(first_embedding, list)
        assert len(first_embedding) == 1024  # Titan v2 dimension
        assert all(isinstance(x, float) for x in first_embedding)

    def test_vectorize_columns_combined_strategy(self, bedrock_client: BedrockClient) -> None:
        """Test vectorize_columns with combined strategy."""
        # Setup
        df = pd.DataFrame(
            {
                "title": ["Product A", "Product B"],
                "description": ["Description for A", "Description for B"],
            }
        )
        columns = ["title", "description"]
        model_id = "amazon.titan-embed-text-v2:0"

        # Execute
        result_df = vectorize_columns(
            bedrock_model_id=model_id,
            client=bedrock_client,
            columns=columns,
            df=df,
            embedding_column_suffix="_emb",
            strategy="combined",
        )

        # Verify
        expected_col = "title_description_emb"
        assert expected_col in result_df.columns
        assert len(result_df) == 2

        # Check embedding dimension
        first_embedding = result_df[expected_col].iloc[0]
        assert isinstance(first_embedding, list)
        assert len(first_embedding) == 1024
