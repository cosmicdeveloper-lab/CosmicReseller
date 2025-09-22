# src/cosmicreseller/pricing.py

"""
Core business logic for CosmicReseller.

Responsibilities:
- Parse price strings into floats.
- Compute average item prices.
- Filter items below a user-defined threshold.
- Route scraping requests to the correct data source (eBay or Facebook).
"""

import re
from decimal import Decimal, InvalidOperation
from statistics import mean
from typing import Iterable, List, Tuple

from cosmicreseller.scrapers.ebay import ebay_scraper
from cosmicreseller.scrapers.facebook import scrape_facebook_marketplace_items

# Type aliases
Item = Tuple[str, str, str]         # (title, price_str, url)
CleanItem = Tuple[str, float, str]  # (title, price_float, url)

# Regex to capture numeric part of prices like "£1,234.50" or "1 234,50"
_price_re = re.compile(r"[£€$]?\s*([0-9]+(?:[,\.\s][0-9]{3})*(?:[,\.\s][0-9]{2})?)")


def _to_float(price_text: str) -> float:
    """
    Convert a raw price string into a float.

    Handles:
      - "£1,234.50"   → 1234.50
      - "1 234,50"    → 1234.50
      - "$2,000"      → 2000.00
      - "2000"        → 2000.00
    """
    cleaned = price_text.replace("\u202f", " ").strip()
    match = _price_re.search(cleaned)
    if not match:
        raise ValueError(f"No numeric price found in: {price_text!r}")

    raw = match.group(1).replace(" ", "")

    if raw.count(",") and raw.count("."):
        # Both present → assume ',' thousands, '.' decimal
        norm = raw.replace(",", "")
    elif raw.count(",") and not raw.count("."):
        # Only comma present → decide by last group length
        parts = raw.split(",")
        last = parts[-1]
        if len(last) == 3:
            # Likely thousands grouping: 2,000 → 2000
            norm = raw.replace(",", "")
        elif len(last) == 2:
            # Likely decimal: 1,23 → 1.23
            norm = raw.replace(",", ".")
        else:
            # Fallback: remove commas
            norm = raw.replace(",", "")
    else:
        norm = raw

    try:
        return float(Decimal(norm))
    except (InvalidOperation, ValueError) as err:
        raise ValueError(f"Invalid price string: {price_text!r}") from err


def filter_cheap_items(
    items: Iterable[Item],
    threshold_ratio: float,
) -> Tuple[float, List[CleanItem]]:
    """
    Filter items priced below (average_price * threshold_ratio).

    Args:
        items (Iterable[Item]): Collection of (title, price_text, url).
        threshold_ratio (float): Ratio between 0 and 1
            (e.g. 0.8 means 20% cheaper than average).

    Returns:
        tuple:
            - average_price (float): Average price of valid items.
            - cheap_items (list[CleanItem]): List of items below threshold.
    """
    prices: List[float] = []
    clean_items: List[CleanItem] = []

    for title, price_text, link in items:
        try:
            price_value = _to_float(price_text)
            prices.append(price_value)
            clean_items.append((title, price_value, link))
        except ValueError:
            continue  # skip unparseable prices

    if not prices:
        return 0.0, []

    avg_price = mean(prices)
    cheap_items = [
        (title, price, url)
        for (title, price, url) in clean_items
        if price < avg_price * threshold_ratio
    ]

    return avg_price, cheap_items


async def get_cheap_items(
    source: str,
    keyword: str,
    max_items: int,
    threshold_ratio: float,
) -> Tuple[float, List[CleanItem]]:
    """
    Orchestrate fetching and filtering cheap items from a source.

    Args:
        source (str): "facebook" or "ebay".
        keyword (str): Search keyword.
        max_items (int): Number of items/pages to fetch.
        threshold_ratio (float): Ratio (0–1), e.g. 0.8 means 20% below average.

    Returns:
        tuple:
            - average_price (float): Average of parsed prices.
            - cheap_items (list[CleanItem]): Filtered items below threshold.

    Raises:
        ValueError: If source is not supported.
    """
    source_name = source.lower().strip()

    if source_name == "facebook":
        items = await scrape_facebook_marketplace_items(keyword, max_items)
    elif source_name == "ebay":
        items = await ebay_scraper(keyword, max_items)
    else:
        raise ValueError(f"Unsupported source: {source!r}")

    return filter_cheap_items(items, threshold_ratio)
