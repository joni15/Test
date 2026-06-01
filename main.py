"""
Point d'entrée principal du bot de sniping.
Usage : python main.py
"""
import logging
import sys
from datetime import datetime, timezone

from config import LOG_LEVEL, TARGET_USERNAME
from address_detector import detect_addresses, DetectedAddress
from safety_checker import run_checks
import solana_trader
import eth_trader
from twitter_monitor import start_monitor

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sniper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# Mémorise les adresses déjà traitées pour éviter les doublons
_processed: set[str] = set()


def handle_tweet(tweet_id: str, text: str) -> None:
    """Appelé dès qu'un nouveau tweet est détecté."""
    log.info(f"[MAIN] Tweet {tweet_id} analysé")
    addresses = detect_addresses(text)

    if not addresses:
        log.debug("[MAIN] Aucune adresse détectée")
        return

    for det in addresses:
        _snipe(det, tweet_id)


def _snipe(det: DetectedAddress, tweet_id: str) -> None:
    addr  = det.address
    chain = det.chain

    if addr.lower() in _processed:
        log.info(f"[MAIN] {addr} déjà traité, ignoré")
        return
    _processed.add(addr.lower())

    log.info(f"[MAIN] ── Nouvelle adresse détectée ──")
    log.info(f"[MAIN]   Chaîne  : {chain}")
    log.info(f"[MAIN]   Adresse : {addr}")
    log.info(f"[MAIN]   Contexte: {det.context}")
    log.info(f"[MAIN]   Tweet   : https://x.com/{TARGET_USERNAME}/status/{tweet_id}")

    # ── Vérifications de sécurité ─────────────────────────────────────────────
    report = run_checks(addr, chain)

    if not report.is_safe:
        log.warning(f"[MAIN] SKIP — Token non sûr :")
        for reason in report.reasons:
            log.warning(f"[MAIN]   • {reason}")
        return

    log.info(f"[MAIN] Token OK — Liquidité ${report.liquidity_usd:.0f} "
             f"| Buy tax {report.buy_tax}% | Sell tax {report.sell_tax}%")

    # ── Exécution du trade ────────────────────────────────────────────────────
    if chain == "solana":
        tx_sig = solana_trader.buy_token(addr)
        if tx_sig:
            solana_trader.confirm_transaction(tx_sig)

    else:  # ethereum, bsc, base, arbitrum, polygon
        tx_hash = eth_trader.buy_token(addr, chain)
        if tx_hash:
            eth_trader.confirm_transaction(tx_hash, chain)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 60)
    log.info(f"  Bot de sniping démarré — cible : @{TARGET_USERNAME}")
    log.info(f"  Démarrage : {datetime.now(timezone.utc).isoformat()}")
    log.info("=" * 60)

    try:
        start_monitor(handle_tweet)
    except KeyboardInterrupt:
        log.info("[MAIN] Arrêt demandé par l'utilisateur")
    except Exception as e:
        log.critical(f"[MAIN] Erreur fatale : {e}", exc_info=True)
        sys.exit(1)
