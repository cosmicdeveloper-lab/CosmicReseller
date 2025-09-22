# src/cosmicreseller/scrapers/facebook.py

"""
Facebook Marketplace scraper using Playwright (async).

This module provides a function to scrape items from Facebook Marketplace
based on a search keyword. It reuses a saved persistent Firefox profile
(created via `scripts/create_fb_profile.py`) to bypass login prompts.
"""

import logging
import urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLAYWRIGHT_PROFILE = PROJECT_ROOT / "scripts" / "playwright_profile"


async def scrape_facebook_marketplace_items(keyword: str, max_items: int):
    """
    Scrape items from Facebook Marketplace for the given keyword.

    Args:
        keyword (str): Search query string.
        max_items (int): Maximum number of items to collect.

    Returns:
        list[tuple[str, str, str]]: A list of (title, price, url) tuples.
    """
    search_url = (
        "https://www.facebook.com/marketplace/search/"
        f"?query={urllib.parse.quote(keyword)}"
    )
    items: list[tuple[str, str, str]] = []
    seen_urls: set[str] = set()

    logger.info("Starting Facebook Marketplace scrape for keyword='%s'", keyword)

    async with async_playwright() as playwright:
        logger.debug("Launching Firefox with persistent profile: %s", PLAYWRIGHT_PROFILE)
        context = await playwright.firefox.launch_persistent_context(
            PLAYWRIGHT_PROFILE,
            headless=True,
        )
        page = await context.new_page()

        try:
            logger.info("Navigating to search URL: %s", search_url)
            await page.goto(search_url, timeout=30_000)
            await page.wait_for_selector('a[href^="/marketplace/item/"]', timeout=30_000)

            logger.debug("Scrolling to load more results...")
            for _ in range(3):
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(1500)

            cards = await page.query_selector_all('a[href^="/marketplace/item/"]')
            logger.info("Found %d potential cards", len(cards))

            for card in cards:
                href = await card.get_attribute("href")
                if not href:
                    continue

                full_url = urllib.parse.urljoin("https://www.facebook.com", href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                try:
                    text_block = await card.inner_text()
                    if not text_block:
                        continue

                    parts = [t.strip() for t in text_block.split("\n") if t.strip()]
                    price = parts[0] if len(parts) > 0 else "N/A"
                    title = parts[1] if len(parts) > 1 else "N/A"
                except Exception as parse_err:
                    logger.warning("Failed to parse a card: %s", parse_err)
                    continue

                logger.debug("Parsed item: title='%s', price='%s'", title, price)
                items.append((title, price, full_url))

                if len(items) >= max_items:
                    logger.info("Reached max_items limit (%d).", max_items)
                    break

        except Exception as scrape_err:
            logger.error("Failed to load Facebook Marketplace: %s", scrape_err)
            return []
        finally:
            logger.debug("Closing browser context.")
            await context.close()

    logger.info("Scraping finished. Collected %d items.", len(items))
    return items
