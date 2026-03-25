from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from humanized_selenium_scraper.config import ScraperConfig


def test_from_mapping_invalid_chrome_profile_root_uses_default() -> None:
    """Non-path types for chrome_profile_root fall back to default."""
    defaults = ScraperConfig()
    cfg = ScraperConfig.from_mapping({"chrome_profile_root": ["./profile"]})
    assert cfg.chrome_profile_root == defaults.chrome_profile_root


def test_from_mapping_invalid_int_uses_default() -> None:
    """Invalid int values fall back to defaults."""
    defaults = ScraperConfig()
    cfg = ScraperConfig.from_mapping({"restart_threshold": "never", "max_retries": "many"})
    assert cfg.restart_threshold == defaults.restart_threshold
    assert cfg.max_retries == defaults.max_retries


def test_from_mapping_valid_chrome_profile_root() -> None:
    """Valid str path is accepted."""
    cfg = ScraperConfig.from_mapping({"chrome_profile_root": "my_profile"})
    assert cfg.chrome_profile_root == Path("my_profile")


def test_validate_on_valid_config_succeeds() -> None:
    """validate() is idempotent on a valid config (e.g. after replace)."""
    config = ScraperConfig()
    config.validate()  # no raise


def test_replace_with_invalid_google_domain_raises() -> None:
    """replace() with invalid google_domain raises; validate() catches __post_init__ bypass."""
    valid = ScraperConfig()
    with pytest.raises(ValueError, match="Invalid Google domain"):
        replace(valid, google_domain="evil.com")
