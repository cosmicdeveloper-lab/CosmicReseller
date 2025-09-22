import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from cosmicreseller.scrapers import facebook as fb_mod

@pytest.mark.asyncio
async def test_scrape_facebook_marketplace_items_with_stubbed_playwright(monkeypatch):
    # Fake "card" elements
    class FakeCard:
        def __init__(self, href, text):
            self._href = href
            self._text = text
        async def get_attribute(self, name):
            assert name == "href"
            return self._href
        async def inner_text(self):
            return self._text

    cards = [
        FakeCard("/marketplace/item/1", "£10\nCool Item"),
        FakeCard("/marketplace/item/2", "£20\nAnother One"),
        FakeCard("/marketplace/item/1", "£10\nDuplicate URL"),  # should dedupe
    ]

    # Fake Page/Context/Browser
    class FakePage:
        async def goto(self, url, timeout=None): return None
        async def wait_for_selector(self, sel, timeout=None): return None
        class mouse:
            @staticmethod
            async def wheel(x, y): return None
        async def wait_for_timeout(self, ms): return None
        async def query_selector_all(self, sel): return cards

    class FakeContext:
        async def new_page(self): return FakePage()
        async def close(self): return None

    class FakeFirefox:
        async def launch_persistent_context(self, *_args, **_kwargs):
            return FakeContext()

    # async_playwright() context manager stub
    class FakeAP:
        def __init__(self): self.firefox = FakeFirefox()
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False

    monkeypatch.setattr(fb_mod, "async_playwright", lambda: FakeAP())

    items = await fb_mod.scrape_facebook_marketplace_items("ps4", max_items=10)
    # Should dedupe URL 1
    assert items == [
        ("Cool Item", "£10", "https://www.facebook.com/marketplace/item/1"),
        ("Another One", "£20", "https://www.facebook.com/marketplace/item/2"),
    ]
