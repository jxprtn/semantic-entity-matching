from typing import Any

from lib.bedrock.adapters.base_model_adapter import ModelAdapter
from lib.bedrock.types import (
    EmbeddingModelOutput,
    EmbeddingType,
    InputType,
    ModelOutputParsingError,
)


class TitanModelAdapter(ModelAdapter):
    """Adapter for Amazon Titan embedding models.

    Response format: {"embedding": [float, ...], "inputTextTokenCount": int}
    """

    def get_supported_dimensions(self) -> list[int]:
        """Titan models only support 1024 dimension (no custom sizes)."""
        return [1024]

    def format_input(
        self,
        *,
        inputs: list[str],
        input_type: InputType = InputType.SEARCH_DOCUMENT,  # noqa: ARG002
        embedding_types: list[EmbeddingType] | None = None,  # noqa: ARG002
        output_dimension: int = 1024,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Format input for Titan models.

        Note: Titan models don't use input_type, embedding_types, or output_dimension,
        but these parameters are part of the ModelAdapter interface.
        """
        return [{"inputText": text_input} for text_input in inputs]

    def format_output(self, *, responses: list[dict[str, Any]]) -> list[EmbeddingModelOutput]:
        """Parse Titan model response: {"embedding": [float, ...]}."""
        try:
            return [
                EmbeddingModelOutput(embeddings={EmbeddingType.FLOAT: response["embedding"]})
                for response in responses
            ]
        except KeyError as e:
            raise ModelOutputParsingError(
                f"Unexpected response format from Titan model: {e!s}. "
                f"First response: {self._format_error_message(responses[0] if responses else {})}",
                original_error=e,
            ) from e
