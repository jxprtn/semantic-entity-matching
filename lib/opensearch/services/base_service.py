from opensearchpy import OpenSearch


class BaseService:
    """Base service for OpenSearch."""

    _client: OpenSearch

    def __init__(self, *, client: OpenSearch) -> None:
        self._client = client
