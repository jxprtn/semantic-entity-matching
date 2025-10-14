"""
Unit tests for vectorize CLI command.
"""

import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.cli.commands import vectorize


@pytest.mark.unit
class TestVectorizeCommand:
    """Test vectorize command functionality."""

    @pytest.fixture
    def sample_csv_file(self, tmp_path: Path) -> str:
        """Create a sample CSV file for testing."""
        csv_file = tmp_path / "sample.csv"
        df = pd.DataFrame(
            {
                "name": ["Product A", "Product B", "Product C"],
                "description": ["Desc A", "Desc B", "Desc C"],
                "price": [10.0, 20.0, 30.0],
            }
        )
        df.to_csv(csv_file, index=False)
        return str(csv_file)

    @pytest.fixture
    def sample_excel_file(self, tmp_path: Path) -> str:
        """Create a sample Excel file for testing."""
        import importlib.util

        if not importlib.util.find_spec("openpyxl"):
            pytest.skip("openpyxl not installed")

        excel_file = tmp_path / "sample.xlsx"
        df = pd.DataFrame(
            {
                "name": ["Product A", "Product B"],
                "description": ["Desc A", "Desc B"],
            }
        )
        df.to_excel(excel_file, index=False)
        return str(excel_file)

    @pytest.fixture
    def mock_vectorize_columns(self) -> Generator[MagicMock, None, None]:
        """Mock the vectorize_columns function."""
        with patch("apps.cli.commands.vectorize.vectorize_columns") as mock:
            # Setup mock to return a DataFrame
            def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
                return pd.DataFrame(
                    {
                        "name": ["Product A", "Product B"],
                        "name_emb": ["[0.1, 0.2, 0.3]", "[0.4, 0.5, 0.6]"],
                    }
                )

            mock.side_effect = side_effect
            yield mock

    def test_command_definition(self) -> None:
        """Test that command definition is properly structured."""
        assert hasattr(vectorize, "DEFINITION")
        assert "name" in vectorize.DEFINITION
        assert vectorize.DEFINITION["name"] == "vectorize"
        assert "description" in vectorize.DEFINITION
        assert "arguments" in vectorize.DEFINITION

        # Check required arguments
        arg_names = [arg["name"] for arg in vectorize.DEFINITION["arguments"]]
        assert "file" in arg_names
        assert "columns" in arg_names
        assert "bedrock-model-id" in arg_names
        assert "output" in arg_names
        assert "vectorize-strategy" in arg_names
        assert "skip-rows" in arg_names
        assert "limit-rows" in arg_names
        assert "max-attempts" in arg_names
        assert "profile" in arg_names
        assert "region" in arg_names
        assert "overwrite" in arg_names
        assert "embedding-column-suffix" in arg_names

    def test_main_function_exists(self) -> None:
        """Test that main function exists and is callable."""
        assert hasattr(vectorize, "main")
        assert callable(vectorize.main)

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="y")
    def test_basic_vectorization_per_column(
        self, mock_input: Any, mock_vectorize: Any, sample_csv_file: str, tmp_path: Path
    ) -> None:
        """Test basic vectorization with per-column strategy."""
        # Mock vectorize_columns to return DataFrame with embeddings
        result_df = pd.DataFrame(
            {
                "name": ["Product A", "Product B", "Product C"],
                "description": ["Desc A", "Desc B", "Desc C"],
                "price": [10.0, 20.0, 30.0],
                "name_emb": [
                    json.dumps([0.1, 0.2, 0.3]),
                    json.dumps([0.4, 0.5, 0.6]),
                    json.dumps([0.7, 0.8, 0.9]),
                ],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Call main function
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name"],
            embedding_column_suffix="_emb",
            file=sample_csv_file,
            limit_rows=None,
            max_attempts=5,
            output=None,
            overwrite=False,
            profile=None,
            region="us-east-1",
            skip_rows=0,
            vectorize_strategy="per-column",
        )

        # Verify vectorize_columns was called with correct arguments
        mock_vectorize.assert_called_once()
        call_kwargs = mock_vectorize.call_args[1]
        # 'df' is passed instead of 'file_path'
        assert isinstance(call_kwargs["df"], pd.DataFrame)
        assert call_kwargs["columns"] == ["name"]
        assert call_kwargs["strategy"] == "per-column"
        assert call_kwargs["bedrock_model_id"] == "amazon.titan-embed-text-v2:0"
        assert call_kwargs["embedding_column_suffix"] == "_emb"

        # Verify output file was created
        expected_output = str(Path(sample_csv_file).parent / "sample_vectorized.csv")
        assert os.path.exists(expected_output)

        # Read and verify output
        output_df = pd.read_csv(expected_output)
        assert "name_emb" in output_df.columns
        assert len(output_df) == 3

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="y")
    def test_vectorization_combined_strategy(
        self, mock_input: Any, mock_vectorize: Any, sample_csv_file: str, tmp_path: Path
    ) -> None:
        """Test vectorization with combined strategy."""
        # Mock vectorize_columns to return DataFrame with combined embeddings
        result_df = pd.DataFrame(
            {
                "name": ["Product A", "Product B", "Product C"],
                "description": ["Desc A", "Desc B", "Desc C"],
                "name_description_emb": [
                    json.dumps([0.1, 0.2, 0.3]),
                    json.dumps([0.4, 0.5, 0.6]),
                    json.dumps([0.7, 0.8, 0.9]),
                ],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Call main function with combined strategy
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name", "description"],
            embedding_column_suffix="_emb",
            file=sample_csv_file,
            limit_rows=None,
            max_attempts=5,
            output=None,
            overwrite=False,
            profile=None,
            region="us-east-1",
            skip_rows=0,
            vectorize_strategy="combined",
        )

        # Verify vectorize_columns was called with combined strategy
        call_kwargs = mock_vectorize.call_args[1]
        assert call_kwargs["strategy"] == "combined"
        assert call_kwargs["columns"] == ["name", "description"]

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="y")
    def test_custom_output_path(self, mock_input: Any, mock_vectorize: Any, sample_csv_file: str) -> None:
        """Test vectorization with custom output path."""
        result_df = pd.DataFrame(
            {
                "name": ["Product A"],
                "name_emb": [json.dumps([0.1, 0.2, 0.3])],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        custom_output = "/tmp/custom_output.csv"

        # Call main function with custom output
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name"],
            embedding_column_suffix="_emb",
            file=sample_csv_file,
            limit_rows=None,
            max_attempts=5,
            output=custom_output,
            overwrite=False,
            profile=None,
            region="us-east-1",
            skip_rows=0,
            vectorize_strategy="per-column",
        )

        # Verify output file was created at custom path
        assert os.path.exists(custom_output)

        # Clean up
        os.remove(custom_output)

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="n")
    def test_file_overwrite_declined(
        self, mock_input: Any, mock_vectorize: Any, sample_csv_file: str, tmp_path: Path
    ) -> None:
        """Test that user can decline file overwrite."""
        result_df = pd.DataFrame(
            {
                "name": ["Product A"],
                "name_emb": [json.dumps([0.1, 0.2, 0.3])],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Create the output file first
        output_path = Path(sample_csv_file).parent / "sample_vectorized.csv"
        output_path.write_text("existing content")

        # Call main function - should abort due to user declining overwrite
        with pytest.raises(SystemExit):
            vectorize.main(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                columns=["name"],
                embedding_column_suffix="_emb",
                file=sample_csv_file,
                limit_rows=None,
                max_attempts=5,
                output=None,
                overwrite=False,
                profile=None,
                region="us-east-1",
                skip_rows=0,
                vectorize_strategy="per-column",
            )

        # Verify original content is preserved
        assert output_path.read_text() == "existing content"

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    def test_file_overwrite_flag(self, mock_vectorize: Any, sample_csv_file: str, tmp_path: Path) -> None:
        """Test that --overwrite flag automatically overwrites existing file."""
        result_df = pd.DataFrame(
            {
                "name": ["Product A"],
                "name_emb": [json.dumps([0.1, 0.2, 0.3])],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Create the output file first
        output_path = Path(sample_csv_file).parent / "sample_vectorized.csv"
        output_path.write_text("existing content")

        # Call main function with overwrite=True - should not prompt
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name"],
            embedding_column_suffix="_emb",
            file=sample_csv_file,
            limit_rows=None,
            max_attempts=5,
            output=None,
            overwrite=True,
            profile=None,
            region="us-east-1",
            skip_rows=0,
            vectorize_strategy="per-column",
        )

        # Verify file was overwritten with new content
        output_df = pd.read_csv(output_path)
        assert "name_emb" in output_df.columns
        assert len(output_df) == 1

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    def test_missing_columns_error(self, mock_vectorize: Any, sample_csv_file: str) -> None:
        """Test error handling for missing columns."""

        # Mock vectorize_columns to raise ValueError for missing columns
        # Since the error is raised synchronously by the mock (simulating error during execution or setup)
        def side_effect(*args: Any, **kwargs: Any) -> None:
            raise ValueError("Columns not found in file: ['nonexistent']")

        mock_vectorize.side_effect = side_effect

        # Call main function with non-existent column - should exit
        with pytest.raises(SystemExit):
            vectorize.main(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                columns=["nonexistent"],
                embedding_column_suffix="_emb",
                file=sample_csv_file,
                limit_rows=None,
                max_attempts=5,
                output=None,
                overwrite=False,
                profile=None,
                region="us-east-1",
                skip_rows=0,
                vectorize_strategy="per-column",
            )

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="y")
    def test_skip_rows_functionality(
        self, mock_input: Any, mock_vectorize: Any, sample_csv_file: str, tmp_path: Path
    ) -> None:
        """Test skip-rows functionality."""
        result_df = pd.DataFrame(
            {
                "name": ["Product B", "Product C"],
                "name_emb": [
                    json.dumps([0.4, 0.5, 0.6]),
                    json.dumps([0.7, 0.8, 0.9]),
                ],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Call main function with skip_rows
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name"],
            embedding_column_suffix="_emb",
            file=sample_csv_file,
            limit_rows=None,
            max_attempts=5,
            output=None,
            overwrite=False,
            profile=None,
            region="us-east-1",
            skip_rows=1,
            vectorize_strategy="per-column",
        )

        # Verify DataReader (implicit) respected skip_rows by checking if mock was called (though implicit)
        # The main function doesn't pass skip_rows to vectorize_columns anymore, it uses DataReader.
        # But we can check call args anyway.
        mock_vectorize.assert_called_once()
        # DataReader logic is tested in test_data_reader.py
        # Here we just ensure vectorize_columns was called successfully

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="y")
    def test_limit_rows_functionality(
        self, mock_input: Any, mock_vectorize: Any, sample_csv_file: str, tmp_path: Path
    ) -> None:
        """Test limit-rows functionality."""
        result_df = pd.DataFrame(
            {
                "name": ["Product A", "Product B"],
                "name_emb": [
                    json.dumps([0.1, 0.2, 0.3]),
                    json.dumps([0.4, 0.5, 0.6]),
                ],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Call main function with limit_rows
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name"],
            embedding_column_suffix="_emb",
            file=sample_csv_file,
            limit_rows=2,
            max_attempts=5,
            output=None,
            overwrite=False,
            profile=None,
            region="us-east-1",
            skip_rows=0,
            vectorize_strategy="per-column",
        )

        # Verify successful call
        mock_vectorize.assert_called_once()

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="y")
    def test_excel_file_support(self, mock_input: Any, mock_vectorize: Any, sample_excel_file: str) -> None:
        """Test that Excel files are supported."""
        result_df = pd.DataFrame(
            {
                "name": ["Product A", "Product B"],
                "name_emb": [
                    json.dumps([0.1, 0.2, 0.3]),
                    json.dumps([0.4, 0.5, 0.6]),
                ],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Call main function with Excel file
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name"],
            embedding_column_suffix="_emb",
            file=sample_excel_file,
            limit_rows=None,
            max_attempts=5,
            output=None,
            overwrite=False,
            profile=None,
            region="us-east-1",
            skip_rows=0,
            vectorize_strategy="per-column",
        )

        # Verify output file has .csv extension (not .xlsx)
        expected_output = str(Path(sample_excel_file).parent / "sample_vectorized.csv")
        assert os.path.exists(expected_output)

    @patch("apps.cli.commands.vectorize.vectorize_columns")
    @patch("builtins.input", return_value="y")
    def test_multiple_columns(self, mock_input: Any, mock_vectorize: Any, sample_csv_file: str) -> None:
        """Test vectorization of multiple columns."""
        result_df = pd.DataFrame(
            {
                "name": ["Product A"],
                "description": ["Desc A"],
                "name_emb": [json.dumps([0.1, 0.2, 0.3])],
                "description_emb": [json.dumps([0.4, 0.5, 0.6])],
            }
        )

        def side_effect(*args: Any, **kwargs: Any) -> pd.DataFrame:
            return result_df

        mock_vectorize.side_effect = side_effect

        # Call main function with multiple columns
        vectorize.main(
            bedrock_model_id="amazon.titan-embed-text-v2:0",
            columns=["name", "description"],
            embedding_column_suffix="_emb",
            file=sample_csv_file,
            limit_rows=None,
            max_attempts=5,
            output=None,
            overwrite=False,
            profile=None,
            region="us-east-1",
            skip_rows=0,
            vectorize_strategy="per-column",
        )

        # Verify vectorize_columns was called with both columns
        call_kwargs = mock_vectorize.call_args[1]
        assert call_kwargs["columns"] == ["name", "description"]

        # Verify output has both embedding columns
        expected_output = str(Path(sample_csv_file).parent / "sample_vectorized.csv")
        output_df = pd.read_csv(expected_output)
        assert "name_emb" in output_df.columns
        assert "description_emb" in output_df.columns

    def test_file_not_found_error(self) -> None:
        """Test error handling for non-existent file."""
        with pytest.raises(SystemExit):
            vectorize.main(
                bedrock_model_id="amazon.titan-embed-text-v2:0",
                columns=["name"],
                embedding_column_suffix="_emb",
                file="/nonexistent/file.csv",
                limit_rows=None,
                max_attempts=5,
                output=None,
                overwrite=False,
                profile=None,
                region="us-east-1",
                skip_rows=0,
                vectorize_strategy="per-column",
            )
