"""
Unit tests for evaluate CLI command.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.cli.commands import evaluate


@pytest.mark.unit
class TestEvaluateCommand:
    """Test evaluate command functionality."""

    @pytest.fixture
    def sample_csv_file(self, tmp_path: Path) -> str:
        """Create a sample CSV file for testing."""
        csv_file = tmp_path / "sample.csv"
        df = pd.DataFrame(
            {
                "loinc code": ["12345-6", "12345-7", "12345-8"],
                "department name": ["Lab", "Lab", "Lab"],
                "test description": ["Test A", "Test B", "Test C"],
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
                "loinc code": ["12345-6", "12345-7"],
                "department name": ["Lab", "Lab"],
                "test description": ["Test A", "Test B"],
            }
        )
        df.to_excel(excel_file, index=False)
        return str(excel_file)

    def test_command_definition(self) -> None:
        """Test that command definition is properly structured."""
        assert hasattr(evaluate, "DEFINITION")
        assert "name" in evaluate.DEFINITION
        assert evaluate.DEFINITION["name"] == "evaluate"
        assert "description" in evaluate.DEFINITION
        assert "arguments" in evaluate.DEFINITION

        # Check required arguments
        arg_names = [arg["name"] for arg in evaluate.DEFINITION["arguments"]]
        assert "file" in arg_names
        assert "index" in arg_names
        assert "column" in arg_names
        assert "assume-role" in arg_names
        assert "batch-size" in arg_names
        assert "display-field" in arg_names
        assert "evaluation-columns" in arg_names
        assert "limit-rows" in arg_names
        assert "match-column" in arg_names
        assert "match-field" in arg_names
        assert "opensearch-host" in arg_names
        assert "opensearch-port" in arg_names
        assert "profile" in arg_names
        assert "region" in arg_names
        assert "skip-rows" in arg_names

    def test_main_function_exists(self) -> None:
        """Test that main function exists and is callable."""
        assert hasattr(evaluate, "main")
        assert callable(evaluate.main)

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_basic_evaluation(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_csv_file: str,
        capsys: Any,
    ) -> None:
        """Test basic evaluation with mocked dependencies."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        # Mock DataReader to return a DataFrame
        test_df = pd.DataFrame(
            {
                "loinc code": ["12345-6", "12345-7"],
                "department name": ["Lab", "Lab"],
                "test description": ["Test A", "Test B"],
            }
        )
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance

        # Mock evaluate to return results
        mock_evaluate.return_value = [
            {
                "row_index": 0,
                "rank": 1,
                "score": 0.95,
                "document": {"LONG_COMMON_NAME": "Result 1"},
                "hits_count": 10,
            },
            {
                "row_index": 1,
                "rank": 2,
                "score": 0.85,
                "document": {"LONG_COMMON_NAME": "Result 2"},
                "hits_count": 10,
            },
        ]

        # Call main function
        evaluate.main(
            assume_role=None,
            batch_size=50,
            column="LONG_COMMON_NAME",
            display_field="LONG_COMMON_NAME",
            evaluation_columns=None,  # Should use default
            file=sample_csv_file,
            index="test-index",
            limit_rows=None,
            match_column="loinc code",
            match_field="LOINC_NUM",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            region="us-east-1",
            skip_rows=0,
        )

        # Verify AWS credentials were requested
        mock_get_credentials.assert_called_once_with(
            assume_role=None,
            profile=None,
            region="us-east-1",
        )

        # Verify OpenSearch client was created
        mock_opensearch_client.assert_called_once()
        call_kwargs_opensearch = mock_opensearch_client.call_args[1]
        assert call_kwargs_opensearch["credentials"] == mock_credentials
        assert call_kwargs_opensearch["host"] == "localhost"
        assert call_kwargs_opensearch["port"] == 9200
        assert call_kwargs_opensearch["region"] == "us-east-1"

        # Verify DataReader was created
        mock_data_reader.assert_called_once()
        call_kwargs_reader = mock_data_reader.call_args[1]
        assert call_kwargs_reader["file_path"] == sample_csv_file
        assert call_kwargs_reader["limit_rows"] is None
        assert call_kwargs_reader["skip_rows"] == 0

        # Verify evaluate was called with correct parameters
        mock_evaluate.assert_called_once()
        call_kwargs = mock_evaluate.call_args[1]
        assert call_kwargs["batch_size"] == 50
        assert call_kwargs["column"] == "LONG_COMMON_NAME"
        assert isinstance(call_kwargs["df"], pd.DataFrame)
        assert call_kwargs["evaluation_columns"] == [
            "department name",
            "test description",
        ]  # Default
        assert call_kwargs["index_name"] == "test-index"
        assert call_kwargs["match_column"] == "loinc code"
        assert call_kwargs["match_field"] == "LOINC_NUM"
        assert call_kwargs["opensearch"] == mock_client_instance

        # Verify output was printed
        captured = capsys.readouterr()
        assert "Evaluating search performance" in captured.out
        assert "test-index" in captured.out
        assert "Total queries to run:" in captured.out

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_evaluation_with_custom_columns(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_csv_file: str,
    ) -> None:
        """Test evaluation with custom evaluation columns."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        test_df = pd.DataFrame(
            {
                "loinc code": ["12345-6"],
                "custom_col1": ["Value 1"],
                "custom_col2": ["Value 2"],
            }
        )
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance
        mock_evaluate.return_value = [
            {
                "row_index": 0,
                "rank": 1,
                "score": 0.95,
                "document": {"LONG_COMMON_NAME": "Result 1"},
                "hits_count": 5,
            },
        ]

        # Call main function with custom evaluation columns
        evaluate.main(
            assume_role=None,
            batch_size=50,
            column="LONG_COMMON_NAME",
            display_field="LONG_COMMON_NAME",
            evaluation_columns=["custom_col1", "custom_col2"],
            file=sample_csv_file,
            index="test-index",
            limit_rows=None,
            match_column="loinc code",
            match_field="LOINC_NUM",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            region="us-east-1",
            skip_rows=0,
        )

        # Verify evaluate was called with custom columns
        call_kwargs = mock_evaluate.call_args[1]
        assert call_kwargs["evaluation_columns"] == ["custom_col1", "custom_col2"]

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_evaluation_with_skip_rows(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_csv_file: str,
        capsys: Any,
    ) -> None:
        """Test evaluation with skip_rows parameter."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        # Create a larger test DataFrame
        test_df = pd.DataFrame(
            {
                "loinc code": ["12345-6", "12345-7", "12345-8", "12345-9"],
                "department name": ["Lab", "Lab", "Lab", "Lab"],
                "test description": ["Test A", "Test B", "Test C", "Test D"],
            }
        )
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance
        mock_evaluate.return_value = [
            {
                "row_index": 0,
                "rank": 1,
                "score": 0.95,
                "document": {"LONG_COMMON_NAME": "Result 1"},
                "hits_count": 10,
            },
        ]

        # Call main function with skip_rows
        evaluate.main(
            assume_role=None,
            batch_size=50,
            column="LONG_COMMON_NAME",
            display_field="LONG_COMMON_NAME",
            evaluation_columns=None,
            file=sample_csv_file,
            index="test-index",
            limit_rows=None,
            match_column="loinc code",
            match_field="LOINC_NUM",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            region="us-east-1",
            skip_rows=2,
        )

        # Verify DataReader was called with skip_rows
        mock_data_reader.assert_called_once()
        call_kwargs_reader = mock_data_reader.call_args[1]
        assert call_kwargs_reader["file_path"] == sample_csv_file
        assert call_kwargs_reader["skip_rows"] == 2

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_skip_rows_exceeds_total_rows(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_csv_file: str,
        capsys: Any,
    ) -> None:
        """Test that skip_rows exceeding total rows handles empty DataFrame gracefully."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        # Setup mock to return empty DataFrame (simulating skip_rows exceeding total rows)
        empty_df = pd.DataFrame()
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = empty_df
        mock_data_reader.return_value = mock_reader_instance

        # Mock evaluate to return empty results for empty DataFrame
        mock_evaluate.return_value = []

        # Call main function with skip_rows exceeding total rows
        evaluate.main(
            assume_role=None,
            batch_size=50,
            column="LONG_COMMON_NAME",
            display_field="LONG_COMMON_NAME",
            evaluation_columns=None,
            file=sample_csv_file,
            index="test-index",
            limit_rows=None,
            match_column="loinc code",
            match_field="LOINC_NUM",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            region="us-east-1",
            skip_rows=10,  # Exceeds total rows
        )

        # Verify it completed successfully with 0 queries
        captured = capsys.readouterr()
        assert "Total queries to run: 0" in captured.out
        assert "Total queries processed:\t0" in captured.out

    def test_missing_file_error(self) -> None:
        """Test error handling for missing file parameter."""
        with pytest.raises(SystemExit):
            evaluate.main(
                assume_role=None,
                batch_size=50,
                column="LONG_COMMON_NAME",
                display_field="LONG_COMMON_NAME",
                evaluation_columns=None,
                file="",  # Empty file path
                index="test-index",
                limit_rows=None,
                match_column="loinc code",
                match_field="LOINC_NUM",
                opensearch_host="localhost",
                opensearch_port=9200,
                profile=None,
                region="us-east-1",
                skip_rows=0,
            )

    def test_missing_column_error(self) -> None:
        """Test error handling for missing column parameter."""
        with pytest.raises(SystemExit):
            evaluate.main(
                assume_role=None,
                batch_size=50,
                column="",  # Empty column
                display_field="LONG_COMMON_NAME",
                evaluation_columns=None,
                file="/tmp/test.csv",
                index="test-index",
                limit_rows=None,
                match_column="loinc code",
                match_field="LOINC_NUM",
                opensearch_host="localhost",
                opensearch_port=9200,
                profile=None,
                region="us-east-1",
                skip_rows=0,
            )

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_evaluation_error_handling(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_csv_file: str,
    ) -> None:
        """Test error handling when evaluate raises ValueError."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        test_df = pd.DataFrame(
            {
                "loinc code": ["12345-6"],
                "department name": ["Lab"],
                "test description": ["Test A"],
            }
        )
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance

        # Mock evaluate to raise ValueError
        mock_evaluate.side_effect = ValueError("Column not found in dataset")

        # Call main function - should exit with error
        with pytest.raises(SystemExit):
            evaluate.main(
                assume_role=None,
                batch_size=50,
                column="LONG_COMMON_NAME",
                display_field="LONG_COMMON_NAME",
                evaluation_columns=None,
                file=sample_csv_file,
                index="test-index",
                limit_rows=None,
                match_column="loinc code",
                match_field="LOINC_NUM",
                opensearch_host="localhost",
                opensearch_port=9200,
                profile=None,
                region="us-east-1",
                skip_rows=0,
            )

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_evaluation_with_all_parameters(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_csv_file: str,
    ) -> None:
        """Test evaluation with all optional parameters."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        # Create a DataFrame with enough rows to skip 5
        test_df = pd.DataFrame(
            {
                "loinc code": ["12345-6", "12345-7", "12345-8", "12345-9", "12345-10", "12345-11"],
                "department name": ["Lab", "Lab", "Lab", "Lab", "Lab", "Lab"],
                "test description": ["Test A", "Test B", "Test C", "Test D", "Test E", "Test F"],
            }
        )
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance
        mock_evaluate.return_value = [
            {
                "row_index": 0,
                "rank": 1,
                "score": 0.95,
                "document": {"CUSTOM_FIELD": "Result 1"},
                "hits_count": 5,
            },
        ]

        # Call main function with all parameters
        evaluate.main(
            assume_role="arn:aws:iam::123456789012:role/test-role",
            batch_size=100,
            column="LONG_COMMON_NAME",
            display_field="CUSTOM_FIELD",
            evaluation_columns=["custom_col1", "custom_col2"],
            file=sample_csv_file,
            index="test-index",
            limit_rows=1000,
            match_column="custom_match_col",
            match_field="CUSTOM_MATCH_FIELD",
            opensearch_host="opensearch.example.com",
            opensearch_port=443,
            profile="test-profile",
            region="us-west-2",
            skip_rows=5,
        )

        # Verify parameters were passed correctly
        mock_get_credentials.assert_called_once_with(
            assume_role="arn:aws:iam::123456789012:role/test-role",
            profile="test-profile",
            region="us-west-2",
        )

        mock_data_reader.assert_called_once()
        call_kwargs_reader = mock_data_reader.call_args[1]
        assert call_kwargs_reader["file_path"] == sample_csv_file
        assert call_kwargs_reader["limit_rows"] == 1000
        assert call_kwargs_reader["skip_rows"] == 5

        call_kwargs = mock_evaluate.call_args[1]
        assert call_kwargs["batch_size"] == 100
        assert call_kwargs["evaluation_columns"] == ["custom_col1", "custom_col2"]
        assert call_kwargs["match_column"] == "custom_match_col"
        assert call_kwargs["match_field"] == "CUSTOM_MATCH_FIELD"

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_evaluation_results_display(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_csv_file: str,
        capsys: Any,
    ) -> None:
        """Test that evaluation results are displayed correctly."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        test_df = pd.DataFrame(
            {
                "loinc code": ["12345-6", "12345-7", "12345-8"],
                "department name": ["Lab", "Lab", "Lab"],
                "test description": ["Test A", "Test B", "Test C"],
            }
        )
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance

        # Mock evaluate to return various result types
        mock_evaluate.return_value = [
            {
                "row_index": 0,
                "rank": 1,
                "score": 0.95,
                "document": {"LONG_COMMON_NAME": "Result 1"},
                "hits_count": 10,
            },
            {"row_index": 1, "error": "Search failed"},
            {"row_index": 2},  # No match found
        ]

        # Call main function
        evaluate.main(
            assume_role=None,
            batch_size=50,
            column="LONG_COMMON_NAME",
            display_field="LONG_COMMON_NAME",
            evaluation_columns=None,
            file=sample_csv_file,
            index="test-index",
            limit_rows=None,
            match_column="loinc code",
            match_field="LOINC_NUM",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            region="us-east-1",
            skip_rows=0,
        )

        # Verify results were displayed
        captured = capsys.readouterr()
        assert "Row 1:" in captured.out
        assert "Row 2:" in captured.out
        assert "Row 3:" in captured.out
        assert "Error" in captured.out
        assert "No match found" in captured.out
        assert "EVALUATION SUMMARY" in captured.out

    @patch("apps.cli.commands.evaluate.evaluate")
    @patch("apps.cli.commands.evaluate.DataReader")
    @patch("apps.cli.commands.evaluate.OpenSearchClient")
    @patch("apps.cli.commands.evaluate.get_aws_credentials")
    def test_excel_file_support(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_evaluate: Any,
        sample_excel_file: str,
    ) -> None:
        """Test that Excel files are supported."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance

        test_df = pd.DataFrame(
            {
                "loinc code": ["12345-6"],
                "department name": ["Lab"],
                "test description": ["Test A"],
            }
        )
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance
        mock_evaluate.return_value = [
            {
                "row_index": 0,
                "rank": 1,
                "score": 0.95,
                "document": {"LONG_COMMON_NAME": "Result 1"},
                "hits_count": 5,
            },
        ]

        # Call main function with Excel file
        evaluate.main(
            assume_role=None,
            batch_size=50,
            column="LONG_COMMON_NAME",
            display_field="LONG_COMMON_NAME",
            evaluation_columns=None,
            file=sample_excel_file,
            index="test-index",
            limit_rows=None,
            match_column="loinc code",
            match_field="LOINC_NUM",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            region="us-east-1",
            skip_rows=0,
        )

        # Verify DataReader was called with Excel file path
        mock_data_reader.assert_called_once()
        call_kwargs_reader = mock_data_reader.call_args[1]
        assert call_kwargs_reader["file_path"] == sample_excel_file
        assert call_kwargs_reader["limit_rows"] is None
        assert call_kwargs_reader["skip_rows"] == 0
