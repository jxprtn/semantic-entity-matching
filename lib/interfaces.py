"""Type definitions and interfaces for the entity matching system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypedDict

from mypy_boto3_bedrock_agent_runtime.type_defs import RerankResponseTypeDef


class IReporter(ABC):
    """Reporter interface."""

    @abstractmethod
    def on_message(self, *messages: str) -> None:
        """On message callback."""

    @abstractmethod
    def on_input(self, message: str) -> str:
        """On input callback."""

    @abstractmethod
    def start_progress(self, total: int) -> None:
        """On start progress callback."""

    @abstractmethod
    def stop_progress(self) -> None:
        """On stop progress callback."""

    @abstractmethod
    def on_progress(self, value: int) -> None:
        """On progress callback."""


@dataclass
class SearchResults:
    """Search result."""

    hits: list[dict[str, Any]]
    count: int


@dataclass
class SearchQuery:
    """Search query."""

    index: Any
    body: Any
    params: Any


class SearchAndRerankResults(TypedDict):
    query: str
    rerank_results: RerankResponseTypeDef | None
    search_results: SearchResults
    sources: list[str] | None


class ISearchService(ABC):
    """Search service interface."""

    @abstractmethod
    def query(self, query: SearchQuery) -> SearchResults:
        """Search for entities matching the query."""
