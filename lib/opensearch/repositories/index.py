"""Index repository."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel

from lib.opensearch.entities.index import (
    Index,
    IndexSettings,
    Mappings,
    Settings,
    TextField,
    VectorField,
    VectorFieldMethod,
    VectorFieldMethodParameters,
    VectorSearchEngine,
    VectorSearchMethod,
    VectorSearchSpaceType,
)
from lib.opensearch.repositories.base_repository import BaseRepository


class IndexRepository(BaseRepository[Index]):
    """Repository for managing Index entities."""

    _base_uri = "/"

    def create(  # noqa: PLR0913
        self,
        *,
        index: str,
        fields: list[str],
        vector_dimension: int,
        method_name: VectorSearchMethod = VectorSearchMethod.HNSW,
        space_type: VectorSearchSpaceType = VectorSearchSpaceType.L2,
        embedding_column_suffix: str,
        engine: VectorSearchEngine = VectorSearchEngine.FAISS,
        ef_construction: int = 512,
        m: int = 48,
        ef_search: int = 512,
        **_: Any,
    ) -> Index:
        """Create a new index with vector search capabilities and return an Index instance.

        Args:
            index: Name of the index
            fields: List of text fields that will have embeddings
            vector_dimension: Dimension of the vector embeddings
            method_name: Vector search method (default: hnsw)
            space_type: Vector space type (default: l2)
            embedding_column_suffix: Suffix for embedding fields (default: _embedding)
            engine: Vector search engine (default: faiss)
            ef_construction: HNSW ef_construction parameter (default: 512)
            m: HNSW m parameter (default: 48)
            ef_search: HNSW ef_search parameter (default: 512)

        Returns:
            An Index domain model instance
        """
        print(f"Creating new index '{index}'...", end="")

        mappings_properties = {
            field: VectorField(
                dimension=vector_dimension,
                method=VectorFieldMethod(
                    name=method_name,
                    space_type=space_type,
                    engine=engine,
                    parameters=VectorFieldMethodParameters(ef_construction=ef_construction, m=m),
                ),
            )
            for field in fields
            if field.endswith(embedding_column_suffix)
        }

        settings = Settings(index=IndexSettings(knn=True, knn_algo_param_ef_search=ef_search))
        mappings = Mappings(properties=mappings_properties)

        # Serialize to dict with enum values converted to strings
        settings_dict: dict[str, Any] = self._serialize_pydantic_with_enums(settings)  # type: ignore[assignment]
        # Serialize mappings properties directly to preserve Pydantic model instances
        mappings_dict = {
            "properties": {
                k: self._serialize_pydantic_with_enums(v) for k, v in mappings.properties.items()
            }
        }

        # OpenSearch expects {'settings': {'index': {...}}, 'mappings': {...}}
        # The knn_algo_param_ef_search needs to be nested under knn.algo_param.ef_search
        # OpenSearch uses flat dot notation: knn=true, knn.algo_param.ef_search=value
        index_settings: dict[str, Any] = dict(settings_dict["index"])  # type: ignore[index]
        # Ensure knn is True (boolean)
        knn_value: bool = index_settings.get("knn", True)  # type: ignore[assignment]
        index_settings["knn"] = knn_value

        if "knn_algo_param_ef_search" in index_settings:
            ef_search_value: int = index_settings.pop("knn_algo_param_ef_search")  # type: ignore[assignment]
            # Use dot notation for nested settings
            index_settings["knn.algo_param.ef_search"] = ef_search_value

        body = {
            "settings": {"index": index_settings},
            "mappings": mappings_dict,
        }

        self._client.indices.create(
            index=index,
            body=body,
        )
        print(" Done")

        return Index(
            name=index,
            settings=settings,
            mappings=mappings,
            _repository=self,
        )

    def get(self, *, index: str, **_: Any) -> Index:
        """Get index information and return an Index instance.

        Args:
            index: Name of the index

        Returns:
            An Index domain model instance
        """
        data = self._client.indices.get(index=index)

        return Index(
            name=index,
            settings=Settings.model_validate(data[index]["settings"]),
            mappings=Mappings.model_validate(data[index]["mappings"]),
            _repository=self,
        )

    def list(self) -> list[Index]:
        """List all indexes."""
        response = self._client.indices.get(index="*")
        return [self._hit_to_entity({**data, "index": name}) for name, data in response.items()]

    def delete(self, *, index: Index) -> Any:
        """Delete an index.

        Args:
            index: The Index entity to delete

        Returns:
            Deletion response
        """
        print(f"Deleting index {index.name}...", end="")
        response = self._client.indices.delete(index=index.name, ignore=[400, 404])  # type: ignore
        print(" Done")
        return response  # type: ignore

    def exists(self, index_name: str) -> bool:
        """Check if an index exists."""
        return self._client.indices.exists(index=index_name)

    def truncate(self, *, index: Index) -> Any:
        """Truncate an index (delete all documents but keep the index structure).

        Args:
            index: The Index entity to truncate

        Returns:
            Truncation response
        """
        print(f"Truncating index {index.name}...", end="")
        response = self._client.http.post(
            url=f"/{index.name}/_delete_by_query", body={"query": {"match_all": {}}}
        )
        print(" Done")
        return response

    def _hit_to_entity(self, hit: dict[str, Any]) -> Index:
        """Convert a result hit to an Index entity."""
        index_name = hit.get("_index", hit.get("index", ""))
        settings_data = hit.get("settings", {})
        mappings_data = hit.get("mappings", {})

        return Index(
            name=index_name,
            settings=Settings.model_validate(settings_data),
            mappings=Mappings.model_validate(mappings_data),
            _repository=self,
        )

    def _serialize_pydantic_with_enums(self, obj: Any) -> dict[str, Any] | list[Any] | Any:
        """Serialize a Pydantic model to a dict, converting Enum values to their string values."""
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, BaseModel):
            # Use model_dump with mode='python' to get native Python types
            # and exclude_none=False to include None values
            # Then recursively process to convert any remaining Enums
            dumped = obj.model_dump(mode="python", exclude_none=False)
            return self._serialize_pydantic_with_enums(dumped)
        if isinstance(obj, dict):
            return {str(k): self._serialize_pydantic_with_enums(v) for k, v in obj.items()}  # type: ignore[misc]
        if isinstance(obj, list):
            return [self._serialize_pydantic_with_enums(item) for item in obj]  # type: ignore[misc]
        return obj
