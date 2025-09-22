import pytest
from unittest.mock import AsyncMock, patch

import httpx
from cosmicreseller.scrapers import ebay as ebay_mod


@pytest.mark.asyncio
async def test_get_app_token_mocks_http():
    # Fake POST response payload from eBay
    fake_payload = {"access_token": "FAKE_TOKEN", "expires_in": 7200}

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return fake_payload

    async def fake_post(url, headers=None, data=None):
        assert "identity/v1/oauth2/token" in url
        return FakeResp()

    with patch.object(httpx, "AsyncClient") as client_cls:
        client = client_cls.return_value.__aenter__.return_value
        client.post = AsyncMock(side_effect=fake_post)

        token = await ebay_mod.get_app_token()
        assert token == "FAKE_TOKEN"

@pytest.mark.asyncio
async def test_ebay_scraper_uses_stubs(monkeypatch):
    # Stub category resolution (avoid real taxonomy call)
    async def fake_get_category_id(keyword, marketplace_id="EBAY_GB"):
        return ("123", "TestCat")

    # Stub search_items pagination: return two pages then stop.
    async def fake_search_items(**kwargs):
        offset = kwargs.get("offset", 0)
        if offset == 0:
            return {
                "itemSummaries": [
                    {"title": "Thing 1", "price": {"value": "10", "currency": "GBP"}, "itemWebUrl": "u1"},
                    {"title": "Thing 2", "price": {"value": "20", "currency": "GBP"}, "itemWebUrl": "u2"},
                ],
                "next": "exists",
            }
        else:
            return {
                "itemSummaries": [
                    {"title": "Thing 3", "price": {"value": "30", "currency": "GBP"}, "itemWebUrl": "u3"},
                ]
            }

    monkeypatch.setattr(ebay_mod, "get_category_id", fake_get_category_id)
    monkeypatch.setattr(ebay_mod, "search_items", fake_search_items)

    items = await ebay_mod.ebay_scraper("ps4", max_items=5)
    # Check normalization: (title, "GBP {value}", url)
    assert items == [
        ("Thing 1", "GBP 10", "u1"),
        ("Thing 2", "GBP 20", "u2"),
        ("Thing 3", "GBP 30", "u3"),
    ]
