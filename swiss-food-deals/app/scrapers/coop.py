"""Scraper Coop — extrait les promotions JSON-LD de la page d'actions."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper, extract_jsonld_products

ACTIONS_URL = "https://www.coop.ch/fr/actions.html"


class CoopScraper(BaseScraper):
    retailer = "Coop"

    def _fetch(self) -> list[Deal]:
        html = self._get_html(ACTIONS_URL)
        return extract_jsonld_products(html, self.retailer, ACTIONS_URL)
