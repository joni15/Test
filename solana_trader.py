"""
Trading Solana via Jupiter Aggregator v6.
Swap SOL → token détecté.
"""
import base64
import logging
import time
from typing import Optional

import requests
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from config import (
    SOLANA_RPC_URL, SOLANA_PRIVATE_KEY,
    SOLANA_BUY_AMOUNT, SOLANA_SLIPPAGE_BPS,
)

log = logging.getLogger(__name__)

SOL_MINT  = "So11111111111111111111111111111111111111112"
JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_URL  = "https://quote-api.jup.ag/v6/swap"


def _load_keypair() -> Keypair:
    raw = SOLANA_PRIVATE_KEY.strip()
    # Accepte base58 ou tableau JSON [1,2,...,64]
    if raw.startswith("["):
        import json
        secret = bytes(json.loads(raw))
    else:
        import base58
        secret = base58.b58decode(raw)
    return Keypair.from_bytes(secret)


def _get_quote(output_mint: str, lamports: int) -> Optional[dict]:
    params = {
        "inputMint":   SOL_MINT,
        "outputMint":  output_mint,
        "amount":      lamports,
        "slippageBps": SOLANA_SLIPPAGE_BPS,
        "onlyDirectRoutes": "false",
    }
    try:
        r = requests.get(JUPITER_QUOTE_URL, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"[SOL] Quote échouée : {e}")
        return None


def _build_swap_tx(quote: dict, wallet_pubkey: str) -> Optional[str]:
    payload = {
        "quoteResponse":           quote,
        "userPublicKey":           wallet_pubkey,
        "wrapAndUnwrapSol":        True,
        "prioritizationFeeLamports": 50_000,  # priority fee ~0.00005 SOL
    }
    try:
        r = requests.post(JUPITER_SWAP_URL, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["swapTransaction"]
    except Exception as e:
        log.error(f"[SOL] Build swap échoué : {e}")
        return None


def buy_token(token_mint: str) -> Optional[str]:
    """
    Achète `SOLANA_BUY_AMOUNT` SOL de `token_mint`.
    Retourne la signature de transaction ou None si échec.
    """
    kp      = _load_keypair()
    client  = Client(SOLANA_RPC_URL)
    lamports = int(SOLANA_BUY_AMOUNT * 1_000_000_000)

    log.info(f"[SOL] Achat {SOLANA_BUY_AMOUNT} SOL → {token_mint}")

    # 1. Quote
    quote = _get_quote(token_mint, lamports)
    if not quote:
        return None
    out_amount = int(quote.get("outAmount", 0)) / 1e6
    log.info(f"[SOL] Quote : {out_amount:.2f} tokens reçus (estimé)")

    # 2. Transaction
    swap_tx_b64 = _build_swap_tx(quote, str(kp.pubkey()))
    if not swap_tx_b64:
        return None

    # 3. Désérialisation et signature
    raw_tx = base64.b64decode(swap_tx_b64)
    tx     = VersionedTransaction.from_bytes(raw_tx)
    tx_signed = VersionedTransaction(tx.message, [kp])

    # 4. Envoi
    try:
        opts = TxOpts(skip_preflight=False, preflight_commitment="confirmed")
        resp = client.send_raw_transaction(bytes(tx_signed), opts=opts)
        sig  = str(resp.value)
        log.info(f"[SOL] TX envoyée : https://solscan.io/tx/{sig}")
        return sig
    except Exception as e:
        log.error(f"[SOL] Envoi TX échoué : {e}")
        return None


def confirm_transaction(sig: str, max_wait: int = 60) -> bool:
    client  = Client(SOLANA_RPC_URL)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            resp = client.get_signature_statuses([sig])
            status = resp.value[0]
            if status and status.confirmation_status in ("confirmed", "finalized"):
                log.info(f"[SOL] TX confirmée : {sig}")
                return True
        except Exception:
            pass
        time.sleep(2)
    log.warning(f"[SOL] TX non confirmée après {max_wait}s")
    return False
