"""Unit tests for the DataReader class."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from lib.data_reader import DataReader
from lib.null_reporter import NullReporter


@pytest.mark.unit
class TestDataReader:
    """Test suite covering CSV/Excel parsing helpers."""

    def test_reads_csv_file_and_supports_iteration(self, tmp_path: Path) -> None:
        """DataReader should read CSV files and provide iterable access."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["alpha", "beta", "gamma"],
            }
        )

        csv_path = tmp_path / "sample.csv"
        df.to_csv(csv_path, index=False)

        reader = DataReader(file_path=str(csv_path), reporter=NullReporter())

        assert len(reader) == len(df)

        rows = [row.to_dict() for _, row in reader]
        assert rows == df.to_dict("records")

        first_row = reader[0]
        assert isinstance(first_row, pd.Series)
        assert first_row["name"] == "alpha"

    def test_passes_limit_and_skip_to_pandas_reader(
        self,
        monkeypatch: Any,
        tmp_path: Path,
    ) -> None:
        """DataReader should forward limit/skip params to pandas.read_csv."""
        csv_path = tmp_path / "limited.csv"
        csv_path.write_text("id,name\n1,alpha\n")

        captured: dict[str, object] = {}

        def fake_read_csv(path: str, **kwargs: Any) -> pd.DataFrame:
            captured["path"] = path
            captured["kwargs"] = kwargs
            return pd.DataFrame({"id": []})

        monkeypatch.setattr(pd, "read_csv", fake_read_csv)

        DataReader(file_path=str(csv_path), limit_rows=10, skip_rows=5, reporter=NullReporter())

        assert captured["path"] == str(csv_path)
        assert captured["kwargs"]["nrows"] == 10
        # Implementation converts skip_rows to range(1, skip_rows + 1)
        assert captured["kwargs"]["skiprows"] == range(1, 6)
        assert captured["kwargs"]["encoding"] == "utf-8"

    def test_uses_excel_reader_for_excel_files(self, monkeypatch: Any, tmp_path: Path) -> None:
        """Excel files should be routed through pandas.read_excel."""
        excel_path = tmp_path / "dataset.xlsx"
        excel_path.touch()

        captured: dict[str, object] = {}

        def fake_read_excel(path: str, **kwargs: Any) -> pd.DataFrame:
            captured["path"] = path
            captured["kwargs"] = kwargs
            return pd.DataFrame({"value": [42]})

        monkeypatch.setattr(pd, "read_excel", fake_read_excel)

        reader = DataReader(file_path=str(excel_path), limit_rows=1, skip_rows=2, reporter=NullReporter())

        assert captured["path"] == str(excel_path)
        assert captured["kwargs"]["nrows"] == 1
        # Implementation converts skip_rows to range(1, skip_rows + 1)
        assert captured["kwargs"]["skiprows"] == range(1, 3)
        # Excel files don't use encoding parameter
        assert "encoding" not in captured["kwargs"]
        assert len(reader) == 1

    def test_raises_value_error_for_unsupported_format(self, tmp_path: Path) -> None:
        """Unsupported file extensions should raise ValueError."""
        bad_path = tmp_path / "data.json"
        bad_path.write_text("{}")

        with pytest.raises(ValueError, match="Unsupported file format"):
            DataReader(file_path=str(bad_path), reporter=NullReporter())
