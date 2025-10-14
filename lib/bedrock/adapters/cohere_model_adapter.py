from typing import Any

from lib.bedrock.adapters.base_model_adapter import ModelAdapter
from lib.bedrock.types import (
    EmbeddingModelOutput,
    EmbeddingType,
    InputType,
    ModelOutputParsingError,
)


class CohereModelAdapter(ModelAdapter):
    """Adapter for Cohere embedding models.

    Response format: {"embeddings": [[float, ...], ...]} or
                     {"embeddings": {"float": [[float, ...], ...]}}
    """

    def get_supported_dimensions(self) -> list[int]:
        """Cohere models support dimensions: 256, 512, 1024, 1536."""
        return [256, 512, 1024, 1536]

    def format_input(
        self,
        *,
        inputs: list[str],
        input_type: InputType,
        embedding_types: list[EmbeddingType],
        output_dimension: int,
    ) -> list[dict[str, Any]]:
        """Format input for Cohere models."""
        return [
            {
                "input_type": input_type.value,
                "texts": inputs,
                "embedding_types": [embedding_type.value for embedding_type in embedding_types],
                "output_dimension": output_dimension,
                "truncate": "NONE",
            }
        ]

    def format_output(self, *, responses: list[dict[str, Any]]) -> list[EmbeddingModelOutput]:
        """Parse Cohere model response."""
        try:
            return [
                EmbeddingModelOutput(
                    embeddings={
                        EmbeddingType(key): values
                        for key, value in response["embeddings"].items()
                        for values in value
                    }
                )
                for response in responses
            ]
        except KeyError as e:
            raise ModelOutputParsingError(
                f"Unexpected response format from Cohere model: {e!s}. "
                f"First response: {self._format_error_message(responses[0] if responses else {})}",
                original_error=e,
            ) from e
