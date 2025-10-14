"""
Unit tests for AsyncBatchProcessor module.

Tests follow Arrange-Act-Assert pattern and use fixtures for common setup.
"""

import asyncio
from collections.abc import Callable

import pytest
from botocore.exceptions import ClientError

from lib.async_batch_processor import (
    AsyncBatchProcessor,
    ProcessorConfig,
    ProcessorResult,
    RetryStrategy,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def simple_items() -> list[int]:
    """Common test items."""
    return [1, 2, 3, 4, 5]


@pytest.fixture
def progress_tracker() -> Callable[[int], None]:
    """Fixture for tracking progress calls."""
    calls: list[int] = []

    def track(n: int) -> None:
        calls.append(n)

    track.calls = calls  # type: ignore
    return track


@pytest.fixture
def throttling_error() -> Callable[[], ClientError]:
    """Fixture for creating throttling errors."""

    def create_error() -> ClientError:
        return ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Throttled"}},
            "test_operation",
        )

    return create_error


@pytest.fixture
def service_error() -> Callable[[], ClientError]:
    """Fixture for creating non-throttling service errors."""

    def create_error() -> ClientError:
        return ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "Service down"}},
            "test_operation",
        )

    return create_error


# ============================================================================
# Basic Functionality Tests
# ============================================================================


@pytest.mark.unit
class TestBasicFunctionality:
    """Tests for basic AsyncBatchProcessor functionality."""

    @pytest.mark.asyncio
    async def test_basic_processing(self, simple_items: list[int]) -> None:
        """Test basic item processing without errors."""

        # Arrange
        async def double(x: int) -> int:
            return x * 2

        processor = AsyncBatchProcessor(
            items=simple_items,
            processor_func=double,
            config=ProcessorConfig(num_workers=2),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 5
        assert result.total_failed == 0
        assert result.total_retried == 0
        assert result.results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_empty_items_list(self) -> None:
        """Test processing with empty items list."""

        # Arrange
        async def double(x: int) -> int:
            return x * 2

        processor = AsyncBatchProcessor(
            items=[],
            processor_func=double,
            config=ProcessorConfig(),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 0
        assert result.total_failed == 0
        assert result.total_retried == 0
        assert result.results == []

    @pytest.mark.asyncio
    async def test_result_ordering_maintained(self) -> None:
        """Test that results maintain input order despite async processing."""

        # Arrange
        async def process_with_delay(x: int) -> int:
            # Add variable delay to ensure workers finish out of order
            await asyncio.sleep(0.01 * (10 - x))
            return x * 2

        items = list(range(10))
        processor = AsyncBatchProcessor(
            items=items,
            processor_func=process_with_delay,
            config=ProcessorConfig(num_workers=5),
        )

        # Act
        result = await processor.process()

        # Assert - Results should still be in original order
        assert result.results == [x * 2 for x in items]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_workers", [1, 2, 10, 100])
    async def test_various_worker_counts(self, simple_items: list[int], num_workers: int) -> None:
        """Test processing with various worker counts."""

        # Arrange
        async def double(x: int) -> int:
            return x * 2

        processor = AsyncBatchProcessor(
            items=simple_items,
            processor_func=double,
            config=ProcessorConfig(num_workers=num_workers),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == len(simple_items)
        assert result.results == [x * 2 for x in simple_items]

    @pytest.mark.asyncio
    async def test_complex_return_types(self) -> None:
        """Test processing with complex return types."""

        # Arrange
        async def dict_func(x: int) -> dict[str, int]:
            return {"value": x, "double": x * 2}

        items = [1, 2, 3]
        processor = AsyncBatchProcessor(
            items=items,
            processor_func=dict_func,
            config=ProcessorConfig(),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 3
        assert result.results[0] == {"value": 1, "double": 2}
        assert result.results[1] == {"value": 2, "double": 4}
        assert result.results[2] == {"value": 3, "double": 6}


# ============================================================================
# Progress Tracking Tests
# ============================================================================


@pytest.mark.unit
class TestProgressTracking:
    """Tests for progress callback functionality."""

    @pytest.mark.asyncio
    async def test_progress_callback_invoked(self, simple_items: list[int], progress_tracker: Callable[[int], None]) -> None:
        """Test that progress callback is invoked for each processed item."""

        # Arrange
        async def double(x: int) -> int:
            return x * 2

        processor = AsyncBatchProcessor(
            items=simple_items,
            processor_func=double,
            config=ProcessorConfig(num_workers=2, on_progress=progress_tracker),
        )

        # Act
        result = await processor.process()

        # Assert
        assert len(progress_tracker.calls) == len(simple_items)
        assert sum(progress_tracker.calls) == len(simple_items)
        assert result.total_processed == len(simple_items)

    @pytest.mark.asyncio
    async def test_progress_callback_none(self, simple_items: list[int]) -> None:
        """Test that processing works without progress callback."""

        # Arrange
        async def double(x: int) -> int:
            return x * 2

        processor = AsyncBatchProcessor(
            items=simple_items,
            processor_func=double,
            config=ProcessorConfig(on_progress=None),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == len(simple_items)
        assert result.results == [x * 2 for x in simple_items]

    @pytest.mark.asyncio
    async def test_progress_callback_exception_handled(self) -> None:
        """Test that exception in progress callback is caught and handled."""
        # Arrange
        call_count = 0

        def failing_progress(n: int) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Progress callback failed")

        async def double(x: int) -> int:
            return x * 2

        processor = AsyncBatchProcessor(
            items=[1, 2, 3],
            processor_func=double,
            config=ProcessorConfig(on_progress=failing_progress, num_workers=1),
        )

        # Act
        result = await processor.process()

        # Assert - Exception in callback should be ignored, processing succeeds
        assert result.total_processed == 3
        assert result.total_failed == 0
        assert result.results == [2, 4, 6]


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling and exception behavior."""

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self) -> None:
        """Test handling of non-retryable exceptions."""

        # Arrange
        async def failing_func(x: int) -> int:
            if x == 2:
                raise ValueError(f"Failed on {x}")
            return x * 2

        processor = AsyncBatchProcessor(
            items=[1, 2, 3],
            processor_func=failing_func,
            config=ProcessorConfig(num_workers=1),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 2
        assert result.total_failed == 1
        assert result.total_retried == 0
        assert result.results[0] == 2
        assert isinstance(result.results[1], ValueError)
        assert result.results[2] == 6

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self) -> None:
        """Test processing with mixed success and failure."""

        # Arrange
        async def mixed_func(x: int) -> int:
            if x % 2 == 0:
                raise ValueError(f"Even number: {x}")
            return x * 2

        items = [1, 2, 3, 4, 5]
        processor = AsyncBatchProcessor(
            items=items,
            processor_func=mixed_func,
            config=ProcessorConfig(num_workers=2),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 3  # 1, 3, 5 succeeded
        assert result.total_failed == 2  # 2, 4 failed
        assert result.results[0] == 2
        assert isinstance(result.results[1], ValueError)
        assert result.results[2] == 6
        assert isinstance(result.results[3], ValueError)
        assert result.results[4] == 10


# ============================================================================
# Retry Logic Tests
# ============================================================================


@pytest.mark.unit
class TestRetryLogic:
    """Tests for retry logic and throttling handling."""

    @pytest.mark.asyncio
    async def test_throttling_with_successful_retry(self, throttling_error: Callable[[], ClientError]) -> None:
        """Test handling of throttling exceptions with successful retry."""
        # Arrange
        call_count = {}

        async def throttling_func(x: int) -> int:
            call_count[x] = call_count.get(x, 0) + 1
            # Fail on first attempt, succeed on second
            if call_count[x] == 1:
                raise throttling_error()
            return x * 2

        processor = AsyncBatchProcessor(
            items=[1, 2, 3],
            processor_func=throttling_func,
            config=ProcessorConfig(
                num_workers=1,
                max_attempts=3,
                handle_throttling=True,
            ),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 3
        assert result.total_failed == 0
        assert result.total_retried == 3  # One retry per item
        assert result.results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_throttling_exhausted_retries(self, throttling_error: Callable[[], ClientError]) -> None:
        """Test throttling that exhausts all retry attempts."""

        # Arrange
        async def always_throttle(x: int) -> int:
            raise throttling_error()

        processor = AsyncBatchProcessor(
            items=[1, 2],
            processor_func=always_throttle,
            config=ProcessorConfig(
                num_workers=1,
                max_attempts=2,
                handle_throttling=True,
            ),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 0
        assert result.total_failed == 2
        assert result.total_retried == 2  # One retry per item before giving up
        assert all(isinstance(r, ClientError) for r in result.results)

    @pytest.mark.asyncio
    async def test_other_client_error_with_retry(self, service_error: Callable[[], ClientError]) -> None:
        """Test handling of non-throttling ClientError with retry."""
        # Arrange
        call_count = {}

        async def client_error_func(x: int) -> int:
            call_count[x] = call_count.get(x, 0) + 1
            # Fail on first attempt
            if call_count[x] == 1:
                raise service_error()
            return x * 2

        processor = AsyncBatchProcessor(
            items=[1],
            processor_func=client_error_func,
            config=ProcessorConfig(num_workers=1, max_attempts=3),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 1
        assert result.total_failed == 0
        assert result.total_retried == 1
        assert result.results == [2]

    @pytest.mark.asyncio
    async def test_throttling_retry_disabled(self, throttling_error: Callable[[], ClientError]) -> None:
        """Test that throttling retry can be disabled."""

        # Arrange
        async def throttling_func(x: int) -> int:
            raise throttling_error()

        processor = AsyncBatchProcessor(
            items=[1],
            processor_func=throttling_func,
            config=ProcessorConfig(
                num_workers=1,
                max_attempts=3,
                handle_throttling=False,  # Disable throttling retry
            ),
        )

        # Act
        result = await processor.process()

        # Assert - Should fail immediately without retry
        assert result.total_processed == 0
        assert result.total_failed == 1
        assert isinstance(result.results[0], ClientError)


# ============================================================================
# Retry Strategy Tests
# ============================================================================


@pytest.mark.unit
class TestRetryStrategies:
    """Tests for different retry strategies."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "strategy",
        [
            RetryStrategy.JITTERED,
            RetryStrategy.FIXED,
            RetryStrategy.EXPONENTIAL,
        ],
    )
    async def test_retry_strategies(self, strategy: RetryStrategy, throttling_error: Callable[[], ClientError]) -> None:
        """Test retry strategies that should succeed after retry."""
        # Arrange
        call_count = 0

        async def fail_once(x: int) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise throttling_error()
            return x * 2

        processor = AsyncBatchProcessor(
            items=[1],
            processor_func=fail_once,
            config=ProcessorConfig(
                retry_strategy=strategy,
                max_attempts=2,
            ),
        )

        # Act
        result = await processor.process()

        # Assert - All strategies should succeed after retry
        assert result.total_processed == 1
        assert result.total_retried == 1
        assert result.results == [2]

    @pytest.mark.asyncio
    async def test_retry_strategy_none(self, throttling_error: Callable[[], ClientError]) -> None:
        """Test RetryStrategy.NONE results in immediate failure."""

        # Arrange
        async def fail_always(x: int) -> int:
            raise throttling_error()

        processor = AsyncBatchProcessor(
            items=[1],
            processor_func=fail_always,
            config=ProcessorConfig(
                retry_strategy=RetryStrategy.NONE,
                max_attempts=3,  # Should be ignored
            ),
        )

        # Act
        result = await processor.process()

        # Assert - Should fail immediately without retry
        assert result.total_processed == 0
        assert result.total_failed == 1
        assert result.total_retried == 0
        assert isinstance(result.results[0], ClientError)

    @pytest.mark.asyncio
    async def test_custom_exception_retry(self) -> None:
        """Test retrying on custom exceptions."""
        # Arrange
        call_count = 0

        class CustomError(Exception):
            pass

        async def fail_once(x: int) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise CustomError("Temporary failure")
            return x * 2

        processor = AsyncBatchProcessor(
            items=[1],
            processor_func=fail_once,
            config=ProcessorConfig(
                retryable_exceptions=(CustomError,),
                max_attempts=2,
            ),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 1
        assert result.total_retried == 1
        assert result.total_failed == 0
        assert result.results == [2]


# ============================================================================
# Configuration Tests
# ============================================================================


@pytest.mark.unit
class TestConfiguration:
    """Tests for ProcessorConfig and configuration behavior."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        # Arrange & Act
        config = ProcessorConfig()

        # Assert
        assert config.max_attempts == 10
        assert config.num_workers == 100
        assert config.retry_strategy == RetryStrategy.JITTERED
        assert config.handle_throttling is True
        assert config.on_progress is None

    def test_custom_config(self) -> None:
        """Test custom configuration values."""

        # Arrange
        def my_progress(n: int) -> None:
            pass

        # Act
        config = ProcessorConfig(
            max_attempts=5,
            num_workers=20,
            retry_strategy=RetryStrategy.EXPONENTIAL,
            handle_throttling=False,
            on_progress=my_progress,
            retryable_exceptions=(ValueError,),
        )

        # Assert
        assert config.max_attempts == 5
        assert config.num_workers == 20
        assert config.retry_strategy == RetryStrategy.EXPONENTIAL
        assert config.handle_throttling is False
        assert config.on_progress == my_progress
        assert config.retryable_exceptions == (ValueError,)


# ============================================================================
# Result Tests
# ============================================================================


@pytest.mark.unit
class TestProcessorResult:
    """Tests for ProcessorResult."""

    def test_processor_result_creation(self) -> None:
        """Test ProcessorResult creation and attributes."""
        # Arrange & Act
        result = ProcessorResult(
            results=[1, 2, 3],
            total_processed=3,
            total_failed=0,
            total_retried=0,
        )

        # Assert
        assert result.results == [1, 2, 3]
        assert result.total_processed == 3
        assert result.total_failed == 0
        assert result.total_retried == 0


# ============================================================================
# Performance and Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.slow
class TestPerformanceAndEdgeCases:
    """Tests for performance and edge cases."""

    @pytest.mark.asyncio
    async def test_very_large_batch(self) -> None:
        """Test processing with large number of items."""

        # Arrange
        async def identity(x: int) -> int:
            return x

        items = list(range(1000))
        processor = AsyncBatchProcessor(
            items=items,
            processor_func=identity,
            config=ProcessorConfig(num_workers=50),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 1000
        assert result.total_failed == 0
        assert len(result.results) == 1000
        assert result.results == items

    @pytest.mark.asyncio
    async def test_more_workers_than_items(self, simple_items: list[int]) -> None:
        """Test with more workers than items."""

        # Arrange
        async def double(x: int) -> int:
            return x * 2

        processor = AsyncBatchProcessor(
            items=simple_items,
            processor_func=double,
            config=ProcessorConfig(num_workers=100),  # More workers than items
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == len(simple_items)
        assert result.results == [x * 2 for x in simple_items]

    @pytest.mark.asyncio
    async def test_concurrent_processing_integrity(self) -> None:
        """Test that concurrent workers don't corrupt shared state."""
        # Arrange
        processed_items = set()

        async def track_item(x: int) -> int:
            processed_items.add(x)
            await asyncio.sleep(0.01)  # Allow concurrency
            return x * 2

        items = list(range(20))
        processor = AsyncBatchProcessor(
            items=items,
            processor_func=track_item,
            config=ProcessorConfig(num_workers=10),
        )

        # Act
        result = await processor.process()

        # Assert
        assert result.total_processed == 20
        assert len(processed_items) == 20
        assert result.results == [x * 2 for x in items]
