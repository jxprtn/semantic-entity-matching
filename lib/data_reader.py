from collections.abc import Callable, Iterable, Iterator
from enum import Enum
from typing import Any, TypedDict

import pandas as pd

from lib.interfaces import IReporter


class FileFormat(Enum):
    EXCEL = "excel"
    CSV = "csv"


class TransformationParams(TypedDict):  # noqa: D101
    columns: list[str]
    callback: Callable[[str, str], Any | None]


class DataReader(Iterable[tuple[int, pd.Series]]):
    """Read data from CSV or Excel file into a pandas DataFrame."""

    def __init__(
        self,
        *,
        file_path: str,
        limit_rows: int | None = None,
        reporter: IReporter,
        skip_rows: int = 0,
        transformations: list[TransformationParams] | None = None,
    ) -> None:
        self._file_path = file_path
        self._limit_rows = limit_rows
        self._skip_rows = skip_rows
        self._file_format = self._parse_file_format()
        self._reporter = reporter
        self.df = self._parse_file_content()

        for params in transformations or []:
            self._transform_columns(params)

    def __iter__(self) -> Iterator[tuple[int, pd.Series]]:
        yield from self.df.iterrows()

    def __getitem__(self, index: int) -> pd.Series:
        return self.df.iloc[index]

    def __len__(self) -> int:
        return len(self.df)

    def _parse_file_format(self) -> FileFormat:
        file_extension = self._file_path.lower().split(".")[-1]
        # Determine file type and read accordingly
        if file_extension in ["xlsx", "xls"]:
            return FileFormat.EXCEL
        if file_extension == "csv":
            return FileFormat.CSV
        raise ValueError(
            f"Unsupported file format: {file_extension}. Supported formats: xlsx, xls, csv",
        )

    def _parse_file_content(self, *, encoding: str = "utf-8") -> pd.DataFrame:
        try:
            if self._file_format == FileFormat.EXCEL:
                return pd.read_excel(
                    self._file_path,
                    nrows=self._limit_rows,
                    skiprows=range(1, self._skip_rows + 1) if self._skip_rows > 0 else None,
                )
            return pd.read_csv(
                self._file_path,
                nrows=self._limit_rows,
                skiprows=range(1, self._skip_rows + 1) if self._skip_rows > 0 else None,
                encoding=encoding,
            )
        except UnicodeDecodeError:
            # If UTF-8 fails, try with different encoding
            self._reporter.on_message("UTF-8 encoding failed, trying with latin-1 encoding...")
            return self._parse_file_content(encoding="latin-1")
        except pd.errors.EmptyDataError as e:
            raise ValueError("The file appears to be empty") from e
        except Exception as e:
            raise ValueError(f"Error reading file: {e!s}") from e

    def _transform_columns(
        self,
        params: TransformationParams,
    ) -> None:
        """Transform specified columns using a parse function.

        Args:
            columns: List of column names to transform
            parse_func: Function that takes (value: str, column_name: str) and returns parsed list or None
            on_warning: Optional callback for warning messages (takes message string)
        """
        for col in params["columns"]:
            if col not in self.df.columns:
                self._reporter.on_message(
                    f"Warning: Column '{col}' not found in DataFrame. Skipping transformation."
                )
                continue

            # Filter out NaN values and convert to string before parsing
            def parse_column_value(val: Any, col_name: str = col) -> list[float] | None:
                """Parse a single value in the column."""
                if pd.isna(val):
                    return None
                return params["callback"](str(val), col_name)

            self.df[col] = self.df[col].apply(parse_column_value)
            self._reporter.on_message(f"Transformed column '{col}' from string to array format")
