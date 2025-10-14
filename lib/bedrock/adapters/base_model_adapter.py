from abc import ABC, abstractmethod
from typing import Any

from lib.bedrock.types import (
    EmbeddingModelOutput,
    EmbeddingType,
    InputType,
)


class ModelAdapter(ABC):
    """Base adapter for handling different text embedding model formats."""

    @abstractmethod
    def get_supported_dimensions(self) -> list[int]:
        """
        Get the list of supported dimensions for this model.

        Returns:
            List of supported dimension values
        """

    def validate_dimension(self, dimension: int) -> None:
        """
        Validate that the requested dimension is supported by this model.

        Args:
            dimension: Requested embedding dimension

        Raises:
            ValueError: If the dimension is not supported
        """
        supported = self.get_supported_dimensions()
        if dimension not in supported:
            raise ValueError(
                f"Dimension {dimension} is not supported. Supported dimensions: {supported}"
            )

    @abstractmethod
    def format_input(
        self,
        *,
        inputs: list[str],
        input_type: InputType,
        embedding_types: list[EmbeddingType],
        output_dimension: int,
    ) -> list[dict[str, Any]]:
        """
        Format the input payload for the embedding model.

        Some models support multiple inputs in a single request.
        Returning a list of dictionaries representing the input for each request
        allows to run a single request with multiple inputs or multiple requests
        with a single input.

        Args:
            inputs: List of texts to generate embeddings for
            input_type: Type of input to generate embeddings for
            embedding_types: List of types of embedding to generate
            output_dimension: Desired embedding dimension (must be validated first)

        Returns:
            List of dictionaries containing the model-specific payload for each input
        """

    @abstractmethod
    def format_output(self, *, responses: list[dict[str, Any]]) -> list[EmbeddingModelOutput]:
        """
        Parse the response body to extract the embedding vector.

        Args:
            responses: List of parsed JSON responses from the API

        Returns:
            EmbeddingModelOutput containing the embedding vectors

        Raises:
            ModelOutputParsingError: If the response format is unexpected
        """

    def _format_error_message(self, response_body: dict[str, Any], max_length: int = 200) -> str:
        """
        Format error message with truncated response body.

        Args:
            response_body: Response body to format
            max_length: Maximum length of preview

        Returns:
            Truncated error message
        """
        preview = str(response_body)
        if len(preview) > max_length:
            return preview[:max_length] + "..."
        return preview
