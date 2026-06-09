"""Scraper Lidl Suisse — extrait les promotions de la semaine (JSON-LD)."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper, extract_jsonld_products

OFFERS_URL = "https://www.lidl.ch/c/fr-CH/offres/a10006065"


class LidlScraper(BaseScraper):
    retailer = "Lidl"

    def _fetch(self) -> list[Deal]:
        with self._client() as client:
            resp = client.get(OFFERS_URL)
            resp.raise_for_status()
        return extract_jsonld_products(resp.text, self.retailer, OFFERS_URL)
