"""
OpenSearch entity repositories.

This module contains repository classes for managing OpenSearch entities.
Repositories handle persistence operations and return domain model instances.
"""

from lib.opensearch.repositories.base_repository import BaseRepository
from lib.opensearch.repositories.index import IndexRepository

__all__ = [
    "BaseRepository",
    "IndexRepository",
]
