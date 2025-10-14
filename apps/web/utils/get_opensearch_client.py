import boto3
import streamlit as st
from botocore.credentials import Credentials

from lib.interfaces import IReporter
from lib.opensearch.client import OpenSearchClient


@st.cache_resource
def get_opensearch_client(
    *,
    endpoint: str,
    iam_role: str | None = None,
    profile: str,
    region: str,
    _reporter: IReporter,
) -> OpenSearchClient:
    """Get an OpenSearch client."""
    # Create a boto3 session with the specified profile (if any)
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()

    # If an assume role is provided, assume it and get temporary credentials
    if iam_role:
        print(f"Assuming role: {iam_role}")
        sts_client = session.client("sts", region_name=region)

        try:
            # Assume the role
            response = sts_client.assume_role(
                RoleArn=iam_role,
                RoleSessionName="opensearch-cli-setup",
            )

            # Extract the temporary credentials
            credentials = response["Credentials"]

            # Create credentials object for OpenSearch client
            assumed_credentials = Credentials(
                access_key=credentials["AccessKeyId"],
                secret_key=credentials["SecretAccessKey"],
                token=credentials["SessionToken"],
            )

            print(f"Successfully assumed role: {iam_role}")

        except Exception as e:
            print(f"Failed to assume role {iam_role}: {e!s}")
            return None
    else:
        # Use the default credentials from the session
        assumed_credentials = session.get_credentials()

    return OpenSearchClient(
        host=endpoint.split(":")[0],
        port=int(endpoint.split(":")[1] or 443),
        credentials=assumed_credentials,
        region=region,
        reporter=_reporter,
    )
