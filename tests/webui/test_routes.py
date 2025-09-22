import pytest
from cosmicreseller.webui import create_app


@pytest.mark.asyncio
async def test_get_index_ok():
    app = create_app()
    async with app.test_app() as test_app:
        client = test_app.test_client()
        resp = await client.get("/")
        assert resp.status_code == 200
        text = await resp.get_data(as_text=True)
        assert "Threshold" in text or "threshold" in text or "Deals" in text  # loose check for template presence


@pytest.mark.asyncio
async def test_post_index_valid(monkeypatch):
    async def fake_get_cheap_items(source, keyword, max_pages, threshold_ratio):
        return (100.0, [("Item A", 50.0, "u1"), ("Item B", 60.0, "u2")])

    import cosmicreseller.webui.routes as routes_mod
    monkeypatch.setattr(routes_mod, "get_cheap_items", fake_get_cheap_items)

    app = create_app()
    async with app.test_app() as test_app:
        client = test_app.test_client()
        resp = await client.post(
            "/",
            form={  # 👈 use `form=` so Quart populates request.form
                "source": "ebay",
                "keyword": "ps4",
                "max_items": "3",
                "threshold_ratio": "0.8",
            },
        )
        assert resp.status_code == 200
        html = await resp.get_data(as_text=True)
        assert "Item A" in html and "Item B" in html
