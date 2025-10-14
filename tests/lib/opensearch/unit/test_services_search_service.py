"""Unit tests for SearchService class."""

from unittest.mock import MagicMock

import pytest

from lib.interfaces import SearchResults
from lib.opensearch.services.search_query_builder import SearchQueryBuilder
from lib.opensearch.services.search_service import SearchService


@pytest.mark.unit
class TestSearchService:
    """Tests for SearchService class."""

    def test_init_with_client(self) -> None:
        """Test SearchService initialization with a client."""
        mock_client = MagicMock()

        service = SearchService(client=mock_client)

        # Verify service was initialized with the client
        assert service._client == mock_client

    def test_query_executes_search_with_correct_params(self) -> None:
        """Test that query() executes search with correct parameters."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        service = SearchService(client=mock_client)

        query = SearchQueryBuilder(index="test-index").match(field="title", value="test query").use_pipeline("test-pipeline").build()
        result = service.query(query)

        # Verify search was called with correct parameters
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args

        assert call_args.kwargs["index"] == "test-index"
        assert call_args.kwargs["params"]["search_pipeline"] == "test-pipeline"
        assert call_args.kwargs["body"]["query"]["match"]["title"] == "test query"
        assert isinstance(result, SearchResults)
        assert result.hits == []
        assert result.count == 0

    def test_query_with_vector_search(self) -> None:
        """Test that query() executes search with correct vector parameters."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        # Create a mock embedding vector
        mock_embedding = [0.1, 0.2, 0.3, 0.4] * 256  # 1024 dimensions

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match_knn(field="title_embedding", value=mock_embedding)
            .limit_results(10)
            .build()
        )
        result = service.query(query)

        # Verify search was called with correct knn query
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args

        assert call_args.kwargs["index"] == "test-index"
        assert call_args.kwargs["body"]["size"] == 10
        assert call_args.kwargs["body"]["query"]["knn"]["title_embedding"]["vector"] == mock_embedding
        assert call_args.kwargs["body"]["query"]["knn"]["title_embedding"]["k"] == 20  # size * 2
        assert isinstance(result, SearchResults)

    def test_query_with_vector_and_filters(self) -> None:
        """Test that query() includes filters in the query when provided."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        mock_embedding = [0.1, 0.2, 0.3] * 341  # 1023 dimensions, close to 1024

        filters = [{"term": {"category": "test"}}]

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match_knn(field="title_embedding", value=mock_embedding)
            .add_filters(filters)
            .limit_results(5)
            .build()
        )
        service.query(query)

        # Verify filter was included in the bool query
        call_args = mock_client.search.call_args
        assert "bool" in call_args.kwargs["body"]["query"]
        assert "filter" in call_args.kwargs["body"]["query"]["bool"]
        assert call_args.kwargs["body"]["query"]["bool"]["filter"] == filters

    def test_query_with_vector_and_exclude_fields(self) -> None:
        """Test that query() excludes fields when provided."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        mock_embedding = [0.1, 0.2, 0.3] * 341

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match_knn(field="title_embedding", value=mock_embedding)
            .exclude_fields(["description", "metadata"])
            .limit_results(10)
            .build()
        )
        service.query(query)

        # Verify _source excludes were included
        call_args = mock_client.search.call_args
        assert call_args.kwargs["body"]["_source"]["excludes"] == ["description", "metadata"]

    def test_query_with_vector_without_filters_or_excludes(self) -> None:
        """Test that query() works without optional parameters."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        mock_embedding = [0.1, 0.2, 0.3] * 341

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match_knn(field="title_embedding", value=mock_embedding)
            .limit_results(10)
            .build()
        )
        service.query(query)

        # Verify _source and filter are not included when not provided
        call_args = mock_client.search.call_args
        assert "_source" not in call_args.kwargs["body"]
        assert "bool" not in call_args.kwargs["body"]["query"]

    def test_query_with_keyword_match(self) -> None:
        """Test that query() uses match query for keyword search."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match(field="title", value="test query")
            .limit_results(10)
            .build()
        )
        result = service.query(query)

        # Verify search was called with match query
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args

        assert call_args.kwargs["index"] == "test-index"
        assert call_args.kwargs["body"]["query"]["match"]["title"] == "test query"
        assert call_args.kwargs["body"]["size"] == 10
        assert isinstance(result, SearchResults)

    def test_query_with_keyword_exact_match(self) -> None:
        """Test that query() uses term query for exact match."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match_exactly(field="title", value="exact value")
            .limit_results(5)
            .build()
        )
        result = service.query(query)

        # Verify search was called with term query
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args

        assert call_args.kwargs["index"] == "test-index"
        assert call_args.kwargs["body"]["query"]["term"]["title.keyword"] == "exact value"
        assert call_args.kwargs["body"]["size"] == 5
        assert isinstance(result, SearchResults)

    def test_query_with_keyword_and_exclude_fields(self) -> None:
        """Test that query() excludes fields when provided."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match(field="title", value="test query")
            .exclude_fields(["description", "metadata"])
            .limit_results(10)
            .build()
        )
        service.query(query)

        # Verify _source excludes were included
        call_args = mock_client.search.call_args
        assert call_args.kwargs["body"]["_source"]["excludes"] == ["description", "metadata"]

    def test_query_with_keyword_and_empty_exclude_fields(self) -> None:
        """Test that query() handles empty exclude_fields list."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        service = SearchService(client=mock_client)

        query = (
            SearchQueryBuilder(index="test-index")
            .match(field="title", value="test query")
            .exclude_fields([])
            .limit_results(10)
            .build()
        )
        service.query(query)

        # Verify _source is not added when exclude_fields is empty
        call_args = mock_client.search.call_args
        assert "_source" not in call_args.kwargs["body"]

    def test_query_with_keyword_default_size(self) -> None:
        """Test that query() works without size limit."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        service = SearchService(client=mock_client)

        query = SearchQueryBuilder(index="test-index").match(field="title", value="test query").build()
        service.query(query)

        # Verify size is not set when not specified
        call_args = mock_client.search.call_args
        assert "size" not in call_args.kwargs["body"]

    def test_query_with_vector_custom_size_affects_k(self) -> None:
        """Test that query() size parameter affects the k value in knn query."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        mock_embedding = [0.1, 0.2, 0.3] * 341

        service = SearchService(client=mock_client)

        # Test with size=5, should result in k=10 (size * 2)
        # Note: limit_results() must be called before match_knn() for k to be calculated correctly
        query = (
            SearchQueryBuilder(index="test-index")
            .limit_results(5)
            .match_knn(field="title_embedding", value=mock_embedding)
            .build()
        )
        service.query(query)

        call_args = mock_client.search.call_args
        assert call_args.kwargs["body"]["size"] == 5
        assert call_args.kwargs["body"]["query"]["knn"]["title_embedding"]["k"] == 10

        # Test with size=20, should result in k=40 (size * 2)
        query = (
            SearchQueryBuilder(index="test-index")
            .limit_results(20)
            .match_knn(field="title_embedding", value=mock_embedding)
            .build()
        )
        service.query(query)

        call_args = mock_client.search.call_args
        assert call_args.kwargs["body"]["size"] == 20
        assert call_args.kwargs["body"]["query"]["knn"]["title_embedding"]["k"] == 40
