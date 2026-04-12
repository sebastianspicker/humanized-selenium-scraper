import pytest

from humanized_selenium_scraper.io import parse_columns_arg


def test_parse_columns_arg_rejects_duplicates() -> None:
    with pytest.raises(ValueError):
        parse_columns_arg("a,b,a")
