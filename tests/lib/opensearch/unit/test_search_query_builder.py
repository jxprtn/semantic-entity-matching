"""Unit tests for QueryBuilder class."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from lib.opensearch.client import OpenSearchClient
from lib.opensearch.services import SearchQuery, SearchQueryBuilder
from lib.opensearch.services.search_service import SearchService


@pytest.mark.unit
class TestSearchQueryBuilder:
    """Tests for SearchQueryBuilder class."""

    def test_init_with_index(self) -> None:
        """Test SearchQueryBuilder initialization with an index name."""
        index_name = "test-index"

        builder = SearchQueryBuilder(index=index_name)

        # Verify the index was stored
        assert builder._index == index_name

    def test_build_returns_empty_query(self) -> None:
        """Test that build() returns a SearchQuery object."""
        builder = SearchQueryBuilder(index="test-index")

        query = builder.build()

        # Verify build returns a SearchQuery object
        assert isinstance(query, SearchQuery)
        # Initially, query body should contain match_all (no query methods called)
        assert query.body is not None
        assert "query" in query.body
        assert query.body["query"] == {"match_all": {}}
        assert query.index == "test-index"

    def test_query_builder_with_client_request(
        self, opensearch_client: OpenSearchClient, mock_opensearch_client: MagicMock
    ) -> None:
        """Test using SearchQueryBuilder with SearchService.query() for search."""
        index_name = "test-index"
        builder = SearchQueryBuilder(index=index_name)

        # Build the query (match_all by default)
        query = builder.build()
        assert isinstance(query, SearchQuery)

        # Mock the search method response
        mock_response: dict[str, Any] = {
            "hits": {
                "hits": [],
                "total": {"value": 0},
            }
        }
        # Create a real SearchService instance with the mocked client
        search_service = SearchService(client=opensearch_client._client)
        opensearch_client._client.search = MagicMock(return_value=mock_response)

        # Use the search service's query method
        response = search_service.query(query)

        # Verify the search was made correctly
        opensearch_client._client.search.assert_called_once_with(
            index=index_name,
            body=query.body,
            params=query.params,
        )
        # Verify the response is a SearchResult
        from lib.interfaces import SearchResults

        assert isinstance(response, SearchResults)
        assert response.hits == []
        assert response.count == 0

    def test_match_sets_query_body(self) -> None:
        """Test that match() sets the query body correctly."""
        builder = SearchQueryBuilder(index="test-index")

        builder.match(field="title", value="test query")

        query = builder.build()

        # Verify the query body contains the match query
        assert query.body is not None
        assert "query" in query.body
        assert query.body["query"] == {"match": {"title": "test query"}}
        assert query.index == "test-index"

    def test_match_adds_field_to_fields_list(self) -> None:
        """Test that match() sets the query correctly."""
        builder = SearchQueryBuilder(index="test-index")

        builder.match(field="title", value="test query")

        # Verify the query was set correctly
        assert builder._query == {"match": {"title": "test query"}}

    def test_match_returns_self_for_chaining(self) -> None:
        """Test that match() returns self for method chaining."""
        builder = SearchQueryBuilder(index="test-index")

        result = builder.match(field="title", value="test query")

        # Verify method chaining works
        assert result is builder
        # Verify we can chain methods
        chained = builder.match(field="description", value="another query").build()
        assert chained.body is not None
        # The last match() call overwrites the previous one
        assert chained.body["query"] == {"match": {"description": "another query"}}

    def test_match_with_different_fields(self) -> None:
        """Test match() with different field names."""
        builder = SearchQueryBuilder(index="test-index")

        builder.match(field="name", value="John Doe")
        query = builder.build()

        assert query.body is not None
        assert query.body["query"] == {"match": {"name": "John Doe"}}

    def test_match_exactly_sets_term_query(self) -> None:
        """Test that match_exactly() sets the term query correctly."""
        builder = SearchQueryBuilder(index="test-index")

        builder.match_exactly(field="code", value="ABC123")

        query = builder.build()

        # Verify the query body contains the term query
        assert query.body is not None
        assert query.body["query"] == {"term": {"code.keyword": "ABC123"}}
        assert query.index == "test-index"

    def test_match_exactly_uses_keyword_field(self) -> None:
        """Test that match_exactly() uses .keyword suffix for exact matching."""
        builder = SearchQueryBuilder(index="test-index")

        builder.match_exactly(field="status", value="active")
        query = builder.build()

        assert query.body is not None
        # Verify it uses .keyword suffix
        assert "term" in query.body["query"]
        assert "status.keyword" in query.body["query"]["term"]
        assert query.body["query"]["term"]["status.keyword"] == "active"

    def test_match_exactly_returns_self_for_chaining(self) -> None:
        """Test that match_exactly() returns self for method chaining."""
        builder = SearchQueryBuilder(index="test-index")

        result = builder.match_exactly(field="code", value="XYZ789")

        # Verify method chaining works
        assert result is builder
        # Verify we can chain methods
        chained = builder.match_exactly(field="id", value="12345").build()
        assert chained.body is not None
        # The last match_exactly() call overwrites the previous one
        assert chained.body["query"] == {"term": {"id.keyword": "12345"}}

    def test_match_exactly_with_different_fields(self) -> None:
        """Test match_exactly() with different field names."""
        builder = SearchQueryBuilder(index="test-index")

        builder.match_exactly(field="sku", value="PROD-001")
        query = builder.build()

        assert query.body is not None
        assert query.body["query"] == {"term": {"sku.keyword": "PROD-001"}}

    def test_match_exactly_different_from_match(self) -> None:
        """Test that match_exactly() uses term query while match() uses match query."""
        # Test match() - build immediately to capture the state
        builder1 = SearchQueryBuilder(index="test-index")
        builder1.match(field="title", value="test")
        query1 = builder1.build()

        # Verify match() uses match query
        assert query1.body is not None
        assert query1.body["query"] == {"match": {"title": "test"}}

        # Test match_exactly() separately - each instance has its own state
        builder2 = SearchQueryBuilder(index="test-index")
        builder2.match_exactly(field="title", value="test")
        query2 = builder2.build()

        # Verify match_exactly() uses term query with .keyword
        assert query2.body is not None
        assert query2.body["query"] == {"term": {"title.keyword": "test"}}

    def test_instances_do_not_share_state(self) -> None:
        """Test that different SearchQueryBuilder instances have independent state."""
        builder1 = SearchQueryBuilder(index="index1")
        builder2 = SearchQueryBuilder(index="index2")

        # Configure builder1
        builder1.match(field="field1", value="value1")
        builder1.add_filter({"term": {"status": "active"}})
        builder1.exclude_fields(["secret"])

        # Configure builder2
        builder2.match_exactly(field="field2", value="value2")
        builder2.limit_results(20)

        # Verify builder1's state is independent
        query1 = builder1.build()
        assert query1.body is not None
        assert query1.body["query"]["bool"]["must"][0] == {"match": {"field1": "value1"}}
        assert query1.index == "index1"
        assert len(builder1._filters) == 1
        assert "secret" in builder1._exclude_fields

        # Verify builder2's state is independent
        query2 = builder2.build()
        assert query2.body is not None
        assert query2.body["query"] == {"term": {"field2.keyword": "value2"}}
        assert query2.index == "index2"
        assert len(builder2._filters) == 0  # builder2 has no filters
        assert len(builder2._exclude_fields) == 0  # builder2 has no excluded fields
        assert builder2._size == 20

    def test_add_filter_adds_single_filter(self) -> None:
        """Test that add_filter() adds a single filter to the filters list."""
        builder = SearchQueryBuilder(index="test-index")

        filter_dict = {"term": {"status": "active"}}
        builder.add_filter(filter_dict)

        # Verify the filter was added
        assert len(builder._filters) == 1
        assert builder._filters[0] == filter_dict

    def test_add_filter_returns_self_for_chaining(self) -> None:
        """Test that add_filter() returns self for method chaining."""
        builder = SearchQueryBuilder(index="test-index")

        result = builder.add_filter({"term": {"status": "active"}})

        # Verify method chaining works
        assert result is builder
        # Verify we can chain methods
        builder.add_filter({"term": {"category": "tech"}}).build()
        assert len(builder._filters) == 2

    def test_add_filter_calls_add_filters(self) -> None:
        """Test that add_filter() internally calls add_filters()."""
        builder = SearchQueryBuilder(index="test-index")

        filter_dict = {"term": {"status": "active"}}
        builder.add_filter(filter_dict)

        # Verify it was added via add_filters (should be in the list)
        assert len(builder._filters) == 1
        assert builder._filters[0] == filter_dict

    def test_add_filters_adds_multiple_filters(self) -> None:
        """Test that add_filters() adds multiple filters to the filters list."""
        builder = SearchQueryBuilder(index="test-index")

        filters = [
            {"term": {"status": "active"}},
            {"term": {"category": "tech"}},
            {"range": {"price": {"gte": 100}}},
        ]
        builder.add_filters(filters)

        # Verify all filters were added
        assert len(builder._filters) == 3
        assert builder._filters == filters

    def test_add_filters_returns_self_for_chaining(self) -> None:
        """Test that add_filters() returns self for method chaining."""
        builder = SearchQueryBuilder(index="test-index")

        result = builder.add_filters([{"term": {"status": "active"}}])

        # Verify method chaining works
        assert result is builder
        # Verify we can chain methods
        builder.add_filters([{"term": {"category": "tech"}}]).build()
        assert len(builder._filters) == 2

    def test_add_filters_extends_existing_filters(self) -> None:
        """Test that add_filters() extends the existing filters list."""
        builder = SearchQueryBuilder(index="test-index")

        # Add initial filters
        builder.add_filters([{"term": {"status": "active"}}])
        assert len(builder._filters) == 1

        # Add more filters
        builder.add_filters([{"term": {"category": "tech"}}, {"range": {"price": {"gte": 100}}}])
        assert len(builder._filters) == 3
        assert builder._filters[0] == {"term": {"status": "active"}}
        assert builder._filters[1] == {"term": {"category": "tech"}}
        assert builder._filters[2] == {"range": {"price": {"gte": 100}}}

    def test_add_filter_and_add_filters_work_together(self) -> None:
        """Test that add_filter() and add_filters() can be used together."""
        builder = SearchQueryBuilder(index="test-index")

        # Use both methods
        builder.add_filter({"term": {"status": "active"}})
        builder.add_filters([{"term": {"category": "tech"}}, {"range": {"price": {"gte": 100}}}])

        # Verify all filters were added
        assert len(builder._filters) == 3
        assert builder._filters[0] == {"term": {"status": "active"}}
        assert builder._filters[1] == {"term": {"category": "tech"}}
        assert builder._filters[2] == {"range": {"price": {"gte": 100}}}

    def test_add_filters_with_empty_list(self) -> None:
        """Test that add_filters() handles an empty list gracefully."""
        builder = SearchQueryBuilder(index="test-index")

        builder.add_filters([])

        # Verify no filters were added
        assert len(builder._filters) == 0

    def test_add_filters_with_various_filter_types(self) -> None:
        """Test add_filters() with different types of OpenSearch filters."""
        builder = SearchQueryBuilder(index="test-index")

        filters = [
            {"term": {"status": "active"}},  # Term filter
            {"range": {"age": {"gte": 18, "lte": 65}}},  # Range filter
            {"exists": {"field": "email"}},  # Exists filter
            {"bool": {"must": [{"term": {"verified": True}}]}},  # Bool filter
        ]
        builder.add_filters(filters)

        # Verify all filters were added
        assert len(builder._filters) == 4
        assert builder._filters == filters

    def test_add_filter_chaining(self) -> None:
        """Test chaining multiple add_filter() calls."""
        builder = SearchQueryBuilder(index="test-index")

        builder.add_filter({"term": {"status": "active"}}).add_filter(
            {"term": {"category": "tech"}}
        ).add_filter({"range": {"price": {"gte": 100}}})

        # Verify all filters were added
        assert len(builder._filters) == 3
        assert builder._filters[0] == {"term": {"status": "active"}}
        assert builder._filters[1] == {"term": {"category": "tech"}}
        assert builder._filters[2] == {"range": {"price": {"gte": 100}}}

    def test_build_with_filters_and_query(self) -> None:
        """Test that build() incorporates filters into query body when both query and filters exist."""
        builder = SearchQueryBuilder(index="test-index")
        builder.match(field="title", value="test")
        builder.add_filter({"term": {"status": "active"}})

        query = builder.build()

        # Verify filters are incorporated into bool query
        assert query.body is not None
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "must" in query.body["query"]["bool"]
        assert "filter" in query.body["query"]["bool"]
        assert query.body["query"]["bool"]["must"][0] == {"match": {"title": "test"}}
        assert query.body["query"]["bool"]["filter"] == [{"term": {"status": "active"}}]

    def test_build_with_filters_only(self) -> None:
        """Test that build() incorporates filters with match_all when only filters exist."""
        builder = SearchQueryBuilder(index="test-index")
        builder.add_filter({"term": {"status": "active"}})

        query = builder.build()

        # Verify filters are incorporated into bool query with match_all
        assert query.body is not None
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "must" in query.body["query"]["bool"]
        assert "filter" in query.body["query"]["bool"]
        assert query.body["query"]["bool"]["must"][0] == {"match_all": {}}
        assert query.body["query"]["bool"]["filter"] == [{"term": {"status": "active"}}]

    def test_build_with_multiple_filters(self) -> None:
        """Test that build() incorporates multiple filters correctly."""
        builder = SearchQueryBuilder(index="test-index")
        builder.match(field="title", value="test")
        builder.add_filters(
            [
                {"term": {"status": "active"}},
                {"range": {"price": {"gte": 100}}},
            ]
        )

        query = builder.build()

        # Verify all filters are incorporated
        assert query.body is not None
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "filter" in query.body["query"]["bool"]
        assert len(query.body["query"]["bool"]["filter"]) == 2
        assert query.body["query"]["bool"]["filter"] == [
            {"term": {"status": "active"}},
            {"range": {"price": {"gte": 100}}},
        ]

    def test_build_with_query_only_no_filters(self) -> None:
        """Test that build() works correctly with query but no filters."""
        builder = SearchQueryBuilder(index="test-index")
        builder.match(field="title", value="test")

        query = builder.build()

        # Verify query is used directly without bool wrapper
        assert query.body is not None
        assert "query" in query.body
        assert "match" in query.body["query"]
        assert query.body["query"]["match"]["title"] == "test"
        assert "bool" not in query.body["query"]

    def test_build_with_match_exactly_and_filters(self) -> None:
        """Test that build() incorporates filters with match_exactly query."""
        builder = SearchQueryBuilder(index="test-index")
        builder.match_exactly(field="code", value="ABC123")
        builder.add_filter({"term": {"status": "active"}})

        query = builder.build()

        # Verify filters are incorporated into bool query
        assert query.body is not None
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "must" in query.body["query"]["bool"]
        assert "filter" in query.body["query"]["bool"]
        assert query.body["query"]["bool"]["must"][0] == {"term": {"code.keyword": "ABC123"}}
        assert query.body["query"]["bool"]["filter"] == [{"term": {"status": "active"}}]

    def test_exclude_fields_adds_fields_to_list(self) -> None:
        """Test that exclude_fields() adds fields to the _exclude_fields list."""
        builder = SearchQueryBuilder(index="test-index")

        builder.exclude_fields(["description", "metadata"])

        # Verify fields were added
        assert len(builder._exclude_fields) == 2
        assert "description" in builder._exclude_fields
        assert "metadata" in builder._exclude_fields

    def test_exclude_fields_returns_self_for_chaining(self) -> None:
        """Test that exclude_fields() returns self for method chaining."""
        builder = SearchQueryBuilder(index="test-index")

        result = builder.exclude_fields(["description"])

        # Verify method chaining works
        assert result is builder
        # Verify we can chain methods
        builder.exclude_fields(["metadata"]).build()
        assert len(builder._exclude_fields) == 2

    def test_exclude_fields_extends_existing_fields(self) -> None:
        """Test that exclude_fields() extends the existing _exclude_fields list."""
        builder = SearchQueryBuilder(index="test-index")

        # Add initial fields
        builder.exclude_fields(["description"])
        assert len(builder._exclude_fields) == 1

        # Add more fields
        builder.exclude_fields(["metadata", "tags"])
        assert len(builder._exclude_fields) == 3
        assert builder._exclude_fields[0] == "description"
        assert builder._exclude_fields[1] == "metadata"
        assert builder._exclude_fields[2] == "tags"

    def test_build_with_exclude_fields_and_query(self) -> None:
        """Test that build() incorporates exclude_fields into query body when query exists."""
        builder = SearchQueryBuilder(index="test-index")
        builder.match(field="title", value="test")
        builder.exclude_fields(["description", "metadata"])

        query = builder.build()

        # Verify exclude_fields are incorporated into _source
        assert query.body is not None
        assert "_source" in query.body
        assert "excludes" in query.body["_source"]
        assert query.body["_source"]["excludes"] == ["description", "metadata"]

    def test_build_with_exclude_fields_only(self) -> None:
        """Test that build() incorporates exclude_fields with match_all when only exclude_fields exist."""
        builder = SearchQueryBuilder(index="test-index")
        builder.exclude_fields(["description"])

        query = builder.build()

        # Verify exclude_fields are incorporated with match_all query
        assert query.body is not None
        assert "query" in query.body
        assert query.body["query"] == {"match_all": {}}
        assert "_source" in query.body
        assert "excludes" in query.body["_source"]
        assert query.body["_source"]["excludes"] == ["description"]

    def test_build_with_exclude_fields_and_filters(self) -> None:
        """Test that build() incorporates exclude_fields with filters."""
        builder = SearchQueryBuilder(index="test-index")
        builder.add_filter({"term": {"status": "active"}})
        builder.exclude_fields(["description"])

        query = builder.build()

        # Verify exclude_fields are incorporated with filters
        assert query.body is not None
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "_source" in query.body
        assert "excludes" in query.body["_source"]
        assert query.body["_source"]["excludes"] == ["description"]

    def test_build_with_exclude_fields_query_and_filters(self) -> None:
        """Test that build() incorporates exclude_fields with both query and filters."""
        builder = SearchQueryBuilder(index="test-index")
        builder.match(field="title", value="test")
        builder.add_filter({"term": {"status": "active"}})
        builder.exclude_fields(["description", "metadata"])

        query = builder.build()

        # Verify exclude_fields are incorporated with query and filters
        assert query.body is not None
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "_source" in query.body
        assert "excludes" in query.body["_source"]
        assert query.body["_source"]["excludes"] == ["description", "metadata"]

    def test_build_without_exclude_fields(self) -> None:
        """Test that build() doesn't add _source when no exclude_fields are specified."""
        builder = SearchQueryBuilder(index="test-index")
        builder.match(field="title", value="test")

        query = builder.build()

        # Verify _source is not added when no exclude_fields
        assert query.body is not None
        assert "_source" not in query.body

    def test_exclude_fields_with_empty_list(self) -> None:
        """Test that exclude_fields() handles an empty list gracefully."""
        builder = SearchQueryBuilder(index="test-index")

        builder.exclude_fields([])

        # Verify no fields were added
        assert len(builder._exclude_fields) == 0
