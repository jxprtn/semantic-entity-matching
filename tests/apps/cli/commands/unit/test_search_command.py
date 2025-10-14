"""
Unit tests for search CLI command.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.cli.commands import search
from lib.interfaces import SearchResults


@pytest.mark.unit
class TestSearchCommand:
    """Test search command functionality."""

    def test_command_definition(self) -> None:
        """Test that command definition is properly structured."""
        assert hasattr(search, "DEFINITION")
        assert "name" in search.DEFINITION
        assert search.DEFINITION["name"] == "search"
        assert "description" in search.DEFINITION
        assert "arguments" in search.DEFINITION

        # Check required arguments
        arg_names = [arg["name"] for arg in search.DEFINITION["arguments"]]
        assert "column" in arg_names
        assert "index" in arg_names
        assert "query" in arg_names
        assert "assume-role" in arg_names
        assert "embedding-column-suffix" in arg_names
        assert "filter-field" in arg_names
        assert "filter-value" in arg_names
        assert "opensearch-host" in arg_names
        assert "opensearch-port" in arg_names
        assert "profile" in arg_names
        assert "region" in arg_names

    def test_main_function_exists(self) -> None:
        """Test that main function exists and is callable."""
        assert hasattr(search, "main")
        assert callable(search.main)

    @patch("apps.cli.commands.search.search_and_rerank")
    @patch("apps.cli.commands.search.BedrockClient")
    @patch("apps.cli.commands.search.OpenSearchClient")
    @patch("apps.cli.commands.search.get_aws_credentials")
    def test_basic_search(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_bedrock_client: Any,
        mock_search_and_rerank: Any,
        capsys: Any,
    ) -> None:
        """Test basic search with mocked dependencies."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_client_instance.count_documents.return_value = 100
        mock_opensearch_client.return_value = mock_client_instance

        # Mock search_and_rerank response
        mock_search_response = {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {
                        "_source": {
                            "LOINC_NUM": "12345-6",
                            "LONG_COMMON_NAME": "Test result 1",
                        }
                    },
                    {
                        "_source": {
                            "LOINC_NUM": "12345-7",
                            "LONG_COMMON_NAME": "Test result 2",
                        }
                    },
                ],
            }
        }
        mock_rerank_response = {
            "results": [
                {"relevanceScore": 0.95, "index": 0},
                {"relevanceScore": 0.85, "index": 1},
            ]
        }
        # Create mock SearchResults object
        mock_search_results = SearchResults(hits=mock_search_response["hits"]["hits"], count=mock_search_response["hits"]["total"]["value"])
        
        mock_search_and_rerank.return_value = {
            "search_results": mock_search_results,
            "rerank_results": mock_rerank_response,
            "query": "test query",
            "sources": ["source1", "source2"],
        }

        # Call main function
        search.main(
            assume_role=None,
            column="LONG_COMMON_NAME",
            filter_field=None,
            filter_value=None,
            index="test-index",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            query="test query",
            region="us-east-1",
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

        # Verify search_and_rerank was called with correct parameters
        mock_search_and_rerank.assert_called_once()
        call_kwargs = mock_search_and_rerank.call_args[1]
        assert call_kwargs["column"] == "LONG_COMMON_NAME"
        assert call_kwargs["filters"] is None
        assert call_kwargs["index"] == "test-index"
        assert call_kwargs["opensearch"] == mock_client_instance
        assert call_kwargs["profile"] is None
        assert call_kwargs["query"] == "test query"
        assert call_kwargs["region"] == "us-east-1"
        assert call_kwargs["top_k"] == 50
        assert call_kwargs["embedding_column_suffix"] == "_embedding"

        # Verify output was printed
        captured = capsys.readouterr()
        assert "100 documents in index test-index" in captured.out
        assert "Target field:" in captured.out
        assert "Searching for:" in captured.out
        assert "test query" in captured.out
        assert "Found 5 results:" in captured.out

    @patch("apps.cli.commands.search.search_and_rerank")
    @patch("apps.cli.commands.search.BedrockClient")
    @patch("apps.cli.commands.search.OpenSearchClient")
    @patch("apps.cli.commands.search.get_aws_credentials")
    def test_search_with_filters(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_bedrock_client: Any,
        mock_search_and_rerank: Any,
        capsys: Any,
    ) -> None:
        """Test search with filter field and value."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_client_instance.count_documents.return_value = 50
        mock_opensearch_client.return_value = mock_client_instance
        
        # Mock BedrockClient
        mock_bedrock_instance = MagicMock()
        mock_bedrock_instance.close = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock_instance

        # Mock search_and_rerank response
        mock_search_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "LOINC_NUM": "12345-6",
                            "LONG_COMMON_NAME": "Filtered result 1",
                        }
                    }
                ],
            }
        }
        mock_rerank_response = {"results": [{"relevanceScore": 0.90, "index": 0}]}
        mock_search_results = SearchResults(hits=mock_search_response["hits"]["hits"], count=mock_search_response["hits"]["total"]["value"])
        
        mock_search_and_rerank.return_value = {
            "search_results": mock_search_results,
            "rerank_results": mock_rerank_response,
            "query": "test query",
            "sources": ["source1"],
        }

        # Call main function with filters
        search.main(
            assume_role=None,
            column="LONG_COMMON_NAME",
            filter_field="CLASS",
            filter_value="MICRO",
            index="test-index",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            query="test query",
            region="us-east-1",
        )

        # Verify search_and_rerank was called with filters
        mock_search_and_rerank.assert_called_once()
        call_kwargs = mock_search_and_rerank.call_args[1]
        assert call_kwargs["filters"] == [{"term": {"CLASS.keyword": "MICRO"}}]

        # Verify filters were printed
        captured = capsys.readouterr()
        assert "Filters:" in captured.out

    @patch("apps.cli.commands.search.search_and_rerank")
    @patch("apps.cli.commands.search.BedrockClient")
    @patch("apps.cli.commands.search.OpenSearchClient")
    @patch("apps.cli.commands.search.get_aws_credentials")
    def test_search_with_all_parameters(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_bedrock_client: Any,
        mock_search_and_rerank: Any,
    ) -> None:
        """Test search with all optional parameters."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        
        # Mock BedrockClient
        mock_bedrock_instance = MagicMock()
        mock_bedrock_instance.close = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock_instance
        mock_client_instance.count_documents.return_value = 200
        mock_opensearch_client.return_value = mock_client_instance

        from lib.interfaces import SearchResults
        mock_search_results = SearchResults(hits=[], count=0)
        
        mock_search_and_rerank.return_value = {
            "search_results": mock_search_results,
            "rerank_results": None,
            "query": "test query",
            "sources": [],
        }

        # Call main function with all parameters
        search.main(
            assume_role="arn:aws:iam::123456789012:role/test-role",
            column="LONG_COMMON_NAME",
            filter_field="CLASS",
            filter_value="MICRO",
            index="test-index",
            opensearch_host="opensearch.example.com",
            opensearch_port=443,
            profile="test-profile",
            query="test query",
            region="us-west-2",
        )

        # Verify parameters were passed correctly
        mock_get_credentials.assert_called_once_with(
            assume_role="arn:aws:iam::123456789012:role/test-role",
            profile="test-profile",
            region="us-west-2",
        )

        mock_opensearch_client.assert_called_once()
        call_kwargs_opensearch = mock_opensearch_client.call_args[1]
        assert call_kwargs_opensearch["credentials"] == mock_credentials
        assert call_kwargs_opensearch["host"] == "opensearch.example.com"
        assert call_kwargs_opensearch["port"] == 443
        assert call_kwargs_opensearch["region"] == "us-west-2"
        assert "reporter" in call_kwargs_opensearch


    def test_missing_query_error(self) -> None:
        """Test error handling for missing query parameter."""
        with pytest.raises(SystemExit):
            search.main(
                assume_role=None,
                column="LONG_COMMON_NAME",
                filter_field=None,
                filter_value=None,
                index="test-index",
                opensearch_host="localhost",
                opensearch_port=9200,
                profile=None,
                query="",  # Empty query
                region="us-east-1",
            )

    @patch("apps.cli.commands.search.search_and_rerank")
    @patch("apps.cli.commands.search.BedrockClient")
    @patch("apps.cli.commands.search.OpenSearchClient")
    @patch("apps.cli.commands.search.get_aws_credentials")
    def test_search_error_handling(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_bedrock_client: Any,
        mock_search_and_rerank: Any,
    ) -> None:
        """Test error handling when search_and_rerank raises an exception."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_client_instance.count_documents.return_value = 100
        mock_opensearch_client.return_value = mock_client_instance
        
        # Mock BedrockClient
        mock_bedrock_instance = MagicMock()
        mock_bedrock_instance.close = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock_instance

        # Mock search_and_rerank to raise an exception
        mock_search_and_rerank.side_effect = Exception("Search failed")

        # Call main function - should exit with error
        with pytest.raises(SystemExit):
            search.main(
                assume_role=None,
                column="LONG_COMMON_NAME",
                filter_field=None,
                filter_value=None,
                index="test-index",
                opensearch_host="localhost",
                opensearch_port=9200,
                profile=None,
                query="test query",
                region="us-east-1",
            )

    @patch("apps.cli.commands.search.search_and_rerank")
    @patch("apps.cli.commands.search.BedrockClient")
    @patch("apps.cli.commands.search.OpenSearchClient")
    @patch("apps.cli.commands.search.get_aws_credentials")
    def test_search_with_no_rerank_results(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_bedrock_client: Any,
        mock_search_and_rerank: Any,
        capsys: Any,
    ) -> None:
        """Test search when rerank returns None."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        mock_client_instance.count_documents.return_value = 100
        mock_opensearch_client.return_value = mock_client_instance
        
        # Mock BedrockClient
        mock_bedrock_instance = MagicMock()
        mock_bedrock_instance.close = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock_instance

        # Mock search_and_rerank response with no rerank results
        mock_search_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "LOINC_NUM": "12345-6",
                            "LONG_COMMON_NAME": "Test result",
                        }
                    }
                ],
            }
        }
        mock_search_results = SearchResults(hits=mock_search_response["hits"]["hits"], count=mock_search_response["hits"]["total"]["value"])
        
        mock_search_and_rerank.return_value = {
            "search_results": mock_search_results,
            "rerank_results": None,  # No rerank results
            "query": "test query",
            "sources": ["source1"],
        }

        # Call main function
        search.main(
            assume_role=None,
            column="LONG_COMMON_NAME",
            filter_field=None,
            filter_value=None,
            index="test-index",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            query="test query",
            region="us-east-1",
        )

        # Verify error message for failed rerank
        captured = capsys.readouterr()
        assert "Failed to get rerank results" in captured.out

    @patch("apps.cli.commands.search.search_and_rerank")
    @patch("apps.cli.commands.search.BedrockClient")
    @patch("apps.cli.commands.search.OpenSearchClient")
    @patch("apps.cli.commands.search.get_aws_credentials")
    def test_search_filter_without_value(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_bedrock_client: Any,
        mock_search_and_rerank: Any,
    ) -> None:
        """Test that filter is not applied when only filter_field is provided without filter_value."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        
        # Mock BedrockClient
        mock_bedrock_instance = MagicMock()
        mock_bedrock_instance.close = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock_instance
        mock_client_instance.count_documents.return_value = 100
        mock_opensearch_client.return_value = mock_client_instance

        from lib.interfaces import SearchResults
        mock_search_results = SearchResults(hits=[], count=0)
        
        mock_search_and_rerank.return_value = {
            "search_results": mock_search_results,
            "rerank_results": None,
            "query": "test query",
            "sources": [],
        }

        # Call main function with only filter_field (no filter_value)
        search.main(
            assume_role=None,
            column="LONG_COMMON_NAME",
            filter_field="CLASS",
            filter_value=None,  # No filter value
            index="test-index",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            query="test query",
            region="us-east-1",
        )

        # Verify filters is None (not applied)
        mock_search_and_rerank.assert_called_once()
        call_kwargs = mock_search_and_rerank.call_args[1]
        assert call_kwargs["filters"] is None

    @patch("apps.cli.commands.search.search_and_rerank")
    @patch("apps.cli.commands.search.BedrockClient")
    @patch("apps.cli.commands.search.OpenSearchClient")
    @patch("apps.cli.commands.search.get_aws_credentials")
    def test_search_with_custom_embedding_column_suffix(
        self,
        mock_get_credentials: Any,
        mock_opensearch_client: Any,
        mock_bedrock_client: Any,
        mock_search_and_rerank: Any,
    ) -> None:
        """Test that custom embedding_column_suffix is passed correctly."""
        # Setup mocks
        mock_credentials = {"access_key": "test", "secret_key": "test"}
        mock_get_credentials.return_value = mock_credentials
        mock_client_instance = MagicMock()
        
        # Mock BedrockClient
        mock_bedrock_instance = MagicMock()
        mock_bedrock_instance.close = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock_instance
        mock_client_instance.count_documents.return_value = 100
        mock_opensearch_client.return_value = mock_client_instance

        from lib.interfaces import SearchResults
        mock_search_results = SearchResults(hits=[], count=0)
        
        mock_search_and_rerank.return_value = {
            "search_results": mock_search_results,
            "rerank_results": None,
            "query": "test query",
            "sources": [],
        }

        # Call main function with custom embedding_column_suffix
        search.main(
            assume_role=None,
            column="LONG_COMMON_NAME",
            embedding_column_suffix="_vector",  # Custom suffix
            filter_field=None,
            filter_value=None,
            index="test-index",
            opensearch_host="localhost",
            opensearch_port=9200,
            profile=None,
            query="test query",
            region="us-east-1",
        )

        # Verify embedding_column_suffix was passed correctly
        mock_search_and_rerank.assert_called_once()
        call_kwargs = mock_search_and_rerank.call_args[1]
        assert call_kwargs["embedding_column_suffix"] == "_vector"

