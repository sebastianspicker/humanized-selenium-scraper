from humanized_selenium_scraper.url_filter import is_relevant_url


def test_is_relevant_url_filters_blacklist() -> None:
    assert is_relevant_url("firma berlin", "https://www.facebook.com/firma") is False


def test_is_relevant_url_requires_tld_and_query_part() -> None:
    assert is_relevant_url("firma berlin", "https://example.invalid/") is False
    assert is_relevant_url("firma berlin", "https://firma-berlin.de/contact") is True


def test_is_relevant_url_rejects_non_http_schemes() -> None:
    """Only http/https are allowed; javascript:, file:, data:, blob: must be rejected."""
    assert is_relevant_url("x", "javascript:alert(1)") is False
    assert is_relevant_url("x", "file:///etc/passwd") is False
    assert is_relevant_url("x", "data:text/html,<script>") is False
    assert is_relevant_url("x", "blob:https://example.com/uuid") is False
    assert is_relevant_url("firma", "https://firma.de/") is True
    assert is_relevant_url("firma", "http://firma.de/") is True
