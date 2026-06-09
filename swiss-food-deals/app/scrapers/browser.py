"""Récupération de pages via navigateur headless (Playwright).

Les sites des détaillants suisses rendent leurs offres en JavaScript et
utilisent des protections anti-bot qui rejettent les clients HTTP simples.
En plus du HTML rendu, on capture les réponses XHR/fetch JSON : les offres
y transitent sous forme structurée, ce qui est bien plus fiable que de
parser le HTML.

Si la variable d'environnement DEALS_DEBUG_DIR est définie, le HTML rendu
et un résumé des réponses JSON capturées y sont écrits (utilisé par le
workflow GitHub Actions pour produire des artefacts de diagnostic).

Installation :
    pip install playwright && python -m playwright install chromium
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

CONSENT_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button#usercentrics-accept-all",
    "[data-testid='uc-accept-all-button']",
    "button:has-text('Tout accepter')",
    "button:has-text('Accepter')",
    "button:has-text('Alle akzeptieren')",
    "button:has-text('Akzeptieren')",
]


@dataclass
class RenderResult:
    html: str = ""
    json_responses: list[tuple[str, object]] = field(default_factory=list)


def render_page(
    url: str,
    follow_link_pattern: str | None = None,
    timeout_ms: int = 45000,
) -> RenderResult:
    """Charge `url` dans Chromium headless ; retourne HTML rendu + JSON capturés.

    `follow_link_pattern` : si fourni, suit le premier lien dont le href
    contient ce motif (pour les pages d'offres à URL changeante).
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright n'est pas installé "
            "(pip install playwright && python -m playwright install chromium)"
        )
    result = RenderResult()
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

            def on_response(resp):
                try:
                    ctype = resp.headers.get("content-type", "")
                    if "json" not in ctype:
                        return
                    body = resp.text()
                    if not body or len(body) > 5_000_000:
                        return
                    result.json_responses.append((resp.url, json.loads(body)))
                except Exception:
                    pass

            page.on("response", on_response)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            _accept_consent(page)

            if follow_link_pattern:
                href = page.evaluate(
                    """(pattern) => {
                        const a = [...document.querySelectorAll('a[href]')]
                            .find(a => a.getAttribute('href').includes(pattern));
                        return a ? a.href : null;
                    }""",
                    follow_link_pattern,
                )
                if href:
                    logger.info("Navigation vers %s", href)
                    page.goto(href, wait_until="domcontentloaded", timeout=timeout_ms)
                    _accept_consent(page)

            _scroll(page)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            result.html = page.content()
        finally:
            browser.close()
    return result


def _accept_consent(page) -> None:
    for selector in CONSENT_SELECTORS:
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=1500):
                button.click(timeout=2000)
                page.wait_for_timeout(800)
                return
        except Exception:
            continue


def _scroll(page, steps: int = 6) -> None:
    """Fait défiler la page pour déclencher le chargement paresseux."""
    for _ in range(steps):
        try:
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(700)
        except Exception:
            break


def dump_debug(retailer: str, result: RenderResult) -> None:
    """Écrit le HTML rendu et un résumé des JSON capturés dans DEALS_DEBUG_DIR."""
    debug_dir = os.environ.get("DEALS_DEBUG_DIR")
    if not debug_dir:
        return
    path = Path(debug_dir)
    path.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"\W+", "-", retailer.lower())
    (path / f"{slug}.html").write_text(result.html[:500_000], errors="replace")
    summary = [
        {
            "url": url,
            "top_level_keys": list(data.keys()) if isinstance(data, dict) else f"list[{len(data)}]",
            "sample": json.dumps(data, ensure_ascii=False)[:2000],
        }
        for url, data in result.json_responses
    ]
    (path / f"{slug}.responses.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1)
    )
