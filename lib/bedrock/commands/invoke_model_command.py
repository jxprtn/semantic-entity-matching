import json
from typing import Any

from botocore.exceptions import ClientError

from lib.bedrock.commands.base_command import BedrockCommand
from lib.bedrock.types import EmbeddingModelId, ModelId
from lib.logging import get_logger

logger = get_logger(__name__)


class InvokeModelCommand(BedrockCommand):
    async def execute(
        self,
        *,
        model_id: ModelId | EmbeddingModelId,
        body: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        semaphore = self._client.get_semaphore()
        try:
            async with semaphore:
                client = await self._client.get_client()
                response = await client.invoke_model(
                    body=json.dumps(body),
                    modelId=model_id.value,
                    accept="application/json",
                    contentType="application/json",
                    **kwargs,
                )
                result = json.loads(await response["body"].read())

                # Report success to dynamic semaphore
                await semaphore.on_success()

                return result
        except ClientError as e:
            # Check if this is a throttling exception
            error_code = e.response.get("Error", {}).get("Code")
            logger.warning(f"ClientError caught: {error_code}")
            if error_code == "ThrottlingException":
                logger.warning(
                    f"Throttling detected! Reducing concurrency from {semaphore.capacity}"
                )
                await semaphore.on_throttle()
                logger.warning(f"Concurrency reduced to {semaphore.capacity}")
            # Re-raise the exception for retry logic
            raise
