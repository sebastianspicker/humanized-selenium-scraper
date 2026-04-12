from humanized_selenium_scraper.relevance import (
    address_score,
    evaluate_page,
    normalize_address_part,
)


def test_normalize_address_part_umlauts_and_street_aliases() -> None:
    # Umlauts and German street abbreviations normalized to canonical form
    assert normalize_address_part("Müllerstraße 1") == "mullerstr 1"
    assert normalize_address_part("Mullerstr. 1") == "mullerstr 1"
    assert normalize_address_part("Mullerstrasse 1") == "mullerstr 1"


def test_address_score_zip_city_street() -> None:
    html = "Contact: Main St 12, 12345 Berlin"
    assert address_score(html, "Main St 12", "12345", "Berlin") == 3


def test_evaluate_page_threshold() -> None:
    html = "Contact Contact Contact Contact Contact Contact Main St 12 12345 Berlin"
    assert (
        evaluate_page(
            html,
            keywords=["contact"],
            min_keyword_hits=6,
            require_address=True,
            street="Main St 12",
            plz="12345",
            city="Berlin",
            address_min_score=2,
        )
        is True
    )
