"""
CLI command for vectorizing CSV/Excel files using AWS Bedrock embeddings.
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Literal

from lib.bedrock import BedrockClient, EmbeddingType
from lib.console_reporter import ConsoleReporter
from lib.data_reader import DataReader
from lib.vectorize_columns import vectorize_columns

DEFINITION = {
    "name": "vectorize",
    "description": "Generate embeddings for columns in a CSV or Excel file",
    "arguments": [
        {
            "name": "bedrock-model-id",
            "type": str,
            "required": True,
            "help": "AWS Bedrock model ID for embeddings (e.g., amazon.titan-embed-text-v2:0)",
        },
        {
            "name": "columns",
            "type": str,
            "nargs": "+",
            "required": True,
            "help": "Columns to vectorize (space-separated list)",
        },
        {
            "name": "file",
            "type": str,
            "required": True,
            "help": "Path to CSV or Excel file to vectorize",
        },
        {
            "name": "limit-rows",
            "type": int,
            "required": False,
            "help": "Limit the number of rows to process (after skipping rows)",
        },
        {
            "name": "max-attempts",
            "type": int,
            "required": False,
            "default": 5,
            "help": "Maximum number of retry attempts for failed batches (default: 5)",
        },
        {
            "name": "output",
            "type": str,
            "required": False,
            "help": "Custom output file path (default: <input_file>_vectorized.csv)",
        },
        {
            "name": "profile",
            "type": str,
            "required": False,
            "help": "AWS profile to use",
        },
        {
            "name": "region",
            "type": str,
            "required": False,
            "default": "us-east-1",
            "help": "AWS region (default: us-east-1)",
        },
        {
            "name": "skip-rows",
            "type": int,
            "required": False,
            "default": 0,
            "help": "Number of rows to skip at the beginning (for resuming)",
        },
        {
            "name": "vectorize-strategy",
            "type": str,
            "required": False,
            "default": "per-column",
            "choices": ["per-column", "combined"],
            "help": "Vectorization strategy: 'per-column' (default) creates separate embedding columns, 'combined' creates a single combined embedding",
        },
        {
            "name": "vector-dimension",
            "type": int,
            "required": False,
            "default": 1024,
            "help": "Vector dimension for embeddings (default: 1024)",
        },
        {
            "name": "overwrite",
            "action": "store_true",
            "required": False,
            "help": "Automatically overwrite existing output file without prompting",
        },
        {
            "name": "embedding-column-suffix",
            "type": str,
            "required": False,
            "default": "_embedding",
            "help": "Suffix to append to column names for embedding columns (default: _embedding)",
        },
    ],
}


def main(
    *,
    bedrock_model_id: str,
    columns: list[str],
    embedding_column_suffix: str,
    file: str,
    limit_rows: int | None = None,
    max_attempts: int = 3,
    output: str | None = None,
    overwrite: bool = False,
    profile: str | None = None,
    region: str = "us-east-1",
    skip_rows: int = 0,
    vector_dimension: int = 1024,
    vectorize_strategy: Literal["per-column", "combined"] = "per-column",
) -> None:
    """
    Main entry point for the vectorize command.

    Args:
        bedrock_model_id: AWS Bedrock model ID for embeddings
        columns: List of column names to vectorize
        embedding_column_suffix: Suffix to append to column names for embedding columns
        file: Path to input CSV or Excel file
        limit_rows: Optional limit on number of rows to process
        max_attempts: Maximum number of retry attempts for failed batches
        output: Custom output file path
        overwrite: Automatically overwrite existing output file without prompting
        profile: AWS profile to use
        region: AWS region
        skip_rows: Number of rows to skip at the beginning
        vector_dimension: Vector dimension for embeddings (default: 1024)
        vectorize_strategy: Vectorization strategy ("per-column" or "combined")
    """
    reporter = ConsoleReporter()

    # Validate input file exists
    if not os.path.exists(file):
        reporter.on_message(f"Error: File not found: {file}")
        sys.exit(1)

    # Set AWS profile if provided
    if profile:
        os.environ["AWS_PROFILE"] = profile

    # Determine output path
    if output:
        output_path = output
    else:
        # Generate default output path: <input_file>_vectorized.csv
        input_path = Path(file)
        output_path = str(input_path.parent / f"{input_path.stem}_vectorized{'.csv'}")

    # Check if output file exists and prompt for overwrite (unless --overwrite flag is set)
    if os.path.exists(output_path) and not overwrite:
        response = reporter.on_input(
            f"Output file already exists: {output_path}\nOverwrite? (y/n): "
        )
        if response.lower() != "y":
            reporter.on_message("Aborting.")
            sys.exit(1)
    elif os.path.exists(output_path) and overwrite:
        reporter.on_message(f"Output file already exists: {output_path}")
        reporter.on_message("Overwriting (--overwrite flag set)...")

    reporter.on_message(f"Input file: {file}")
    reporter.on_message(f"Output file: {output_path}")
    reporter.on_message(f"Columns to vectorize: {columns}")
    reporter.on_message(f"Strategy: {vectorize_strategy}")
    reporter.on_message(f"Model: {bedrock_model_id}")
    reporter.on_message(f"Vector dimension: {vector_dimension}")
    reporter.on_message("")

    # Create Bedrock client
    client = BedrockClient(profile=profile, region=region)

    try:
        # Read the data file
        df = DataReader(
            file_path=file,
            limit_rows=limit_rows,
            skip_rows=skip_rows,
            reporter=reporter,
        ).df

        # Vectorize columns
        result_df = vectorize_columns(
            bedrock_model_id=bedrock_model_id,
            client=client,
            columns=columns,
            df=df,
            embedding_column_suffix=embedding_column_suffix,
            embedding_type=EmbeddingType.FLOAT,
            max_attempts=max_attempts,
            output_dimension=vector_dimension,
            reporter=reporter,
            strategy=vectorize_strategy,
        )

        # Write output to CSV
        reporter.on_message(f"\nWriting output to: {output_path}")
        result_df.to_csv(output_path, index=False)
        reporter.on_message(f"Successfully wrote {len(result_df)} rows to {output_path}")

        # Report on embedding columns
        if vectorize_strategy == "per-column":
            embedding_cols = [f"{col}{embedding_column_suffix}" for col in columns]
        else:
            # Column name is concatenation of column names with suffix
            embedding_cols = ["_".join(columns) + embedding_column_suffix]

        reporter.on_message(f"\nEmbedding columns created: {embedding_cols}")

        # Check for null embeddings
        for col in embedding_cols:
            null_count = result_df[col].isna().sum()
            if null_count > 0:
                reporter.on_message(
                    f"Warning: {null_count} rows have null values in {col} (check error logs)"
                )

    except ValueError as e:
        reporter.on_message(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        reporter.on_message(f"Unexpected error: {e}")
        reporter.on_message(traceback.format_exc())
        sys.exit(1)
    finally:
        # Clean up client connections
        # Check if there's a running event loop to avoid errors during Ctrl+C
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            asyncio.run(client.close())
        else:
            # Loop is running (shouldn't happen here, but handle gracefully)
            # Create a new event loop for cleanup
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(client.close())
            finally:
                loop.close()
