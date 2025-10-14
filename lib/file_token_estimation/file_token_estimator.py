"""File token estimation implementation using tiktoken."""

from pathlib import Path

import tiktoken

from lib.file_token_estimation.formats import FileFormat
from lib.file_token_estimation.methods import TokenEstimationMethod
from lib.file_token_estimation.result import TokenEstimationResult


class FileTokenEstimator:
    """Estimates token counts for files using tiktoken."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize the file token estimator.

        Args:
            encoding_name: Tiktoken encoding to use (default: cl100k_base)
        """
        self.encoding = tiktoken.get_encoding(encoding_name)

    def estimate_tokens(self, file_path: Path) -> TokenEstimationResult:
        """
        Estimate token count for a file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            TokenEstimationResult with estimation details
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        file_extension = file_path.suffix.lower().lstrip(".")
        file_format = self._detect_file_format(file_extension)

        # For non-text files, use conservative estimation
        if file_format != FileFormat.TEXT:
            return self._create_fallback_result(
                file_size=file_size,
                file_extension=file_extension,
                file_format=file_format,
            )

        # Use tiktoken for text files
        try:
            return self._estimate_with_tokenizer(
                file_path=file_path,
                file_size=file_size,
                file_extension=file_extension,
            )
        except Exception as e:
            return self._create_failed_result(
                file_size=file_size,
                file_extension=file_extension,
                file_format=file_format,
                error=str(e),
            )

    def _detect_file_format(self, file_extension: str) -> FileFormat:
        """
        Detect file format from extension.

        Args:
            file_extension: File extension without dot

        Returns:
            FileFormat enum value
        """
        for fmt in FileFormat:
            if file_extension in fmt.value.extensions:
                return fmt
        return FileFormat.DOCUMENT

    def _estimate_with_tokenizer(
        self,
        file_path: Path,
        file_size: int,
        file_extension: str,
    ) -> TokenEstimationResult:
        """
        Estimate tokens using tiktoken.

        Args:
            file_path: Path to the file
            file_size: Size of the file in bytes
            file_extension: File extension without dot

        Returns:
            TokenEstimationResult with tokenizer estimation
        """
        content = file_path.read_text(encoding="utf-8")

        token_count = len(self.encoding.encode(content))
        tokens_per_byte = token_count / file_size if file_size > 0 else 0

        return TokenEstimationResult(
            method=TokenEstimationMethod.TOKENIZER,
            estimated_tokens=token_count,
            file_size_bytes=file_size,
            file_extension=file_extension,
            tokens_per_byte=tokens_per_byte,
            note=TokenEstimationMethod.TOKENIZER.value.description,
        )

    def _create_fallback_result(
        self,
        file_size: int,
        file_extension: str,
        file_format: FileFormat,
    ) -> TokenEstimationResult:
        """
        Create result for non-text files using conservative estimation.

        Args:
            file_size: Size of the file in bytes
            file_extension: File extension without dot
            file_format: Detected file format

        Returns:
            TokenEstimationResult with fallback estimation
        """
        estimated_tokens = int(file_size * file_format.value.ratio)

        return TokenEstimationResult(
            method=TokenEstimationMethod.TOKENIZER_FALLBACK,
            estimated_tokens=estimated_tokens,
            file_size_bytes=file_size,
            file_extension=file_extension,
            tokens_per_byte=file_format.value.ratio,
            note=f"{TokenEstimationMethod.TOKENIZER_FALLBACK.value.description} File extension: {file_extension}.",
        )

    def _create_failed_result(
        self,
        file_size: int,
        file_extension: str,
        file_format: FileFormat,
        error: str,
    ) -> TokenEstimationResult:
        """
        Create result when tokenizer fails.

        Args:
            file_size: Size of the file in bytes
            file_extension: File extension without dot
            file_format: Detected file format
            error: Error message from tokenizer

        Returns:
            TokenEstimationResult with failed estimation
        """
        estimated_tokens = int(file_size * file_format.value.ratio)

        return TokenEstimationResult(
            method=TokenEstimationMethod.TOKENIZER_FAILED,
            estimated_tokens=estimated_tokens,
            file_size_bytes=file_size,
            file_extension=file_extension,
            tokens_per_byte=file_format.value.ratio,
            note=f"{TokenEstimationMethod.TOKENIZER_FAILED.value.description} Error: {error}.",
            tokenizer_error=error,
        )
