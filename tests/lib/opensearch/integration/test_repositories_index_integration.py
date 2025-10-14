"""Integration tests for IndexRepository."""

import time
import uuid

import pytest

from lib.opensearch.client import OpenSearchClient
from lib.opensearch.entities.index import (
    Index,
    VectorSearchEngine,
    VectorSearchMethod,
    VectorSearchSpaceType,
)
from lib.opensearch.repositories.index import IndexRepository


@pytest.mark.integration
class TestIndexRepositoryIntegration:
    """Integration tests for IndexRepository."""

    @pytest.fixture
    def index_repo(self, opensearch: OpenSearchClient) -> IndexRepository:
        """Create an IndexRepository instance with real OpenSearch client."""
        return IndexRepository(client=opensearch._client)

    @pytest.fixture
    def test_index_name(self) -> str:
        """Generate a unique test index name."""
        return f"test-index-repo-{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def test_index(self, index_repo: IndexRepository, test_index_name: str) -> Index:
        """Create a test index for integration tests."""
        index = index_repo.create(
            index=test_index_name,
            fields=["title", "description"],
            vector_dimension=1024,
            embedding_column_suffix="_embedding",
        )

        yield index

        # Cleanup
        try:
            index_repo.delete(index=index)
        except Exception:
            pass

    def test_create_index(self, index_repo: IndexRepository, test_index_name: str) -> None:
        """Test creating an index with real OpenSearch."""
        index = index_repo.create(
            index=test_index_name,
            fields=["title", "description"],
            vector_dimension=1024,
            embedding_column_suffix="_embedding",
        )

        try:
            assert isinstance(index, Index)
            assert index.name == test_index_name
            assert "title" in index.mappings.properties
            assert "description" in index.mappings.properties
            # Properties are dicts when retrieved from OpenSearch
            title_embedding = index.mappings.properties["title_embedding"]
            if isinstance(title_embedding, dict):
                assert title_embedding["dimension"] == 1024
            else:
                assert title_embedding.dimension == 1024
            assert index._repository == index_repo

            # Verify index was actually created
            assert index_repo.exists(index_name=index.name)
        finally:
            # Cleanup
            try:
                index_repo.delete(index=index)
            except Exception:
                pass

    def test_create_index_with_custom_parameters(self, index_repo: IndexRepository) -> None:
        """Test creating an index with custom HNSW parameters."""
        index_name = f"test-index-custom-{uuid.uuid4().hex[:8]}"

        index = index_repo.create(
            index=index_name,
            fields=["title"],
            vector_dimension=512,
            method_name=VectorSearchMethod.HNSW,
            space_type=VectorSearchSpaceType.L2,
            engine=VectorSearchEngine.FAISS,
            ef_construction=256,
            m=24,
            ef_search=256,
            embedding_column_suffix="_embedding",
        )

        try:
            assert isinstance(index, Index)
            title_embedding = index.mappings.properties["title_embedding"]
            if isinstance(title_embedding, dict):
                assert title_embedding["dimension"] == 512
            else:
                assert title_embedding.dimension == 512
            assert index_repo.exists(index_name=index.name)
        finally:
            try:
                index_repo.delete(index=index)
            except Exception:
                pass

    def test_get_index(self, index_repo: IndexRepository, test_index: Index) -> None:
        """Test getting an index by name."""
        index = index_repo.get(index=test_index.name)

        assert isinstance(index, Index)
        assert index.name == test_index.name
        assert set(index.mappings.properties.keys()) == set(test_index.mappings.properties.keys())
        # Check vector dimension from the first embedding field
        # Properties from OpenSearch are dicts
        test_vector_dim = None
        for k, v in test_index.mappings.properties.items():
            if k.endswith("_embedding"):
                if isinstance(v, dict):
                    test_vector_dim = v.get("dimension")
                else:
                    test_vector_dim = v.dimension
                break
        index_vector_dim = None
        for k, v in index.mappings.properties.items():
            if k.endswith("_embedding"):
                if isinstance(v, dict):
                    index_vector_dim = v.get("dimension")
                else:
                    index_vector_dim = v.dimension
                break
        assert index_vector_dim == test_vector_dim

    def test_delete_index(self, index_repo: IndexRepository) -> None:
        """Test deleting an index."""
        index_name = f"test-index-delete-{uuid.uuid4().hex[:8]}"

        # Create an index to delete
        index = index_repo.create(
            index=index_name,
            fields=["title"],
            vector_dimension=1024,
            embedding_column_suffix="_embedding",
        )

        # Verify it exists
        assert index_repo.exists(index_name=index.name)

        # Delete it
        result = index_repo.delete(index=index)

        assert result is not None

        # Verify it's deleted
        assert not index_repo.exists(index_name=index.name)

    def test_exists_returns_true_for_existing_index(
        self, index_repo: IndexRepository, test_index: Index
    ) -> None:
        """Test exists returns True for an existing index."""
        result = index_repo.exists(index_name=test_index.name)

        assert result is True

    def test_exists_returns_false_for_non_existing_index(self, index_repo: IndexRepository) -> None:
        """Test exists returns False for a non-existing index."""
        non_existing_index_name = f"non-existing-{uuid.uuid4().hex[:8]}"

        result = index_repo.exists(index_name=non_existing_index_name)

        assert result is False

    def test_truncate_index(
        self, index_repo: IndexRepository, test_index: Index, opensearch: OpenSearchClient
    ) -> None:
        """Test truncating an index."""
        # Add some documents to the index
        bulk_body = (
            f'{{"index": {{"_index": "{test_index.name}"}}}}\n'
            '{"title": "Document 1", "description": "Description 1"}\n'
            f'{{"index": {{"_index": "{test_index.name}"}}}}\n'
            '{"title": "Document 2", "description": "Description 2"}\n'
            f'{{"index": {{"_index": "{test_index.name}"}}}}\n'
            '{"title": "Document 3", "description": "Description 3"}\n'
        )
        opensearch.bulk_index(body=bulk_body)

        # Verify documents were inserted
        time.sleep(1)  # Wait for indexing
        count_before = opensearch._client.count(index=test_index.name)["count"]
        assert count_before > 0

        # Truncate the index
        result = index_repo.truncate(index=test_index)

        assert result is not None

        # Verify all documents were deleted but index still exists
        time.sleep(1)  # Wait for deletion
        assert index_repo.exists(index_name=test_index.name)
        count_after = opensearch._client.count(index=test_index.name)["count"]
        assert count_after == 0

    def test_list_indices(self, index_repo: IndexRepository, test_index: Index) -> None:
        """Test listing all indices."""
        indices = index_repo.list()

        assert len(indices) > 0
        assert all(isinstance(idx, Index) for idx in indices)
        assert all(idx._repository == index_repo for idx in indices)

        # Verify the test index is in the list
        index_names = {idx.name for idx in indices}
        assert test_index.name in index_names

        # Find the test index and verify its structure
        found_index = next(idx for idx in indices if idx.name == test_index.name)
        assert found_index.name == test_index.name
        assert set(found_index.mappings.properties.keys()) == set(
            test_index.mappings.properties.keys()
        )
