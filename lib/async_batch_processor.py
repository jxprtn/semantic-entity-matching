"""Generic async batch processor with queue-based workers and retry logic.

This module provides a reusable pattern for processing large batches of items
asynchronously with configurable workers, retry strategies, and progress tracking.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from botocore.exceptions import ClientError

from lib.logging import get_logger

logger = get_logger(__name__)

# Generic types for input and output
TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class RetryStrategy(Enum):
    """Retry strategy for handling failures."""

    NONE = "none"  # No retries
    IMMEDIATE = "immediate"  # Retry immediately without backoff
    FIXED = "fixed"  # Fixed backoff
    EXPONENTIAL = "exponential"  # Exponential backoff
    JITTERED = "jittered"  # Jittered backoff (random between 0.5-2.0s)


@dataclass
class ProcessorConfig:
    """Configuration for the async batch processor."""

    max_attempts: int = 10
    num_workers: int = 100
    retry_strategy: RetryStrategy = RetryStrategy.JITTERED
    handle_throttling: bool = True
    on_progress: Callable[[int], None] | None = None
    # Optional custom exception handling
    retryable_exceptions: tuple[type[Exception], ...] | None = None
    is_throttling: Callable[[Exception], bool] | None = None

    def __post_init__(self):
        if self.retryable_exceptions is None:
            self.retryable_exceptions = (ClientError,)


@dataclass
class WorkItem[TInput]:
    """Represents a single work item in the queue."""

    index: int
    data: TInput
    remaining_attempts: int


@dataclass
class ProcessorResult[TOutput]:
    """Result of batch processing."""

    results: list[TOutput | Exception]
    total_processed: int
    total_failed: int
    total_retried: int


class AsyncBatchProcessor[TInput, TOutput]:
    """Generic async batch processor using queue-based workers.

    This processor handles:
    - Concurrent execution with configurable workers
    - Automatic retry logic with configurable strategies
    - Progress reporting via callback (for tqdm, logging, metrics, etc.)
    - Result ordering (maintains input order)
    - Exception handling and error collection

    Example usage:

        Define an async processing function and create a processor with items
        and configuration. The processor will handle concurrent execution,
        retries, and progress tracking automatically.
    """

    def __init__(
        self,
        *,
        items: list[TInput],
        processor_func: Callable[[TInput], Awaitable[TOutput]],
        config: ProcessorConfig | None = None,
    ) -> None:
        """Initialize the batch processor.

        Args:
            items: List of items to process
            processor_func: Async function that processes a single item
            config: Processor configuration (defaults to ProcessorConfig())

        """
        self._items = items
        self._processor_func = processor_func
        self._config = config or ProcessorConfig()

        # Statistics (not thread-safe, only for single event loop)
        self._total_retried = 0
        self._total_failed = 0

    async def process(self) -> ProcessorResult[TOutput]:
        """Process all items using queue-based workers.

        Returns:
            ProcessorResult containing results and statistics

        """
        # Pre-allocate results list to maintain order
        results: list[TOutput | Exception | None] = [None] * len(self._items)

        # Create queue and pre-fill with work items
        queue: asyncio.Queue[WorkItem[TInput]] = asyncio.Queue()
        for index, item in enumerate(self._items):
            work_item = WorkItem(
                index=index,
                data=item,
                remaining_attempts=self._config.max_attempts,
            )
            queue.put_nowait(work_item)

        # Start workers
        workers = [
            asyncio.create_task(self._worker(queue, results))
            for _ in range(self._config.num_workers)
        ]

        await asyncio.gather(*workers)

        # Count failures
        total_failed = sum(1 for result in results if isinstance(result, Exception))

        return ProcessorResult(
            results=results,  # type: ignore
            total_processed=len(self._items) - total_failed,
            total_failed=total_failed,
            total_retried=self._total_retried,
        )

    async def _worker(
        self,
        queue: asyncio.Queue[WorkItem[TInput]],
        results: list[TOutput | Exception | None],
    ) -> None:
        """Worker that processes items from the queue.

        Args:
            queue: Queue of work items
            results: Shared results list

        """
        while True:
            try:
                work_item = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                # Process the item
                result = await self._processor_func(work_item.data)
                results[work_item.index] = result

                # Report progress via callback
                if self._config.on_progress:
                    try:
                        self._config.on_progress(1)
                    except Exception as e:
                        logger.warning(f"Progress callback failed: {e}")
                        # Don't fail the task just because progress reporting failed

            except Exception as e:
                # Check if this exception type is configured for retry
                is_retryable = False
                if self._config.retryable_exceptions:
                    is_retryable = isinstance(e, self._config.retryable_exceptions)

                if is_retryable:
                    await self._handle_retryable_error(e, work_item, queue, results)
                else:
                    # Non-retryable exception
                    logger.error(f"Item {work_item.index}: Non-retryable error: {e}")
                    results[work_item.index] = e
                    self._total_failed += 1

            finally:
                queue.task_done()

    async def _handle_retryable_error(
        self,
        error: Exception,
        work_item: WorkItem[TInput],
        queue: asyncio.Queue[WorkItem[TInput]],
        results: list[TOutput | Exception | None],
    ) -> None:
        """Handle retryable errors.

        Args:
            error: The exception that occurred
            work_item: The work item that failed
            queue: The work queue to re-add items to
            results: Shared results list

        """
        # Check if throttling using configured checker or default logic
        is_throttling = False
        error_code = "UnknownError"

        if self._config.is_throttling:
            is_throttling = self._config.is_throttling(error)
            error_code = "ThrottlingException" if is_throttling else str(error)
        elif isinstance(error, ClientError):
            # Default AWS logic
            error_code = error.response.get("Error", {}).get("Code")
            is_throttling = error_code == "ThrottlingException"
        else:
            error_code = str(error)

        # If RetryStrategy.NONE is selected, do not retry regardless of error type
        if self._config.retry_strategy == RetryStrategy.NONE:
            logger.error(f"Item {work_item.index}: Retry disabled by strategy (NONE)")
            results[work_item.index] = error
            self._total_failed += 1
            return

        # Check if we should retry based on error type and remaining attempts
        should_retry = False
        if is_throttling:
            should_retry = self._config.handle_throttling and work_item.remaining_attempts > 1
        else:
            should_retry = work_item.remaining_attempts > 1

        if should_retry:
            # Apply backoff before retrying
            backoff = self._calculate_backoff(work_item.remaining_attempts)
            logger.info(
                f"Item {work_item.index}: {error_code}, retrying in {backoff:.2f}s "
                f"(attempts left: {work_item.remaining_attempts - 1})",
            )

            if backoff > 0:
                await asyncio.sleep(backoff)

            # Re-queue the item
            work_item.remaining_attempts -= 1
            queue.put_nowait(work_item)
            self._total_retried += 1

        else:
            # Exhausted retries or throttling disabled
            logger.error(f"Item {work_item.index}: Failed after all retry attempts")
            results[work_item.index] = error
            self._total_failed += 1

    def _calculate_backoff(self, remaining_attempts: int) -> float:
        """Calculate backoff delay based on retry strategy.

        Args:
            remaining_attempts: Number of remaining retry attempts

        Returns:
            Backoff delay in seconds

        """
        if self._config.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0.0

        if self._config.retry_strategy == RetryStrategy.FIXED:
            return 1.0

        if self._config.retry_strategy == RetryStrategy.EXPONENTIAL:
            attempt_number = self._config.max_attempts - remaining_attempts
            return min(2**attempt_number, 60.0)  # Cap at 60 seconds

        # Default: Use jittered backoff strategy
        return random.uniform(0.5, 2.0)
