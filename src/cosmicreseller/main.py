# src/cosmicreseller/main.py

"""
Main entry point for CosmicReseller.

Runs both:
1. Telegram bot interface.
2. Quart web UI (via Hypercorn ASGI server).

These are executed concurrently under asyncio.
"""

import asyncio

from hypercorn.asyncio import serve
from hypercorn.config import Config

from src.cosmicreseller.telegram_bot import start_bot
from src.cosmicreseller.webui import create_app
from src.cosmicreseller.logger import configure_root_logger


async def run_webui() -> None:
    """
    Launch the Quart web UI using Hypercorn.
    """
    app = create_app()
    cfg = Config()
    cfg.bind = ["0.0.0.0:8000"]
    cfg.use_reloader = False
    await serve(app, cfg)


async def main() -> None:
    """
    Run the Telegram bot and web UI concurrently.
    """
    await asyncio.gather(
        start_bot(),
        run_webui(),
    )


if __name__ == "__main__":
    configure_root_logger()
    asyncio.run(main())
