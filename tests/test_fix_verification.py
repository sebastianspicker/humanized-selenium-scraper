from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

from selenium.webdriver.common.by import By

from humanized_selenium_scraper.config import ScraperConfig
from humanized_selenium_scraper.extract_selenium import parse_phone_email_deep
from humanized_selenium_scraper.scraper import Session
from humanized_selenium_scraper.spec import SearchSpec
from humanized_selenium_scraper.url_filter import is_relevant_url


def test_url_filter_refinement():
    # Test that empty/short queries allow any domain if TLD passes
    assert is_relevant_url("a", "https://example.de") is True
    # Test that long queries require a part match
    assert is_relevant_url("MyCompany", "https://other.de") is False
    assert is_relevant_url("MyCompany", "https://mycompany.de") is True
    # Test that redundant parts are handled (set behavior)
    assert is_relevant_url("MyCompany MyCompany", "https://mycompany.de") is True


def test_extraction_priority():
    mock_driver = MagicMock()
    mock_driver.page_source = "Text with dummy@email.com and +49 123 456789012"

    # Mock tags
    link_tel = MagicMock()
    link_tel.get_attribute.return_value = "tel:+499999999"
    link_tel.text = "Call us"

    link_mail = MagicMock()
    link_mail.get_attribute.return_value = "mailto:priority@email.com"
    link_mail.text = "Mail us"

    mock_driver.find_elements.side_effect = lambda by, val: {
        (By.TAG_NAME, "a"): [link_tel, link_mail],
        (By.TAG_NAME, "meta"): [],
        (By.CSS_SELECTOR, "input[type='hidden']"): [],
    }.get((by, val), [])

    phone, email = parse_phone_email_deep(mock_driver)

    # +49 123 456789012 is longer than +499999999
    assert phone == "+49 123 456789012"
    # priority@email.com (18) is longer than dummy@email.com (15)
    assert email == "priority@email.com"


def test_search_loop_always_calls_back():
    config = ScraperConfig(max_retries=1)
    mock_driver = MagicMock()
    mock_driver.current_url = "https://www.google.com/"

    # Mock search box and results
    sb = MagicMock()
    mock_driver.find_element.return_value = sb  # simplify

    # Mock find_elements for links
    link = MagicMock()
    link.get_attribute.return_value = "https://target.de"

    # Use a side effect to mock glinks
    def find_elems(by, val):
        if "xpath" in str(by).lower() or "//a" in str(val):
            return [link]
        return []

    mock_driver.find_elements.side_effect = find_elems

    session = Session(config=config, driver=mock_driver)
    spec = SearchSpec(query_template="{name}")
    spec = replace(spec, navigation=replace(spec.navigation, max_google_results=1))

    # Mock evaluate_page to return False to force the loop to continue/end
    with MagicMock():
        import humanized_selenium_scraper.scraper as scraper_mod

        original_eval = scraper_mod.evaluate_page
        scraper_mod.evaluate_page = lambda *a, **k: False

        # Also mock safe_get to record calls and always return True
        original_safe_get = scraper_mod.safe_get
        safe_get_calls = []

        def _tracking_safe_get(*a, **k):
            safe_get_calls.append(a)
            return True

        scraper_mod.safe_get = _tracking_safe_get

        # Mock WebDriverWait directly in the scraper module
        mock_wait_obj = MagicMock()
        mock_wait_obj.until.return_value = MagicMock()  # The search box

        # We need to mock it where it's USED
        import humanized_selenium_scraper.scraper as scraper_mod

        original_wait_in_scraper = scraper_mod.WebDriverWait
        scraper_mod.WebDriverWait = lambda *a, **k: mock_wait_obj

        try:
            # Query must match link "target.de" to pass filter
            session.search(query="target", row={"name": "target"}, spec=spec)
        finally:
            scraper_mod.evaluate_page = original_eval
            scraper_mod.safe_get = original_safe_get
            scraper_mod.WebDriverWait = original_wait_in_scraper

    # Verify safe_get was called with google_url to navigate back (not driver.back())
    google_url = f"https://www.{config.google_domain}/"
    back_nav_calls = [c for c in safe_get_calls if len(c) >= 3 and c[2] == google_url]
    assert len(back_nav_calls) > 0, (
        f"Expected safe_get to be called with google_url={google_url} but got: {safe_get_calls}"
    )
