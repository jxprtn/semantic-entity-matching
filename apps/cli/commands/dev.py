import json

from lib.console_reporter import ConsoleReporter
from lib.opensearch.client import OpenSearchClient
from lib.utils import get_aws_credentials

DEFINITION = {
    "name": "dev",
    "description": "Interactive OpenSearch request console",
    "arguments": [
        {
            "name": "assume-role",
            "type": str,
            "required": False,
            "help": "AWS role to assume for OpenSearch operations",
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
    ],
}


def main(
    *,
    assume_role: str | None = None,
    opensearch_host: str = "localhost",
    opensearch_port: int = 9200,
    profile: str | None = None,
    region: str = "us-east-1",
) -> None:
    """
    Main entry point for the dev command.

    Args:
        assume_role: AWS role to assume for OpenSearch operations
        opensearch_host: OpenSearch host
        opensearch_port: OpenSearch port
        profile: AWS profile to use
        region: AWS region
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

    # Call the dev function
    dev(opensearch=opensearch)


def dev(*, opensearch: OpenSearchClient):
    """Interactive OpenSearch request console"""
    print("OpenSearch Dev Console")
    print("=" * 50)
    print("Enter your request in the format:")
    print("HTTP_METHOD /path")
    print("{")
    print('  "json": "body"')
    print("}")
    print()
    print("Example:")
    print("PUT /your-index-name/_mapping")
    print("{")
    print('  "properties": {')
    print('    "new_field_name": {')
    print('      "type": "text"')
    print("    }")
    print("  }")
    print("}")
    print()
    print("Press Ctrl+C to exit")
    print("=" * 50)

    while True:
        try:
            print("\nEnter your request (press Enter twice when done):")

            # Read the first line (HTTP method and path)
            first_line = input().strip()
            if not first_line:
                continue

            # Parse HTTP method and URL
            parts = first_line.split(" ", 1)
            if len(parts) != 2:
                print("Error: Please provide HTTP method and path (e.g., 'PUT /index/_mapping')")
                continue

            http_method, url = parts
            http_method = http_method.upper()

            # Read JSON body (multi-line input)
            json_lines = []
            print("Enter JSON body (press Enter on empty line to finish):")
            while True:
                line = input()
                if line.strip() == "":
                    break
                json_lines.append(line)

            # Parse JSON body if provided
            body = None
            if json_lines:
                json_str = "\n".join(json_lines)
                try:
                    body = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON - {e}")
                    continue

            # Make the request
            print(f"\nSending {http_method} request to {url}")
            if body:
                print(f"Body: {json.dumps(body, indent=2)}")

            try:
                response = opensearch.request(http_verb=http_method, url=url, body=body)

                print("\nResponse:")
                print(json.dumps(response, indent=2))

            except Exception as e:
                print(f"Request error: {e!s}")

        except KeyboardInterrupt:
            print("\n\nExiting dev console...")
            break
        except EOFError:
            print("\n\nExiting dev console...")
            break
