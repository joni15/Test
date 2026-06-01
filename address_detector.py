"""
Détection d'adresses crypto dans du texte.
Supporte Ethereum/EVM, Solana, et filtrage basique anti-faux-positif.
"""
import re
from dataclasses import dataclass
from typing import Optional

# Adresses EVM connues à ignorer (tokens majeurs, etc.)
EVM_BLACKLIST = {
    "0x0000000000000000000000000000000000000000",
    "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
    "0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT
}

# Mots-clés Solana natifs à ignorer
SOLANA_BLACKLIST = {
    "11111111111111111111111111111111",            # System program
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", # Token program
    "So11111111111111111111111111111111111111112",  # Wrapped SOL
}


@dataclass
class DetectedAddress:
    chain: str          # "ethereum" | "solana" | "bsc" | "base" | ...
    address: str
    context: str        # quelques mots autour dans le tweet
    raw_text: str


def _extract_context(text: str, match: re.Match, window: int = 60) -> str:
    start = max(0, match.start() - window)
    end   = min(len(text), match.end() + window)
    snippet = text[start:end].replace("\n", " ")
    return f"...{snippet}..."


def detect_addresses(text: str) -> list[DetectedAddress]:
    results: list[DetectedAddress] = []
    seen: set[str] = set()

    # ── Ethereum / EVM (0x + 40 hex chars) ───────────────────────────────────
    evm_pattern = re.compile(r'\b(0x[a-fA-F0-9]{40})\b')
    for m in evm_pattern.finditer(text):
        addr = m.group(1).lower()
        if addr in seen or addr in EVM_BLACKLIST:
            continue
        seen.add(addr)
        # Heuristique : exclure les hashes de tx (0x + 64 chars)
        chain = _guess_evm_chain(text, m)
        results.append(DetectedAddress(
            chain=chain,
            address=m.group(1),
            context=_extract_context(text, m),
            raw_text=text,
        ))

    # ── Solana (base58, 32-44 chars) ─────────────────────────────────────────
    sol_pattern = re.compile(r'\b([1-9A-HJ-NP-Za-km-z]{32,44})\b')
    for m in sol_pattern.finditer(text):
        addr = m.group(1)
        if addr in seen or addr in SOLANA_BLACKLIST:
            continue
        if not _is_likely_solana(addr, text, m):
            continue
        seen.add(addr)
        results.append(DetectedAddress(
            chain="solana",
            address=addr,
            context=_extract_context(text, m),
            raw_text=text,
        ))

    return results


def _guess_evm_chain(text: str, match: re.Match) -> str:
    ctx = text[max(0, match.start()-100):match.end()+100].lower()
    if any(k in ctx for k in ["bsc", "binance", "bnb", "pancake"]):
        return "bsc"
    if any(k in ctx for k in ["base", "base chain", "coinbase"]):
        return "base"
    if any(k in ctx for k in ["arbitrum", "arb"]):
        return "arbitrum"
    if any(k in ctx for k in ["polygon", "matic"]):
        return "polygon"
    return "ethereum"


def _is_likely_solana(addr: str, text: str, match: re.Match) -> bool:
    # Doit contenir des lettres ET des chiffres (base58 réel)
    has_digit  = any(c.isdigit() for c in addr)
    has_letter = any(c.isalpha() for c in addr)
    if not (has_digit and has_letter):
        return False

    # Indices contextuels positifs
    ctx = text[max(0, match.start()-120):match.end()+120].lower()
    positive_keywords = [
        "solana", "sol", "pump.fun", "raydium", "jupiter",
        "ca:", "contract:", "mint:", "token address", "address:"
    ]
    if any(k in ctx for k in positive_keywords):
        return True

    # Indices contextuels négatifs (liens, hashes normaux)
    if re.search(r'https?://', ctx):
        return False

    # Par défaut : inclure si >= 40 chars (très probablement une adresse)
    return len(addr) >= 40
