"""Dynamic semaphore with automatic concurrency adjustment based on throttling.

Uses AIMD (Additive Increase / Multiplicative Decrease) algorithm:
- On throttle: Reduce capacity by decrease_factor% (multiplicative decrease)
- On success: Increase capacity by 1 after increase_threshold% number of successes (additive increase)
"""

import asyncio
from typing import Any, Literal

from lib.logging import get_logger

logger = get_logger(__name__)


class DynamicSemaphore:
    """A semaphore with adjustable capacity that responds to throttling.

    This implementation uses condition variables to allow precise control
    over capacity changes without recreating semaphores.

    Auto-tuning parameters are calculated based on initial concurrency:
    - min_value: 1 (never go below 1)
    - increase_threshold: 10x initial concurrency (require sustained success)
    - decrease_factor: 0.5 (cut in half on throttle)
    - No maximum capacity - can grow unbounded
    """

    def __init__(
        self,
        *,
        decrease_factor: float = 0.5,
        increase_threshold: int | None = None,
        initial: int = 4,
        log_level: Literal["debug", "info", "none"] = "info",
        min_value: int = 1,
    ) -> None:
        """Initialize the dynamic semaphore.

        Args:
            decrease_factor: Factor to multiply capacity by on throttle (default: 0.5)
            increase_threshold: Number of successes before increasing capacity.
                              If None, defaults to 10x initial concurrency.
            initial: Initial capacity (default: 4)
            log_level: Logging level for capacity changes ("debug", "info", "none")
            min_value: Minimum capacity (default: 1)

        """
        if not 0 < decrease_factor < 1:
            raise ValueError("decrease_factor must be between 0 and 1")
        if initial < min_value:
            raise ValueError(f"initial ({initial}) must be >= min_value ({min_value})")

        self._capacity = initial
        self._min_value = min_value
        self._increase_threshold = (
            increase_threshold if increase_threshold is not None else initial * 10
        )
        self._decrease_factor = decrease_factor
        self._success_count = 0
        self._current_count = 0  # Currently acquired slots
        self._condition = asyncio.Condition()
        self._log_level = log_level

    async def acquire(self) -> None:
        """Acquire a slot, waiting if capacity is full."""
        async with self._condition:
            # Wait until we can acquire
            await self._condition.wait_for(lambda: self._current_count < self._capacity)
            self._current_count += 1

    async def release(self) -> None:
        """Release a slot and notify waiting tasks."""
        async with self._condition:
            self._current_count -= 1
            # Notify one waiting task that a slot is available
            self._condition.notify()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        await self.release()

    async def on_throttle(self) -> None:
        """Decrease capacity when throttled (multiplicative decrease).

        This method should be called when a ThrottlingException is encountered.
        """
        async with self._condition:
            old_capacity = self._capacity
            new_capacity = max(self._min_value, int(self._capacity * self._decrease_factor))

            if new_capacity < old_capacity:
                self._capacity = new_capacity
                self._success_count = 0
                self._log_change("throttle", old_capacity, new_capacity)

    async def on_success(self) -> None:
        """Increase capacity gradually after sustained success (additive increase).

        This method should be called after each successful request.
        Capacity can grow unbounded.
        """
        async with self._condition:
            self._success_count += 1

            if self._success_count >= self._increase_threshold:
                old_capacity = self._capacity
                new_capacity = self._capacity + 1

                self._capacity = new_capacity
                # Notify waiting tasks that capacity increased
                self._condition.notify()
                self._log_change("success", old_capacity, new_capacity)

                self._success_count = 0

    def _log_change(self, reason: str, old_capacity: int, new_capacity: int) -> None:
        """Log capacity changes based on configured log level."""
        if self._log_level == "none":
            return

        message = f"Concurrency adjusted ({reason}): {old_capacity} → {new_capacity}"

        if self._log_level == "debug":
            logger.debug(message)
        elif self._log_level == "info":
            logger.info(message)

    @property
    def capacity(self) -> int:
        """Current capacity of the semaphore."""
        return self._capacity

    @property
    def current_count(self) -> int:
        """Number of currently acquired slots."""
        return self._current_count

    @property
    def success_count(self) -> int:
        """Number of successful requests since last capacity increase."""
        return self._success_count
