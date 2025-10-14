import streamlit as st

from lib.interfaces import IReporter


class WebReporter(IReporter):
    def on_message(self, *messages: str) -> None:
        pass

    def on_input(self, message: str) -> str:
        return input(message)

    def start_progress(self, total: int) -> None:
        pass

    def on_progress(self, value: int) -> None:
        pass

    def stop_progress(self) -> None:
        pass
