"""Integration tests for Bedrock generate_embedding method."""

from dataclasses import dataclass, field

import pytest

from lib.bedrock import (
    EmbeddingModelId,
    EmbeddingModelOutput,
    EmbeddingType,
    InputType,
    InvokeEmbeddingModelCommand,
)


@dataclass
class GenerateEmbeddingParams:
    """Parameters for generating an embedding."""

    embedding_types: list[EmbeddingType] | None = field(
        default_factory=lambda: [EmbeddingType.FLOAT]
    )
    input_type: InputType | None = InputType.SEARCH_DOCUMENT
    model_id: EmbeddingModelId | None = EmbeddingModelId.COHERE
    output_dimension: int | None = 1024


@pytest.mark.integration
@pytest.mark.aws
class TestGenerateEmbeddingIntegration:
    """Integration tests for Bedrock generate_embedding method."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "params",
        [
            GenerateEmbeddingParams(),
            GenerateEmbeddingParams(output_dimension=256),
            GenerateEmbeddingParams(output_dimension=512),
            GenerateEmbeddingParams(output_dimension=1536),
            GenerateEmbeddingParams(embedding_types=[EmbeddingType.INT8]),
            GenerateEmbeddingParams(embedding_types=[EmbeddingType.UINT8]),
            GenerateEmbeddingParams(embedding_types=[EmbeddingType.BINARY]),
            GenerateEmbeddingParams(embedding_types=[EmbeddingType.UBINARY]),
            GenerateEmbeddingParams(input_type=InputType.SEARCH_QUERY),
            GenerateEmbeddingParams(input_type=InputType.CLASSIFICATION),
            GenerateEmbeddingParams(input_type=InputType.CLUSTERING),
            GenerateEmbeddingParams(model_id=EmbeddingModelId.TITAN),
        ],
    )
    async def test_generate_embedding(
        self,
        params: GenerateEmbeddingParams,
        invoke_embedding_model_command: InvokeEmbeddingModelCommand,
    ) -> None:
        """Test generate_embedding with different embedding models."""
        outputs = await invoke_embedding_model_command.execute(
            embedding_types=params.embedding_types,
            inputs=["test"],
            input_type=params.input_type,
            model_id=params.model_id,
        )

        # Verify output is a list
        assert isinstance(outputs, list), (
            "Output should be a list of EmbeddingModelOutput objects"
        )
        assert len(outputs) == 1, (
            "Output should contain exactly one EmbeddingModelOutput for a single input"
        )

        # Verify the first element is an EmbeddingModelOutput
        output = outputs[0]
        assert isinstance(output, EmbeddingModelOutput), (
            "Output should be an EmbeddingModelOutput object"
        )

        for embedding_type in params.embedding_types:
            assert embedding_type in output.embeddings, (
                f"Output should contain '{embedding_type.value}' key"
            )
            assert isinstance(output.embeddings[embedding_type], list), (
                f"Output should contain a list for '{embedding_type.value}' key"
            )
