# src/cosmicreseller/telegram_bot.py

"""
Telegram bot for fetching and sending cheap item deals from Facebook Marketplace or eBay.

Conversation flow:
1. Ask user for the source market ("facebook" or "ebay").
2. Ask for a search keyword.
3. Ask for number of pages/items to fetch.
4. Ask for a threshold ratio (0–1).
5. Fetch items, filter cheap ones, and send formatted results to Telegram.
"""

import os
import re
import logging
from typing import List, Tuple

import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram_text import Link

from src.cosmicreseller.pricing import get_cheap_items

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Conversation states
SOURCE, KEYWORD, MAX_PAGES, THRESHOLD_RATIO = range(4)


def escape_markdown_v2(text: str) -> str:
    """
    Escape Telegram MarkdownV2 special characters.

    Args:
        text (str): Raw text.

    Returns:
        str: Escaped text safe for MarkdownV2.
    """
    escape_chars = r"_*\[\]()~`>#+-=|{}.!,%-"
    return re.sub(f"([{re.escape(escape_chars)}])", "", text)


def format_message(avg_price: float, cheap_items: List[Tuple[str, float, str]]) -> str:
    """
    Format a message containing average price and cheap items.

    Args:
        avg_price (float): Computed average market price.
        cheap_items (list): List of (title, price, url).

    Returns:
        str: MarkdownV2 formatted message for Telegram.
    """
    if not cheap_items:
        return "No cheap items found."

    lines = [f"*Average Market Price:* £{avg_price:.2f}\n*Deals found:*\n"]

    for title, price, link in cheap_items:
        safe_title = escape_markdown_v2(title)
        formatted_link = Link(safe_title, link)
        safe_price = escape_markdown_v2(f"£{price:.0f}")
        lines.append(f"- {formatted_link} - {safe_price}\n")

    return "".join(lines)


async def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    """
    Send a (potentially long) message to a Telegram chat, splitting
    into chunks if it exceeds Telegram's 4096-character limit.

    Args:
        token (str): Bot token.
        chat_id (str): Target chat ID.
        message (str): Markdown-formatted message.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    max_len = 4096

    lines = message.splitlines(keepends=True)
    chunks: List[str] = []
    chunk = ""

    for line in lines:
        if len(chunk) + len(line) > max_len:
            chunks.append(chunk)
            chunk = line
        else:
            chunk += line
    if chunk:
        chunks.append(chunk)

    async with aiohttp.ClientSession() as session:
        for c in chunks:
            payload = {"chat_id": chat_id, "text": c, "parse_mode": "Markdown"}
            resp = await session.post(url, data=payload)
            resp.raise_for_status()


# --- Conversation Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: ask which marketplace to search."""
    await update.message.reply_text(
        "Which market are you looking for?\nType: *facebook* or *ebay*",
        parse_mode="MarkdownV2",
    )
    return SOURCE


async def handle_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user choice of marketplace."""
    text = update.message.text.strip().lower()
    if text not in ["facebook", "ebay"]:
        await update.message.reply_text('Please type "facebook" or "ebay".')
        return SOURCE

    context.user_data["source"] = text
    await update.message.reply_text("What are you looking for?")
    return KEYWORD


async def handle_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user-provided search keyword."""
    context.user_data["keyword"] = update.message.text.strip()
    await update.message.reply_text("How many pages do you want to extract?")
    return MAX_PAGES


async def handle_max_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user-provided max pages/items."""
    try:
        pages = int(update.message.text.strip())
        context.user_data["max_pages"] = pages
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return MAX_PAGES

    await update.message.reply_text(
        "Enter the threshold ratio as a float (e.g., 0.8 means 20% below average):"
    )
    return THRESHOLD_RATIO


async def handle_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle threshold ratio and trigger the search."""
    try:
        ratio = float(update.message.text.strip())
        if not (0 < ratio < 1):
            await update.message.reply_text(
                "Please enter a valid float between 0 and 1."
            )
            return THRESHOLD_RATIO
        context.user_data["threshold_ratio"] = ratio
    except ValueError:
        await update.message.reply_text("Please enter a valid float (e.g., 0.8).")
        return THRESHOLD_RATIO

    source = context.user_data["source"]
    keyword = context.user_data["keyword"]
    max_pages = context.user_data["max_pages"]
    threshold_ratio = context.user_data["threshold_ratio"]

    await update.message.reply_text(
        f"Searching {source.title()} for '{keyword}'... This may take a moment."
    )

    try:
        avg_price, cheap_items = await get_cheap_items(
            source, keyword, max_pages, threshold_ratio
        )
        message = format_message(avg_price, cheap_items)
    except Exception as exc:
        logger.exception("Error while fetching deals")
        message = f"Error occurred while fetching deals: {exc}"

    await send_telegram_message(TOKEN, CHAT_ID, message)
    return ConversationHandler.END


async def error_handler(update: object, context: CallbackContext) -> None:
    """Global error handler for the bot."""
    logger.exception("Exception occurred during update: %s", update)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow user to cancel conversation."""
    await update.message.reply_text("Canceled.")
    return ConversationHandler.END


async def start_bot() -> None:
    """
    Initialize and run the Telegram bot.
    """
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_source)],
            KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyword)],
            MAX_PAGES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_max_pages)],
            THRESHOLD_RATIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_threshold)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
