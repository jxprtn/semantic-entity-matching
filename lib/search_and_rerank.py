"""Core search and reranking functionality.

This module contains business logic for performing vector search and reranking
results using AWS Bedrock. It is framework-agnostic and reusable by
CLI, Lambda, and web applications.
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from lib.bedrock import EmbeddingVector
from lib.interfaces import IReporter, SearchAndRerankResults
from lib.logging import get_logger
from lib.opensearch.client import OpenSearchClient
from lib.opensearch.services import SearchQueryBuilder
from lib.rerank import rerank

logger = get_logger(__name__)


def search_and_rerank(  # noqa: PLR0913
    *,
    column: str,
    embedding_column_suffix: str,
    enable_reranking: bool = True,
    filters: list[dict[str, Any]] | None,
    index: str,
    opensearch: OpenSearchClient,
    get_embedding: Callable[[], Coroutine[Any, Any, EmbeddingVector]],
    profile: str | None,
    query: str,
    region: str,
    reporter: IReporter,
    top_k: int = 50,
) -> SearchAndRerankResults:
    """Perform vector search and rerank results using AWS Bedrock.

    Args:
        column: Column/field to search on
        embedding_column_suffix: Suffix appended to column names for embedding columns (default: _embedding)
        enable_reranking: Whether to rerank results (default: True)
        filters: Optional list of filter dictionaries for search
        index: Index name to search
        opensearch: OpenSearchClient instance
        get_embedding: Function to get embeddings from model
        profile: AWS profile to use for reranking
        query: Search query text
        region: AWS region
        reporter: Reporter for status messages and progress updates
        top_k: Number of results to return from reranking (default: 50)

    Returns:
        Dictionary containing:
            - search_response: Raw OpenSearch search response
            - rerank_response: Bedrock rerank API response (or None if reranking failed)
            - query: The original query
            - sources: List of source texts extracted from search results

    """
    reporter.on_message(f"Searching index '{index}' for query: {query}")

    # Perform vector search
    embedding = asyncio.run(get_embedding())

    search_results = opensearch.search.query(
        SearchQueryBuilder(index=index)
        .match_knn(field=column, value=embedding)
        .add_filters(filters or [])
        .exclude_fields([f"*{embedding_column_suffix}"])
        .build()
    )

    reporter.on_message(f"Search returned {search_results.count} results")

    if enable_reranking and len(search_results.hits) > 0:
        # Extract sources from search results for reranking
        # Filter out embedding columns and convert to strings formatted as 'key: value' joined with newlines
        sources = [
            "\n".join(
                f"{k}: {v}"
                for k, v in hit["_source"].items()
                if not k.endswith(embedding_column_suffix)
            )
            for hit in search_results.hits
        ]

        # Rerank results
        rerank_query = f"What is the most relevant description to '{query}'"
        reporter.on_message(f"Reranking {len(sources)} documents with query: {rerank_query}")

        rerank_results = rerank(
            profile=profile,
            query=rerank_query,
            region=region,
            reporter=reporter,
            sources=sources,
            top_k=top_k,
        )

        return {
            "search_results": search_results,
            "rerank_results": rerank_results,
            "query": query,
            "sources": sources,
        }

    return {
        "search_results": search_results,
        "rerank_results": None,
        "query": query,
        "sources": None,
    }
