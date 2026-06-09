"""Scraper Denner — page des actions actuelles."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper

OFFERS_URL = "https://www.denner.ch/fr/actions"


class DennerScraper(BaseScraper):
    retailer = "Denner"

    def _fetch(self) -> list[Deal]:
        return self._harvest(OFFERS_URL)
