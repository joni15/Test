"""Offres de démonstration, utilisées quand aucune source en ligne ne répond.

Les prix sont représentatifs des actions hebdomadaires typiques en Suisse,
mais ce ne sont PAS des offres réelles en cours.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..models import Deal


def sample_deals() -> list[Deal]:
    today = date.today()
    until = today + timedelta(days=6)
    raw = [
        # (détaillant, titre, catégorie, prix, prix normal, unité)
        ("Migros", "Filet de saumon bio", "Poisson", 19.90, 33.20, "100 g"),
        ("Migros", "Bananes équitables", "Fruits & Légumes", 1.95, 2.60, "kg"),
        ("Migros", "Emmentaler doux", "Fromage", 1.55, 2.25, "100 g"),
        ("Migros", "Café en grains Boncampo", "Épicerie", 4.95, 7.10, "500 g"),
        ("Migros", "Poulet entier suisse", "Viande", 7.90, 11.30, "kg"),
        ("Coop", "Entrecôte de bœuf suisse", "Viande", 4.95, 9.90, "100 g"),
        ("Coop", "Tomates grappes du pays", "Fruits & Légumes", 2.95, 4.50, "kg"),
        ("Coop", "Gruyère surchoix AOP", "Fromage", 1.75, 2.50, "100 g"),
        ("Coop", "Huile d'olive extra vierge Naturaplan", "Épicerie", 9.95, 14.20, "500 ml"),
        ("Coop", "Jus d'orange fraîchement pressé", "Boissons", 3.50, 5.00, "750 ml"),
        ("Denner", "Raclette nature en tranches", "Fromage", 2.19, 3.15, "100 g"),
        ("Denner", "Spaghetti Barilla", "Épicerie", 1.40, 2.35, "500 g"),
        ("Denner", "Vin rouge Primitivo di Manduria DOC", "Boissons", 6.95, 11.95, "750 ml"),
        ("Denner", "Escalopes de poulet", "Viande", 11.95, 19.95, "kg"),
        ("Lidl", "Fraises d'Espagne", "Fruits & Légumes", 2.49, 3.99, "500 g"),
        ("Lidl", "Mozzarella di bufala", "Fromage", 1.79, 2.69, "125 g"),
        ("Lidl", "Saumon fumé d'Écosse", "Poisson", 4.49, 6.99, "100 g"),
        ("Lidl", "Pain aux noix artisanal", "Boulangerie", 2.79, 3.99, "400 g"),
        ("Aldi", "Avocats prêts à consommer", "Fruits & Légumes", 1.99, 3.29, "2 pièces"),
        ("Aldi", "Côtelettes de porc suisses", "Viande", 1.39, 2.19, "100 g"),
        ("Aldi", "Beurre de choix", "Produits laitiers", 2.49, 3.20, "250 g"),
        ("Aldi", "Chocolat noir 72%", "Douceurs", 1.29, 1.99, "100 g"),
    ]
    deals = []
    for retailer, title, category, price, original, unit in raw:
        deal = Deal(
            retailer=retailer,
            title=title,
            category=category,
            price=price,
            original_price=original,
            unit=unit,
            valid_from=today,
            valid_until=until,
            is_sample=True,
        )
        deal.compute_discount()
        deals.append(deal)
    return deals
