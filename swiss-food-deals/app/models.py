"""Modèles de données pour les offres alimentaires."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Deal(BaseModel):
    """Une offre alimentaire chez un détaillant suisse."""

    id: Optional[int] = None
    retailer: str = Field(description="Détaillant (Migros, Coop, Denner, Lidl, Aldi…)")
    title: str = Field(description="Nom du produit")
    description: str = ""
    category: str = "Divers"
    price: float = Field(description="Prix promotionnel en CHF")
    original_price: Optional[float] = Field(default=None, description="Prix normal en CHF")
    discount_percent: Optional[float] = Field(default=None, description="Rabais en %")
    unit: str = ""
    image_url: str = ""
    deal_url: str = ""
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    fetched_at: Optional[str] = None
    is_sample: bool = False

    def compute_discount(self) -> None:
        """Calcule le rabais si absent mais déductible des prix."""
        if self.discount_percent is None and self.original_price and self.original_price > 0:
            self.discount_percent = round(
                (1 - self.price / self.original_price) * 100, 1
            )

    def dedupe_key(self) -> str:
        return f"{self.retailer.lower()}|{self.title.lower().strip()}|{self.price}"
