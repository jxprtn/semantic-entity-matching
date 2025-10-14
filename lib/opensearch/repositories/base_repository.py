"""Base repository class for OpenSearch entity repositories."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from opensearchpy import OpenSearch


class BaseRepository[T](ABC):
    """Abstract base class for OpenSearch entity repositories.

    Repositories handle ALL persistence operations for domain entities.
    This includes creation, retrieval, and instance operations (delete, deploy, etc.).

    Entities are pure domain objects that delegate to their repository
    for any persistence operations.

    Type Parameters:
        EntityType: The type of entity this repository manages, must be a subclass of BaseEntity
    """

    _base_uri: ClassVar[str]

    def __init__(self, *, client: OpenSearch) -> None:
        """Initialize the repository with an OpenSearch client."""
        self._client = client

    @abstractmethod
    def create(self, **_: Any) -> T:
        """Create a new entity and return a domain model instance."""

    @abstractmethod
    def get(self, **_: Any) -> T | None:
        """Get an entity by identifier and return a domain model instance."""

    @abstractmethod
    def delete(self, *_: Any, force: bool = False, **__: Any) -> None:
        """Delete an entity.

        Args:
            force: If True, delete associated entities as well.
            **kwargs: Entity-specific deletion parameters (typically the entity itself)

        Returns:
            Deletion response
        """
