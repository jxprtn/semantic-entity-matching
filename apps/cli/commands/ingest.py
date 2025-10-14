import json
import sys

from apps.cli.utils import is_vector_embedding
from lib.console_reporter import ConsoleReporter
from lib.data_reader import DataReader
from lib.ingest import ingest
from lib.opensearch.client import OpenSearchClient
from lib.utils import get_aws_credentials

DEFINITION = {
    "name": "ingest",
    "description": "Ingest data from file",
    "arguments": [
        {
            "name": "assume-role",
            "type": str,
            "required": False,
            "help": "AWS role to assume for OpenSearch operations",
        },
        {
            "name": "delete",
            "action": "store_true",
            "required": False,
            "help": "Delete existing index before setup",
        },
        {
            "name": "file",
            "type": str,
            "required": True,
            "help": "Excel (.xlsx, .xls) or CSV (.csv) file to import",
        },
        {
            "name": "index",
            "type": str,
            "required": True,
            "help": "Index name to use",
        },
        {
            "name": "knn-columns",
            "type": str,
            "nargs": "+",
            "required": True,
            "help": "Columns to ingest as vectors for KNN search",
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
            "help": "Maximum number of retry attempts for ingestion (default: 5)",
        },
        {
            "name": "opensearch-host",
            "type": str,
            "required": False,
            "default": "localhost",
            "help": "OpenSearch host (default: localhost)",
        },
        {
            "name": "opensearch-port",
            "type": int,
            "required": False,
            "default": 9200,
            "help": "OpenSearch port (default: 9200)",
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
            "help": "AWS region",
        },
        {
            "name": "skip-rows",
            "type": int,
            "required": False,
            "default": 0,
            "help": "Number of rows to skip at the beginning (for resuming ingestion)",
        },
    ],
}


def main(
    *,
    assume_role: str | None = None,
    delete: bool = False,
    file: str,
    index: str,
    knn_columns: list[str],
    limit_rows: int | None = None,
    max_attempts: int = 5,
    opensearch_host: str = "localhost",
    opensearch_port: int = 9200,
    profile: str | None = None,
    region: str = "us-east-1",
    skip_rows: int = 0,
) -> None:
    """
    Main entry point for the ingest command.

    Args:
        assume_role: AWS role to assume for OpenSearch operations
        delete: Delete existing index before ingestion
        file: Excel (.xlsx, .xls) or CSV (.csv) file to import
        index: Index name to use
        knn_columns: Columns to ingest as vectors for KNN search
        limit_rows: Limit the number of rows to process (after skipping rows)
        max_attempts: Maximum number of retry attempts for ingestion
        opensearch_host: OpenSearch host
        opensearch_port: OpenSearch port
        profile: AWS profile to use
        region: AWS region
        skip_rows: Number of rows to skip at the beginning
    """
    reporter = ConsoleReporter()

    if not file:
        reporter.on_message("Error: File path is required for ingest command")
        sys.exit(1)

    credentials = get_aws_credentials(
        assume_role=assume_role,
        profile=profile,
        region=region,
    )

    opensearch = OpenSearchClient(
        credentials=credentials,
        host=opensearch_host,
        port=opensearch_port,
        region=region,
        reporter=reporter,
    )

    def parse_vector(value: str, column_name: str) -> list[float] | None:
        """Parse string representation of vector to list using JSON."""
        max_length = 100
        try:
            parsed = json.loads(value)
            if is_vector_embedding(parsed):
                return parsed
            error_msg = value[:max_length] + "..." if len(value) > max_length else value
            reporter.on_message(
                f"Warning: Parsed value in column '{column_name}' is not a list: {error_msg}"
            )
        except json.JSONDecodeError:
            error_msg = value[:max_length] + "..." if len(value) > max_length else value
            reporter.on_message(
                f"Warning: Could not parse vector in column '{column_name}': {error_msg}"
            )
        return None

    reader = DataReader(
        file_path=file,
        limit_rows=limit_rows,
        skip_rows=skip_rows,
        reporter=reporter,
        transformations=[{"columns": knn_columns, "callback": parse_vector}],
    )


    ingest(
        delete=delete,
        rows=reader.df.to_dict(orient="records"),
        index_name=index,
        max_attempts=max_attempts,
        opensearch=opensearch,
        reporter=reporter,
    )
