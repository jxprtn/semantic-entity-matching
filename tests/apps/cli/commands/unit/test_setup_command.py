"""
Unit tests for setup CLI command.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from opensearchpy.exceptions import TransportError

from apps.cli.commands import setup
from lib.null_reporter import NullReporter


@pytest.mark.unit
class TestSetupCommand:
    """Test setup command functionality."""

    # ============================================================================
    # Fixtures
    # ============================================================================

    @pytest.fixture
    def mock_credentials(self) -> dict[str, str]:
        """Mock AWS credentials."""
        return {"access_key": "test", "secret_key": "test"}

    @pytest.fixture
    def mock_opensearch_client(self) -> MagicMock:
        """Mock OpenSearch client."""
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = False
        return mock_opensearch

    @pytest.fixture
    def base_setup_args(self) -> dict[str, Any]:
        """Base arguments for setup.main() calls."""
        return {
            "assume_role": None,
            "columns": ["name"],
            "delete": False,
            "ef_construction": 512,
            "ef_search": 512,
            "engine": "faiss",
            "index": "test-index",
            "m": 48,
            "no_confirm": False,
            "opensearch_host": "localhost",
            "opensearch_port": 9200,
            "profile": None,
            "region": "us-east-1",
            "space_type": "l2",
            "vector_dimension": 1024,
        }

    # ============================================================================
    # Command Definition Tests
    # ============================================================================

    def test_command_definition(self) -> None:
        """Test that command definition is properly structured."""
        assert hasattr(setup, "DEFINITION")
        assert "name" in setup.DEFINITION
        assert setup.DEFINITION["name"] == "setup"
        assert "description" in setup.DEFINITION
        assert "arguments" in setup.DEFINITION

        # Check required arguments
        arg_names = [arg["name"] for arg in setup.DEFINITION["arguments"]]
        assert "assume-role" in arg_names
        assert "columns" in arg_names
        assert "delete" in arg_names
        assert "ef-construction" in arg_names
        assert "ef-search" in arg_names
        assert "engine" in arg_names
        assert "index" in arg_names
        assert "m" in arg_names
        assert "no-confirm" in arg_names
        assert "opensearch-host" in arg_names
        assert "opensearch-port" in arg_names
        assert "profile" in arg_names
        assert "region" in arg_names
        assert "space-type" in arg_names
        assert "vector-dimension" in arg_names

    def test_main_function_exists(self) -> None:
        """Test that main function exists and is callable."""
        assert hasattr(setup, "main")
        assert callable(setup.main)

    def test_confirm_function_exists(self) -> None:
        """Test that confirm helper function exists."""
        assert hasattr(setup, "confirm")
        assert callable(setup.confirm)

    # ============================================================================
    # Confirm Function Tests
    # ============================================================================

    @pytest.mark.parametrize("input_value", ["yes", "YES", "Yes", "yEs"])
    def test_confirm_accepts_yes_variations(self, input_value: str) -> None:
        """Test that confirm accepts 'yes' in various cases."""
        mock_reporter = MagicMock()
        mock_reporter.on_input.return_value = input_value
        # Should not raise SystemExit
        setup.confirm("Test prompt", reporter=mock_reporter)
        mock_reporter.on_input.assert_called_once_with("Test prompt (yes/no): ")

    @pytest.mark.parametrize("input_value", ["no", "NO", "No", "nO"])
    def test_confirm_rejects_no_variations(self, input_value: str) -> None:
        """Test that confirm rejects 'no' in various cases."""
        mock_reporter = MagicMock()
        mock_reporter.on_input.return_value = input_value
        with pytest.raises(SystemExit) as exc_info:
            setup.confirm("Test prompt", reporter=mock_reporter)
        assert exc_info.value.code == 0
        mock_reporter.on_input.assert_called_once_with("Test prompt (yes/no): ")

    @pytest.mark.parametrize("input_value", ["", "maybe", "y", "n", "invalid"])
    def test_confirm_rejects_invalid_input(self, input_value: str) -> None:
        """Test that confirm rejects invalid input."""
        mock_reporter = MagicMock()
        mock_reporter.on_input.return_value = input_value
        with pytest.raises(SystemExit) as exc_info:
            setup.confirm("Test prompt", reporter=mock_reporter)
        assert exc_info.value.code == 0

    # ============================================================================
    # Setup Main Function - Basic Functionality
    # ============================================================================

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_calls_get_aws_credentials_with_correct_args(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that get_aws_credentials is called with correct arguments."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(**base_setup_args)

        mock_get_credentials.assert_called_once_with(
            assume_role=None,
            profile=None,
            region="us-east-1",
        )

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_instantiates_opensearch_client_correctly(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that OpenSearchClient is instantiated with correct arguments."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(**base_setup_args)

        mock_opensearch_class.assert_called_once()
        call_kwargs_opensearch = mock_opensearch_class.call_args[1]
        assert call_kwargs_opensearch["credentials"] == mock_credentials
        assert call_kwargs_opensearch["host"] == "localhost"
        assert call_kwargs_opensearch["port"] == 9200
        assert call_kwargs_opensearch["region"] == "us-east-1"
        assert "reporter" in call_kwargs_opensearch

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_calls_setup_opensearch_with_correct_args(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that setup_opensearch is called with correct arguments."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(**base_setup_args)

        mock_setup_opensearch.assert_called_once()
        call_kwargs = mock_setup_opensearch.call_args[1]
        assert call_kwargs["columns"] == ["name"]
        assert call_kwargs["delete"] is False
        assert call_kwargs["index_name"] == "test-index"
        assert call_kwargs["opensearch"] == mock_opensearch_client
        assert call_kwargs["ef_construction"] == 512
        assert call_kwargs["ef_search"] == 512
        assert call_kwargs["engine"] == "faiss"
        assert call_kwargs["m"] == 48
        assert call_kwargs["space_type"] == "l2"
        assert call_kwargs["vector_dimension"] == 1024

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_with_multiple_columns(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test setup with multiple columns."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        columns = ["name", "description", "category", "tags"]
        setup.main(**{**base_setup_args, "columns": columns})

        call_kwargs = mock_setup_opensearch.call_args[1]
        assert call_kwargs["columns"] == columns

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_prints_success_message(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
        capsys: Any,
    ) -> None:
        """Test that success message is printed on completion."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(**base_setup_args)

        captured = capsys.readouterr()
        assert "Setup completed successfully!" in captured.out

    # ============================================================================
    # Setup Main Function - Delete Flag and Confirmation
    # ============================================================================

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    @patch("builtins.input", return_value="yes")
    def test_setup_with_delete_prompts_for_confirmation(
        self,
        mock_input: Any,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that setup with delete flag prompts for user confirmation."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = True
        mock_opensearch_class.return_value = mock_opensearch

        setup.main(**{**base_setup_args, "delete": True})

        # Verify user was prompted for confirmation twice (once for delete, once for index)
        assert mock_input.call_count == 2

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    @patch("builtins.input", return_value="yes")
    def test_setup_with_delete_calls_setup_opensearch_ml_with_delete_true(
        self,
        mock_input: Any,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that setup with delete flag calls setup_opensearch with delete=True."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = True
        mock_opensearch_class.return_value = mock_opensearch

        setup.main(**{**base_setup_args, "delete": True})

        call_kwargs = mock_setup_opensearch.call_args[1]
        assert call_kwargs["delete"] is True

    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_user_declines_delete_confirmation_exits(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that user declining delete confirmation exits with code 0."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = False
        mock_opensearch_class.return_value = mock_opensearch
        
        # Mock ConsoleReporter to simulate user declining
        with patch("apps.cli.commands.setup.ConsoleReporter") as mock_reporter_class:
            mock_reporter = MagicMock()
            mock_reporter.on_input.return_value = "no"  # User declines
            mock_reporter_class.return_value = mock_reporter

            with pytest.raises(SystemExit) as exc_info:
                setup.main(**{**base_setup_args, "delete": True})

            assert exc_info.value.code == 0

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_with_delete_when_index_not_exists_only_prompts_once(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that when index doesn't exist, only one confirmation prompt is shown."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = False
        mock_opensearch_class.return_value = mock_opensearch

        with patch("builtins.input", return_value="yes") as mock_input:
            setup.main(**{**base_setup_args, "delete": True})

            # Only one prompt when index doesn't exist
            assert mock_input.call_count == 1

    # ============================================================================
    # Setup Main Function - No Confirm Flag
    # ============================================================================

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    @patch("builtins.input")
    def test_no_confirm_skips_all_prompts(
        self,
        mock_input: Any,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that --no-confirm skips all confirmation prompts."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = True
        mock_opensearch_class.return_value = mock_opensearch

        setup.main(**{**base_setup_args, "delete": True, "no_confirm": True})

        # Verify input() was never called
        mock_input.assert_not_called()

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_no_confirm_with_delete_calls_setup_opensearch_ml(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that --no-confirm with delete still calls setup_opensearch."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = True
        mock_opensearch_class.return_value = mock_opensearch

        setup.main(**{**base_setup_args, "delete": True, "no_confirm": True})

        call_kwargs = mock_setup_opensearch.call_args[1]
        assert call_kwargs["delete"] is True

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    @patch("builtins.input", return_value="yes")
    def test_no_confirm_defaults_to_false(
        self,
        mock_input: Any,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that no_confirm defaults to False, preserving existing behavior."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = True
        mock_opensearch_class.return_value = mock_opensearch

        setup.main(**{**base_setup_args, "delete": True})

        # Verify input() was called (confirmation prompts were shown)
        assert mock_input.call_count == 2

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    @patch("builtins.input")
    def test_no_confirm_with_delete_false_has_no_effect(
        self,
        mock_input: Any,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that --no-confirm with delete=False has no effect (no prompts anyway)."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(**{**base_setup_args, "no_confirm": True})

        # Verify input() was never called (no delete, so no prompts)
        mock_input.assert_not_called()

    # ============================================================================
    # Setup Main Function - Custom Parameters
    # ============================================================================

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_with_custom_pipeline_name(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test that custom pipeline name is properly constructed."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(**{**base_setup_args, "index": "my-index"})

        call_kwargs = mock_setup_opensearch.call_args[1]
        assert call_kwargs["index_name"] == "my-index"

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_with_custom_aws_settings(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test setup with custom AWS profile and region."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(
            **{
                **base_setup_args,
                "assume_role": "arn:aws:iam::123456789012:role/assume-role",
                "profile": "custom-profile",
                "region": "us-west-2",
            }
        )

        mock_get_credentials.assert_called_once_with(
            assume_role="arn:aws:iam::123456789012:role/assume-role",
            profile="custom-profile",
            region="us-west-2",
        )

        mock_opensearch_class.assert_called_once()
        call_kwargs_opensearch = mock_opensearch_class.call_args[1]
        assert call_kwargs_opensearch["credentials"] == mock_credentials
        assert call_kwargs_opensearch["host"] == "localhost"
        assert call_kwargs_opensearch["port"] == 9200
        assert call_kwargs_opensearch["region"] == "us-west-2"
        assert "reporter" in call_kwargs_opensearch

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_with_custom_opensearch_host_and_port(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test setup with custom OpenSearch host and port."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(
            **{
                **base_setup_args,
                "opensearch_host": "my-opensearch-domain.com",
                "opensearch_port": 443,
            }
        )

        mock_opensearch_class.assert_called_once()
        call_kwargs_opensearch = mock_opensearch_class.call_args[1]
        assert call_kwargs_opensearch["credentials"] == mock_credentials
        assert call_kwargs_opensearch["host"] == "my-opensearch-domain.com"
        assert call_kwargs_opensearch["port"] == 443
        assert call_kwargs_opensearch["region"] == "us-east-1"
        assert "reporter" in call_kwargs_opensearch

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_with_custom_vector_parameters(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test setup with custom vector parameters."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client

        setup.main(
            **{
                **base_setup_args,
                "ef_construction": 256,
                "ef_search": 100,
                "engine": "nmslib",
                "m": 16,
                "space_type": "cosine",
                "vector_dimension": 768,
            }
        )

        call_kwargs = mock_setup_opensearch.call_args[1]
        assert call_kwargs["ef_construction"] == 256
        assert call_kwargs["ef_search"] == 100
        assert call_kwargs["engine"] == "nmslib"
        assert call_kwargs["m"] == 16
        assert call_kwargs["space_type"] == "cosine"
        assert call_kwargs["vector_dimension"] == 768

    # ============================================================================
    # Setup Main Function - Index Existence
    # ============================================================================

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_prints_message_when_index_exists(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        base_setup_args: dict[str, Any],
        capsys: Any,
    ) -> None:
        """Test that message is printed when index already exists."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch = MagicMock()
        mock_opensearch.index_exists.return_value = True
        mock_opensearch_class.return_value = mock_opensearch

        setup.main(**base_setup_args)

        captured = capsys.readouterr()
        assert "already exists" in captured.out

    # ============================================================================
    # Setup Main Function - Error Handling
    # ============================================================================

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_handles_value_error(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test error handling for ValueError."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client
        mock_setup_opensearch.side_effect = ValueError("Invalid configuration")

        with pytest.raises(SystemExit) as exc_info:
            setup.main(**base_setup_args)

        assert exc_info.value.code == 1

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_handles_transport_error(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test error handling for TransportError."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client
        mock_setup_opensearch.side_effect = TransportError(500, "Connection failed")

        with pytest.raises(SystemExit) as exc_info:
            setup.main(**base_setup_args)

        assert exc_info.value.code == 1

    @patch("apps.cli.commands.setup.setup_opensearch")
    @patch("apps.cli.commands.setup.OpenSearchClient")
    @patch("apps.cli.commands.setup.get_aws_credentials")
    def test_setup_handles_general_exception(
        self,
        mock_get_credentials: Any,
        mock_opensearch_class: Any,
        mock_setup_opensearch: Any,
        mock_credentials: dict[str, str],
        mock_opensearch_client: Any,
        base_setup_args: dict[str, Any],
    ) -> None:
        """Test error handling for general exceptions."""
        mock_get_credentials.return_value = mock_credentials
        mock_opensearch_class.return_value = mock_opensearch_client
        mock_setup_opensearch.side_effect = Exception("Unexpected error")

        with pytest.raises(SystemExit) as exc_info:
            setup.main(**base_setup_args)

        assert exc_info.value.code == 1
