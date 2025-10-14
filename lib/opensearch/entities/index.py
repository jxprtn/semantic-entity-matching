"""Index domain entity."""

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, PrivateAttr, field_validator

from lib.opensearch.entities.base_entity import BaseEntity

if TYPE_CHECKING:
    from lib.opensearch.repositories.index import IndexRepository


class TextField(BaseModel):
    """Represents a text field mapping."""

    type: str = "text"


class VectorFieldMethodParameters(BaseModel):
    """Parameters for vector field search method."""

    ef_construction: int = Field(default=128, gt=0)
    m: int = Field(default=24, gt=0)


class VectorSearchEngine(Enum):
    """Vector search engine types."""

    FAISS = "faiss"
    NMSLIB = "nmslib"


class VectorSearchSpaceType(Enum):
    """Vector space distance metrics."""

    L2 = "l2"
    COSINE = "cosine"


class VectorSearchMethod(Enum):
    """Vector search algorithm methods."""

    HNSW = "hnsw"
    IVF = "ivf"


class VectorFieldMethod(BaseModel):
    """Configuration for vector field search method."""

    name: VectorSearchMethod = VectorSearchMethod.HNSW
    space_type: VectorSearchSpaceType = VectorSearchSpaceType.L2
    engine: VectorSearchEngine = VectorSearchEngine.FAISS
    parameters: VectorFieldMethodParameters = Field(default_factory=VectorFieldMethodParameters)


class VectorField(BaseModel):
    """Represents a knn_vector field mapping."""

    type: str = "knn_vector"
    dimension: int = Field(default=1024, gt=0)
    method: VectorFieldMethod = Field(default_factory=VectorFieldMethod)


class IndexSettings(BaseModel):
    """Index-level settings."""

    knn: bool = False
    knn_algo_param_ef_search: int | None = Field(default=None, gt=0)

    @field_validator("knn_algo_param_ef_search")
    @classmethod
    def validate_ef_search(cls, v: int | None) -> int | None:
        """Validate ef_search is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("knn_algo_param_ef_search must be positive if provided")
        return v


class Settings(BaseModel):
    """Index settings container."""

    index: IndexSettings = Field(default_factory=IndexSettings)


class Mappings(BaseModel):
    """Index mappings container."""

    properties: dict[str, VectorField] = Field(default_factory=dict)


class Index(BaseModel, BaseEntity["Index"]):
    """Domain model representing an OpenSearch Index.

    An index stores documents and provides search capabilities including vector search.
    """

    name: str
    settings: Settings
    mappings: Mappings
    _repository: "IndexRepository" = PrivateAttr()  # type: ignore[assignment]

    def __init__(self, **data: Any) -> None:
        """Initialize Index with repository support."""
        repository = data.pop("_repository", None)
        super().__init__(**data)
        if repository is not None:
            object.__setattr__(self, "_repository", repository)

    def delete(self) -> Any:  # type: ignore[override]
        """Delete this index.

        Returns:
            Deletion response from OpenSearch
        """
        return self._repository.delete(index=self)

    def exists(self) -> bool:
        """Check if this index exists.

        Returns:
            True if the index exists, False otherwise
        """
        return self._repository.exists(index=self)

    def truncate(self) -> Any:
        """Truncate this index (delete all documents but keep the index structure).

        Returns:
            Truncation response from OpenSearch
        """
        return self._repository.truncate(index=self)
