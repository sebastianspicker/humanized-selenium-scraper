from __future__ import annotations

import pytest

from humanized_selenium_scraper.io import read_csv_rows


def test_read_csv_rows_empty_header_raises(tmp_path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        list(read_csv_rows(path, has_header=True))


def test_read_csv_rows_columns_mismatch_raises(tmp_path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("a,b\n", encoding="utf-8")
    with pytest.raises(ValueError):
        list(read_csv_rows(path, columns=["col1"]))
