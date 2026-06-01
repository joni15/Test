"""
Trading Ethereum / EVM via Uniswap v2 (UniswapV2Router02).
Fonctionne aussi sur BSC (PancakeSwap), Base, Arbitrum avec les bons RPC/router.
"""
import logging
import time
from typing import Optional

from web3 import Web3
from web3.middleware import geth_poa_middleware

from config import (
    ETH_RPC_URL, ETH_PRIVATE_KEY,
    ETH_BUY_AMOUNT_ETH, ETH_SLIPPAGE_PCT,
)

log = logging.getLogger(__name__)

# ── Routers Uniswap V2 par chaîne ────────────────────────────────────────────
ROUTERS = {
    "ethereum": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "bsc":      "0x10ED43C718714eb63d5aA57B78B54704E256024E",  # PancakeSwap
    "base":     "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24",
    "arbitrum": "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24",
    "polygon":  "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",  # QuickSwap
}

WETH_ADDRESSES = {
    "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "bsc":      "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
    "base":     "0x4200000000000000000000000000000000000006",
    "arbitrum": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    "polygon":  "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
}

ROUTER_ABI = [
    {
        "name": "swapExactETHForTokens",
        "type": "function",
        "inputs": [
            {"name": "amountOutMin",  "type": "uint256"},
            {"name": "path",          "type": "address[]"},
            {"name": "to",            "type": "address"},
            {"name": "deadline",      "type": "uint256"},
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
    },
    {
        "name": "getAmountsOut",
        "type": "function",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path",     "type": "address[]"},
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
    },
]


def _connect(chain: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
    if chain in ("bsc", "polygon"):
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    if not w3.is_connected():
        raise ConnectionError(f"Impossible de se connecter au RPC : {ETH_RPC_URL}")
    return w3


def buy_token(token_address: str, chain: str = "ethereum") -> Optional[str]:
    """
    Achète `ETH_BUY_AMOUNT_ETH` ETH de `token_address` via Uniswap V2.
    Retourne le hash de la TX ou None si échec.
    """
    w3 = _connect(chain)
    account  = w3.eth.account.from_key(ETH_PRIVATE_KEY)
    router   = ROUTERS.get(chain, ROUTERS["ethereum"])
    weth     = WETH_ADDRESSES.get(chain, WETH_ADDRESSES["ethereum"])
    token    = Web3.to_checksum_address(token_address)
    router_c = w3.eth.contract(address=Web3.to_checksum_address(router), abi=ROUTER_ABI)

    amount_in_wei = Web3.to_wei(ETH_BUY_AMOUNT_ETH, "ether")
    path          = [Web3.to_checksum_address(weth), token]

    log.info(f"[ETH] Achat {ETH_BUY_AMOUNT_ETH} ETH → {token} sur {chain}")

    # 1. Estimation de la sortie
    try:
        amounts = router_c.functions.getAmountsOut(amount_in_wei, path).call()
        amount_out_min = int(amounts[-1] * (1 - ETH_SLIPPAGE_PCT / 100))
        log.info(f"[ETH] Min tokens reçus : {amount_out_min}")
    except Exception as e:
        log.warning(f"[ETH] Impossible d'estimer la sortie : {e} — on continue avec 0")
        amount_out_min = 0

    # 2. Construction de la TX
    deadline  = int(time.time()) + 300  # 5 min
    nonce     = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    try:
        tx = router_c.functions.swapExactETHForTokens(
            amount_out_min, path, account.address, deadline
        ).build_transaction({
            "from":     account.address,
            "value":    amount_in_wei,
            "gas":      300_000,
            "gasPrice": int(gas_price * 1.3),   # +30% pour priorité
            "nonce":    nonce,
            "chainId":  w3.eth.chain_id,
        })
    except Exception as e:
        log.error(f"[ETH] Build TX échoué : {e}")
        return None

    # 3. Signature et envoi
    try:
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        hex_hash = tx_hash.hex()
        log.info(f"[ETH] TX envoyée : https://etherscan.io/tx/{hex_hash}")
        return hex_hash
    except Exception as e:
        log.error(f"[ETH] Envoi TX échoué : {e}")
        return None


def confirm_transaction(tx_hash: str, chain: str = "ethereum", max_wait: int = 120) -> bool:
    w3       = _connect(chain)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                ok = receipt["status"] == 1
                status = "confirmée ✓" if ok else "REVERTÉE ✗"
                log.info(f"[ETH] TX {status} : {tx_hash}")
                return ok
        except Exception:
            pass
        time.sleep(3)
    log.warning(f"[ETH] TX non confirmée après {max_wait}s")
    return False
