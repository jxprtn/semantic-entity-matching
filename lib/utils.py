"""Utility functions for the OpenSearch CLI tool."""

from typing import Any

import boto3
from botocore.credentials import Credentials

from lib.opensearch.client import OpenSearchClient


def get_aws_credentials(
    *,
    profile: str | None = None,
    assume_role: str | None = None,
    region: str = "us-east-1",
    role_session_name: str = "opensearch-cli-setup",
) -> Credentials:
    """Get AWS credentials, optionally from a profile or by assuming a role.

    Args:
        profile: Optional AWS profile name
        assume_role: Optional IAM role ARN to assume
        region: AWS region (default: us-east-1)
        role_session_name: Name of the role session (default: opensearch-cli-setup)

    Returns:
        Credentials object

    Raises:
        Exception: If role assumption fails or credentials cannot be obtained

    """
    # Create a boto3 session with the specified profile (if any)
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()

    # If an assume role is provided, assume it and get temporary credentials
    if assume_role:
        print(f"Assuming role: {assume_role}")
        sts_client = session.client("sts", region_name=region)

        try:
            # Assume the role
            response = sts_client.assume_role(
                RoleArn=assume_role,
                RoleSessionName=role_session_name,
            )

            # Extract the temporary credentials
            credentials = response["Credentials"]

            # Create credentials object for OpenSearch client
            assumed_credentials = Credentials(
                access_key=credentials["AccessKeyId"],
                secret_key=credentials["SecretAccessKey"],
                token=credentials["SessionToken"],
            )

            print(f"Successfully assumed role: {assume_role}")
            return assumed_credentials

        except Exception as e:
            raise Exception(f"Failed to assume role {assume_role}: {e!s}") from e
    else:
        # Use the default credentials from the session
        credentials = session.get_credentials()
        if credentials is None:
            raise Exception(
                "No AWS credentials found. Please configure AWS credentials or use --profile or --assume-role.",
            )
        return credentials


def validate_opensearch_client(
    opensearch: OpenSearchClient | None,
) -> OpenSearchClient:
    """Validate that an OpenSearchClient is not None.

    Args:
        opensearch: Optional OpenSearchClient instance

    Returns:
        OpenSearchClient instance

    Raises:
        ValueError: If opensearch is None

    """
    if opensearch is None:
        raise ValueError("OpenSearch client is not available. Check your connection settings.")
    return opensearch


def get_opensearch_client(args: Any) -> OpenSearchClient:
    """Create and return an OpenSearchClient instance.

    Args:
        args: Parsed command-line arguments

    Returns:
        OpenSearchClient instance

    Raises:
        Exception: If credentials cannot be obtained or client creation fails

    """
    credentials = get_aws_credentials(
        profile=getattr(args, "profile", None),
        assume_role=getattr(args, "assume_role", None),
        region=getattr(args, "region", "us-east-1"),
    )

    return OpenSearchClient(
        host=args.endpoint,
        credentials=credentials,
        region=getattr(args, "region", "us-east-1"),
    )
