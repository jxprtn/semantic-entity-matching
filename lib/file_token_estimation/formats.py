"""File format definitions for token estimation."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class FileFormatConfig:
    """Configuration for a file format."""

    extensions: frozenset[str]
    ratio: float


class FileFormat(Enum):
    """File format enumeration with configuration."""

    TEXT = FileFormatConfig(
        extensions=frozenset({"txt", "md", "csv", "json", "html"}),
        ratio=0.25,
    )
    IMAGE = FileFormatConfig(
        extensions=frozenset({"jpg", "jpeg", "png", "gif", "webp"}),
        ratio=0.6,
    )
    DOCUMENT = FileFormatConfig(
        extensions=frozenset(),
        ratio=0.15,
    )
