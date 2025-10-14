"""Core vectorization logic for generating embeddings from text data."""

import asyncio
from typing import Any, Literal

import nest_asyncio  # type: ignore
import pandas as pd
from pandas.core.series import Series

from lib.async_batch_processor import AsyncBatchProcessor, ProcessorConfig, ProcessorResult
from lib.bedrock import (
    BedrockClient,
    EmbeddingModelOutput,
    EmbeddingType,
    InputType,
    InvokeEmbeddingModelCommand,
    InvokeModelCommand,
)
from lib.interfaces import IReporter
from lib.logging import get_logger

# Enable nested event loops to allow asyncio.run() in async contexts
nest_asyncio.apply()  # type: ignore

logger = get_logger(__name__)


def vectorize_columns(  # noqa: C901, PLR0913
    *,
    bedrock_model_id: str,
    client: BedrockClient,
    columns: list[str],
    df: pd.DataFrame,
    embedding_column_suffix: str = "_embedding",
    embedding_type: EmbeddingType = EmbeddingType.FLOAT,
    max_attempts: int = 10,
    num_workers: int = 100,
    output_dimension: int = 1024,
    reporter: IReporter,
    strategy: Literal["per-column", "combined"] = "per-column",
) -> pd.DataFrame:
    """Vectorize columns in a CSV/Excel file using AWS Bedrock embeddings.

    Args:
        bedrock_model_id: Bedrock model ID for embeddings
        client: BedrockClient instance
        columns: List of column names to vectorize
        df: DataFrame containing the data
        embedding_column_suffix: Suffix to append to column names for embedding columns
        embedding_type: Type of embedding to generate
        max_attempts: Maximum number of retry attempts for failed requests
        num_workers: Number of concurrent workers (default: 100)
        output_dimension: Desired embedding dimension (default: 1024)
        reporter: Reporter for status messages and progress updates
        strategy: Vectorization strategy ("per-column" or "combined")

    Returns:
        DataFrame with original data plus new embedding columns

    Raises:
        ValueError: If columns don't exist in the file

    """
    # Validate columns exist
    missing_columns = [col for col in columns if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Columns not found in file: {missing_columns}. Available columns: {list(df.columns)}",
        )

    reporter.on_message(f"Vectorizing columns: {columns} using strategy: {strategy}\n")
    invoke_command = InvokeModelCommand(client=client)
    invoke_embedding_model_command = InvokeEmbeddingModelCommand(invoke_command)

    # Convert DataFrame rows to list of Series
    rows = [row for _, row in df.iterrows()]

    # Define async processor function
    async def process_row(row: pd.Series) -> list[EmbeddingModelOutput]:
        return await invoke_embedding_model_command.execute(
            embedding_types=[embedding_type],
            inputs=row[columns].tolist()
            if strategy == "per-column"
            else [" ".join(row[columns].tolist())],
            input_type=InputType.CLASSIFICATION,
            model_id=InvokeEmbeddingModelCommand.get_model_id(bedrock_model_id),
            output_dimension=output_dimension,
        )

    # Process rows using AsyncBatchProcessor
    async def _main() -> ProcessorResult[list[EmbeddingModelOutput]]:
        processor = AsyncBatchProcessor[Series, list[EmbeddingModelOutput]](
            items=rows,
            processor_func=process_row,
            config=ProcessorConfig(
                max_attempts=max_attempts,
                num_workers=num_workers,
                handle_throttling=True,
                on_progress=reporter.on_progress,
            ),
        )
        return await processor.process()

    try:
        reporter.start_progress(total=len(rows))
        processor_result = asyncio.run(_main())
    finally:
        reporter.stop_progress()

    # Get and report token usage
    input_tokens, output_tokens = invoke_embedding_model_command.get_tokens_count()
    reporter.on_message(
        f"\nToken usage: {input_tokens} input tokens, {output_tokens} output tokens"
    )

    # Report statistics
    if processor_result.total_retried > 0:
        reporter.on_message(f"Retried: {processor_result.total_retried} requests")
    if processor_result.total_failed > 0:
        reporter.on_message(f"Failed: {processor_result.total_failed} requests")

    # Check for exceptions and narrow types
    for result in processor_result.results:
        if isinstance(result, Exception):
            raise result

    # At this point, all results are list[EmbeddingModelOutput] (exceptions already raised)
    # Convert requests to embeddings)

    batch_embeddings = [
        [output.embeddings[embedding_type] for output in result]
        for result in processor_result.results
        if not isinstance(result, Exception)
    ]

    if strategy == "per-column":
        if batch_embeddings and len(columns) > 1 and len(batch_embeddings[0]) != len(columns):
            logger.warning(
                "Number of returned embeddings (%d) does not match number of columns (%d). "
                "This might happen if the model combines inputs (e.g. Titan). "
                "Assigning the first embedding to all columns.",
                len(batch_embeddings[0]),
                len(columns),
            )

        for i, column in enumerate(columns):
            # Extract the i-th embedding from each batch
            col_vectors: list[Any] = []
            for batch in batch_embeddings:
                # Use i-th embedding if available, otherwise use 0-th (fallback for combined models)
                idx = i if i < len(batch) else 0
                col_vectors.append(batch[idx])

            df[f"{column}{embedding_column_suffix}"] = col_vectors
    else:
        # Combined strategy
        col_vectors = [batch[0] for batch in batch_embeddings]
        df["_".join(columns) + embedding_column_suffix] = col_vectors

    return df
