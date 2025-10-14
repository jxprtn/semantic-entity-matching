import asyncio
import contextlib
import sys
import traceback
from typing import Any

from lib.bedrock import (
    BedrockClient,
    EmbeddingModelId,
    EmbeddingType,
    EmbeddingVector,
    InvokeEmbeddingModelCommand,
    InvokeModelCommand,
)
from lib.console_reporter import ConsoleReporter
from lib.opensearch.client import OpenSearchClient
from lib.search_and_rerank import search_and_rerank
from lib.utils import get_aws_credentials

DEFINITION = {
    "name": "search",
    "description": "Search data",
    "arguments": [
        {
            "name": "assume-role",
            "type": str,
            "required": False,
            "help": "AWS role to assume for OpenSearch operations",
        },
        {
            "name": "bedrock-model-id",
            "type": str,
            "required": True,
            "help": "Bedrock model ID to use",
        },
        {
            "name": "column",
            "type": str,
            "required": True,
            "help": "Column to search on",
        },
        {
            "name": "embedding-column-suffix",
            "type": str,
            "required": False,
            "default": "_embedding",
            "help": "Suffix appended to column names for embedding columns (default: _embedding)",
        },
        {
            "name": "filter-field",
            "type": str,
            "required": False,
            "help": "Field name for filtering search results (e.g., 'CLASS')",
        },
        {
            "name": "filter-value",
            "type": str,
            "required": False,
            "help": "Value for filtering search results (e.g., 'MICRO')",
        },
        {
            "name": "index",
            "type": str,
            "required": True,
            "help": "Index name to use",
        },
        {
            "name": "opensearch-host",
            "type": str,
            "required": False,
            "default": "localhost",
            "help": "OpenSearch host (default: localhost)",
        },
        {
            "name": "opensearch-port",
            "type": int,
            "required": False,
            "default": 9200,
            "help": "OpenSearch port (default: 9200)",
        },
        {
            "name": "profile",
            "type": str,
            "required": False,
            "help": "AWS profile to use",
        },
        {
            "name": "query",
            "type": str,
            "required": True,
            "help": "Query to search",
        },
        {
            "name": "region",
            "type": str,
            "required": False,
            "default": "us-east-1",
            "help": "AWS region",
        },
        {
            "name": "vector-dimension",
            "type": int,
            "required": True,
            "help": "Vector dimension for embeddings",
        },
    ],
}


def main(
    *,
    assume_role: str | None = None,
    bedrock_model_id: str,
    column: str,
    embedding_column_suffix: str = "_embedding",
    filter_field: str | None = None,
    filter_value: str | None = None,
    index: str,
    opensearch_host: str = "localhost",
    opensearch_port: int = 9200,
    profile: str | None = None,
    query: str,
    region: str = "us-east-1",
    vector_dimension: int,
) -> None:
    """
    Main entry point for the search command.

    Args:
        assume_role: AWS role to assume for OpenSearch operations
        bedrock_model_id: Bedrock model ID to use
        column: Column to search on
        embedding_column_suffix: Suffix appended to column names for embedding columns (default: _embedding)
        filter_field: Field name for filtering search results
        filter_value: Value for filtering search results
        index: Index name to use
        opensearch_host: OpenSearch host
        opensearch_port: OpenSearch port
        profile: AWS profile to use
        query: Query to search
        region: AWS region
        vector_dimension: Vector dimension for embeddings
    """
    reporter = ConsoleReporter()

    # Validate inputs
    if not query:
        reporter.on_message("Error: Query is required for search command")
        sys.exit(1)

    # Get AWS credentials
    credentials = get_aws_credentials(
        assume_role=assume_role,
        profile=profile,
        region=region,
    )

    # Create OpenSearch client
    opensearch = OpenSearchClient(
        credentials=credentials,
        host=opensearch_host,
        port=opensearch_port,
        region=region,
        reporter=reporter,
    )

    # Build filters from arguments if provided
    filters: list[dict[str, Any]] = []
    if filter_field and filter_value:
        filters.append({"term": {f"{filter_field}.keyword": filter_value}})

    # Print header
    reporter.on_message("=" * 80)
    reporter.on_message(f"{opensearch.count_documents(index=index)} documents in index {index}\n")
    reporter.on_message(f"Target field:  {column}")
    reporter.on_message(f"Searching for: {query}")
    if filters:
        reporter.on_message(f"Filters: {filters}")

    # Call library function to perform search and reranking
    bedrock_client = BedrockClient(region=region)
    try:
        invoke_embedding_model_command = InvokeEmbeddingModelCommand(
            InvokeModelCommand(client=bedrock_client)
        )

        async def get_embedding() -> EmbeddingVector:
            results = await invoke_embedding_model_command.execute(
                inputs=[query],
                model_id=EmbeddingModelId(bedrock_model_id),
                embedding_types=[EmbeddingType.FLOAT],
                output_dimension=vector_dimension,
            )
            return results[0].embeddings[EmbeddingType.FLOAT]

        results = search_and_rerank(
            column=column,
            embedding_column_suffix=embedding_column_suffix,
            get_embedding=get_embedding,
            filters=filters if filters else None,
            index=index,
            opensearch=opensearch,
            profile=profile,
            query=query,
            region=region,
            reporter=reporter,
            top_k=50,
        )
    except Exception as e:
        reporter.on_message(f"Error during search: {e}")
        reporter.on_message(traceback.format_exc())
        sys.exit(1)
    finally:
        # Ensure BedrockClient is properly closed to clean up aiohttp connections
        with contextlib.suppress(Exception):
            asyncio.run(bedrock_client.close())

    # Extract results
    search_results = results["search_results"]
    rerank_results = results["rerank_results"]
    sources = results["sources"]

    # Display search results summary
    reporter.on_message(f"Found {search_results.count} results:")
    reporter.on_message("\n")

    # Display reranking info
    reporter.on_message(f"Reranking {len(sources)} documents...")
    reporter.on_message(f"Query: What is the most relevant description to '{query}'")
    reporter.on_message("=" * 50)

    # Display reranked results
    if rerank_results:
        reporter.on_message("Reranked Results:")
        for i, item in enumerate(rerank_results.get("results", []), 1):
            score = item.get("relevanceScore", 0)
            result_index = item.get("index", 0)

            reporter.on_message(f"{i}. Score: {score:.3f} | Index: {result_index + 1}")
            if "LOINC_NUM" in search_results.hits[result_index]["_source"]:
                reporter.on_message(
                    f"    LOINC_NUM: {search_results.hits[result_index]['_source']['LOINC_NUM']}"
                )
            reporter.on_message(sources[result_index])
            reporter.on_message("")
    else:
        reporter.on_message("Failed to get rerank results")
