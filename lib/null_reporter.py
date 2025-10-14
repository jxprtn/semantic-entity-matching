"""Null reporter for testing purposes, or when no reporter is needed."""

from lib.interfaces import IReporter


class NullReporter(IReporter):
    """Null reporter that does nothing."""

    def on_message(self, *messages: str) -> None:
        """Do nothing."""

    def on_input(self, message: str) -> str:  # noqa: ARG002
        """Return empty string."""
        return ""

    def start_progress(self, total: int) -> None:
        """Do nothing."""

    def stop_progress(self) -> None:
        """Do nothing."""

    def on_progress(self, value: int) -> None:
        """Do nothing."""
