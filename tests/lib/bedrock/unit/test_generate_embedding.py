"""Integration tests for Bedrock generate_embedding method."""

import pytest

from lib.bedrock import EmbeddingModelId, EmbeddingType, InputType, InvokeEmbeddingModelCommand


@pytest.mark.unit
class TestTextEmbeddingModelUnsupportedModel:
    """Unit tests for unsupported model handling."""

    @pytest.mark.asyncio
    async def test_generate_embedding_unsupported_model_raises_value_error(
        self,
        invoke_embedding_model_command: InvokeEmbeddingModelCommand,
    ) -> None:
        """Test that generate_embedding raises ValueError for unsupported models."""
        with pytest.raises(ValueError, match="Unsupported text embedding model ID"):
            await invoke_embedding_model_command.execute(
                embedding_types=[EmbeddingType.FLOAT],
                inputs=["test"],
                input_type=InputType.SEARCH_DOCUMENT,
                model_id="unsupported.model-id:0",
                output_dimension=1024,
            )


@pytest.mark.unit
class TestGenerateEmbeddingDimensionValidation:
    """Unit tests for dimension validation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "model_id,output_dimension,should_raise",
        [
            (EmbeddingModelId.COHERE, 1024, False),
            (EmbeddingModelId.COHERE, 1536, False),
            (EmbeddingModelId.COHERE, 2048, True),
            (EmbeddingModelId.COHERE, 3072, True),
        ],
    )
    async def test_output_dimension_validation(
        self,
        invoke_embedding_model_command: InvokeEmbeddingModelCommand,
        model_id: EmbeddingModelId,
        output_dimension: int,
        should_raise: bool,
    ) -> None:
        """Test that dimension validation works correctly for each model."""
        if should_raise:
            with pytest.raises(ValueError, match="Dimension .* is not supported"):
                await invoke_embedding_model_command.execute(
                    model_id=model_id,
                    inputs=["test"],
                    input_type=InputType.SEARCH_DOCUMENT,
                    embedding_types=[EmbeddingType.FLOAT],
                    output_dimension=output_dimension,
                )
