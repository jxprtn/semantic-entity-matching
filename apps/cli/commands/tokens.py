import os
import sys
from pathlib import Path

from lib.file_token_estimation import FileTokenEstimator

DEFINITION = {
    "name": "tokens",
    "description": "Estimate token count for a file using tiktoken",
    "arguments": [
        {
            "name": "file",
            "type": str,
            "required": True,
            "help": "Excel (.xlsx, .xls) or CSV (.csv) file to import",
        },
    ],
}


def main(
    *,
    file: str,
) -> None:
    """
    Main entry point for the tokens command.

    Args:
        file: Excel (.xlsx, .xls) or CSV (.csv) file to import
    """
    if not file:
        print("Error: --file is required for tokens command")
        sys.exit(1)

    if not os.path.exists(file):
        print(f"Error: File not found: {file}")
        sys.exit(1)

    estimator = FileTokenEstimator()
    try:
        result = estimator.estimate_tokens(Path(file))

        print(f"\nToken estimation for: {file}")
        print("=" * 50)
        print(f"Method: {result.format_method_name()}")
        print(f"Estimated tokens: {result.estimated_tokens:,}")
        print(f"File size: {result.file_size_bytes:,} bytes")
        print(f"Tokens per byte: {result.tokens_per_byte:.4f}")
        print(f"Note: {result.note}")
        print(f"File extension: {result.file_extension}")

    except Exception as e:
        print(f"Error estimating tokens: {e!s}")
        sys.exit(1)
