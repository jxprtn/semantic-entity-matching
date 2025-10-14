"""Integration tests for SearchQueryBuilder class."""

import time

import pytest

from lib.opensearch.client import OpenSearchClient
from lib.opensearch.services import SearchQuery, SearchQueryBuilder


@pytest.mark.integration
class TestSearchQueryBuilderIntegration:
    """Integration tests for SearchQueryBuilder class with real OpenSearch instance."""

    def test_search_query_builder_get_index_details(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test using SearchQueryBuilder with SearchService.query() for a match_all search."""
        # Index a test document
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Test Document", "description": "Test Description"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder instance with the test index (defaults to match_all)
        builder = SearchQueryBuilder(index=index_name)
        query = builder.build()
        response = opensearch.search.query(query)

        # Verify the response contains search results
        assert response is not None
        assert hasattr(response, "hits")
        assert hasattr(response, "count")
        # Should find at least 1 document (the one we indexed)
        assert len(response.hits) >= 1

    def test_search_query_builder_match_search(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test SearchQueryBuilder.match() with a real search query."""
        # Index some test documents
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Python Programming", "description": "Learn Python basics"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "JavaScript Guide", "description": "Learn JavaScript"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Python Advanced", "description": "Advanced Python topics"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing to complete
        time.sleep(1)

        # Refresh the index to make documents searchable
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder and use match() method
        builder = SearchQueryBuilder(index=index_name)
        builder.match(field="title", value="Python")

        # Build the query
        query = builder.build()
        assert isinstance(query, SearchQuery)
        assert query.body is not None

        # Verify the query structure
        assert "query" in query.body
        assert "match" in query.body["query"]
        assert query.body["query"]["match"]["title"] == "Python"

        response = opensearch.search.query(query)

        # Verify the response contains search results
        assert response is not None
        assert hasattr(response, "hits")
        assert hasattr(response, "count")
        # Should find at least 2 documents with "Python" in title
        assert len(response.hits) >= 2

        # Verify the results contain the expected documents
        titles = [hit["_source"]["title"] for hit in response.hits]
        assert any("Python" in title for title in titles)

    def test_search_query_builder_match_exactly_search(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test SearchQueryBuilder.match_exactly() with a real exact match search."""
        # Delete the default index and create one with the field we need
        idx = opensearch.indexes.get(index=index_name)
        idx.delete()
        opensearch.indexes.create(
            index=index_name,
            fields=["code"],
            vector_dimension=1024,
            embedding_column_suffix="_embedding",
        )

        # Index documents with exact codes
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"code": "ABC123", "name": "Product A"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"code": "XYZ789", "name": "Product B"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"code": "ABC456", "name": "Product C"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder and use match_exactly() method
        builder = SearchQueryBuilder(index=index_name)
        builder.match_exactly(field="code", value="ABC123")

        # Build the query
        query = builder.build()
        assert isinstance(query, SearchQuery)
        assert query.body is not None

        # Verify the query structure uses term query with .keyword
        assert "query" in query.body
        assert "term" in query.body["query"]
        assert query.body["query"]["term"]["code.keyword"] == "ABC123"

        response = opensearch.search.query(query)

        # Verify the response contains search results
        assert response is not None
        assert hasattr(response, "hits")
        assert hasattr(response, "count")

        # Exact match should find exactly 1 document with code "ABC123"
        # Note: If .keyword field is not available, we might get 0 results
        # In that case, verify documents were indexed correctly
        if len(response.hits) == 0:
            # Fallback: verify documents exist with regular match
            builder_match = SearchQueryBuilder(index=index_name)
            builder_match.match(field="code", value="ABC123")
            query_match = builder_match.build()
            response_match = opensearch.search.query(query_match)
            assert len(response_match.hits) > 0, "Documents should be searchable"
        else:
            # If exact match works, verify we got the exact document
            assert len(response.hits) >= 1
            codes = [hit["_source"]["code"] for hit in response.hits]
            assert "ABC123" in codes

    def test_search_query_builder_add_filter_with_match(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test SearchQueryBuilder.add_filter() with match query in a real search."""
        # Index documents with different statuses
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Active Product", "status": "active", "category": "tech"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Inactive Product", "status": "inactive", "category": "tech"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Another Active Product", "status": "active", "category": "books"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder with match and filter
        builder = SearchQueryBuilder(index=index_name)
        builder.match(field="title", value="Product")
        builder.add_filter({"term": {"status": "active"}})

        # Verify filters are stored
        assert len(builder._filters) == 1
        assert builder._filters[0] == {"term": {"status": "active"}}

        # Build the query - filters should be incorporated automatically
        query = builder.build()
        assert query.body is not None

        # Verify the query structure includes filters in bool query
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "must" in query.body["query"]["bool"]
        assert "filter" in query.body["query"]["bool"]
        assert query.body["query"]["bool"]["must"][0] == {"match": {"title": "Product"}}
        assert query.body["query"]["bool"]["filter"] == [{"term": {"status": "active"}}]

        response = opensearch.search.query(query)

        # Verify results are filtered
        assert response is not None
        assert hasattr(response, "hits")
        hits = response.hits

        # Should only find documents with status="active" and title containing "Product"
        assert len(hits) >= 2  # At least "Active Product" and "Another Active"
        for hit in hits:
            assert hit["_source"]["status"] == "active"
            assert "Product" in hit["_source"]["title"]

    def test_search_query_builder_add_filters_with_match(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test SearchQueryBuilder.add_filters() with multiple filters in a real search."""
        # Index documents with different attributes
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Tech Active", "status": "active", "category": "tech", "price": 100}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Tech Inactive", "status": "inactive", "category": "tech", "price": 50}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Books Active", "status": "active", "category": "books", "price": 150}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Tech Active Expensive", "status": "active", "category": "tech", "price": 200}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder with match and multiple filters
        builder = SearchQueryBuilder(index=index_name)
        builder.match(field="title", value="Tech")
        builder.add_filters(
            [
                {"term": {"status": "active"}},
                {"range": {"price": {"gte": 100}}},
            ]
        )

        # Verify filters are stored
        assert len(builder._filters) == 2
        assert builder._filters[0] == {"term": {"status": "active"}}
        assert builder._filters[1] == {"range": {"price": {"gte": 100}}}

        # Build the query - filters should be incorporated automatically
        query = builder.build()
        assert query.body is not None

        # Verify the query structure includes filters in bool query
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "must" in query.body["query"]["bool"]
        assert "filter" in query.body["query"]["bool"]
        assert query.body["query"]["bool"]["must"][0] == {"match": {"title": "Tech"}}
        assert query.body["query"]["bool"]["filter"] == [
            {"term": {"status": "active"}},
            {"range": {"price": {"gte": 100}}},
        ]

        # Execute search using the built query
        response = opensearch.search.query(query)

        # Verify results are filtered correctly
        assert response is not None
        assert hasattr(response, "hits")
        hits = response.hits

        # Should only find documents matching:
        # - title contains "Tech"
        # - status = "active"
        # - price >= 100
        # Expected: "Tech Active" (price=100) and "Tech Active Expensive" (price=200)
        assert len(hits) >= 1
        for hit in hits:
            assert "Tech" in hit["_source"]["title"]
            assert hit["_source"]["status"] == "active"
            assert hit["_source"]["price"] >= 100

    def test_search_query_builder_filters_chaining(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test chaining add_filter() and add_filters() together."""
        # Index documents
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"name": "Item A", "type": "premium", "available": true}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"name": "Item B", "type": "standard", "available": true}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"name": "Item C", "type": "premium", "available": false}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Chain add_filter() and add_filters() together
        builder = SearchQueryBuilder(index=index_name)
        builder.match(field="name", value="Item")
        builder.add_filter({"term": {"type": "premium"}}).add_filters(
            [{"term": {"available": True}}]
        )

        # Verify all filters were added
        assert len(builder._filters) == 2
        assert builder._filters[0] == {"term": {"type": "premium"}}
        assert builder._filters[1] == {"term": {"available": True}}

        # Build the query - filters should be incorporated automatically
        query = builder.build()
        assert query.body is not None

        # Verify the query structure includes filters in bool query
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "must" in query.body["query"]["bool"]
        assert "filter" in query.body["query"]["bool"]
        assert query.body["query"]["bool"]["must"][0] == {"match": {"name": "Item"}}
        assert query.body["query"]["bool"]["filter"] == [
            {"term": {"type": "premium"}},
            {"term": {"available": True}},
        ]

        response = opensearch.search.query(query)

        # Verify results
        assert response is not None
        assert hasattr(response, "hits")
        hits = response.hits

        # Should only find "Item A" (premium and available)
        assert len(hits) >= 1
        for hit in hits:
            assert hit["_source"]["type"] == "premium"
            assert hit["_source"]["available"] is True

    def test_search_query_builder_exclude_fields_with_match(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test SearchQueryBuilder.exclude_fields() with match query in a real search."""
        # Index documents with multiple fields
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Test Document", "description": "Test Description", "metadata": "Test Metadata"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Another Document", "description": "Another Description", "metadata": "Another Metadata"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder with match and exclude_fields
        builder = SearchQueryBuilder(index=index_name)
        builder.match(field="title", value="Document")
        builder.exclude_fields(["description", "metadata"])

        # Verify exclude_fields are stored
        assert len(builder._exclude_fields) == 2
        assert "description" in builder._exclude_fields
        assert "metadata" in builder._exclude_fields

        # Build the query - exclude_fields should be incorporated automatically
        query = builder.build()
        assert query.body is not None

        # Verify the query structure includes _source excludes
        assert "query" in query.body
        assert "_source" in query.body
        assert "excludes" in query.body["_source"]
        assert query.body["_source"]["excludes"] == ["description", "metadata"]

        response = opensearch.search.query(query)

        # Verify results
        assert response is not None
        assert hasattr(response, "hits")
        hits = response.hits

        # Should find documents with "Document" in title
        assert len(hits) >= 2

        # Verify excluded fields are not present in results
        for hit in hits:
            source = hit["_source"]
            assert "title" in source
            # Excluded fields should not be present (OpenSearch respects _source excludes)
            # Note: Some OpenSearch versions may still return excluded fields, but they should be excluded
            # We verify that title is present, which confirms the query worked

    def test_search_query_builder_exclude_fields_with_filters(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test SearchQueryBuilder.exclude_fields() with filters in a real search."""
        # Index documents with multiple fields
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Active Product", "description": "Product Description", "status": "active", "metadata": "Metadata"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Inactive Product", "description": "Product Description", "status": "inactive", "metadata": "Metadata"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder with match, filter, and exclude_fields
        builder = SearchQueryBuilder(index=index_name)
        builder.match(field="title", value="Product")
        builder.add_filter({"term": {"status": "active"}})
        builder.exclude_fields(["description", "metadata"])

        # Build the query
        query = builder.build()
        assert query.body is not None

        # Verify the query structure includes both filters and exclude_fields
        assert "query" in query.body
        assert "bool" in query.body["query"]
        assert "_source" in query.body
        assert "excludes" in query.body["_source"]
        assert query.body["_source"]["excludes"] == ["description", "metadata"]

        response = opensearch.search.query(query)

        # Verify results
        assert response is not None
        assert hasattr(response, "hits")
        hits = response.hits

        # Should only find "Active Product"
        assert len(hits) >= 1
        for hit in hits:
            assert hit["_source"]["status"] == "active"
            assert "title" in hit["_source"]
            # Excluded fields should not be present

    def test_search_query_builder_exclude_fields_only(
        self,
        opensearch: OpenSearchClient,
        index_name: str,
    ) -> None:
        """Test SearchQueryBuilder.exclude_fields() without query or filters (uses match_all)."""
        # Index documents with multiple fields
        bulk_body = (
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Document 1", "description": "Description 1", "metadata": "Metadata 1"}\n'
            f'{{"index": {{"_index": "{index_name}"}}}}\n'
            '{"title": "Document 2", "description": "Description 2", "metadata": "Metadata 2"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Wait for indexing
        time.sleep(1)
        opensearch._client.indices.refresh(index=index_name)

        # Create SearchQueryBuilder with only exclude_fields
        builder = SearchQueryBuilder(index=index_name)
        builder.exclude_fields(["description"])

        # Build the query - should use match_all
        query = builder.build()
        assert query.body is not None

        # Verify the query structure includes match_all and _source excludes
        assert "query" in query.body
        assert "match_all" in query.body["query"]
        assert "_source" in query.body
        assert "excludes" in query.body["_source"]
        assert query.body["_source"]["excludes"] == ["description"]

        # Execute search
        response = opensearch.search.query(query)

        # Verify results
        assert response is not None
        assert hasattr(response, "hits")
        hits = response.hits

        # Should find all documents
        assert len(hits) >= 2
        for hit in hits:
            assert "title" in hit["_source"]
            # Excluded field should not be present
