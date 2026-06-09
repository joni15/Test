"""Scraper Coop — extrait les promotions JSON-LD de la page d'actions."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper, extract_jsonld_products

ACTIONS_URL = "https://www.coop.ch/fr/actions.html"


class CoopScraper(BaseScraper):
    retailer = "Coop"

    def _fetch(self) -> list[Deal]:
        with self._client() as client:
            resp = client.get(ACTIONS_URL)
            resp.raise_for_status()
        return extract_jsonld_products(resp.text, self.retailer, ACTIONS_URL)
