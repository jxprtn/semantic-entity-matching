"""Query builder for OpenSearch queries."""

from typing import Any, Self

from lib.interfaces import SearchQuery


class SearchQueryBuilder:
    """Search query builder for OpenSearch."""

    def __init__(self, index: str) -> None:
        """Initialize SearchQueryBuilder with an index name."""
        self._exclude_fields: list[str] = []
        self._filters: list[dict[str, Any]] = []
        self._index = index
        self._pipeline_name: str | None = None
        self._query: dict[str, Any] = {"match_all": {}}
        self._size: int | None = None

    def add_filter(self, value: dict[str, Any]) -> Self:
        """Add a single filter to the query."""
        self.add_filters([value])
        return self

    def add_filters(self, values: list[dict[str, Any]]) -> Self:
        """Add multiple filters to the query."""
        self._filters.extend(values)
        return self

    def match(self, *, field: str, value: str) -> Self:
        """Match a field to a query."""
        if "knn" in self._query:
            raise ValueError("Cannot use match() after match_knn()")
        self._query = {"match": {field: value}}
        return self

    def match_exactly(self, *, field: str, value: str) -> Self:
        """Match a field to a query exactly."""
        if "knn" in self._query:
            raise ValueError(
                "Cannot use match_exactly() after match_knn(), use add_filters() to add filters to the query."
            )
        self._query = {"term": {f"{field}.keyword": value}}
        return self

    def match_knn(self, *, field: str, value: list[float]) -> Self:
        """Add a vector to the query."""
        if "match" in self._query:
            raise ValueError("Cannot use match_knn() after match()")
        if "match_exactly" in self._query:
            raise ValueError(
                "Cannot use match_knn() after match_exactly(), use add_filters() to add filters to the query."
            )
        self._query = {
            "knn": {
                field: {
                    "vector": value,
                    "k": (self._size or 10) * 2,
                }
            }
        }
        return self

    def use_pipeline(self, pipeline_name: str) -> Self:
        """Add a pipeline to the query."""
        self._pipeline_name = pipeline_name
        return self

    def exclude_fields(self, fields: list[str]) -> Self:
        """Exclude fields from the query."""
        self._exclude_fields.extend(fields)
        return self

    def limit_results(self, size: int) -> Self:
        """Limit the number of results."""
        self._size = size
        return self

    def build(self) -> SearchQuery:
        """Build the query."""
        params: dict[str, Any] = {}
        body: dict[str, Any] = {}

        # Build the body
        if len(self._filters) > 0:
            body = {
                "query": {
                    "bool": {
                        "must": [self._query],
                        "filter": self._filters,
                    }
                }
            }
        else:
            body = {"query": self._query}

        if len(self._exclude_fields) > 0:
            body["_source"] = {"excludes": self._exclude_fields}

        if self._size is not None:
            body["size"] = self._size

        if self._pipeline_name is not None:
            params["search_pipeline"] = self._pipeline_name

        return SearchQuery(index=self._index, body=body, params=params)
