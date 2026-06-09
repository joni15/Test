"""Outils en ligne de commande.

    python -m app.cli aggregate [--output data/deals.json]
        Lance tous les scrapers et écrit le résultat en JSON (utilisé par le
        workflow GitHub Actions). Échoue (code 1) si seules les données de
        démonstration sont disponibles, pour ne jamais publier de fausses
        offres dans le flux.

    python -m app.cli doctor
        Diagnostique l'accès à chaque source : politique réseau de
        l'environnement, protection anti-bot, page sans données exploitables.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .aggregator import collect_deals
from .scrapers import ALL_SCRAPERS
from .scrapers.base import JSONLD_RE, USER_AGENT
from .scrapers.browser import PLAYWRIGHT_AVAILABLE

PROBE_URLS = {
    "Migros": "https://www.migros.ch/fr",
    "Coop": "https://www.coop.ch/fr/actions.html",
    "Denner": "https://www.denner.ch/fr/offres-hebdomadaires/",
    "Lidl": "https://www.lidl.ch/c/fr-CH/offres/a10006065",
    "Aldi": "https://www.aldi-suisse.ch/fr/actions/",
}


def cmd_aggregate(output: str | None) -> int:
    deals, sources = collect_deals(use_remote_feed=False)
    if sources == ["démo"]:
        print(
            "ERREUR : aucune source réelle n'a répondu, le flux ne sera pas écrit.",
            file=sys.stderr,
        )
        return 1
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "deals": [
            deal.model_dump(mode="json", exclude={"id", "fetched_at", "is_sample"})
            for deal in deals
        ],
    }
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        print(f"{len(deals)} offres écrites dans {path} (sources : {', '.join(sources)})")
    else:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=1)
    return 0


def cmd_doctor() -> int:
    print(f"Playwright disponible : {'oui' if PLAYWRIGHT_AVAILABLE else 'non'}")
    print()
    blocked_by_policy = 0
    for name, url in PROBE_URLS.items():
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            if resp.headers.get("x-deny-reason") == "host_not_allowed":
                status = (
                    "❌ bloqué par la politique réseau de l'environnement "
                    "(ajouter le domaine à l'allowlist)"
                )
                blocked_by_policy += 1
            elif resp.status_code == 403:
                status = "🛡️ protection anti-bot (essayer Playwright ou GitHub Actions)"
            elif resp.status_code >= 400:
                status = f"⚠️ HTTP {resp.status_code}"
            elif JSONLD_RE.search(resp.text):
                status = "✅ accessible, données JSON-LD présentes"
            else:
                status = "⚠️ accessible mais sans JSON-LD (rendu JavaScript requis)"
        except httpx.HTTPError as exc:
            status = f"❌ erreur réseau : {type(exc).__name__}"
        print(f"  {name:8s} {status}")

    print()
    if blocked_by_policy == len(PROBE_URLS):
        print(
            "Tous les domaines sont bloqués par la politique réseau.\n"
            "Solutions :\n"
            " 1. Exécuter l'app en local ou via le workflow GitHub Actions\n"
            "    (.github/workflows/aggregate-deals.yml) qui publie data/deals.json.\n"
            " 2. Ou autoriser les domaines des détaillants dans les réglages\n"
            "    réseau de l'environnement (claude.ai/code → environnement)."
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    agg = sub.add_parser("aggregate", help="Scrape et exporte les offres en JSON")
    agg.add_argument("--output", "-o", default=None, help="Fichier JSON de sortie")
    sub.add_parser("doctor", help="Diagnostique l'accès aux sources")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    if args.command == "aggregate":
        return cmd_aggregate(args.output)
    return cmd_doctor()


if __name__ == "__main__":
    sys.exit(main())
