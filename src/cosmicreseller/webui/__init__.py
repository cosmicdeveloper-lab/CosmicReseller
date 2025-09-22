# src/cosmicreseller/webui/__init__.py

"""
Web UI package for CosmicReseller.

Exposes a Quart application factory (`create_app`) that registers the
web UI blueprint and can be used by ASGI servers (e.g. Hypercorn).
"""

from quart import Quart
from cosmicreseller.webui.routes import bp


def create_app() -> Quart:
    """
    Application factory for the CosmicReseller web UI.

    Returns:
        Quart: Configured Quart application with the web UI blueprint.
    """
    app = Quart(__name__)
    app.register_blueprint(bp)
    return app


# Convenience for ASGI runners (e.g., `hypercorn src.cosmicreseller.webui:app`)
app = create_app()
