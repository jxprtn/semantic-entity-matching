from pathlib import Path
from typing import Any, cast

from types_aiobotocore_bedrock_runtime.type_defs import (
    ContentBlockTypeDef,
    ConverseResponseTypeDef,
    InferenceConfigurationTypeDef,
    MessageTypeDef,
)

from lib.bedrock.commands.base_command import BedrockCommand
from lib.bedrock.types import ModelId


def _remove_none_items(items: list[Any | None]) -> list[Any]:
    return [item for item in items if item is not None]


class ConverseCommand(BedrockCommand):
    async def execute(
        self,
        *,
        file_path: str | None = None,
        inference_config: InferenceConfigurationTypeDef | None = None,
        model_id: ModelId = ModelId.SONNET_4_5_20250929_V1,
        prefill: str | None = None,
        system_prompt: str | None = None,
        user_prompt: str,
    ) -> str:
        """
        Converse with a Bedrock model.

        Args:
            file_path: Path to the file to analyze
            inference_config: Inference configuration
            model_id: Model ID
            prefill: Text to prefill the model response with
            system_prompt: System prompt for the conversation
            user_prompt: User prompt for the conversation

        Returns:
            Response text from the model
        """
        messages = _remove_none_items(
            [
                {
                    "role": "user",
                    "content": _remove_none_items(
                        [
                            {"text": user_prompt},
                            self.__get_content_block(file_path=file_path) if file_path else None,
                        ]
                    ),
                },
                {"role": "assistant", "content": [{"text": prefill}]} if prefill else None,
            ]
        )

        response = await self.__converse(
            inference_config=inference_config or {"temperature": 0},
            model_id=model_id,
            system_prompt=system_prompt,
            messages=messages,
        )

        await self._input_tokens_count.add(response["usage"]["inputTokens"])
        await self._output_tokens_count.add(response["usage"]["outputTokens"])

        return response["output"]["message"]["content"][0]["text"]

    async def __converse(
        self,
        *,
        inference_config: InferenceConfigurationTypeDef | None = None,
        messages: list[MessageTypeDef],
        model_id: ModelId = ModelId.SONNET_4_5_20250929_V1,
        system_prompt: str | None = None,
    ) -> ConverseResponseTypeDef:
        async with self._client.get_semaphore():
            client = await self._client.get_client()
            return await client.converse(
                messages=messages,
                system=[{"text": system_prompt}] if system_prompt else [],
                modelId=model_id.value,
                inferenceConfig=inference_config or {"temperature": 0.0},
            )

    def __get_content_block(
        self,
        *,
        file_path: str,
    ) -> ContentBlockTypeDef:
        """
        Query Bedrock with the Converse API using a multimodal approach.
        Attaches a file and sends a query about its contents.

        Args:
            file_path: Path to the file to analyze
            inference_config: Additional inference configuration
            model_id: Bedrock model ID (default: Claude 3.5 Sonnet)
            prefill: Text to prefill the model response with
            system_prompt: System prompt for the conversation
            user_prompt: User prompt for the conversation

        Returns:
            Response text from the model
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Read the file content as bytes
        file_content = path.read_bytes()

        # Get file extension without the dot
        file_extension = path.suffix.lower().lstrip(".")

        # Define supported formats
        image_formats = {"jpg", "jpeg", "png", "gif", "webp"}
        document_formats = {
            "csv",
            "xls",
            "xlsx",
            "doc",
            "docx",
            "txt",
            "md",
            "pdf",
            "html",
        }

        # Prepare message content based on file type
        if file_extension in image_formats:
            # For images, use the image format
            file_content_block = {
                "image": {"format": file_extension, "source": {"bytes": file_content}}
            }
        elif file_extension in document_formats:
            # For documents, use the document format
            file_content_block = {
                "document": {
                    "name": path.stem,  # Use stem to remove extension
                    "format": file_extension,
                    "source": {"bytes": file_content},
                }
            }
        else:
            # For unsupported formats, try as document
            file_content_block = {
                "document": {
                    "name": path.stem,  # Use stem to remove extension
                    "format": file_extension,
                    "source": {"bytes": file_content},
                }
            }

        return cast("ContentBlockTypeDef", file_content_block)
