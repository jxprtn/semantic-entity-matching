import asyncio


class AsyncCounter:
    def __init__(self, *, initial_value=0) -> None:
        self._count = initial_value
        self._lock = asyncio.Lock()

    async def add(self, value: int) -> None:
        async with self._lock:
            self._count += value

    def value(self) -> int:
        return self._count
