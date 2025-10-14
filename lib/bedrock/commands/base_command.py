from abc import ABC, abstractmethod
from typing import Any

from lib.bedrock.client import BedrockClient
from lib.counter import AsyncCounter


class BedrockCommandInterface(ABC):
    """Interface for all Bedrock commands."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_tokens_count(self) -> tuple[int, int]:
        raise NotImplementedError


class BedrockCommand(BedrockCommandInterface):
    """Base class for all commands."""

    _client: BedrockClient
    _input_tokens_count: AsyncCounter
    _output_tokens_count: AsyncCounter

    def __init__(self, *, client: BedrockClient):
        self._client = client
        self._input_tokens_count = AsyncCounter()
        self._output_tokens_count = AsyncCounter()

    def get_tokens_count(self):
        return (self._input_tokens_count.value(), self._output_tokens_count.value())

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        raise NotImplementedError
