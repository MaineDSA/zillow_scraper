import re

from bs4 import NavigableString, Tag

from src.exceptions import ZillowParseError


def _parse_address(card: Tag) -> str:
    """Extract address from a property card."""
    address_element = card.find("address")
    if address_element:
        return address_element.get_text(strip=True).replace("|", "")
    return ""


def _parse_main_link(card: Tag) -> str:
    """Extract main property link from a property card."""
    link_element = card.find("a", class_="property-card-link", attrs={"data-test": "property-card-link"})
    if not link_element or isinstance(link_element, NavigableString):
        return ""

    href = link_element.get("href")
    if not isinstance(href, str):
        return ""

    return href if href.startswith("http") else f"https://www.zillow.com{href}"


def _clean_price_text(price_text: str) -> str:
    """Clean and standardize price text."""
    cleaned = re.sub(r"\+?\s*\d+\s*bds?(?:\s|$)", "", price_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\+?\s*bd(?:\s|$)", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("utilities", "")
    cleaned = cleaned.replace("/mo", "")
    cleaned = cleaned.replace("+", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_numeric_price(price_text: str) -> int:
    """Extract numeric value from price text for comparison."""
    numeric_only = re.sub(r"[^\d,.]", "", price_text).replace(",", "")
    try:
        return int(float(numeric_only))
    except (ValueError, TypeError):
        return 0


def _format_price_range(prices: list[str]) -> str:
    """Format a list of prices into a range or single price."""
    if not prices:
        return ""

    if len(prices) == 1:
        return prices[0]

    price_values = [(price, _extract_numeric_price(price)) for price in prices]
    valid_prices = [(price, value) for price, value in price_values if value > 0]
    if not valid_prices:
        return prices[0]
    valid_prices.sort(key=lambda x: x[1])

    min_price = valid_prices[0][0]
    max_price = valid_prices[-1][0]
    if valid_prices[0][1] == valid_prices[-1][1]:
        return min_price

    return f"{min_price} - {max_price}"


def _validate_card_basics(address: str, main_link: str) -> None:
    """Validate that card has required basic information."""
    if not address or not address.strip() or not main_link or not main_link.strip():
        missing = []
        if not address or not address.strip():
            missing.append("Address")
        if not main_link or not main_link.strip():
            missing.append("Link")
        err = f"Missing {', '.join(missing)} in card."
        raise ZillowParseError(err)


def _extract_available_units_count(card: Tag) -> int:
    """Extract the number of available units from property card badges."""
    badge_area = card.find("div", class_=re.compile(r"StyledPropertyCardBadgeArea"))
    if not badge_area or isinstance(badge_area, NavigableString):
        return 1

    badges = badge_area.find_all("span", class_=re.compile(r"StyledPropertyCardBadge"))
    for badge in badges:
        badge_text = badge.get_text(strip=True).lower()
        unit_match = re.search(r"(\d+)\s+(?:available\s+)?units?", badge_text)
        if unit_match:
            try:
                return int(unit_match.group(1))
            except ValueError:
                continue

    return 1


def _extract_main_price(card: Tag, address: str, main_link: str) -> list[tuple[str, str, str]]:
    """Extract the main price from the property card."""
    main_price_element = card.find("span", attrs={"data-test": "property-card-price"})
    if not main_price_element:
        return []

    price_text = _clean_price_text(main_price_element.get_text(strip=True))
    if not price_text:
        return []

    units_count = _extract_available_units_count(card)

    unit_suffix = f" ({units_count} units available)" if units_count > 1 else ""
    final_address = f"{address}{unit_suffix}"

    return [(final_address, price_text, main_link)]


def _create_specific_link(main_link: str, bed_info: str) -> str:
    """Create a specific link with bedroom anchor if bed info is available."""
    if not bed_info or "bd" not in bed_info.lower():
        return main_link

    bed_num = re.search(r"\d+", bed_info)
    if not bed_num:
        return main_link

    return f"{main_link}#bedrooms-{bed_num.group()}"


def _parse_inventory_data(inventory_section: Tag) -> list[tuple[str, str]]:
    """Extract price and bedroom data from inventory section."""
    inventory_prices = inventory_section.find_all("span", class_=re.compile(r"PriceText"))
    inventory_beds = inventory_section.find_all("span", class_=re.compile(r"BedText"))

    results = []
    for i, price_elem in enumerate(inventory_prices):
        price_text = _clean_price_text(price_elem.get_text(strip=True))
        if not price_text:
            continue

        bed_info = ""
        if i < len(inventory_beds):
            bed_info = inventory_beds[i].get_text(strip=True)

        results.append((price_text, bed_info))

    return results


def _create_inventory_entry(address: str, main_link: str, price: str, bed_info: str, units_count: int) -> tuple[str, str, str]:
    """Create a single inventory entry with proper formatting."""
    bed_address = f"{address} ({bed_info})" if bed_info else address

    if units_count > 1:
        bed_address = f"{bed_address} ({units_count} units available)"

    specific_link = _create_specific_link(main_link, bed_info)

    return bed_address, price, specific_link


def _extract_inventory_prices(card: Tag, address: str, main_link: str) -> list[tuple[str, str, str]]:
    """Extract multiple prices from the inventory section."""
    inventory_section = card.find("div", class_=re.compile(r"property-card-inventory-set"))
    if not inventory_section or isinstance(inventory_section, NavigableString):
        return []

    # Parse all price/bedroom combinations
    inventory_data = _parse_inventory_data(inventory_section)
    if not inventory_data:
        return []

    units_count = _extract_available_units_count(card)

    if units_count > 1 and len(inventory_data) > 1:
        prices = [price for price, _ in inventory_data]
        price_range = _format_price_range(prices)
        final_address = f"{address} ({units_count} units available)"

        return [(final_address, price_range, main_link)]

    results = []
    for price, bed_info in inventory_data:
        entry = _create_inventory_entry(address, main_link, price, bed_info, units_count)
        results.append(entry)

    return results


def _parse_zillow_card(card: Tag) -> list[tuple[str, str, str]]:
    """Parse a single property card and extract all price variations."""
    address = _parse_address(card)
    main_link = _parse_main_link(card)

    _validate_card_basics(address, main_link)

    main_prices = _extract_main_price(card, address, main_link)
    inventory_prices = _extract_inventory_prices(card, address, main_link)

    results = inventory_prices if inventory_prices else main_prices

    if not results:
        msg = "No valid prices found in card."
        raise ZillowParseError(msg)

    return results
