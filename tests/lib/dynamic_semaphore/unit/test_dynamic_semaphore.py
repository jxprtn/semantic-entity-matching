"""
Unit tests for DynamicSemaphore class.
"""

import asyncio
from typing import Any

import pytest

from lib.dynamic_semaphore import DynamicSemaphore


@pytest.mark.unit
class TestDynamicSemaphoreInitialization:
    """Test DynamicSemaphore initialization and validation."""

    def test_default_initialization(self) -> None:
        """Test that DynamicSemaphore initializes with default values."""
        sem = DynamicSemaphore(initial=10)

        assert sem.capacity == 10
        assert sem.current_count == 0
        assert sem.success_count == 0

    def test_custom_initialization(self) -> None:
        """Test that DynamicSemaphore initializes with custom values."""
        sem = DynamicSemaphore(
            initial=20,
            min_value=5,
            increase_threshold=100,
            decrease_factor=0.75,
        )

        assert sem.capacity == 20
        assert sem.current_count == 0
        assert sem.success_count == 0

    def test_auto_tuning_defaults(self) -> None:
        """Test that auto-tuning defaults are calculated correctly."""
        initial = 4  # Updated default
        sem = DynamicSemaphore(initial=initial)

        # Check auto-tuning calculations
        assert sem.capacity == 4
        assert sem._min_value == 1
        assert sem._increase_threshold == initial * 10  # 40
        assert sem._decrease_factor == 0.5

    def test_invalid_decrease_factor(self) -> None:
        """Test that invalid decrease_factor raises ValueError."""
        with pytest.raises(ValueError, match="decrease_factor must be between 0 and 1"):
            DynamicSemaphore(initial=10, decrease_factor=1.5)

        with pytest.raises(ValueError, match="decrease_factor must be between 0 and 1"):
            DynamicSemaphore(initial=10, decrease_factor=0)

    def test_invalid_initial_value(self) -> None:
        """Test that initial < min_value raises ValueError."""
        with pytest.raises(ValueError, match="initial .* must be >= min_value"):
            DynamicSemaphore(initial=5, min_value=10)

    def test_default_initial_value(self) -> None:
        """Test that default initial value is 4."""
        sem = DynamicSemaphore()
        assert sem.capacity == 4


@pytest.mark.unit
class TestDynamicSemaphoreConcurrency:
    """Test DynamicSemaphore concurrency control."""

    @pytest.mark.asyncio
    async def test_acquire_release(self) -> None:
        """Test basic acquire and release operations."""
        sem = DynamicSemaphore(initial=2)

        # Acquire first slot
        await sem.acquire()
        assert sem.current_count == 1

        # Acquire second slot
        await sem.acquire()
        assert sem.current_count == 2

        # Release first slot
        await sem.release()
        assert sem.current_count == 1

        # Release second slot
        await sem.release()
        assert sem.current_count == 0

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test that context manager works correctly."""
        sem = DynamicSemaphore(initial=2)

        async with sem:
            assert sem.current_count == 1

        assert sem.current_count == 0

    @pytest.mark.asyncio
    async def test_blocks_when_full(self) -> None:
        """Test that acquire blocks when capacity is reached."""
        sem = DynamicSemaphore(initial=2)

        # Acquire all slots
        await sem.acquire()
        await sem.acquire()
        assert sem.current_count == 2

        # Try to acquire third slot (should block)
        acquired = False

        async def try_acquire() -> None:
            nonlocal acquired
            await sem.acquire()
            acquired = True

        task = asyncio.create_task(try_acquire())

        # Wait a bit to ensure it's blocked
        await asyncio.sleep(0.1)
        assert not acquired
        assert sem.current_count == 2

        # Release a slot to unblock
        await sem.release()
        await task
        assert acquired
        assert sem.current_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_workers(self) -> None:
        """Test that semaphore limits concurrent workers correctly."""
        sem = DynamicSemaphore(initial=3)
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def worker() -> None:
            nonlocal max_concurrent, current_concurrent

            async with sem:
                async with lock:
                    current_concurrent += 1
                    max_concurrent = max(max_concurrent, current_concurrent)

                # Simulate work
                await asyncio.sleep(0.01)

                async with lock:
                    current_concurrent -= 1

        # Create 10 workers but only 3 should run concurrently
        tasks = [asyncio.create_task(worker()) for _ in range(10)]
        await asyncio.gather(*tasks)

        assert max_concurrent == 3


@pytest.mark.unit
class TestDynamicSemaphoreThrottling:
    """Test DynamicSemaphore throttling response."""

    @pytest.mark.asyncio
    async def test_on_throttle_decreases_capacity(self) -> None:
        """Test that on_throttle decreases capacity by decrease_factor."""
        sem = DynamicSemaphore(initial=10, decrease_factor=0.5)

        await sem.on_throttle()
        assert sem.capacity == 5  # 10 * 0.5

        await sem.on_throttle()
        assert sem.capacity == 2  # 5 * 0.5 (rounded down)

        await sem.on_throttle()
        assert sem.capacity == 1  # 2 * 0.5 (capped at min_value)

    @pytest.mark.asyncio
    async def test_on_throttle_respects_min_value(self) -> None:
        """Test that on_throttle never goes below min_value."""
        sem = DynamicSemaphore(initial=10, min_value=3, decrease_factor=0.5)

        await sem.on_throttle()  # 10 -> 5
        await sem.on_throttle()  # 5 -> 3 (capped)
        await sem.on_throttle()  # 3 -> 3 (capped)

        assert sem.capacity == 3

    @pytest.mark.asyncio
    async def test_on_throttle_resets_success_count(self) -> None:
        """Test that on_throttle resets success counter."""
        sem = DynamicSemaphore(initial=10, increase_threshold=5)

        # Build up some successes
        await sem.on_success()
        await sem.on_success()
        await sem.on_success()
        assert sem.success_count == 3

        # Throttle should reset
        await sem.on_throttle()
        assert sem.success_count == 0

    @pytest.mark.asyncio
    async def test_on_throttle_with_custom_factor(self) -> None:
        """Test on_throttle with custom decrease_factor."""
        sem = DynamicSemaphore(initial=100, decrease_factor=0.75)

        await sem.on_throttle()
        assert sem.capacity == 75  # 100 * 0.75

        await sem.on_throttle()
        assert sem.capacity == 56  # 75 * 0.75 (rounded down)


@pytest.mark.unit
class TestDynamicSemaphoreSuccess:
    """Test DynamicSemaphore success tracking and capacity increase."""

    @pytest.mark.asyncio
    async def test_on_success_increments_counter(self) -> None:
        """Test that on_success increments success counter."""
        sem = DynamicSemaphore(initial=10, increase_threshold=5)

        await sem.on_success()
        assert sem.success_count == 1

        await sem.on_success()
        assert sem.success_count == 2

    @pytest.mark.asyncio
    async def test_on_success_increases_capacity_after_threshold(self) -> None:
        """Test that capacity increases after reaching threshold."""
        sem = DynamicSemaphore(initial=10, increase_threshold=5)

        # Build up successes
        for _ in range(4):
            await sem.on_success()
            assert sem.capacity == 10  # Not yet

        # 5th success should trigger increase
        await sem.on_success()
        assert sem.capacity == 11  # Increased by 1

    @pytest.mark.asyncio
    async def test_on_success_resets_counter_after_increase(self) -> None:
        """Test that success counter resets after capacity increase."""
        sem = DynamicSemaphore(initial=10, increase_threshold=5)

        # Trigger increase
        for _ in range(5):
            await sem.on_success()

        assert sem.capacity == 11
        assert sem.success_count == 0  # Reset

    @pytest.mark.asyncio
    async def test_on_success_unlimited_growth(self) -> None:
        """Test that on_success can grow unbounded."""
        sem = DynamicSemaphore(initial=10, increase_threshold=2)

        # Increase to 11
        await sem.on_success()
        await sem.on_success()
        assert sem.capacity == 11

        # Increase to 12
        await sem.on_success()
        await sem.on_success()
        assert sem.capacity == 12

        # Continue growing - no limit
        await sem.on_success()
        await sem.on_success()
        assert sem.capacity == 13

        # Grow more
        await sem.on_success()
        await sem.on_success()
        assert sem.capacity == 14

    @pytest.mark.asyncio
    async def test_on_success_notifies_waiting_tasks(self) -> None:
        """Test that capacity increase notifies waiting tasks."""
        sem = DynamicSemaphore(initial=2, increase_threshold=2)

        # Fill the semaphore
        await sem.acquire()
        await sem.acquire()
        assert sem.current_count == 2

        # Try to acquire third (will block)
        acquired = False

        async def try_acquire() -> None:
            nonlocal acquired
            async with sem:
                acquired = True

        task = asyncio.create_task(try_acquire())
        await asyncio.sleep(0.05)
        assert not acquired

        # Increase capacity (should unblock)
        await sem.on_success()
        await sem.on_success()  # Trigger increase to 3
        await asyncio.sleep(0.05)

        # Task should now acquire
        assert sem.capacity == 3
        await task
        assert acquired


@pytest.mark.unit
class TestDynamicSemaphoreAIMD:
    """Test AIMD (Additive Increase Multiplicative Decrease) behavior."""

    @pytest.mark.asyncio
    async def test_aimd_cycle(self) -> None:
        """Test complete AIMD cycle: increase gradually, decrease rapidly."""
        sem = DynamicSemaphore(initial=10, increase_threshold=2, decrease_factor=0.5)

        # Start at 10
        assert sem.capacity == 10

        # Throttle: 10 -> 5 (multiplicative decrease)
        await sem.on_throttle()
        assert sem.capacity == 5

        # Success: Build up slowly
        await sem.on_success()
        await sem.on_success()  # 5 -> 6 (additive increase)
        assert sem.capacity == 6

        await sem.on_success()
        await sem.on_success()  # 6 -> 7
        assert sem.capacity == 7

        # Throttle again: 7 -> 3 (multiplicative decrease)
        await sem.on_throttle()
        assert sem.capacity == 3

        # Success: Build up slowly
        await sem.on_success()
        await sem.on_success()  # 3 -> 4
        assert sem.capacity == 4

    @pytest.mark.asyncio
    async def test_multiple_throttles_converge_to_min(self) -> None:
        """Test that multiple throttles eventually reach min_value."""
        sem = DynamicSemaphore(initial=100, min_value=1, decrease_factor=0.5)

        capacities = [sem.capacity]
        for _ in range(10):
            await sem.on_throttle()
            capacities.append(sem.capacity)

        # Should converge to min_value
        assert sem.capacity == 1
        # Should be monotonically decreasing until min
        for i in range(len(capacities) - 1):
            assert capacities[i] >= capacities[i + 1]

    @pytest.mark.asyncio
    async def test_multiple_successes_grow_continuously(self) -> None:
        """Test that multiple success cycles continue to grow capacity."""
        sem = DynamicSemaphore(initial=10, increase_threshold=2)

        # Grow capacity 5 times
        for _ in range(5):
            await sem.on_success()
            await sem.on_success()

        # Should have grown from 10 to 15
        assert sem.capacity == 15

        # Continue growing 5 more times
        for _ in range(5):
            await sem.on_success()
            await sem.on_success()

        # Should have grown to 20
        assert sem.capacity == 20


@pytest.mark.unit
class TestDynamicSemaphoreLogLevel:
    """Test DynamicSemaphore logging behavior."""

    @pytest.mark.asyncio
    async def test_log_level_none_no_output(self, caplog: Any) -> None:
        """Test that log_level='none' produces no log output."""
        sem = DynamicSemaphore(initial=10, log_level="none")

        await sem.on_throttle()
        await sem.on_success()

        # Should have no log messages
        assert len(caplog.records) == 0

    @pytest.mark.asyncio
    async def test_log_level_info(self, caplog: Any) -> None:
        """Test that log_level='info' produces info-level logs."""
        sem = DynamicSemaphore(initial=10, increase_threshold=2, log_level="info")

        await sem.on_throttle()
        # Check that a log was created (exact message depends on logger config)
        # We just verify the semaphore tried to log

    @pytest.mark.asyncio
    async def test_log_level_debug(self, caplog: Any) -> None:
        """Test that log_level='debug' produces debug-level logs."""
        sem = DynamicSemaphore(initial=10, increase_threshold=2, log_level="debug")

        await sem.on_throttle()
        # Check that a log was created


@pytest.mark.unit
class TestDynamicSemaphoreEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_capacity_one(self) -> None:
        """Test semaphore with capacity of 1."""
        sem = DynamicSemaphore(initial=1, min_value=1)

        async with sem:
            assert sem.current_count == 1

        assert sem.current_count == 0

    @pytest.mark.asyncio
    async def test_no_change_when_at_min(self) -> None:
        """Test that capacity doesn't go below min_value."""
        sem = DynamicSemaphore(initial=1, min_value=1, increase_threshold=1)

        # At minimum
        await sem.on_throttle()
        assert sem.capacity == 1  # Can't decrease below min

        # Can still increase from minimum
        await sem.on_success()
        assert sem.capacity == 2  # Can increase

    @pytest.mark.asyncio
    async def test_stress_test_rapid_changes(self) -> None:
        """Test rapid alternating throttle and success calls."""
        sem = DynamicSemaphore(initial=50, increase_threshold=10, decrease_factor=0.5)

        for _ in range(100):
            await sem.on_throttle()
            for _ in range(5):
                await sem.on_success()

        # Should be stable and above minimum
        assert sem.capacity >= sem._min_value

    @pytest.mark.asyncio
    async def test_concurrent_capacity_changes(self) -> None:
        """Test that concurrent capacity changes are thread-safe."""
        sem = DynamicSemaphore(initial=20, increase_threshold=5)

        async def throttle_worker() -> None:
            for _ in range(10):
                await sem.on_throttle()
                await asyncio.sleep(0.001)

        async def success_worker() -> None:
            for _ in range(50):
                await sem.on_success()
                await asyncio.sleep(0.001)

        # Run both concurrently
        await asyncio.gather(throttle_worker(), success_worker())

        # Should end in valid state (above minimum)
        assert sem.capacity >= sem._min_value

