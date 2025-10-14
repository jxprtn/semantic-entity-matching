"""Unit tests for IndexRepository."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from lib.opensearch.entities.index import (
    Index,
    IndexSettings,
    Mappings,
    Settings,
    VectorSearchEngine,
    VectorSearchMethod,
    VectorSearchSpaceType,
)
from lib.opensearch.repositories.index import IndexRepository


@pytest.mark.unit
class TestIndexRepository:
    """Tests for IndexRepository."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock OpenSearch client."""
        mock = MagicMock()
        mock.indices = MagicMock()
        mock.http = MagicMock()
        return mock

    @pytest.fixture
    def index_repo(self, mock_client: MagicMock) -> IndexRepository:
        """Create an IndexRepository instance with mock client."""
        return IndexRepository(client=mock_client)

    def test_create_index(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test creating an index."""
        mock_client.indices.create.return_value = {"acknowledged": True}

        index = index_repo.create(
            index="test-index",
            fields=["title", "description"],
            vector_dimension=1024,
            embedding_column_suffix="_embedding",
        )

        assert isinstance(index, Index)
        assert index.name == "test-index"
        assert "title" in index.mappings.properties
        assert "description" in index.mappings.properties
        # Implementation creates separate text fields and vector fields with suffix
        assert "title_embedding" in index.mappings.properties
        assert "description_embedding" in index.mappings.properties
        # Properties are dicts when serialized, check the dict structure
        title_embedding_field = index.mappings.properties["title_embedding"]
        if isinstance(title_embedding_field, dict):
            assert title_embedding_field["dimension"] == 1024
        else:
            assert title_embedding_field.dimension == 1024
        assert index._repository == index_repo

        # Verify indices.create was called
        mock_client.indices.create.assert_called_once()
        call_args = mock_client.indices.create.call_args
        assert call_args[1]["index"] == "test-index"

        # Verify mappings include both text and vector fields with suffix
        mappings = call_args[1]["body"]["mappings"]["properties"]
        assert "title" in mappings
        assert "description" in mappings
        assert mappings["title"]["type"] == "text"
        assert mappings["description"]["type"] == "text"
        # Implementation creates vector fields with suffix
        assert "title_embedding" in mappings
        assert "description_embedding" in mappings
        title_embedding_field = mappings["title_embedding"]
        assert title_embedding_field["type"] == "knn_vector"
        assert title_embedding_field["dimension"] == 1024

    def test_create_index_with_custom_parameters(
        self, index_repo: IndexRepository, mock_client: Any
    ) -> None:
        """Test creating an index with custom HNSW parameters."""
        mock_client.indices.create.return_value = {"acknowledged": True}

        index = index_repo.create(
            index="test-index",
            fields=["title"],
            vector_dimension=512,
            method_name=VectorSearchMethod.HNSW,
            space_type=VectorSearchSpaceType.COSINE,
            engine=VectorSearchEngine.NMSLIB,
            ef_construction=256,
            m=24,
            ef_search=256,
            embedding_column_suffix="_embedding",
        )

        assert isinstance(index, Index)
        # Implementation creates separate text fields and vector fields with suffix
        assert "title" in index.mappings.properties
        assert "title_embedding" in index.mappings.properties
        title_embedding_field = index.mappings.properties["title_embedding"]
        if isinstance(title_embedding_field, dict):
            assert title_embedding_field["dimension"] == 512
        else:
            assert title_embedding_field.dimension == 512

        # Verify custom parameters were used
        call_args = mock_client.indices.create.call_args
        mappings = call_args[1]["body"]["mappings"]["properties"]
        assert mappings["title"]["type"] == "text"
        vector_field = mappings["title_embedding"]
        assert vector_field["dimension"] == 512
        assert vector_field["method"]["space_type"] == "cosine"
        assert vector_field["method"]["engine"] == "nmslib"
        assert vector_field["method"]["parameters"]["ef_construction"] == 256
        assert vector_field["method"]["parameters"]["m"] == 24

        settings = call_args[1]["body"]["settings"]["index"]
        assert settings["knn"] is True
        assert settings["knn.algo_param.ef_search"] == 256

    def test_get_index(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test getting an index by name."""
        mock_client.indices.get.return_value = {
            "test-index": {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn_algo_param_ef_search": 512,
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "description": {"type": "text"},
                        "title_embedding": {"type": "knn_vector", "dimension": 1024},
                        "description_embedding": {"type": "knn_vector", "dimension": 1024},
                    }
                },
            }
        }

        index = index_repo.get(index="test-index")

        assert isinstance(index, Index)
        assert index.name == "test-index"
        assert "title" in index.mappings.properties
        assert "description" in index.mappings.properties
        # Properties from OpenSearch are dicts
        # Check that vector embedding fields exist (mock data has both text and embedding fields)
        assert "title_embedding" in index.mappings.properties
        title_embedding_field = index.mappings.properties["title_embedding"]
        assert isinstance(title_embedding_field, dict)
        assert title_embedding_field["type"] == "knn_vector"
        assert title_embedding_field["dimension"] == 1024
        assert index._repository == index_repo

        mock_client.indices.get.assert_called_once_with(index="test-index")

    def test_delete_index(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test deleting an index."""
        mock_client.indices.delete.return_value = {"acknowledged": True}

        index = Index(
            name="test-index",
            settings=Settings(index=IndexSettings()),
            mappings=Mappings(properties={}),
            _repository=index_repo,
        )

        result = index_repo.delete(index=index)

        mock_client.indices.delete.assert_called_once_with(index="test-index", ignore=[400, 404])
        assert result == {"acknowledged": True}

    def test_exists_returns_true(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test exists returns True when index exists."""
        mock_client.indices.exists.return_value = True

        result = index_repo.exists(index_name="test-index")

        assert result is True
        mock_client.indices.exists.assert_called_once_with(index="test-index")

    def test_exists_returns_false(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test exists returns False when index doesn't exist."""
        mock_client.indices.exists.return_value = False

        result = index_repo.exists(index_name="test-index")

        assert result is False
        mock_client.indices.exists.assert_called_once_with(index="test-index")

    def test_exists_raises_on_other_error(
        self, index_repo: IndexRepository, mock_client: Any
    ) -> None:
        """Test exists raises exception for non-NotFoundError errors."""
        mock_client.indices.exists.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            index_repo.exists(index_name="test-index")

    def test_truncate_index(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test truncating an index."""
        mock_client.http.post.return_value = {"deleted": 100}

        index = Index(
            name="test-index",
            settings=Settings(index=IndexSettings()),
            mappings=Mappings(properties={}),
            _repository=index_repo,
        )

        result = index_repo.truncate(index=index)

        mock_client.http.post.assert_called_once()
        call_args = mock_client.http.post.call_args
        assert call_args[1]["url"] == "/test-index/_delete_by_query"
        assert call_args[1]["body"] == {"query": {"match_all": {}}}
        assert result == {"deleted": 100}

    def test_list_indices(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test listing all indices."""
        mock_client.indices.get.return_value = {
            "test-index-1": {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 512,
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {"type": "knn_vector", "dimension": 1024},
                    }
                },
            },
            "test-index-2": {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 256,
                    }
                },
                "mappings": {
                    "properties": {
                        "description": {"type": "knn_vector", "dimension": 512},
                    }
                },
            },
        }

        indices = index_repo.list()

        assert len(indices) == 2
        assert all(isinstance(idx, Index) for idx in indices)
        assert all(idx._repository == index_repo for idx in indices)

        # Verify indices.get was called with wildcard
        mock_client.indices.get.assert_called_once_with(index="*")

        # Verify the indices have correct names and structure
        index_names = {idx.name for idx in indices}
        assert "test-index-1" in index_names
        assert "test-index-2" in index_names

        # Find specific indices and verify their properties
        index1 = next(idx for idx in indices if idx.name == "test-index-1")
        index2 = next(idx for idx in indices if idx.name == "test-index-2")

        # Implementation creates vector fields with same name as text fields
        assert "title" in index1.mappings.properties
        assert "description" in index2.mappings.properties

    def test_list_indices_empty(self, index_repo: IndexRepository, mock_client: Any) -> None:
        """Test listing indices when no indices exist."""
        mock_client.indices.get.return_value = {}

        indices = index_repo.list()

        assert len(indices) == 0
        assert isinstance(indices, list)
        mock_client.indices.get.assert_called_once_with(index="*")
