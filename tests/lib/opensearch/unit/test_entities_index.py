"""Unit tests for Index entity."""

from unittest.mock import MagicMock

import pytest

from lib.opensearch.entities.index import Index, Mappings, Settings


@pytest.mark.unit
class TestIndex:
    """Tests for Index entity."""

    def test_index_initialization(self) -> None:
        """Test Index can be initialized with all required fields."""
        mock_repo = MagicMock()
        index = Index(
            name="test-index",
            settings=Settings(),
            mappings=Mappings(properties={}),
            _repository=mock_repo,
        )

        assert index.name == "test-index"
        assert index.settings is not None
        assert index.mappings is not None
        assert index._repository == mock_repo

    def test_index_delete(self) -> None:
        """Test Index delete method delegates to repository."""
        mock_repo = MagicMock()
        index = Index(
            name="test-index",
            settings=Settings(),
            mappings=Mappings(properties={}),
            _repository=mock_repo,
        )

        mock_repo.delete.return_value = {"acknowledged": True}

        result = index.delete()

        mock_repo.delete.assert_called_once_with(index=index)
        assert result == {"acknowledged": True}

    def test_index_exists_returns_true(self) -> None:
        """Test Index exists method delegates to repository and returns True."""
        mock_repo = MagicMock()
        index = Index(
            name="test-index",
            settings=Settings(),
            mappings=Mappings(properties={}),
            _repository=mock_repo,
        )

        mock_repo.exists.return_value = True

        result = index.exists()

        mock_repo.exists.assert_called_once_with(index=index)
        assert result is True

    def test_index_exists_returns_false(self) -> None:
        """Test Index exists method delegates to repository and returns False."""
        mock_repo = MagicMock()
        index = Index(
            name="test-index",
            settings=Settings(),
            mappings=Mappings(properties={}),
            _repository=mock_repo,
        )

        mock_repo.exists.return_value = False

        result = index.exists()

        mock_repo.exists.assert_called_once_with(index=index)
        assert result is False

    def test_index_truncate(self) -> None:
        """Test Index truncate method delegates to repository."""
        mock_repo = MagicMock()
        index = Index(
            name="test-index",
            settings=Settings(),
            mappings=Mappings(properties={}),
            _repository=mock_repo,
        )

        mock_repo.truncate.return_value = {"deleted": 100}

        result = index.truncate()

        mock_repo.truncate.assert_called_once_with(index=index)
        assert result == {"deleted": 100}
