"""Récupération de pages via navigateur headless (Playwright).

Les sites des détaillants suisses rendent leurs offres en JavaScript et
utilisent des protections anti-bot (Akamai, Cloudflare…) qui rejettent les
clients HTTP simples. Un vrai navigateur passe ces barrières dans la plupart
des cas. Playwright est optionnel : si absent, les scrapers se rabattent
sur httpx uniquement.

Installation :
    pip install playwright && python -m playwright install chromium
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def fetch_html_browser(url: str, wait_selector: str | None = None, timeout_ms: int = 30000) -> str:
    """Charge `url` dans Chromium headless et retourne le HTML rendu.

    Lève une exception si Playwright n'est pas installé ou si la page
    ne charge pas — l'appelant gère l'échec.
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright n'est pas installé "
            "(pip install playwright && python -m playwright install chromium)"
        )
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            context = browser.new_context(
                locale="fr-CH",
                timezone_id="Europe/Zurich",
                viewport={"width": 1366, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=timeout_ms)
            else:
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            return page.content()
        finally:
            browser.close()
