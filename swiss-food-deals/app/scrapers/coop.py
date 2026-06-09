"""Scraper Coop — extrait les promotions JSON-LD de la page d'actions."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper

ACTIONS_URL = "https://www.coop.ch/fr/actions.html"


class CoopScraper(BaseScraper):
    retailer = "Coop"

    def _fetch(self) -> list[Deal]:
        return self._harvest(ACTIONS_URL)
