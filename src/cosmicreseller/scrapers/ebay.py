# src/cosmicreseller/scrapers/ebay.py

"""
eBay Browse & Taxonomy API integration.

This module provides helpers to:
- Authenticate with eBay using OAuth2 app tokens.
- Resolve search keywords into taxonomy category IDs.
- Query the eBay Browse API for item summaries.

Business logic:
- Cached app tokens are reused to avoid re-authentication.
- Keyword is auto-resolved into a leaf category ID to reduce noise.
"""

import asyncio
import base64
import json
import logging
import os
import time
from typing import Optional

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# eBay API credentials
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")

# OAuth & Browse
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
BROWSE_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# Taxonomy
TAXONOMY_DEFAULT_TREE_URL = (
    "https://api.ebay.com/commerce/taxonomy/v1/get_default_category_tree_id"
)
TAXONOMY_SUGGEST_URL_TMPL = (
    "https://api.ebay.com/commerce/taxonomy/v1/category_tree/{tree_id}/get_category_suggestions"
)

# Token cache
_token_cache: dict[str, float | str | None] = {"value": None, "expires_at": 0}
TOKEN_SCOPE = "https://api.ebay.com/oauth/api_scope"


async def get_app_token(scope: str = TOKEN_SCOPE) -> str:
    """
    Get (and cache) an OAuth2 app token.

    Args:
        scope (str): OAuth2 scope to request.

    Returns:
        str: A valid app token.
    """
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"] - 60:
        logger.debug("Using cached eBay app token.")
        return _token_cache["value"]  # type: ignore

    logger.info("Fetching new eBay app token...")
    auth = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials", "scope": scope}

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(TOKEN_URL, headers=headers, data=data)
        resp.raise_for_status()
        payload = resp.json()

    token = payload["access_token"]
    expires_at = now + payload.get("expires_in", 0)
    _token_cache.update({"value": token, "expires_at": expires_at})

    logger.debug("Received eBay app token, expires in %s seconds.", payload.get("expires_in"))
    return token


async def get_default_category_tree_id(marketplace_id: str = "EBAY_GB") -> str:
    """
    Ask eBay which taxonomy tree applies to a given marketplace.

    Args:
        marketplace_id (str): eBay marketplace code (default "EBAY_GB").

    Returns:
        str: Category tree ID for the marketplace.
    """
    token = await get_app_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
        "Accept-Language": "en-GB",
    }
    params = {"marketplace_id": marketplace_id}

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(TAXONOMY_DEFAULT_TREE_URL, headers=headers, params=params)
        resp.raise_for_status()
        payload = resp.json()

    return payload["categoryTreeId"]


async def get_category_id(
    keyword: str, marketplace_id: str = "EBAY_GB"
) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve a keyword to a LEAF categoryId via the Taxonomy API.

    Args:
        keyword (str): Search keyword to resolve.
        marketplace_id (str): eBay marketplace code.

    Returns:
        tuple[str | None, str | None]: (category_id, category_name),
        or (None, None) if not found.
    """
    token = await get_app_token()
    tree_id = await get_default_category_tree_id(marketplace_id)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
        "Accept-Language": "en-GB",
    }
    params = {"q": keyword}

    url = TAXONOMY_SUGGEST_URL_TMPL.format(tree_id=tree_id)
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        payload = resp.json()

    suggestions = payload.get("categorySuggestions", [])
    if not suggestions:
        logger.warning("No category suggestions found for keyword='%s'", keyword)
        return None, None

    cat = suggestions[0]["category"]
    cat_id = cat["categoryId"]
    cat_name = cat["categoryName"]

    logger.info(
        "Resolved keyword='%s' → category_id=%s (%s) [tree=%s]",
        keyword,
        cat_id,
        cat_name,
        tree_id,
    )
    return cat_id, cat_name


async def search_items(
    q: str,
    limit: int = 100,
    offset: int = 0,
    sort: str = "best_match",
    buying_options: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    category_id: Optional[str] = None,
    conditions: Optional[list[str]] = None,
    country: str | None = "GB",
    aspect_filter: Optional[str] = None,
) -> dict:
    """
    Query the eBay Browse API for items.

    Args:
        q (str): Search keyword.
        limit (int): Max results per page (≤ 200).
        offset (int): Result offset for pagination.
        sort (str): Sorting mode (default: "best_match").
        buying_options (str | None): "FIXED_PRICE", "AUCTION|BEST_OFFER", etc.
        price_min (float | None): Minimum price filter.
        price_max (float | None): Maximum price filter.
        category_id (str | None): eBay category ID filter.
        conditions (list[str] | None): Condition filters (e.g., ["NEW", "USED"]).
        country (str | None): Location filter.
        aspect_filter (str | None): Aspect filter string.

    Returns:
        dict: JSON payload from eBay Browse API.
    """
    token = await get_app_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        "Accept-Language": "en-GB",
    }

    params: dict[str, str | int] = {
        "q": q,
        "limit": min(int(limit), 200),
        "offset": int(offset),
        "sort": sort,
        "fieldgroups": (
            "MATCHING_ITEMS,ASPECT_REFINEMENTS,CONDITION_REFINEMENTS,CATEGORY_REFINEMENTS"
        ),
    }

    filters: list[str] = []
    if buying_options:
        filters.append(f"buyingOptions:{{{buying_options}}}")
    if conditions:
        filters.append("conditions:{" + "|".join(conditions) + "}")
    if price_min is not None or price_max is not None:
        lo = "" if price_min is None else f"{float(price_min):.2f}"
        hi = "" if price_max is None else f"{float(price_max):.2f}"
        filters.append(f"price:[{lo}..{hi}]")
        filters.append("priceCurrency:GBP")
    if country:
        filters.append(f"itemLocationCountry:{country}")
        filters.append(f"deliveryCountry:{country}")
    if category_id:
        filters.append(f"categoryId:{{{category_id}}}")
    if filters:
        params["filter"] = ",".join(filters)
    if aspect_filter:
        params["aspect_filter"] = aspect_filter

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(BROWSE_SEARCH_URL, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


async def ebay_scraper(keyword: str, max_items: int) -> list[tuple[str, str, str]]:
    """
    Fetch items from eBay Browse API.

    Args:
        keyword (str): Search keyword.
        max_items (int): Maximum number of items to fetch.

    Returns:
        list[tuple[str, str, str]]: List of (title, price_str, url) tuples.
    """
    category_id, category_name = await get_category_id(keyword, marketplace_id="EBAY_GB")

    results: list[tuple[str, str, str]] = []
    offset = 0
    while offset < max_items:
        page = await search_items(
            q=keyword,
            limit=min(200, max_items - offset),
            offset=offset,
            sort="best_match",
            buying_options="FIXED_PRICE",
            category_id=category_id,
            conditions=["USED", "NEW"],
            country="GB",
        )
        items = page.get("itemSummaries", []) or []
        if not items:
            break

        for item in items:
            title = item.get("title") or "N/A"
            price = (item.get("price") or {}).get("value")
            currency = (item.get("price") or {}).get("currency", "")
            url = item.get("itemWebUrl") or "#"

            if price:
                results.append((title, f"{currency} {price}", url))

        logger.info("Fetched %d items (offset=%d)", len(items), offset)

        offset += len(items)
        if "next" not in page:
            break

    logger.info("Total collected: %d items", len(results))
    return results
