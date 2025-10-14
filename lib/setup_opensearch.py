"""OpenSearch cluster setup."""

from lib.opensearch.client import OpenSearchClient
from lib.opensearch.entities.index import VectorSearchEngine, VectorSearchSpaceType


def setup_opensearch(  # noqa: PLR0913
    *,
    columns: list[str],
    delete: bool = False,
    ef_construction: int = 512,
    ef_search: int = 512,
    embedding_column_suffix: str = "_embedding",
    engine: str = VectorSearchEngine.FAISS.value,
    index_name: str,
    m: int = 48,
    opensearch: OpenSearchClient,
    space_type: str = VectorSearchSpaceType.L2.value,
    vector_dimension: int = 1024,
) -> None:
    """Setup OpenSearch cluster.

    Args:
        columns: List of columns to use for ingestion
        delete: If True, delete existing resources before recreating
        ef_construction: HNSW ef_construction parameter for index creation
        ef_search: HNSW ef_search parameter for index creation
        engine: Vector search engine for index creation
        index_name: Index name to use
        m: HNSW m parameter for index creation
        opensearch: OpenSearchClient instance
        space_type: Space type for vector similarity
        vector_dimension: Vector dimension for embeddings
    """
    index_exists = opensearch.indexes.exists(index_name=index_name)

    if index_exists:
        if delete:
            idx = opensearch.indexes.get(index=index_name)
            idx.delete()
            index_exists = False
        else:
            return

    opensearch.indexes.create(
        index=index_name,
        fields=columns,
        ef_construction=ef_construction,
        ef_search=ef_search,
        embedding_column_suffix=embedding_column_suffix,
        engine=VectorSearchEngine(engine),
        m=m,
        space_type=VectorSearchSpaceType(space_type),
        vector_dimension=vector_dimension,
    )
