"""
Utility functions for the OpenSearch CLI tool.
"""

from typing import Any, TypeGuard


def is_list(value: Any) -> TypeGuard[list[Any]]:
    """Check if a value is a list."""
    return isinstance(value, list)


def is_vector_embedding(value: Any) -> TypeGuard[list[float]]:
    """Check if a value is a vector embedding."""
    return is_list(value) and all(isinstance(item, float) for item in value)


def build_pipeline_name(*, base_name: str, index_name: str, column: str | None = None) -> str:
    """
    Build a pipeline name from base name, index name, and optionally a column.

    Args:
        base_name: Base pipeline name
        index_name: Index name
        column: Optional column name for search pipelines

    Returns:
        Constructed pipeline name
    """
    if column:
        return f"{base_name}-{index_name}-{column}"
    return f"{base_name}-{index_name}"
