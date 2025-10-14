"""Core evaluation functionality for search performance testing.

This module contains business logic for evaluating search performance
by running vector searches against test datasets. It is framework-agnostic
and reusable by CLI, Lambda, and web applications.
"""

import json
from typing import Any

import pandas as pd

from lib.interfaces import IReporter
from lib.logging import get_logger
from lib.opensearch.client import OpenSearchClient

logger = get_logger(__name__)


def get_top_k_metric(matched_queries: list[dict], k: int, total_queries: int) -> float:
    """Calculate the percentage of matched queries that have rank <= k.

    Args:
        matched_queries: List of matched query results with 'rank' field
        k: Top-k threshold
        total_queries: Total number of queries

    Returns:
        Percentage of queries with rank <= k

    """
    if not matched_queries:
        return 0.0
    return len([r for r in matched_queries if r.get("rank", 0) <= k]) / total_queries * 100


def evaluate(  # noqa: C901, PLR0913, PLR0912
    *,
    batch_size: int,
    column: str,
    df: pd.DataFrame,
    evaluation_columns: list[str],
    index_name: str,
    match_column: str,
    match_field: str,
    opensearch: OpenSearchClient,
    reporter: IReporter,
) -> list[dict[str, Any]]:
    """Evaluate search performance by running vector searches against a test dataset using batch processing.

    Args:
        batch_size: Number of queries to process in each batch
        column: Column name to run the search against
        df: DataFrame containing test data
        display_field: Field name in OpenSearch index to display in results
        evaluation_columns: List of columns to combine for query text
        index_name: Name of the OpenSearch index
        match_column: Column name in test dataset to match against
        match_field: Field name in OpenSearch index to match against
        opensearch: OpenSearchClient instance
        pipeline_name: Name of the pipeline to use

    Returns:
        List of dictionaries containing search results for each row

    """
    # Check if the specified columns exist in the dataset
    for evaluation_column in evaluation_columns:
        if evaluation_column not in df.columns:
            available_columns = list(df.columns)
            raise ValueError(
                f"Column '{evaluation_column}' not found in dataset. Available columns: {available_columns}",
            )

    reporter.on_message(
        f"Starting evaluation: index={index_name}queries={len(df)}, batch_size={batch_size}",
    )

    results = []

    # Process data in batches
    for batch_start in range(0, len(df), batch_size):
        batch_end = min(batch_start + batch_size, len(df))
        batch_df = df.iloc[batch_start:batch_end]

        logger.debug(f"Processing batch: rows {batch_start + 1}-{batch_end}")

        # Prepare batch queries
        batch_queries = []
        batch_metadata = []

        for idx, row in batch_df.iterrows():
            query_text = " ".join(
                [str(row[evaluation_column]) for evaluation_column in evaluation_columns],
            )

            # Skip rows with NaN or empty values
            if pd.isna(query_text) or str(query_text).strip() == "" or query_text == "nan":
                batch_metadata.append(
                    {
                        "row_index": idx,
                        "query": None,
                        "error": "Empty or NaN query",
                        "skip": True,
                    },
                )
                continue

            batch_queries.append(
                {
                    "index": index_name,
                },
            )
            batch_queries.append(
                {
                    "query": {"match": {column: query_text}},
                    "_source": [match_field],
                    "size": 50,
                },
            )

            batch_metadata.append(
                {
                    "row_index": idx,
                    "query": query_text,
                    "skip": False,
                    "row_data": row,
                },
            )

        # Execute batch search if there are valid queries
        if batch_queries:
            try:
                # Use opensearch.request() for batch search
                batch_response = opensearch.request(
                    url="/_msearch",
                    http_verb="POST",
                    body="\n".join([json.dumps(query) for query in batch_queries]) + "\n",
                )

                # Process batch results
                response_idx = 0
                for metadata in batch_metadata:
                    if metadata["skip"]:
                        results.append(
                            {
                                "row_index": metadata["row_index"],
                                "query": metadata["query"],
                                "results": [],
                                "error": metadata["error"],
                            },
                        )
                        continue

                    if response_idx < len(batch_response["responses"]):
                        response = batch_response["responses"][response_idx]
                        response_idx += 1

                        if "error" in response:
                            logger.warning(f"Query error: {response['error']}")
                            results.append(
                                {
                                    "row_index": metadata["row_index"],
                                    "query": metadata["query"],
                                    "results": [],
                                    "error": str(response["error"]),
                                },
                            )
                            continue

                        # Extract search results (full documents)
                        hits_count = len(response["hits"]["hits"])
                        found_match = False

                        for i, hit in enumerate(response["hits"]["hits"]):
                            if hit["_source"].get(match_field) == metadata["row_data"].get(
                                match_column,
                            ):
                                result = {
                                    "row_index": metadata["row_index"],
                                    "query": metadata["query"],
                                    "score": hit["_score"],
                                    "document": hit["_source"],
                                    "rank": i + 1,
                                    "hits_count": hits_count,
                                }
                                results.append(result)
                                logger.debug(
                                    f"Row {metadata['row_index']}: rank={i + 1}/{hits_count}, "
                                    f"score={hit['_score']:.4f}",
                                )
                                found_match = True
                                break

                        if not found_match:
                            results.append(
                                {
                                    "row_index": metadata["row_index"],
                                    "query": metadata["query"],
                                    "rank": None,
                                    "hits_count": hits_count,
                                },
                            )
                            logger.debug(f"Row {metadata['row_index']}: No match found")

            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                # Add error results for all queries in this batch
                for metadata in batch_metadata:
                    if not metadata["skip"]:
                        results.append(
                            {
                                "row_index": metadata["row_index"],
                                "query": metadata["query"],
                                "results": [],
                                "error": str(e),
                            },
                        )

    reporter.on_message(f"Evaluation complete: processed {len(results)} queries")
    return results
