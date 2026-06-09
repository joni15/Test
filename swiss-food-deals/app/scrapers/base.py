"""Classe de base pour les scrapers de détaillants suisses.

Chaque scraper interroge une source publique (API ou page d'actions) et
retourne une liste de `Deal`. Les sources web sont fragiles : un scraper
qui échoue retourne une liste vide et n'interrompt jamais l'agrégation.
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

import httpx

from ..models import Deal

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = httpx.Timeout(15.0)


class BaseScraper(ABC):
    retailer: str = "?"

    def fetch(self) -> list[Deal]:
        """Récupère les offres ; ne lève jamais d'exception."""
        try:
            deals = self._fetch()
            for deal in deals:
                deal.compute_discount()
            logger.info("%s: %d offres récupérées", self.retailer, len(deals))
            return deals
        except Exception:
            logger.exception("%s: échec de la récupération", self.retailer)
            return []

    @abstractmethod
    def _fetch(self) -> list[Deal]:
        ...

    def _client(self) -> httpx.Client:
        return httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-CH,fr;q=0.9"},
            timeout=TIMEOUT,
            follow_redirects=True,
        )

    def _get_html(self, url: str, wait_selector: str | None = None) -> str:
        """Récupère le HTML d'une page : httpx d'abord, navigateur en secours.

        Les pages d'actions sont souvent derrière une protection anti-bot
        et/ou rendues en JavaScript ; si la requête HTTP simple échoue ou
        renvoie une page sans données, on recharge via Playwright.
        """
        html = ""
        try:
            with self._client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as exc:
            logger.info("%s: requête HTTP simple refusée (%s)", self.retailer, exc)

        if html and JSONLD_RE.search(html):
            return html

        from .browser import PLAYWRIGHT_AVAILABLE, fetch_html_browser

        if PLAYWRIGHT_AVAILABLE:
            logger.info("%s: tentative via navigateur headless", self.retailer)
            return fetch_html_browser(url, wait_selector=wait_selector)
        return html


JSONLD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def extract_jsonld_products(html: str, retailer: str, page_url: str) -> list[Deal]:
    """Extrait les produits/offres schema.org (JSON-LD) d'une page d'actions.

    Beaucoup de pages de détaillants embarquent leurs promotions en JSON-LD ;
    c'est plus stable que de parser le HTML lui-même.
    """
    deals: list[Deal] = []
    for match in JSONLD_RE.finditer(html):
        try:
            data = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        for node in _walk_jsonld(data):
            deal = _product_to_deal(node, retailer, page_url)
            if deal:
                deals.append(deal)
    return deals


def _walk_jsonld(data) -> list[dict]:
    """Aplati récursivement un document JSON-LD en nœuds de type Product."""
    nodes: list[dict] = []
    if isinstance(data, list):
        for item in data:
            nodes.extend(_walk_jsonld(item))
    elif isinstance(data, dict):
        if data.get("@type") in ("Product", "Offer", "AggregateOffer") and data.get("name"):
            nodes.append(data)
        for value in data.values():
            if isinstance(value, (list, dict)):
                nodes.extend(_walk_jsonld(value))
    return nodes


def _product_to_deal(node: dict, retailer: str, page_url: str) -> Deal | None:
    offers = node.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price") or node.get("price")
    if price is None:
        return None
    try:
        price_val = float(str(price).replace("CHF", "").strip())
    except ValueError:
        return None
    image = node.get("image") or ""
    if isinstance(image, list):
        image = image[0] if image else ""
    if isinstance(image, dict):
        image = image.get("url", "")
    return Deal(
        retailer=retailer,
        title=str(node.get("name", "")).strip(),
        description=str(node.get("description") or "").strip()[:300],
        price=price_val,
        image_url=str(image),
        deal_url=str(node.get("url") or offers.get("url") or page_url),
    )
