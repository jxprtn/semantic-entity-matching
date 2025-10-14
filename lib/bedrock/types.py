from dataclasses import dataclass
from enum import Enum

EmbeddingVector = list[float]

class ModelId(Enum):
    """Model ID enumeration."""

    HAIKU_4_5_20251001_V1 = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    SONNET_4_5_20250929_V1 = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


class EmbeddingModelId(Enum):
    """Embedding model ID enumeration."""

    TITAN = "amazon.titan-embed-text-v2:0"
    COHERE = "us.cohere.embed-v4:0"


class EmbeddingType(Enum):
    """Embedding type enumeration."""

    FLOAT = "float"
    INT8 = "int8"
    UINT8 = "uint8"
    BINARY = "binary"
    UBINARY = "ubinary"


class InputType(Enum):
    """Input type enumeration."""

    SEARCH_DOCUMENT = "search_document"
    SEARCH_QUERY = "search_query"
    CLASSIFICATION = "classification"
    CLUSTERING = "clustering"


@dataclass
class EmbeddingModelOutput:
    """Embedding model output configuration."""

    embeddings: dict[EmbeddingType, EmbeddingVector]


@dataclass
class ModelOutputParsingError(Exception):
    """
    Raised when the model response cannot be parsed correctly.

    This error indicates that the API returned a response that doesn't match
    the expected schema for the given model, or that the response is malformed.
    """

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
