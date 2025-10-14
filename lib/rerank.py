from typing import TYPE_CHECKING, Any, cast

import boto3

from lib.interfaces import IReporter  # type: ignore

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime import BedrockAgentRuntimeClient  # type: ignore
    from mypy_boto3_bedrock_agent_runtime.type_defs import RerankResponseTypeDef  # type: ignore
else:
    BedrockAgentRuntimeClient = object
    RerankResponseTypeDef = dict[str, Any]


def rerank(
    *,
    profile: str | None,
    query: str,
    region: str,
    reporter: IReporter,
    top_k: int = 3,
    sources: list[str],
) -> RerankResponseTypeDef | None:
    # Create Bedrock Agent Runtime client
    session = boto3.Session(profile_name=profile)
    bedrock_client = session.client("bedrock-agent-runtime", region_name=region)  # type: ignore

    try:
        # Ensure numberOfResults doesn't exceed the number of sources
        num_sources = len(sources)
        if num_sources == 0:
            reporter.on_message("No sources to rerank")
            return None

        # Cap number_of_results at the number of sources
        number_of_results = min(top_k, num_sources)

        # Call Bedrock Agent Runtime Rerank API
        # Explicitly cast the client to the specific type if not automatically inferred
        client = cast("BedrockAgentRuntimeClient", bedrock_client)  # type: ignore

        # Explicitly cast the response to the specific type
        # Use type ignore here because client.rerank returns a Dict which is compatible with RerankResponseTypeDef
        # but type checkers might not see it that way due to boto3 dynamic nature
        return cast(
            "RerankResponseTypeDef",
            client.rerank(  # type: ignore
                rerankingConfiguration={
                    "type": "BEDROCK_RERANKING_MODEL",
                    "bedrockRerankingConfiguration": {
                        "modelConfiguration": {
                            # TODO: Set your rerank model ARN
                            "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/cohere.rerank-v3-5:0",
                        },
                        "numberOfResults": number_of_results,
                    },
                },
                queries=[{"type": "TEXT", "textQuery": {"text": query}}],
                sources=[
                    {
                        "type": "INLINE",
                        "inlineDocumentSource": {
                            "type": "TEXT",
                            "textDocument": {"text": source},
                        },
                    }
                    for source in sources
                ],
            ),
        )

    except Exception as e:
        reporter.on_message(f"Error calling Bedrock Rerank API: {e}")
        return None
