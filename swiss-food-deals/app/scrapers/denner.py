"""Scraper Denner — extrait les offres hebdomadaires (JSON-LD)."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper, extract_jsonld_products

OFFERS_URL = "https://www.denner.ch/fr/offres-hebdomadaires/"


class DennerScraper(BaseScraper):
    retailer = "Denner"

    def _fetch(self) -> list[Deal]:
        html = self._get_html(OFFERS_URL)
        return extract_jsonld_products(html, self.retailer, OFFERS_URL)
