# src/cosmicreseller/webui/routes.py

"""
Quart web UI for CosmicReseller.

Shows a simple form to search Facebook Marketplace or eBay and displays
items priced below a user-defined threshold.
"""

from quart import Blueprint, render_template, request
from cosmicreseller.pricing import get_cheap_items

bp = Blueprint(
    "webui",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@bp.route("/", methods=["GET", "POST"])
async def index():
    """
    Render the index page.

    GET:
        Show the form with default values.
    POST:
        Validate input, run the scraper/orchestrator, and render results.
    """
    # Defaults
    source = "facebook"
    keyword = ""
    max_items = 1
    threshold_ratio = 0.8
    error = None
    avg_price = None
    items = []

    if request.method == "POST":
        form = await request.form
        try:
            source = (form.get("source") or "").strip().lower()
            keyword = (form.get("keyword") or "").strip()
            max_items = int(form.get("max_items") or 1)
            threshold_ratio = float(form.get("threshold_ratio") or 0.8)

            if source not in {"facebook", "ebay"}:
                raise ValueError("Source must be 'facebook' or 'ebay'.")
            if not keyword:
                raise ValueError("Keyword cannot be empty.")
            if max_items < 1:
                raise ValueError("Max pages must be ≥ 1.")
            if not (0 < threshold_ratio < 1):
                raise ValueError(
                    "Threshold ratio must be between 0 and 1 (e.g., 0.8)."
                )

            # Orchestrate and fetch results
            avg_price, items = await get_cheap_items(
                source, keyword, max_items, threshold_ratio
            )

        except Exception as exc:
            error = str(exc)

    return await render_template(
        "index.html",
        source=source,
        keyword=keyword,
        max_pages=max_items,        # template expects 'max_pages'
        threshold_ratio=threshold_ratio,
        error=error,
        avg_price=avg_price,
        items=items,
    )
