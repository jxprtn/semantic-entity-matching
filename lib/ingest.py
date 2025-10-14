"""Core ingestion functionality for OpenSearch."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import nest_asyncio  # type: ignore
import pandas as pd  # type: ignore

from lib.async_batch_processor import AsyncBatchProcessor, ProcessorConfig
from lib.interfaces import IReporter
from lib.logging import get_logger
from lib.opensearch.client import OpenSearchClient

# Enable nested event loops to allow asyncio.run() in async contexts
nest_asyncio.apply()  # type: ignore

logger = get_logger(__name__)

# Constants
BATCH_SIZE = 50
NUM_WORKERS = 10


@dataclass
class BatchItem:
    """Represents a batch of rows to be indexed."""

    batch_rows: list[dict[str, Any]]
    batch_num: int
    start_idx: int


def _is_valid_value(value: Any) -> bool:
    """Check if value is valid (not None/NaN).

    Handles lists/arrays specially since pd.notna() on arrays returns
    an array, which causes "ambiguous truth value" errors.
    """
    if value is None:
        return False
    # For lists/arrays, they're valid if they exist (even if empty)
    if isinstance(value, (list, tuple)):
        return True
    # For scalar values, use pd.notna
    # pd.notna on a scalar returns a scalar bool
    return bool(pd.notna(value))


def _filter_nan_values(record: dict[str, Any]) -> dict[str, Any]:
    """Filter out NaN/None values from a record dict."""
    return {k: v for k, v in record.items() if _is_valid_value(v)}


def _create_bulk_body(*, batch_rows: list[dict[str, Any]], index_name: str, start_idx: int) -> str:
    """Create bulk indexing body from list of row dicts."""
    bulk_body: list[str] = []
    for idx, row in enumerate(batch_rows):
        doc_id = start_idx + idx
        # Filter out NaN values from the record
        filtered_record = _filter_nan_values(row)
        bulk_body.append(json.dumps({"create": {"_index": index_name, "_id": str(doc_id)}}))
        bulk_body.append(json.dumps(filtered_record))
    return "\n".join(bulk_body) + "\n"


def _parse_bulk_errors(  # noqa: C901
    *,
    response: dict[str, Any],
    batch_num: int,
    reporter: IReporter,
) -> None:
    """Parse and handle errors from bulk indexing response."""
    if not response.get("errors"):
        return

    errors: dict[str, Any] = {}
    error_count = 0

    for item in response["items"]:
        if "create" not in item or "error" not in item["create"]:
            continue

        error_type = item["create"]["error"]["type"]
        error_message = item["create"]["error"]["reason"]
        doc_id = item["create"]["_id"]

        # Handle ignorable errors
        if error_type == "version_conflict_engine_exception":
            reporter.on_message(
                f"  Error ignored while processing item ID '{doc_id}', use --log-level INFO for more details"
            )
            logger.info(error_message)
            continue

        # Track non-ignorable errors
        if error_type not in errors:
            errors[error_type] = {}
        errors[error_type][doc_id] = item["create"]["error"]
        error_count += 1

    if error_count > 0:
        error_types = list(errors.keys())
        error_msg = f"Batch {batch_num} has {error_count} errors ({error_types})"
        reporter.on_message(f"  {error_msg}")
        reporter.on_message("  Use --log-level WARNING for more details")
        logger.warning(errors)
        raise Exception(error_msg)


def ingest(  # noqa: PLR0913
    *,
    delete: bool = False,
    index_name: str,
    max_attempts: int = 5,
    opensearch: OpenSearchClient,
    reporter: IReporter,
    rows: list[dict[str, Any]],
) -> None:
    """Ingests data from a file into an OpenSearch index.

    https://opensearch.org/docs/2.15/ml-commons-plugin/remote-models/batch-ingestion/#step-6-perform-bulk-indexing.

    Args:
        delete: Whether to delete existing index before ingestion
        rows: List of rows to ingest
        index_name: Name of the OpenSearch index
        max_attempts: Maximum number of retry attempts for failed batches (default: 5)
        opensearch: OpenSearchClient instance
        reporter: Reporter instance
    """
    if not len(rows):
        reporter.on_message("No rows to ingest")
        return

    reporter.on_message(f"Processing all columns: {rows[0].keys()}")

    if delete:
        idx = opensearch.indexes.get(index=index_name)
        idx.truncate()
        reporter.on_message(f"Deleted all documents from index {index_name}")

    # Create batches
    batches: list[BatchItem] = [
        BatchItem(
            batch_rows=rows[i : i + BATCH_SIZE],
            batch_num=batch_num,
            start_idx=i,
        )
        for batch_num, i in enumerate(range(0, len(rows), BATCH_SIZE), 1)
    ]

    reporter.on_message(f"Processing {len(batches)} batches of up to {BATCH_SIZE} rows each\n")

    # Define async processor function
    async def process_batch(batch_item: BatchItem) -> dict[str, Any]:
        """Process a single batch - bulk index to OpenSearch."""
        bulk_body = _create_bulk_body(
            batch_rows=batch_item.batch_rows,
            index_name=index_name,
            start_idx=batch_item.start_idx,
        )
        response = await asyncio.to_thread(opensearch.bulk_index, body=bulk_body)

        logger.debug(response)
        _parse_bulk_errors(response=response, batch_num=batch_item.batch_num, reporter=reporter)

        return {"batch_num": batch_item.batch_num, "success": True}

    processor = AsyncBatchProcessor[BatchItem, dict[str, Any]](
        items=batches,
        processor_func=process_batch,
        config=ProcessorConfig(
            max_attempts=max_attempts,
            num_workers=NUM_WORKERS,
            handle_throttling=True,
            on_progress=reporter.on_progress,
        ),
    )

    try:
        reporter.start_progress(total=len(batches))
        asyncio.run(processor.process())
    finally:
        reporter.stop_progress()

    reporter.on_message(f"\nProcessing completed successfully. Processed {len(rows)} rows.\n")
