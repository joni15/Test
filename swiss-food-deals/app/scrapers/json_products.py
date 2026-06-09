"""Extraction heuristique de produits depuis des structures JSON arbitraires.

Les API internes des détaillants ont chacune leur schéma, mais un produit en
promotion contient presque toujours un nom et un prix sous des clés
prévisibles. On parcourt récursivement n'importe quel document JSON capturé
par le navigateur et on en extrait les nœuds « produit ».
"""
from __future__ import annotations

from ..models import Deal

NAME_KEYS = ("name", "title", "productName", "label", "description1")
PRICE_KEYS = ("price", "currentPrice", "salesPrice", "actionPrice", "offerPrice", "promoPrice")
ORIGINAL_KEYS = (
    "originalPrice",
    "normalPrice",
    "oldPrice",
    "regularPrice",
    "strikePrice",
    "strikethroughPrice",
    "crossedOutPrice",
    "basePrice",
)
IMAGE_KEYS = ("image", "imageUrl", "imageURL", "img", "pictureUrl")
URL_KEYS = ("url", "link", "productUrl", "href", "canonicalUrl")
UNIT_KEYS = ("unit", "quantity", "packaging", "weight", "basePriceText")

MAX_DEALS_PER_DOC = 500


def _as_price(value) -> float | None:
    """Convertit une valeur de prix (nombre, chaîne, ou dict imbriqué)."""
    if isinstance(value, dict):
        for key in ("value", "amount", "price", "current"):
            if key in value:
                return _as_price(value[key])
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        price = float(value)
    elif isinstance(value, str):
        cleaned = value.replace("CHF", "").replace("'", "").replace(",", ".").strip()
        try:
            price = float(cleaned)
        except ValueError:
            return None
    else:
        return None
    return price if 0.05 <= price <= 10000 else None


def _first(node: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in node and node[key] is not None:
            return node[key]
    return None


def _as_str(value) -> str:
    if isinstance(value, dict):
        return str(value.get("url") or value.get("src") or "")
    if isinstance(value, list):
        return _as_str(value[0]) if value else ""
    return str(value) if value is not None else ""


def _node_to_deal(node: dict, retailer: str, source_url: str) -> Deal | None:
    name = _first(node, NAME_KEYS)
    if not isinstance(name, str) or not (3 <= len(name.strip()) <= 150):
        return None
    # Le prix est souvent imbriqué un niveau plus bas ({'offer': {'price': …}})
    candidates = [node] + [v for v in node.values() if isinstance(v, dict)]
    price = next(
        (p for c in candidates if (p := _as_price(_first(c, PRICE_KEYS))) is not None),
        None,
    )
    if price is None:
        return None
    original = next(
        (p for c in candidates if (p := _as_price(_first(c, ORIGINAL_KEYS))) is not None),
        None,
    )
    if original is not None and original <= price:
        original = None
    def find_str(keys):
        for c in candidates:
            value = _as_str(_first(c, keys))
            if value:
                return value
        return ""

    deal = Deal(
        retailer=retailer,
        title=name.strip(),
        price=price,
        original_price=original,
        unit=find_str(UNIT_KEYS)[:60],
        image_url=find_str(IMAGE_KEYS)[:500],
        deal_url=find_str(URL_KEYS)[:500] or source_url,
    )
    deal.compute_discount()
    return deal


def extract_products_from_json(data, retailer: str, source_url: str) -> list[Deal]:
    """Extrait récursivement tous les nœuds « produit » d'un document JSON."""
    deals: list[Deal] = []
    seen: set[str] = set()
    stack = [data]
    while stack and len(deals) < MAX_DEALS_PER_DOC:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            deal = _node_to_deal(node, retailer, source_url)
            if deal and deal.dedupe_key() not in seen:
                seen.add(deal.dedupe_key())
                deals.append(deal)
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
    return deals
