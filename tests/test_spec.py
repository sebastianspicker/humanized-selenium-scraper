from humanized_selenium_scraper.spec import render_template


def test_render_template_success() -> None:
    row = {"name": "ACME", "city": "Berlin"}
    assert render_template("{name} {city} contact", row) == "ACME Berlin contact"


def test_render_template_missing_key_has_helpful_error() -> None:
    row = {"name": "ACME"}
    try:
        render_template("{name} {city}", row)
    except ValueError as exc:
        msg = str(exc)
        assert "city" in msg
        assert "Available columns" in msg
    else:
        raise AssertionError("Expected ValueError")
