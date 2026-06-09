"""Scraper Aldi Suisse — actions de la semaine."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper

OFFERS_URL = "https://www.aldi-suisse.ch/fr/actions/"


class AldiScraper(BaseScraper):
    retailer = "Aldi"

    def _fetch(self) -> list[Deal]:
        return self._harvest(OFFERS_URL)
