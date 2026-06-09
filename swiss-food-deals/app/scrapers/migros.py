"""Scraper Migros — utilise l'API de recherche produits avec un jeton invité."""
from __future__ import annotations

from ..models import Deal
from .base import BaseScraper

GUEST_TOKEN_URL = (
    "https://www.migros.ch/authentication/public/v1/api/guest"
    "?authorizationNotRequired=true"
)
SEARCH_URL = "https://www.migros.ch/onesearch-oc-seaapi/public/v5/search"


class MigrosScraper(BaseScraper):
    retailer = "Migros"

    def _fetch(self) -> list[Deal]:
        with self._client() as client:
            token_resp = client.post(GUEST_TOKEN_URL)
            token_resp.raise_for_status()
            token = token_resp.headers.get("leshopch", "")
            if not token:
                return []

            resp = client.post(
                SEARCH_URL,
                headers={"leshopch": token},
                json={
                    "algorithm": "DEFAULT",
                    "filters": {"reduction": ["all"]},
                    "language": "fr",
                    "productIds": [],
                    "regionId": "national",
                    "sortFields": [],
                    "sortOrder": "asc",
                    "from": 0,
                    "size": 100,
                },
            )
            resp.raise_for_status()
            payload = resp.json()

        deals: list[Deal] = []
        for product in payload.get("productInfos", payload.get("products", [])):
            offer = product.get("offer") or {}
            price = offer.get("price", {}).get("value")
            if price is None:
                continue
            original = (offer.get("normalPrice") or {}).get("value")
            deals.append(
                Deal(
                    retailer=self.retailer,
                    title=product.get("name", "").strip(),
                    description=(product.get("description") or "")[:300],
                    category=(product.get("categories") or [{}])[0].get("name", "Divers")
                    if product.get("categories")
                    else "Divers",
                    price=float(price),
                    original_price=float(original) if original else None,
                    unit=offer.get("quantity", ""),
                    image_url=(product.get("images") or [{}])[0].get("url", "")
                    if product.get("images")
                    else "",
                    deal_url=f"https://www.migros.ch/fr/product/{product.get('migrosId', '')}",
                )
            )
        return deals
