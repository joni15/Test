"""Source « flux distant » : offres réelles publiées par GitHub Actions.

Le workflow `.github/workflows/aggregate.yml` scrape les détaillants depuis
un runner GitHub (accès internet complet + Playwright) et committe le
résultat dans `data/deals.json`. Cette source lit ce fichier via
raw.githubusercontent.com — accessible même depuis des environnements dont
la politique réseau bloque les sites des détaillants.

Configurable via la variable d'environnement DEALS_FEED_URL.
"""
from __future__ import annotations

import os
from datetime import date

from ..models import Deal
from .base import BaseScraper

# Le workflow planifié ne tourne que sur la branche par défaut du dépôt ;
# c'est donc là que data/deals.json est publié.
DEFAULT_FEED_URL = (
    "https://raw.githubusercontent.com/joni15/Test/"
    "claude/address-sniping-check-Idthi/data/deals.json"
)


class RemoteFeedScraper(BaseScraper):
    retailer = "Flux distant"

    def __init__(self) -> None:
        self.feed_url = os.environ.get("DEALS_FEED_URL", DEFAULT_FEED_URL)

    def _fetch(self) -> list[Deal]:
        with self._client() as client:
            resp = client.get(self.feed_url)
            resp.raise_for_status()
            payload = resp.json()

        deals: list[Deal] = []
        for item in payload.get("deals", []):
            try:
                deals.append(
                    Deal(
                        retailer=item["retailer"],
                        title=item["title"],
                        description=item.get("description", ""),
                        category=item.get("category", "Divers"),
                        price=float(item["price"]),
                        original_price=item.get("original_price"),
                        discount_percent=item.get("discount_percent"),
                        unit=item.get("unit", ""),
                        image_url=item.get("image_url", ""),
                        deal_url=item.get("deal_url", ""),
                        valid_from=date.fromisoformat(item["valid_from"])
                        if item.get("valid_from")
                        else None,
                        valid_until=date.fromisoformat(item["valid_until"])
                        if item.get("valid_until")
                        else None,
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        return deals
