"""Logging configuration for the OpenSearch CLI tool.
"""

import logging
import sys
from enum import Enum


class LogLevel(Enum):
    """Logging level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def setup_logging(
    level: str | LogLevel = LogLevel.INFO,
    format_string: str | None = None,
    include_timestamp: bool = True,
) -> logging.Logger:
    """Configure logging for the CLI application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) as string or LogLevel enum
        format_string: Custom format string (optional)
        include_timestamp: Whether to include timestamps in logs

    Returns:
        Configured logger instance

    """
    # Convert LogLevel enum or string to logging constant
    level_str = level.value if isinstance(level, LogLevel) else level.upper()
    numeric_level = getattr(logging, level_str, logging.INFO)

    # Default format with timestamp and module info
    if format_string is None:
        if include_timestamp:
            format_string = "%(asctime)s  %(name)s  %(levelname)s  %(message)s"
        else:
            format_string = "%(name)s  %(levelname)s  %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Override any existing configuration
    )

    # Return logger for the main application
    return logging.getLogger("opensearch-cli")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    """
    return logging.getLogger(name)
