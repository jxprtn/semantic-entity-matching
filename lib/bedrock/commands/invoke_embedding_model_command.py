import asyncio
from typing import Any, ClassVar

from lib.bedrock.adapters.base_model_adapter import ModelAdapter
from lib.bedrock.adapters.cohere_model_adapter import CohereModelAdapter
from lib.bedrock.adapters.titan_model_adapter import TitanModelAdapter
from lib.bedrock.commands.base_command import BedrockCommandInterface
from lib.bedrock.commands.invoke_model_command import InvokeModelCommand
from lib.bedrock.types import (
    EmbeddingModelId,
    EmbeddingModelOutput,
    EmbeddingType,
    InputType,
)


class InvokeEmbeddingModelCommand(BedrockCommandInterface):
    __adapters: ClassVar[dict[EmbeddingModelId, ModelAdapter]] = {
        EmbeddingModelId.TITAN: TitanModelAdapter(),
        EmbeddingModelId.COHERE: CohereModelAdapter(),
    }

    def __init__(
        self,
        invoke_model_command: InvokeModelCommand,
    ):
        self.__invoke_model_command = invoke_model_command

    def __get_model_adapter(self, model_id: EmbeddingModelId) -> ModelAdapter:
        """
        Get the appropriate text embedding model adapter for the given model ID.

        Args:
            model_id: Bedrock embedding model ID

        Returns:
            ModelAdapter instance for the model
        """
        if model_id not in self.__adapters:
            raise ValueError(f"Unsupported text embedding model ID: {model_id}")
        return self.__adapters[model_id]

    async def execute(
        self,
        *,
        embedding_types: list[EmbeddingType] | None = None,
        inputs: list[str],
        input_type: InputType = InputType.SEARCH_DOCUMENT,
        model_id: EmbeddingModelId,
        output_dimension: int = 1024,
        **_: Any,
    ) -> list[EmbeddingModelOutput]:
        """
        Generate embeddings using Amazon Bedrock text embedding models.

        Args:
            embedding_types: List of types of embedding to generate
            inputs: List of text to generate embeddings for
            input_type: Type of input to generate embeddings for
            model_id: Bedrock text embedding model ID (e.g., amazon.titan-embed-text-v2:0)
            output_dimension: Desired embedding dimension
        """
        # Default embedding_types to FLOAT if not provided
        if embedding_types is None:
            embedding_types = [EmbeddingType.FLOAT]

        # Get the appropriate text embedding model adapter for this model
        adapter = self.__get_model_adapter(model_id)

        # Validate dimension before formatting input
        adapter.validate_dimension(output_dimension)

        # Format input using the text embedding model adapter
        payloads = adapter.format_input(
            inputs=inputs,
            input_type=input_type,
            embedding_types=embedding_types,
            output_dimension=output_dimension,
        )

        responses = await asyncio.gather(
            *[
                self.__invoke_model_command.execute(model_id=model_id, body=payload)
                for payload in payloads
            ]
        )
        return adapter.format_output(responses=responses)


    def get_tokens_count(self) -> tuple[int, int]:
        return self.__invoke_model_command.get_tokens_count()

    @staticmethod
    def get_model_id(model_id: str) -> EmbeddingModelId:
        """
        Get the EmbeddingModelId enum value for the given model ID.

        Args:
            model_id: Bedrock embedding model ID

        Returns:
            EmbeddingModelId enum value
        """
        try:
            return {model_id.value: model_id for model_id in EmbeddingModelId}[model_id]
        except KeyError as e:
            raise ValueError(f"Unsupported embedding model ID: {model_id}") from e
