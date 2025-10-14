"""Token estimation result types."""

from dataclasses import dataclass

from lib.file_token_estimation.methods import TokenEstimationMethod


@dataclass(frozen=True)
class TokenEstimationResult:
    """Result of token estimation for a file."""

    method: TokenEstimationMethod
    estimated_tokens: int
    file_size_bytes: int
    file_extension: str
    tokens_per_byte: float
    note: str
    tokenizer_error: str | None = None

    def format_method_name(self) -> str:
        """Format the method name for display."""
        method_names = {
            TokenEstimationMethod.TOKENIZER: "Tiktoken Tokenizer (good approximation)",
            TokenEstimationMethod.TOKENIZER_FALLBACK: "Conservative Estimation (non-text file)",
            TokenEstimationMethod.TOKENIZER_FAILED: "Simple Estimation (tokenizer failed)",
        }
        return method_names.get(self.method, "Unknown Method")

    def to_dict(self) -> dict:
        """Convert result to dictionary for backward compatibility."""
        result = {
            "method": self.method.value.name,
            "estimated_tokens": self.estimated_tokens,
            "file_size_bytes": self.file_size_bytes,
            "file_extension": self.file_extension,
            "tokens_per_byte": self.tokens_per_byte,
            "note": self.note,
        }
        if self.tokenizer_error:
            result["tokenizer_error"] = self.tokenizer_error
        return result
