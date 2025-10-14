import sys
import traceback

from opensearchpy.exceptions import TransportError

from lib.console_reporter import ConsoleReporter
from lib.interfaces import IReporter
from lib.opensearch.client import OpenSearchClient
from lib.setup_opensearch import setup_opensearch
from lib.utils import get_aws_credentials

DEFINITION = {
    "name": "setup",
    "description": "Setup OpenSearch ML connector and document index",
    "arguments": [
        {
            "name": "assume-role",
            "type": str,
            "required": False,
            "help": "AWS role to assume for OpenSearch operations",
        },
        {
            "name": "columns",
            "nargs": "+",
            "type": str,
            "required": True,
            "help": "List of columns to use for ingestion",
        },
        {
            "name": "delete",
            "action": "store_true",
            "required": False,
            "help": "Delete existing index before setup",
        },
        {
            "name": "ef-construction",
            "type": int,
            "required": False,
            "default": 512,
            "help": "HNSW ef_construction parameter for index creation (default: 512)",
        },
        {
            "name": "ef-search",
            "type": int,
            "required": False,
            "default": 512,
            "help": "HNSW ef_search parameter for index creation (default: 512)",
        },
        {
            "name": "embedding-column-suffix",
            "type": str,
            "required": False,
            "default": "_embedding",
            "help": "Suffix appended to column names for embedding columns (default: _embedding)",
        },
        {
            "name": "engine",
            "type": str,
            "required": False,
            "default": "faiss",
            "help": "Vector search engine for index creation (default: faiss)",
        },
        {
            "name": "index",
            "type": str,
            "required": True,
            "help": "Index name to use",
        },
        {
            "name": "m",
            "type": int,
            "required": False,
            "default": 48,
            "help": "HNSW m parameter for index creation (default: 48)",
        },
        {
            "name": "no-confirm",
            "action": "store_true",
            "required": False,
            "help": "Skip confirmation prompts",
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
            "name": "space-type",
            "type": str,
            "required": False,
            "default": "l2",
            "help": "Space type for vector similarity (default: l2)",
        },
        {
            "name": "vector-dimension",
            "type": int,
            "required": False,
            "default": 1024,
            "help": "Vector dimension for embeddings (default: 1024 for Titan v2)",
        },
    ],
}


def confirm(prompt: str, *, reporter: IReporter) -> None:
    """Prompt user for confirmation."""
    confirmation = reporter.on_input(f"{prompt} (yes/no): ")
    if confirmation.lower() != "yes":
        reporter.on_message("Aborting...")
        sys.exit(0)
    else:
        reporter.on_message("Continuing...")


def main(
    *,
    assume_role: str | None = None,
    columns: list[str],
    delete: bool = False,
    ef_construction: int = 512,
    ef_search: int = 512,
    embedding_column_suffix: str = "_embedding",
    engine: str = "faiss",
    index: str,
    m: int = 48,
    no_confirm: bool = False,
    opensearch_host: str = "localhost",
    opensearch_port: int = 9200,
    profile: str | None = None,
    region: str = "us-east-1",
    space_type: str = "l2",
    vector_dimension: int = 1024,
) -> None:
    """
    Main entry point for the setup command.

    Args:
        assume_role: AWS role to assume for OpenSearch operations
        columns: List of columns to use for ingestion
        delete: Delete existing index before setup
        ef_construction: HNSW ef_construction parameter for index creation
        ef_search: HNSW ef_search parameter for index creation
        embedding_column_suffix: Suffix appended to column names for embedding columns
        engine: Vector search engine for index creation
        index: Index name to use
        m: HNSW m parameter for index creation
        no_confirm: Skip confirmation prompts
        opensearch_host: OpenSearch host
        opensearch_port: OpenSearch port
        profile: AWS profile to use
        region: AWS region
        space_type: Space type for vector similarity
        vector_dimension: Vector dimension for embeddings
    """
    reporter = ConsoleReporter()

    # Get AWS credentials
    credentials = get_aws_credentials(
        assume_role=assume_role,
        profile=profile,
        region=region,
    )

    # Create OpenSearch client
    opensearch = OpenSearchClient(
        credentials=credentials,
        host=opensearch_host,
        port=opensearch_port,
        region=region,
        reporter=reporter,
    )

    # Ask the user for confirmation if the delete flag has been set to True
    if delete:
        if not no_confirm:
            confirm(
                f"""
This command will delete the following resources if they exist, before recreating them:
  - Any index named '{index}'

Please confirm if you want to proceed.""",
                reporter=reporter,
            )

        # Additional confirmation specifically for index deletion (matches original behavior)
        if not no_confirm and opensearch.index_exists(index=index):
            confirm(
                f"\nAre you sure you want to permanently delete the existing '{index}' index and its content?",
                reporter=reporter,
            )

    # Call the library function for business logic
    try:
        setup_opensearch(
            columns=columns,
            delete=delete,
            ef_construction=ef_construction,
            ef_search=ef_search,
            embedding_column_suffix=embedding_column_suffix,
            engine=engine,
            index_name=index,
            m=m,
            opensearch=opensearch,
            space_type=space_type,
            vector_dimension=vector_dimension,
        )

        # Check if index already exists (for user feedback)
        if not delete and opensearch.index_exists(index=index):
            reporter.on_message(
                f"Index {index} already exists, skipping. (use --delete to delete and recreate)"
            )

        reporter.on_message("Setup completed successfully!")

    except ValueError as e:
        reporter.on_message(f"Error: {e}")
        sys.exit(1)
    except TransportError as e:
        reporter.on_message(f"OpenSearch error: {e}")
        sys.exit(1)
    except Exception as e:
        reporter.on_message(f"Unexpected error: {e}")
        reporter.on_message(traceback.format_exc())
        sys.exit(1)
