import json
import sys
from pathlib import Path


# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st  # noqa: E402

from apps.web.utils import WebReporter, get_embedding_callback, get_opensearch_client  # noqa: E402
from lib.bedrock import BedrockClient # noqa: E402
from lib.interfaces import SearchAndRerankResults  # noqa: E402
from lib.opensearch.services import SearchQueryBuilder  # noqa: E402
from lib.search_and_rerank import search_and_rerank  # noqa: E402

for secret in [
    "opensearch_endpoint",
    "opensearch_indices",
    "opensearch_fields",
    "aws_region",
]:
    if secret not in st.secrets:
        st.error(f"Missing secret: {secret}")
        st.stop()

reporter = WebReporter()

bedrock_model_id = st.secrets.get("bedrock_model_id", "us.cohere.embed-v4:0")
aws_region = st.secrets.get("aws_region", "us-east-1")
vector_dimension = st.secrets.get("vector_dimension", 1536)

bedrock_client = BedrockClient(region=aws_region)

# Initialize OpenSearch client
indices = st.secrets.get("opensearch_indices", [])
fields = st.secrets.get("opensearch_fields", [])

opensearch = get_opensearch_client(
    endpoint=st.secrets.get("opensearch_endpoint", "localhost:9200"),
    iam_role=st.secrets.get("opensearch_iam_role", None),
    profile=st.secrets.get("aws_profile", None),
    region=st.secrets.get("aws_region", "us-east-1"),
    _reporter=reporter,
)

# -------------
# Streamlit app
# -------------

st.set_page_config(
    page_title="OpenSearch Query App",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar settings
with st.sidebar:
    index = st.selectbox(
        label="Index",
        options=indices,
        index=0,
        help="Select which index to search against",
    )

    # Field selection
    field = st.selectbox(
        label="Search field",
        options=fields,
        index=0,
        help="Select which field to search against",
    )

    # Search type selection
    search_type = st.radio(
        label="Search Type",
        options=["Semantic Search", "Keyword Search"],
        index=0,
        help="Choose between semantic (vector) search or traditional keyword search",
    )
    enable_reranking = st.checkbox(
        label="Rerank results",
        value=False,
        help="Enable reranking of search results",
    )

    st.divider()
    result_field_1 = st.text_input(
        label="Result Field 1",
        value="LOINC_NUM",
        help="Select which field to show in result summary",
    )
    result_field_2 = st.text_input(
        label="Result Field 2",
        value="LONG_COMMON_NAME",
        help="Select which field to show in result summary",
    )

# Create tabs
search_tab, dev_tab = st.tabs(["Search", "Dev"])

with search_tab:
    # Custom CSS for vertical centering and search layout
    st.markdown(
        """
    <style>
    .main-search-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 100%;
        text-align: center;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Main content area with vertical centering
    st.markdown('<div class="main-search-container">', unsafe_allow_html=True)

    # Center the search input with button on the right
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Create sub-columns for input and button side by side
        input_col, button_col = st.columns([4, 1])

        with input_col:
            # Initialize session state for search trigger
            if "search_query" not in st.session_state:
                st.session_state.search_query = ""
            if "should_search" not in st.session_state:
                st.session_state.should_search = False

            def on_query_change() -> None:
                # Trigger search when query changes and is not empty
                if st.session_state.query_input and st.session_state.query_input.strip():
                    st.session_state.should_search = True
                    st.session_state.search_query = st.session_state.query_input.strip()

            query = st.text_input(
                label="Search Query",
                placeholder="Enter your search terms and press Enter...",
                label_visibility="collapsed",
                key="query_input",
                on_change=on_query_change,
            )

        with button_col:
            search_button = st.button("Go", type="primary", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Search results - trigger on Enter or button click
    should_search = (search_button and query and field and index) or (
        st.session_state.should_search and st.session_state.search_query and field
    )
    search_query = st.session_state.search_query if st.session_state.should_search else query

    if should_search and index and field:
        try:
            with st.spinner("Searching..."):
                if search_type == "Semantic Search":
                    search_results = search_and_rerank(
                        column=field,
                        embedding_column_suffix=field,
                        enable_reranking=enable_reranking,
                        filters=[],
                        index=index,
                        opensearch=opensearch,
                        get_embedding=get_embedding_callback(
                            bedrock_client=bedrock_client,
                            bedrock_model_id=st.secrets.get(
                                "bedrock_model_id", "us.cohere.embed-v4:0"
                            ),
                            query=search_query,
                            vector_dimension=st.secrets.get("vector_dimension", 1536),
                        ),
                        profile=st.secrets.get("aws_profile", "default"),
                        query=search_query,
                        region=st.secrets.get("aws_region", "us-east-1"),
                        reporter=reporter,
                    )
                else:
                    search_results: SearchAndRerankResults = {
                        "search_results": opensearch.search.query(
                            SearchQueryBuilder(index=index)
                            .match(field=field, value=search_query)
                            .build()
                        ),
                        "rerank_results": None,
                        "query": query,
                        "sources": None,
                    }

                hits = search_results["search_results"].hits

                if len(hits) > 0:
                    for i, hit in enumerate(hits, 1):
                        source = hit["_source"]
                        # Safely get the display value, fallback to a default field or index
                        display_value_1 = source.get(
                            result_field_1, source.get(field, f"Result {i}")
                        )
                        display_value_2 = source.get(result_field_2, source.get(field, ""))
                        with st.expander(
                            f"{display_value_1} | {hit['_score']:.3f} | {display_value_2} "
                        ):
                            for key, value in source.items():
                                st.write(f"**{key}:** {value}")
                else:
                    st.warning("No results found for your query.")

        except Exception as e:
            st.error(f"An error occurred while searching: {e!s}")

    elif (search_button or st.session_state.should_search) and not search_query:
        st.warning("Please enter a search query.")
        st.session_state.should_search = False
    elif (search_button or st.session_state.should_search) and not field:
        st.warning("Please select a field to search.")
        st.session_state.should_search = False

with dev_tab:
    # Add CSS for monospace font in text areas
    st.markdown(
        """
        <style>
        .stTextArea textarea {
            font-family: 'Courier New', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Display OpenSearch endpoint (read-only)
    st.text_input(
        "OpenSearch Endpoint",
        value=st.secrets["opensearch_endpoint"],
        disabled=True,
        help="OpenSearch cluster endpoint (configured in secrets)",
    )

    # HTTP method selection
    method = st.selectbox("HTTP Method", options=["GET", "POST", "PUT", "DELETE"], index=0)

    # URL path input
    url_path = st.text_input(
        "URL Path",
        placeholder="/_cluster/health",
        help="Enter the OpenSearch API path (e.g., /_cluster/health, /_cat/indices)",
    )

    # Show full URL for reference
    if url_path:
        full_url = f"{st.secrets['opensearch_endpoint']}{url_path}"
        st.caption(f"Full URL: `{full_url}`")

    # JSON payload
    payload = st.text_area(
        "JSON Body",
        placeholder='{\n  "query": {\n    "match_all": {}\n  }\n}',
        height=200,
        help="Enter JSON body for POST/PUT requests (optional for GET/DELETE)",
    )

    # Send request button
    if st.button("Send Request", type="primary"):
        if not url_path:
            st.error("Please enter a URL path")
        else:
            try:
                # Parse payload
                json_payload = None
                if payload.strip():
                    try:
                        json_payload = json.loads(payload)
                    except json.JSONDecodeError:
                        st.error("Invalid JSON format in body")
                        st.stop()

                # Make the request using OpenSearch client
                with st.spinner("Sending request..."):
                    response = opensearch.request(url=url_path, http_verb=method, body=json_payload)

                # Display response
                st.subheader("Response")

                # Success indicator
                st.success("Request completed successfully")

                # Response body
                st.subheader("Response Body")
                if isinstance(response, dict):
                    st.json(response)
                else:
                    st.text(str(response))

            except ValueError as e:
                if "Invalid HTTP verb" in str(e):
                    st.error(f"Invalid HTTP method: {method}")
                else:
                    st.error(f"Invalid request: {e!s}")
            except Exception as e:
                st.error(f"Request failed: {e!s}")
                # Show more details for debugging
                st.text(f"Error type: {type(e).__name__}")
                if hasattr(e, "info"):
                    st.json(e.info)
