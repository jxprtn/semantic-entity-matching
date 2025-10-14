"""
Unit tests for tokens CLI command.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.cli.commands import tokens
from lib.file_token_estimation.methods import TokenEstimationMethod
from lib.file_token_estimation.result import TokenEstimationResult


@pytest.mark.unit
class TestTokensCommand:
    """Test tokens command functionality."""

    @pytest.fixture
    def sample_csv_file(self, tmp_path: Path) -> str:
        """Create a sample CSV file for testing."""
        csv_file = tmp_path / "sample.csv"
        df = pd.DataFrame(
            {
                "name": ["Product A", "Product B", "Product C"],
                "description": ["Desc A", "Desc B", "Desc C"],
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
        assert hasattr(tokens, "DEFINITION")
        assert "name" in tokens.DEFINITION
        assert tokens.DEFINITION["name"] == "tokens"
        assert "description" in tokens.DEFINITION
        assert "arguments" in tokens.DEFINITION

        # Check required arguments
        arg_names = [arg["name"] for arg in tokens.DEFINITION["arguments"]]
        assert "file" in arg_names

    def test_main_function_exists(self) -> None:
        """Test that main function exists and is callable."""
        assert hasattr(tokens, "main")
        assert callable(tokens.main)

    @patch("apps.cli.commands.tokens.FileTokenEstimator")
    def test_basic_token_estimation(self, mock_estimator_class: Any, sample_csv_file: str, capsys: Any) -> None:
        """Test basic token estimation with mocked FileTokenEstimator."""
        # Setup mock
        mock_estimator_instance = MagicMock()
        mock_estimator_class.return_value = mock_estimator_instance

        # Create a mock result
        mock_result = TokenEstimationResult(
            method=TokenEstimationMethod.TOKENIZER,
            estimated_tokens=1500,
            file_size_bytes=5000,
            file_extension="csv",
            tokens_per_byte=0.3,
            note="Token estimation completed successfully",
        )
        mock_estimator_instance.estimate_tokens.return_value = mock_result

        # Call main function
        tokens.main(file=sample_csv_file)

        # Verify FileTokenEstimator was instantiated
        mock_estimator_class.assert_called_once()

        # Verify estimate_tokens was called with correct path
        mock_estimator_instance.estimate_tokens.assert_called_once_with(
            Path(sample_csv_file)
        )

        # Verify output was printed
        captured = capsys.readouterr()
        assert "Token estimation for:" in captured.out
        assert sample_csv_file in captured.out
        assert "Estimated tokens:" in captured.out
        assert "1,500" in captured.out or "1500" in captured.out
        assert "File size:" in captured.out
        assert "5,000" in captured.out or "5000" in captured.out

    @patch("apps.cli.commands.tokens.FileTokenEstimator")
    def test_excel_file_support(self, mock_estimator_class: Any, sample_excel_file: str, capsys: Any) -> None:
        """Test that Excel files are supported."""
        # Setup mock
        mock_estimator_instance = MagicMock()
        mock_estimator_class.return_value = mock_estimator_instance

        # Create a mock result for Excel file
        mock_result = TokenEstimationResult(
            method=TokenEstimationMethod.TOKENIZER_FALLBACK,
            estimated_tokens=2000,
            file_size_bytes=8000,
            file_extension="xlsx",
            tokens_per_byte=0.25,
            note="Conservative estimation for non-text file",
        )
        mock_estimator_instance.estimate_tokens.return_value = mock_result

        # Call main function with Excel file
        tokens.main(file=sample_excel_file)

        # Verify estimate_tokens was called with Excel file path
        mock_estimator_instance.estimate_tokens.assert_called_once_with(
            Path(sample_excel_file)
        )

        # Verify output includes Excel file info
        captured = capsys.readouterr()
        assert sample_excel_file in captured.out
        assert "xlsx" in captured.out

    def test_missing_file_error(self) -> None:
        """Test error handling for missing file parameter."""
        with pytest.raises(SystemExit):
            tokens.main(file="")  # Empty file path

    def test_file_not_found_error(self) -> None:
        """Test error handling for non-existent file."""
        with pytest.raises(SystemExit):
            tokens.main(file="/nonexistent/file.csv")

    @patch("apps.cli.commands.tokens.FileTokenEstimator")
    def test_estimation_error_handling(
        self, mock_estimator_class: Any, sample_csv_file: str, capsys: Any
    ) -> None:
        """Test error handling when estimation raises an exception."""
        # Setup mock to raise an exception
        mock_estimator_instance = MagicMock()
        mock_estimator_class.return_value = mock_estimator_instance
        mock_estimator_instance.estimate_tokens.side_effect = Exception(
            "Estimation failed"
        )

        # Call main function - should exit with error message
        with pytest.raises(SystemExit):
            tokens.main(file=sample_csv_file)

        # Verify error message was printed
        captured = capsys.readouterr()
        assert "Error estimating tokens" in captured.out
        assert "Estimation failed" in captured.out

    @patch("apps.cli.commands.tokens.FileTokenEstimator")
    def test_output_format(self, mock_estimator_class: Any, sample_csv_file: str, capsys: Any) -> None:
        """Test that output format is correct."""
        # Setup mock
        mock_estimator_instance = MagicMock()
        mock_estimator_class.return_value = mock_estimator_instance

        # Create a mock result
        mock_result = TokenEstimationResult(
            method=TokenEstimationMethod.TOKENIZER,
            estimated_tokens=1234,
            file_size_bytes=5678,
            file_extension="csv",
            tokens_per_byte=0.2174,
            note="Test note",
        )
        mock_estimator_instance.estimate_tokens.return_value = mock_result

        # Call main function
        tokens.main(file=sample_csv_file)

        # Verify all expected output fields are present
        captured = capsys.readouterr()
        output = captured.out

        assert "Token estimation for:" in output
        assert "Method:" in output
        assert "Estimated tokens:" in output
        assert "File size:" in output
        assert "Tokens per byte:" in output
        assert "Note:" in output
        assert "File extension:" in output
        assert "csv" in output

    @patch("apps.cli.commands.tokens.FileTokenEstimator")
    def test_tokenizer_failed_method(self, mock_estimator_class: Any, sample_csv_file: str, capsys: Any) -> None:
        """Test handling of tokenizer failed method."""
        # Setup mock
        mock_estimator_instance = MagicMock()
        mock_estimator_class.return_value = mock_estimator_instance

        # Create a mock result with tokenizer failed method
        mock_result = TokenEstimationResult(
            method=TokenEstimationMethod.TOKENIZER_FAILED,
            estimated_tokens=1000,
            file_size_bytes=4000,
            file_extension="csv",
            tokens_per_byte=0.25,
            note="Tokenizer failed, using simple estimation",
            tokenizer_error="Encoding error",
        )
        mock_estimator_instance.estimate_tokens.return_value = mock_result

        # Call main function
        tokens.main(file=sample_csv_file)

        # Verify output includes method information
        captured = capsys.readouterr()
        assert "Method:" in captured.out

