"""Unit tests for BaseService class."""

from unittest.mock import MagicMock

import pytest

from lib.opensearch.services.base_service import BaseService


@pytest.mark.unit
class TestBaseService:
    """Tests for BaseService class."""

    def test_init_with_client(self) -> None:
        """Test BaseService initialization with a client."""
        mock_client = MagicMock()

        service = BaseService(client=mock_client)

        # Verify service was initialized with the client
        assert service._client == mock_client

    def test_init_stores_client_reference(self) -> None:
        """Test that BaseService stores the client reference correctly."""
        mock_client = MagicMock()
        mock_client.info.return_value = {"cluster_name": "test-cluster"}

        service = BaseService(client=mock_client)

        # Verify the client can be accessed and used
        assert service._client is mock_client
        # Verify we can call methods on the stored client
        result = service._client.info()
        assert result == {"cluster_name": "test-cluster"}
        mock_client.info.assert_called_once()
