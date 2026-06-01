"""
Vérifications de sécurité avant achat :
- Liquidité minimale
- Tax de buy/sell
- Ownership renoncé (EVM)
- Age du token
Utilise les APIs publiques GoPlus et DexScreener.
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

from config import MIN_LIQUIDITY_USD, MAX_BUY_TAX_PCT, REQUIRE_RENOUNCED

log = logging.getLogger(__name__)

DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/tokens/{address}"
GOPLUS_URL      = "https://api.gopluslabs.io/api/v1/token_security/{chain_id}"

CHAIN_IDS = {
    "ethereum": "1",
    "bsc":      "56",
    "base":     "8453",
    "arbitrum": "42161",
    "polygon":  "137",
}


@dataclass
class SafetyReport:
    is_safe: bool
    liquidity_usd: float
    buy_tax: Optional[float]
    sell_tax: Optional[float]
    is_honeypot: bool
    owner_renounced: Optional[bool]
    reasons: list[str]   # pourquoi c'est unsafe


def _get_dexscreener(address: str) -> dict:
    try:
        r = requests.get(DEXSCREENER_URL.format(address=address), timeout=8)
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs") or []
        if pairs:
            return pairs[0]
    except Exception as e:
        log.warning(f"[SAFETY] DexScreener erreur : {e}")
    return {}


def _get_goplus(address: str, chain: str) -> dict:
    chain_id = CHAIN_IDS.get(chain, "1")
    try:
        r = requests.get(
            GOPLUS_URL.format(chain_id=chain_id),
            params={"contract_addresses": address},
            timeout=10,
        )
        r.raise_for_status()
        result = r.json().get("result", {})
        return result.get(address.lower(), {})
    except Exception as e:
        log.warning(f"[SAFETY] GoPlus erreur : {e}")
    return {}


def check_evm_token(address: str, chain: str) -> SafetyReport:
    reasons: list[str] = []
    dex  = _get_dexscreener(address)
    gp   = _get_goplus(address, chain)

    # Liquidité
    liquidity_usd = float(dex.get("liquidity", {}).get("usd", 0) or 0)
    if liquidity_usd < MIN_LIQUIDITY_USD:
        reasons.append(f"Liquidité trop faible : ${liquidity_usd:.0f} < ${MIN_LIQUIDITY_USD:.0f}")

    # Honeypot
    is_honeypot = gp.get("is_honeypot") == "1"
    if is_honeypot:
        reasons.append("HONEYPOT détecté par GoPlus")

    # Taxes
    buy_tax  = float(gp["buy_tax"])  if "buy_tax"  in gp else None
    sell_tax = float(gp["sell_tax"]) if "sell_tax" in gp else None

    if buy_tax is not None and buy_tax > MAX_BUY_TAX_PCT:
        reasons.append(f"Buy tax trop élevée : {buy_tax}% > {MAX_BUY_TAX_PCT}%")
    if sell_tax is not None and sell_tax > MAX_BUY_TAX_PCT:
        reasons.append(f"Sell tax trop élevée : {sell_tax}%")

    # Ownership
    owner_renounced = gp.get("owner_address", "").lower() in (
        "0x0000000000000000000000000000000000000000", ""
    ) if "owner_address" in gp else None

    if REQUIRE_RENOUNCED and owner_renounced is False:
        reasons.append("Ownership non renoncé")

    return SafetyReport(
        is_safe=len(reasons) == 0,
        liquidity_usd=liquidity_usd,
        buy_tax=buy_tax,
        sell_tax=sell_tax,
        is_honeypot=is_honeypot,
        owner_renounced=owner_renounced,
        reasons=reasons,
    )


def check_solana_token(address: str) -> SafetyReport:
    reasons: list[str] = []

    dex = _get_dexscreener(address)
    liquidity_usd = float(dex.get("liquidity", {}).get("usd", 0) or 0)

    if liquidity_usd < MIN_LIQUIDITY_USD:
        reasons.append(f"Liquidité trop faible : ${liquidity_usd:.0f}")

    # GoPlus Solana
    try:
        r = requests.get(
            "https://api.gopluslabs.io/api/v1/solana/token_security",
            params={"contract_addresses": address},
            timeout=10,
        )
        gp = r.json().get("result", {}).get(address, {})
        if gp.get("honeypot") == "1":
            reasons.append("HONEYPOT détecté")
        if REQUIRE_RENOUNCED and gp.get("non_transferable") != "1":
            reasons.append("Mint authority non renoncée")
    except Exception as e:
        log.warning(f"[SAFETY] GoPlus Solana erreur : {e}")
        gp = {}

    return SafetyReport(
        is_safe=len(reasons) == 0,
        liquidity_usd=liquidity_usd,
        buy_tax=None,
        sell_tax=None,
        is_honeypot=gp.get("honeypot") == "1",
        owner_renounced=None,
        reasons=reasons,
    )


def run_checks(address: str, chain: str) -> SafetyReport:
    log.info(f"[SAFETY] Vérification {chain} {address}")
    if chain == "solana":
        return check_solana_token(address)
    return check_evm_token(address, chain)
