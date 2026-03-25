from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

from humanized_selenium_scraper import cli
from humanized_selenium_scraper.config import ScraperConfig
from humanized_selenium_scraper.exceptions import SkipEntryError
from humanized_selenium_scraper.spec import SearchSpec


class DummySession:
    @classmethod
    def create(cls, config: ScraperConfig, *, profile_dir: Path):
        return cls()

    def close(self) -> None:
        return None

    def search(self, *, query: str, row: dict[str, str], spec: SearchSpec, attempt: int = 1):
        if "skip" in query.lower():
            raise SkipEntryError("skip row")
        if "error" in query.lower():
            raise RuntimeError("boom")
        return "https://example.com", "123", "a@b.com"


def test_version_exits_zero() -> None:
    """--version prints version and exits 0."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(Path(__file__).resolve().parent.parent)] + env.get("PYTHONPATH", "").split(os.pathsep)
    )
    result = subprocess.run(
        [sys.executable, "-m", "humanized_selenium_scraper", "--version"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout or "0.1.0" in result.stderr


def test_run_writes_output_and_handles_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cli, "Session", DummySession)
    monkeypatch.setattr(cli, "random_pause", lambda *_a, **_k: None)

    input_path = tmp_path / "input.csv"
    input_path.write_text("GoodCo\nSkipCo\nErrorCo\n", encoding="utf-8")

    output_path = tmp_path / "output.csv"

    spec = SearchSpec(query_template="{name}")
    config = ScraperConfig()

    exit_code = cli.run(
        input_file=input_path,
        output_file=output_path,
        config=config,
        spec=spec,
        delimiter=",",
        has_header=False,
        columns=["name"],
    )

    assert exit_code == 0

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == ["name", "Website", "Phone", "Email"]
    assert rows[1] == ["GoodCo", "https://example.com", "123", "a@b.com"]
    assert rows[2] == ["SkipCo", "", "", ""]
    assert rows[3] == ["ErrorCo", "", "", ""]


def test_run_escapes_csv_formula_injection(tmp_path, monkeypatch) -> None:
    """Output cells that look like formulas (e.g. =, +, -) must be escaped."""

    class FormulaSession(DummySession):
        def search(self, *, query: str, row: dict[str, str], spec: SearchSpec, attempt: int = 1):
            # Return values that could be interpreted as formulas in Excel
            return "https://evil.com", "=1+1", "+1234567890"

    monkeypatch.setattr(cli, "Session", FormulaSession)
    monkeypatch.setattr(cli, "random_pause", lambda *_a, **_k: None)

    input_path = tmp_path / "input.csv"
    input_path.write_text("Name\nAcme\n", encoding="utf-8")
    output_path = tmp_path / "output.csv"

    exit_code = cli.run(
        input_file=input_path,
        output_file=output_path,
        config=ScraperConfig(),
        spec=SearchSpec(query_template="{Name}"),
        delimiter=",",
        has_header=True,
        columns=None,
    )
    assert exit_code == 0

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["Name", "Website", "Phone", "Email"]
    # Phone and Email should be prefixed with ' so not interpreted as formula
    assert rows[1][2].startswith("'") and "=1+1" in rows[1][2]
    assert rows[1][3].startswith("'") and "+1234567890" in rows[1][3]


def test_run_zero_data_rows_writes_header_only(tmp_path, monkeypatch) -> None:
    """When input has only a header (no data rows), output file is created with header only."""
    monkeypatch.setattr(cli, "Session", DummySession)
    monkeypatch.setattr(cli, "random_pause", lambda *_a, **_k: None)

    input_path = tmp_path / "input.csv"
    input_path.write_text("Name,City\n", encoding="utf-8")
    output_path = tmp_path / "output.csv"

    exit_code = cli.run(
        input_file=input_path,
        output_file=output_path,
        config=ScraperConfig(),
        spec=SearchSpec(query_template="{Name} {City}"),
        delimiter=",",
        has_header=True,
        columns=None,
    )
    assert exit_code == 0
    assert output_path.exists()
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == 1
    assert rows[0] == ["Name", "City", "Website", "Phone", "Email"]
