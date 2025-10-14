import sys

from lib.console_reporter import ConsoleReporter
from lib.data_reader import DataReader
from lib.evaluate import evaluate, get_top_k_metric
from lib.opensearch.client import OpenSearchClient
from lib.utils import get_aws_credentials

DEFINITION = {
    "name": "evaluate",
    "description": "Evaluate search performance against test dataset",
    "arguments": [
        {
            "name": "assume-role",
            "type": str,
            "required": False,
            "help": "AWS role to assume for OpenSearch operations",
        },
        {
            "name": "batch-size",
            "type": int,
            "required": False,
            "default": 50,
            "help": "Number of documents to process in each batch (default: 50)",
        },
        {
            "name": "column",
            "type": str,
            "required": True,
            "help": "Column to search on",
        },
        {
            "name": "display-field",
            "type": str,
            "required": False,
            "default": "LONG_COMMON_NAME",
            "help": "Field name in OpenSearch index to display in results (default: LONG_COMMON_NAME)",
        },
        {
            "name": "evaluation-columns",
            "nargs": "+",
            "type": str,
            "required": False,
            "help": "List of columns to combine for evaluation query text (default: ['department name', 'test description'])",
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
            "name": "limit-rows",
            "type": int,
            "required": False,
            "help": "Limit the number of rows to process (after skipping rows)",
        },
        {
            "name": "match-column",
            "type": str,
            "required": False,
            "default": "loinc code",
            "help": "Column name in test dataset to match against (default: 'loinc code')",
        },
        {
            "name": "match-field",
            "type": str,
            "required": False,
            "default": "LOINC_NUM",
            "help": "Field name in OpenSearch index to match against (default: LOINC_NUM)",
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
    batch_size: int = 50,
    column: str,
    display_field: str = "LONG_COMMON_NAME",
    evaluation_columns: list[str] | None = None,
    file: str,
    index: str,
    limit_rows: int | None = None,
    match_column: str = "loinc code",
    match_field: str = "LOINC_NUM",
    opensearch_host: str = "localhost",
    opensearch_port: int = 9200,
    profile: str | None = None,
    region: str = "us-east-1",
    skip_rows: int = 0,
) -> None:
    """
    Main entry point for the evaluate command.

    Args:
        assume_role: AWS role to assume for OpenSearch operations
        batch_size: Number of queries to process in each batch
        column: Column name to run the search against
        display_field: Field name in OpenSearch index to display in results
        evaluation_columns: List of columns to combine for query text
        file: Excel (.xlsx, .xls) or CSV (.csv) file to import
        index: Index name to use
        limit_rows: Limit the number of rows to process (after skipping rows)
        match_column: Column name in test dataset to match against
        match_field: Field name in OpenSearch index to match against
        opensearch_host: OpenSearch host
        opensearch_port: OpenSearch port
        profile: AWS profile to use
        region: AWS region
        skip_rows: Number of rows to skip at the beginning
    """
    reporter = ConsoleReporter()

    # Validate inputs
    if not file:
        reporter.on_message("Error: File path is required for evaluate command")
        sys.exit(1)

    if not column:
        reporter.on_message("Error: Column is required for evaluate command")
        sys.exit(1)

    # Get evaluation columns from args or use default
    if evaluation_columns is None:
        evaluation_columns = ["department name", "test description"]

    # Read the test dataset
    df = DataReader(
        file_path=file,
        limit_rows=limit_rows,
        skip_rows=skip_rows,
        reporter=reporter,
    ).df

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

    # Print header
    reporter.on_message("=" * 80)
    reporter.on_message("Evaluating search performance")
    reporter.on_message(f"Dataset: {file}")
    reporter.on_message(f"Index: {index}")
    reporter.on_message(f"Target field: {column}")
    reporter.on_message(f"Total queries to run: {len(df)}")
    reporter.on_message(f"Batch size: {batch_size}")
    reporter.on_message("=" * 80)

    # Call the library function
    try:
        results = evaluate(
            batch_size=batch_size,
            column=column,
            df=df,
            evaluation_columns=evaluation_columns,
            index_name=index,
            match_column=match_column,
            match_field=match_field,
            opensearch=opensearch,
            reporter=reporter,
        )
    except ValueError as e:
        reporter.on_message(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        reporter.on_message(f"Unexpected error: {e}")
        import traceback

        reporter.on_message(traceback.format_exc())
        sys.exit(1)

    # Print results for each row
    for result in results:
        if result.get("error"):
            actual_row_number = result["row_index"] + skip_rows + 1
            reporter.on_message(f"  Row {actual_row_number}: Error - {result['error']}")
        elif result.get("rank"):
            actual_row_number = result["row_index"] + skip_rows + 1
            display_value = result["document"].get(display_field, "N/A")
            hits_count = result.get("hits_count", 0)
            reporter.on_message(
                f"  Row {actual_row_number}: {result['rank']}/{hits_count} | "
                f"{result['score']:.4f} | {display_value}"
            )
        else:
            actual_row_number = result["row_index"] + skip_rows + 1
            reporter.on_message(f"  Row {actual_row_number}: No match found")

    # Calculate and print summary
    total_queries = len(results)
    failed_queries = [r for r in results if r.get("error")]
    failed_queries_count = len(failed_queries)
    successful_queries = [r for r in results if r.get("rank")]
    successful_queries_count = len(successful_queries)

    reporter.on_message("\n" + "=" * 80)
    reporter.on_message("EVALUATION SUMMARY")
    reporter.on_message(f"Total queries processed:\t{total_queries}")
    reporter.on_message(f"Successful queries:\t{successful_queries_count}")
    reporter.on_message(f"Failed queries:\t\t{failed_queries_count}")

    if successful_queries_count > 0:
        success_rate = successful_queries_count / total_queries * 100
        top_5 = get_top_k_metric(successful_queries, 5, total_queries)
        top_10 = get_top_k_metric(successful_queries, 10, total_queries)
        top_25 = get_top_k_metric(successful_queries, 25, total_queries)
        reporter.on_message(f"Top-5 accuracy:\t\t{top_5:.1f}%")
        reporter.on_message(f"Top-10 accuracy:\t\t{top_10:.1f}%")
        reporter.on_message(f"Top-25 accuracy:\t\t{top_25:.1f}%")
        reporter.on_message(f"Top-{total_queries} accuracy:\t\t{success_rate:.1f}%")

    reporter.on_message("=" * 80)
