import os
from typing import Any, cast

import aioboto3  # type: ignore
from botocore.config import Config
from types_aiobotocore_bedrock_runtime import BedrockRuntimeClient

from lib.dynamic_semaphore import DynamicSemaphore


class BedrockClient:
    __client: BedrockRuntimeClient | None
    __client_context: Any
    __config: Config
    __initial_concurrency: int
    __region: str
    __semaphore: DynamicSemaphore | None
    __session: Any

    def __init__(
        self,
        *,
        initial_concurrency: int = 5,
        max_attempts: int = 5,
        profile: str | None = None,
        region: str | None = None,
        timeout: float = 30,
    ):
        self.__client = None
        self.__client_context = None
        self.__config = Config(
            max_pool_connections=initial_concurrency * 10,
            read_timeout=timeout,
            retries={
                "max_attempts": max_attempts - 1,
                "mode": "standard",
            },
        )
        self.__initial_concurrency = initial_concurrency
        self.__region = region or os.getenv("AWS_REGION", "us-east-1")
        self.__semaphore = None
        self.__session = aioboto3.Session(profile_name=profile)

    async def get_client(self) -> BedrockRuntimeClient:
        """
        Get or create the Bedrock runtime client.

        This method ensures the client is created once and reused across all requests,
        which enables connection pooling and eliminates connection setup/teardown overhead.

        Returns:
            BedrockRuntimeClient instance
        """
        if self.__client is None:
            # Create the client context manager
            self.__client_context = self.__session.client(
                "bedrock-runtime",
                config=self.__config,
                region_name=self.__region,
            )
            # Enter the context manager and cache the client
            self.__client = await self.__client_context.__aenter__()

        return cast("BedrockRuntimeClient", self.__client)

    def get_semaphore(self) -> DynamicSemaphore:
        """
        Get or create the dynamic semaphore for the current event loop.

        This method ensures the semaphore is created in the correct event loop
        context, which is important when running in Jupyter notebooks or when
        event loops are created/destroyed (e.g., via asyncio.run()).

        The dynamic semaphore automatically adjusts concurrency based on throttling:
        - Starts at configured concurrency
        - Decreases by 25% on throttle
        - Increases by 1 after sustained success (10x concurrency successful requests)
        - Min: 1, no maximum (can grow unbounded)

        Returns:
            DynamicSemaphore bound to the current event loop
        """
        if self.__semaphore is None:
            self.__semaphore = DynamicSemaphore(
                decrease_factor=0.75,
                initial=self.__initial_concurrency,
                increase_threshold=100,
                log_level="info",
                min_value=1,
            )

        return self.__semaphore

    async def close(self) -> None:
        """
        Close the Bedrock client and clean up connections.

        This method should be called when you're done using the client to ensure
        proper cleanup of HTTP connections and resources.
        """
        if self.__client is not None and self.__client_context is not None:
            await self.__client_context.__aexit__(None, None, None)
            self.__client = None
            self.__client_context = None

    async def __aenter__(self) -> "BedrockClient":
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager and clean up resources."""
        await self.close()
