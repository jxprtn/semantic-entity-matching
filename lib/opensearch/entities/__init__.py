"""
OpenSearch domain entities.

This module contains domain entities for OpenSearch entities.
Entities are pure domain objects that delegate all persistence
operations to their repository.
"""

from lib.opensearch.entities.base_entity import BaseEntity
from lib.opensearch.entities.index import Index

__all__ = [
    "BaseEntity",
    "Index",
]
