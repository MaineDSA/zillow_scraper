import pytest
from _pytest.logging import LogCaptureFixture
from bs4 import BeautifulSoup

from src.main import ZillowHomeFinder, ZillowParseError


async def test_homefinder_no_property_cards() -> None:
    """Read Zillow HTML from ../zillow.html and return a ZillowHomeFinder instance."""
    soup = BeautifulSoup("<html></html>", "html.parser")
    with pytest.raises(ZillowParseError, match="No property cards found"):
        ZillowHomeFinder(soup)


async def test_homefinder_empty_soup() -> None:
    """Read Zillow HTML from ../zillow.html and return a ZillowHomeFinder instance."""
    soup = BeautifulSoup("", "html.parser")
    with pytest.raises(ZillowParseError, match="No property cards found"):
        ZillowHomeFinder(soup)


def test_cards_with_parsing_errors_are_skipped(caplog: LogCaptureFixture) -> None:
    """Test that cards with parsing errors are logged and skipped."""
    # Create HTML with one valid card and one invalid card (missing address)
    html = """
        <html><body>
            <article data-test="property-card">
                <address>123 Valid St, Valid City</address>
                <a class="property-card-link" data-test="property-card-link" href="/valid-link/">Valid Link</a>
                <span data-test="property-card-price">$2000</span>
            </article>
            <article data-test="property-card">
                <!-- Missing address element -->
                <a class="property-card-link" data-test="property-card-link" href="/invalid-link/">Invalid Link</a>
                <span data-test="property-card-price">$1500</span>
            </article>
        </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")

    # This should not raise an exception, but should log errors
    home_finder = ZillowHomeFinder(soup)
    assert len(home_finder.addresses) == 1
    assert len(home_finder.prices) == 1
    assert len(home_finder.links) == 1

    # Check that error was logged
    assert "Skipping card 2 due to parse error" in caplog.text
