import json
import os
import tempfile
from urllib.parse import urlparse

import boto3

from lib.ingest import ingest
from lib.opensearch.client import OpenSearchClient


def lambda_handler(event, context):
    """
    AWS Lambda handler for ingesting data from S3 files into OpenSearch.

    Expected event structure:
    {
        "s3_uri": "s3://bucket-name/path/to/file.csv",
        "opensearch_endpoint": "https://your-opensearch-domain.region.es.amazonaws.com",
        "index_name": "your-index",
        "pipeline_name": "embedding-pipeline",  # optional
        "region": "us-east-1",
        "limit_rows": 1000,  # optional
        "delete": false,  # optional
        "batch_size": 50,  # optional, number of documents per batch
        "wait_time": 5.0,  # optional, wait time in seconds between batches
        "max_attempts": 5,  # optional, maximum retry attempts
        "skip_rows": 0,  # optional, number of rows to skip
    }
    """
    try:
        # Parse event parameters
        s3_uri = event.get("s3_uri")
        opensearch_endpoint = event.get("opensearch_endpoint")
        index_name = event.get("index_name")
        pipeline_name = event.get("pipeline_name", "nlp-ingest-pipeline")
        region = event.get("region", "us-east-1")
        limit_rows = event.get("limit_rows")
        delete = event.get("delete", False)
        batch_size = event.get("batch_size", 50)
        wait_time = event.get("wait_time", 5.0)
        max_attempts = event.get("max_attempts", 5)
        skip_rows = event.get("skip_rows", 0)

        # Validate required parameters
        if not s3_uri:
            raise ValueError("s3_uri is required")
        if not opensearch_endpoint:
            raise ValueError("opensearch_endpoint is required")
        if not index_name:
            raise ValueError("index_name is required")

        # Parse S3 URI
        parsed_uri = urlparse(s3_uri)
        if parsed_uri.scheme != "s3":
            raise ValueError("Invalid S3 URI format. Expected s3://bucket/key")

        bucket_name = parsed_uri.netloc
        object_key = parsed_uri.path.lstrip("/")

        if not bucket_name or not object_key:
            raise ValueError("Invalid S3 URI. Both bucket and key are required")

        # Download file from S3
        print(f"Downloading file from S3: {s3_uri}")
        s3_client = boto3.client("s3", region_name=region)

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(object_key)[1]
        ) as temp_file:
            temp_file_path = temp_file.name

        try:
            # Download the file
            s3_client.download_file(bucket_name, object_key, temp_file_path)
            print(f"File downloaded successfully to: {temp_file_path}")

            # Initialize OpenSearch client
            opensearch = OpenSearchClient(host=opensearch_endpoint, region=region)

            # Perform ingest operation
            print("Starting ingest operation...")
            ingest(
                batch_size=batch_size,
                delete=delete,
                file_path=temp_file_path,
                index_name=index_name,
                limit_rows=limit_rows,
                max_attempts=max_attempts,
                opensearch=opensearch,
                pipeline_name=pipeline_name,
                skip_rows=skip_rows,
                wait_time=wait_time,
            )

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Ingest operation completed successfully",
                        "s3_uri": s3_uri,
                        "index_name": index_name,
                        "pipeline_name": pipeline_name,
                        "rows_processed": limit_rows if limit_rows else "all",
                    }
                ),
            }

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                print(f"Cleaned up temporary file: {temp_file_path}")

    except Exception as e:
        print(f"Error in lambda_handler: {e!s}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "message": "Ingest operation failed"}),
        }


# Example usage for local testing
if __name__ == "__main__":
    # Example event for testing
    test_event = {
        "batch_size": 25,
        "delete": False,
        "index_name": "test-index",
        "limit_rows": 100,
        "max_attempts": 5,
        "opensearch_endpoint": "https://your-opensearch-domain.region.es.amazonaws.com",
        "pipeline_name": "embedding-pipeline",
        "region": "us-east-1",
        "s3_uri": "s3://your-bucket/data/sample.csv",
        "skip_rows": 0,
        "wait_time": 3.0,
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
