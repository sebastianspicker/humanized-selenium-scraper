from __future__ import annotations

from pathlib import Path

import pytest

from humanized_selenium_scraper.config import ScraperConfig
from humanized_selenium_scraper.driver import _validate_path_safe, create_driver


def test_create_driver_raises_when_profile_path_is_file(tmp_path) -> None:
    """When profile_dir exists as a file (not a directory), create_driver raises ValueError."""
    profile_file = tmp_path / "profile"
    profile_file.write_text("", encoding="utf-8")
    assert profile_file.is_file()

    config = ScraperConfig(chrome_profile_root=profile_file)
    with pytest.raises(ValueError, match="Cannot create Chrome profile directory"):
        create_driver(config, profile_dir=config.chrome_profile_root)


def test_validate_path_safe_allows_windows_style_backslashes() -> None:
    candidate = Path(r"C:\Users\alice\chrome_profile")
    resolved = _validate_path_safe(candidate)
    assert isinstance(resolved, Path)
