# scripts/create_fb_profile.py

"""
Create and save a persistent Facebook login profile using Playwright.

Usage:
    python create_fb_profile.py

This script:
1. Opens Firefox with a persistent user data directory.
2. Lets the user manually log in to Facebook.
3. Ensures Marketplace is opened once to clear any intro pop-ups.
4. Saves the profile in the `playwright_profile` directory for reuse.
"""

from playwright.sync_api import sync_playwright

# Directory where the persistent Firefox profile will be stored
USER_DATA_DIR = "playwright_profile"


def create_facebook_profile() -> None:
    """
    Launch Firefox with a persistent profile and prompt the user to log in.

    The saved profile (cookies, local storage, etc.) will allow automated
    scripts to reuse the authenticated session without repeated logins.
    """
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
        )
        page = browser.new_page()
        page.goto("https://www.facebook.com/")

        print("⚠️ Please log in manually in the opened Firefox window.")
        print("Complete any 2FA or checkpoints as required.")
        print("👉 Once logged in, go through Marketplace to close pop-ups.")
        input("Press Enter here when finished...")

        browser.close()
        print(f"✅ Facebook profile saved in '{USER_DATA_DIR}'.")


if __name__ == "__main__":
    create_facebook_profile()
