"""Agrégation quotidienne : lance tous les scrapers, déduplique, classe."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from . import database
from .models import Deal
from .scrapers import ALL_SCRAPERS
from .scrapers.sample_data import sample_deals

logger = logging.getLogger(__name__)


def collect_deals() -> tuple[list[Deal], list[str]]:
    """Interroge toutes les sources en parallèle et fusionne les résultats."""
    scrapers = [cls() for cls in ALL_SCRAPERS]
    sources: list[str] = []
    merged: dict[str, Deal] = {}

    with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
        results = pool.map(lambda s: (s.retailer, s.fetch()), scrapers)

    for retailer, deals in results:
        if deals:
            sources.append(retailer)
        for deal in deals:
            merged.setdefault(deal.dedupe_key(), deal)

    if not merged:
        logger.warning(
            "Aucune source en ligne n'a répondu — utilisation des données de démonstration"
        )
        for deal in sample_deals():
            merged.setdefault(deal.dedupe_key(), deal)
        sources = ["démo"]

    ranked = sorted(
        merged.values(),
        key=lambda d: d.discount_percent or 0,
        reverse=True,
    )
    return ranked, sources


def refresh() -> int:
    """Cycle complet : collecte + remplacement en base. Retourne le nombre d'offres."""
    deals, sources = collect_deals()
    count = database.replace_deals(deals, sources)
    logger.info("Agrégation terminée : %d offres (%s)", count, ", ".join(sources))
    return count
