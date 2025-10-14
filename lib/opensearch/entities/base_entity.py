"""Base entity class for OpenSearch domain models."""

from abc import ABC, abstractmethod

from lib.opensearch.repositories.base_repository import BaseRepository


class BaseEntity[T](ABC):
    """Abstract base class for OpenSearch domain entities.

    All domain entities must:
    - Have a repository property that references their repository
    - Implement a delete() method that delegates to the repository

    Entities are pure domain objects that delegate all persistence
    operations to their repository.
    """

    _repository: BaseRepository[T]

    @abstractmethod
    def delete(self) -> None:
        """Delete this entity.

        This method should delegate to the repository's delete method,
        passing self as an argument.

        Args:
            **kwargs: Additional deletion parameters (e.g., callbacks)

        Returns:
            Deletion response
        """
