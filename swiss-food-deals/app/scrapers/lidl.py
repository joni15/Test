"""Scraper Lidl Suisse — promotions de la semaine.

L'URL de la page change chaque semaine (identifiant tournant) ; on part de
la page d'accueil et on suit le premier lien « promotions-de-la-semaine ».
"""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper

HOME_URL = "https://www.lidl.ch/"


class LidlScraper(BaseScraper):
    retailer = "Lidl"

    def _fetch(self) -> list[Deal]:
        return self._harvest(HOME_URL, follow_link_pattern="promotions-de-la-semaine")
