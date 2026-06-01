"""
Configuration du bot de sniping.
Copier .env.example en .env et remplir les valeurs.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Twitter/X ────────────────────────────────────────────────────────────────
X_BEARER_TOKEN      = os.getenv("X_BEARER_TOKEN", "")
X_API_KEY           = os.getenv("X_API_KEY", "")
X_API_SECRET        = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN      = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET     = os.getenv("X_ACCESS_SECRET", "")

# Compte à surveiller (username sans @)
TARGET_USERNAME     = os.getenv("TARGET_USERNAME", "Kekius_Sage")

# ── Solana ───────────────────────────────────────────────────────────────────
SOLANA_RPC_URL      = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
SOLANA_PRIVATE_KEY  = os.getenv("SOLANA_PRIVATE_KEY", "")   # base58
SOLANA_BUY_AMOUNT   = float(os.getenv("SOLANA_BUY_AMOUNT", "0.1"))   # en SOL
SOLANA_SLIPPAGE_BPS = int(os.getenv("SOLANA_SLIPPAGE_BPS", "1000"))  # 10%

# ── Ethereum / EVM ───────────────────────────────────────────────────────────
ETH_RPC_URL         = os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com")
ETH_PRIVATE_KEY     = os.getenv("ETH_PRIVATE_KEY", "")      # hex avec 0x
ETH_BUY_AMOUNT_ETH  = float(os.getenv("ETH_BUY_AMOUNT_ETH", "0.05"))  # en ETH
ETH_SLIPPAGE_PCT    = int(os.getenv("ETH_SLIPPAGE_PCT", "15"))         # %

# ── Sécurité / filtres ───────────────────────────────────────────────────────
MIN_LIQUIDITY_USD   = float(os.getenv("MIN_LIQUIDITY_USD", "5000"))
MAX_BUY_TAX_PCT     = float(os.getenv("MAX_BUY_TAX_PCT", "10"))
REQUIRE_RENOUNCED   = os.getenv("REQUIRE_RENOUNCED", "false").lower() == "true"

# ── Monitoring ───────────────────────────────────────────────────────────────
POLL_INTERVAL_SEC   = int(os.getenv("POLL_INTERVAL_SEC", "60"))
USE_STREAMING       = os.getenv("USE_STREAMING", "true").lower() == "true"
LOG_LEVEL           = os.getenv("LOG_LEVEL", "INFO")
