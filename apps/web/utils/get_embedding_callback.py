from collections.abc import Callable, Coroutine
from typing import Any

from lib.bedrock import (
    BedrockClient,
    EmbeddingModelId,
    EmbeddingType,
    EmbeddingVector,
    InvokeEmbeddingModelCommand,
    InvokeModelCommand,
)


def get_embedding_callback(
    *,
    bedrock_client: BedrockClient,
    bedrock_model_id: EmbeddingModelId,
    query: str,
    vector_dimension: int,
) -> Callable[[], Coroutine[Any, Any, EmbeddingVector]]:
    """Returns a callback that gets a query embedding."""
    invoke_embedding_model_command = InvokeEmbeddingModelCommand(
        InvokeModelCommand(client=bedrock_client)
    )

    async def get_embedding() -> EmbeddingVector:
        results = await invoke_embedding_model_command.execute(
            inputs=[query],
            model_id=EmbeddingModelId(bedrock_model_id),
            embedding_types=[EmbeddingType.FLOAT],
            output_dimension=vector_dimension,
        )
        return results[0].embeddings[EmbeddingType.FLOAT]

    return get_embedding
