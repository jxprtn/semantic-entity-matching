"""Console reporter for CLI commands."""

from typing import NoReturn

from tqdm import tqdm

from lib.interfaces import IReporter


class ConsoleReporter(IReporter):
    """Console reporter that prints messages to stdout and updates a progress bar."""

    def __init__(self) -> None:
        """Initialize the reporter."""
        self._progress_bar: tqdm[NoReturn] | None = None

    def on_message(self, *messages: str) -> None:
        """Print message to console."""
        for message in messages:
            print(message)

    def on_input(self, message: str) -> str:
        """Read input from console."""
        return input(message)

    def start_progress(self, total: int) -> None:
        """Start progress bar."""
        self._progress_bar = tqdm(total=total)

    def stop_progress(self) -> None:
        """Stop progress bar."""
        if self._progress_bar:
            self._progress_bar.close()

    def on_progress(self, value: int) -> None:
        """Update progress bar."""
        if self._progress_bar:
            self._progress_bar.update(value)
