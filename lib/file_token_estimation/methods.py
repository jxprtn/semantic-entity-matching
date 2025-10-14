"""Token estimation method definitions."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class MethodInfo:
    """Information about a token estimation method."""

    name: str
    description: str


class TokenEstimationMethod(Enum):
    """Token estimation method enumeration with name and description."""

    TOKENIZER = MethodInfo(
        name="tokenizer",
        description="Estimated using tiktoken (cl100k_base encoding, good approximation for Claude).",
    )
    TOKENIZER_FALLBACK = MethodInfo(
        name="tokenizer_fallback",
        description="Non-text file, using conservative estimation.",
    )
    TOKENIZER_FAILED = MethodInfo(
        name="tokenizer_failed",
        description="Tokenizer failed, using simple estimation.",
    )
