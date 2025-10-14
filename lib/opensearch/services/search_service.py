"""Search service for OpenSearch queries."""

from opensearchpy import OpenSearch

from lib.interfaces import ISearchService, SearchQuery, SearchResults
from lib.opensearch.services.base_service import BaseService


class SearchService(BaseService, ISearchService):
    """Search service for OpenSearch."""

    _client: OpenSearch

    def query(self, query: SearchQuery) -> SearchResults:
        """Execute a search query."""
        response = self._client.search(index=query.index, body=query.body, params=query.params)
        return SearchResults(
            hits=response["hits"]["hits"],
            count=response["hits"]["total"]["value"],
        )
