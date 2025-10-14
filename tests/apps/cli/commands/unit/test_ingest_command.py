"""
Unit tests for ingest CLI command.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.cli.commands import ingest


@pytest.mark.unit
class TestIngestCommand:
    """Test ingest command functionality."""

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

    def test_command_definition(self) -> None:
        """Test that command definition is properly structured."""
        assert hasattr(ingest, "DEFINITION")
        assert "name" in ingest.DEFINITION
        assert ingest.DEFINITION["name"] == "ingest"
        assert "description" in ingest.DEFINITION
        assert "arguments" in ingest.DEFINITION

        # Check required arguments
        arg_names = [arg["name"] for arg in ingest.DEFINITION["arguments"]]
        assert "file" in arg_names
        assert "index" in arg_names
        assert "assume-role" in arg_names
        assert "delete" in arg_names
        assert "knn-columns" in arg_names
        assert "limit-rows" in arg_names
        assert "max-attempts" in arg_names
        assert "opensearch-host" in arg_names
        assert "opensearch-port" in arg_names
        assert "profile" in arg_names
        assert "region" in arg_names
        assert "skip-rows" in arg_names

    def test_main_function_exists(self) -> None:
        """Test that main function exists and is callable."""
        assert hasattr(ingest, "main")
        assert callable(ingest.main)

    @patch("apps.cli.commands.ingest.ingest")
    @patch("apps.cli.commands.ingest.DataReader")
    @patch("apps.cli.commands.ingest.OpenSearchClient")
    @patch("apps.cli.commands.ingest.get_aws_credentials")
    def test_basic_ingestion(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_ingest: Any,
        sample_csv_file: str,
    ) -> None:
        """Test basic ingestion with mocked dependencies."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance
        # Mock DataReader
        test_df = pd.DataFrame({"name": ["Product A"], "description": ["Desc A"]})
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance

        # Call main function
        ingest.main(
            assume_role=None,
            delete=False,
            file=sample_csv_file,
            index="test-index",
            knn_columns=["name"],
            limit_rows=None,
            max_attempts=5,
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
        assert "reporter" in call_kwargs_opensearch

        # Verify DataReader was created
        mock_data_reader.assert_called_once()
        call_kwargs_reader = mock_data_reader.call_args[1]
        assert call_kwargs_reader["file_path"] == sample_csv_file
        assert call_kwargs_reader["limit_rows"] is None
        assert call_kwargs_reader["skip_rows"] == 0

        # Verify ingest function was called with correct parameters
        mock_ingest.assert_called_once()
        call_kwargs = mock_ingest.call_args[1]
        assert call_kwargs["delete"] is False
        assert call_kwargs["index_name"] == "test-index"
        assert call_kwargs["max_attempts"] == 5
        assert call_kwargs["opensearch"] == mock_client_instance
        assert isinstance(call_kwargs["rows"], list)

    @patch("apps.cli.commands.ingest.ingest")
    @patch("apps.cli.commands.ingest.DataReader")
    @patch("apps.cli.commands.ingest.OpenSearchClient")
    @patch("apps.cli.commands.ingest.get_aws_credentials")
    def test_ingestion_with_all_parameters(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_ingest: Any,
        sample_csv_file: str,
    ) -> None:
        """Test ingestion with all optional parameters."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance
        # Mock DataReader
        test_df = pd.DataFrame({"name": ["Product A"], "description": ["Desc A"]})
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance

        # Call main function with all parameters
        ingest.main(
            assume_role="arn:aws:iam::123456789012:role/test-role",
            delete=True,
            file=sample_csv_file,
            index="test-index",
            knn_columns=["name", "description"],
            limit_rows=1000,
            max_attempts=10,
            opensearch_host="opensearch.example.com",
            opensearch_port=443,
            profile="test-profile",
            region="us-west-2",
            skip_rows=10,
        )

        # Verify parameters were passed correctly
        mock_get_credentials.assert_called_once_with(
            assume_role="arn:aws:iam::123456789012:role/test-role",
            profile="test-profile",
            region="us-west-2",
        )

        # Verify DataReader was called with correct parameters
        mock_data_reader.assert_called_once()
        call_kwargs_reader = mock_data_reader.call_args[1]
        assert call_kwargs_reader["file_path"] == sample_csv_file
        assert call_kwargs_reader["limit_rows"] == 1000
        assert call_kwargs_reader["skip_rows"] == 10

        call_kwargs = mock_ingest.call_args[1]
        assert call_kwargs["delete"] is True
        assert call_kwargs["max_attempts"] == 10

    def test_missing_file_error(self) -> None:
        """Test error handling for missing file parameter."""
        with pytest.raises(SystemExit):
            ingest.main(
                assume_role=None,
                delete=False,
                file="",  # Empty file path
                index="test-index",
                knn_columns=["name"],
                limit_rows=None,
                max_attempts=5,
                opensearch_host="localhost",
                opensearch_port=9200,
                profile=None,
                region="us-east-1",
                skip_rows=0,
            )

    @patch("apps.cli.commands.ingest.ingest")
    @patch("apps.cli.commands.ingest.DataReader")
    @patch("apps.cli.commands.ingest.OpenSearchClient")
    @patch("apps.cli.commands.ingest.get_aws_credentials")
    def test_excel_file_support(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_ingest: Any,
        sample_excel_file: str,
    ) -> None:
        """Test that Excel files are supported."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance
        # Mock DataReader
        test_df = pd.DataFrame({"name": ["Product A"], "description": ["Desc A"]})
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance

        # Call main function with Excel file
        ingest.main(
            assume_role=None,
            delete=False,
            file=sample_excel_file,
            index="test-index",
            knn_columns=["name"],
            limit_rows=None,
            max_attempts=5,
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

    @patch("apps.cli.commands.ingest.ingest")
    @patch("apps.cli.commands.ingest.DataReader")
    @patch("apps.cli.commands.ingest.OpenSearchClient")
    @patch("apps.cli.commands.ingest.get_aws_credentials")
    def test_ingestion_error_handling(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_data_reader: Any,
        mock_ingest: Any,
        sample_csv_file: str,
    ) -> None:
        """Test error handling when ingest function raises an exception."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_opensearch_client.return_value = mock_client_instance
        # Mock DataReader
        test_df = pd.DataFrame({"name": ["Product A"], "description": ["Desc A"]})
        mock_reader_instance = MagicMock()
        mock_reader_instance.df = test_df
        mock_data_reader.return_value = mock_reader_instance

        # Mock ingest to raise an exception
        mock_ingest.side_effect = Exception("Ingestion failed")

        # Call main function - should propagate the exception
        with pytest.raises(Exception, match="Ingestion failed"):
            ingest.main(
                assume_role=None,
                delete=False,
                file=sample_csv_file,
                index="test-index",
                knn_columns=["name"],
                limit_rows=None,
                max_attempts=5,
                opensearch_host="localhost",
                opensearch_port=9200,
                profile=None,
                region="us-east-1",
                skip_rows=0,
            )

