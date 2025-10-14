import os
import re
from typing import Any

from botocore.credentials import Credentials
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import AuthorizationException

from lib.interfaces import IReporter
from lib.opensearch.repositories import IndexRepository
from lib.opensearch.services.search_service import SearchService


class OpenSearchClient:
    def __init__(
        self,
        *,
        credentials: Credentials | None = None,
        host: str,
        port: int = 443,
        region: str = "us-east-1",
        reporter: IReporter,
    ) -> None:
        """Initialize OpenSearch client."""
        self._host = re.sub(r"^https?://", "", host)
        self._port = port
        self._region = region
        self._reporter = reporter
        self._credentials = credentials
        self._client = self._connect()

        # Initialize repository classes
        self.indexes = IndexRepository(client=self._client)

        # Initialize service classes
        self.search = SearchService(client=self._client)

    def _connect(self) -> OpenSearch:
        # Determine if this is an AWS OpenSearch domain (requires SSL)
        is_aws_domain = ".es.amazonaws.com" in self._host or ".es.amazonaws.com.cn" in self._host

        # Use AWS authentication only if credentials are provided
        if self._credentials is not None and is_aws_domain:
            auth = AWSV4SignerAuth(self._credentials, self._region)
            http_auth = auth
            use_ssl = True
        else:
            http_auth = None
            use_ssl = False

        client = OpenSearch(
            hosts=[{"host": self._host, "port": self._port}],
            http_compress=True,
            http_auth=http_auth,
            use_ssl=use_ssl,
            verify_certs=use_ssl,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            connection_class=RequestsHttpConnection,
            timeout=60,
        )

        # Test the connection
        try:
            info = client.info()
            self._reporter.on_message(f"Connected to OpenSearch cluster: {info['cluster_name']}")
        except AuthorizationException as e:
            if "AWS_EXECUTION_ENV" not in os.environ:
                raise Exception(
                    f"Authentication successful but access denied (403). "
                    f"Please check the OpenSearch domain's resource-based access policy. "
                    f"The user/role needs 'es:ESHttp*' permissions. "
                    f"Error details: {e.info if hasattr(e, 'info') else 'Access denied'}"
                ) from e
            self._reporter.on_message("Skipping connection test")
        except Exception as e:
            raise Exception(f"Failed to connect to OpenSearch: {type(e).__name__}: {e}") from e

        return client

    def get_settings(self) -> dict[str, Any]:
        """Get current OpenSearch cluster settings."""
        return self._client.http.get(url="/_cluster/settings?include_defaults=true")

    def predict(self, *, model_id: str, input: str) -> dict[str, Any]:
        return self._client.http.post(
            url=f"/_plugins/_ml/models/{model_id}/_predict",
            body={"parameters": {"inputText": input}},
        )

    # Indexes (backward compatibility)

    def index_exists(self, *, index: str) -> bool:
        """Check if an index exists (backward compatibility method)."""
        from lib.opensearch.entities.index import Index

        idx = Index(
            name=index,
            fields=[],
            vector_dimension=0,
            _repository=self.indexes,
        )
        return idx.exists()

    def bulk_index(self, *, body: str, pipeline_name: str | None = None) -> dict[str, Any]:
        """
        Perform bulk indexing operation.

        Args:
            body: Bulk request body (newline-delimited JSON)
            pipeline_name: Optional pipeline name to use for ingestion

        Returns:
            Bulk operation response
        """
        params = {}
        if pipeline_name:
            params["pipeline"] = pipeline_name
        return self._client.bulk(body=body, params=params)

    def count_documents(self, *, index: str) -> int:
        return self._client.count(index=index)["count"]

    def get_one_document(self, *, index: str) -> dict[str, Any]:
        return self._client.search(index=index, body={"size": 1})["hits"]["hits"][0]["_source"]

    def request(
        self,
        *,
        url: str,
        http_verb: str = "GET",
        body: str | None = None,
    ):
        if http_verb not in ["GET", "POST", "PUT", "DELETE"]:
            raise ValueError("Invalid HTTP verb")

        # Dynamically call the appropriate HTTP method
        method = getattr(self._client.http, http_verb.lower())
        return method(url=url, body=body if body else None)
