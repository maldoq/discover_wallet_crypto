import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # --- Blockchain.info explorer-gateway-kt ---
    BLOCKCHAIN_HOST = os.getenv("BLOCKCHAIN_HOST", "api.blockchain.info")
    BLOCKCHAIN_TIMEOUT = int(os.getenv("BLOCKCHAIN_TIMEOUT", "15"))

    # --- SQLite ---
    DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "explorer.db")))

    # --- Ethereum RPC (ENS, optionnel) ---
    ETH_RPC_URL = os.getenv("ETH_RPC_URL", "")

    # --- Etherscan (nametags, optionnel) ---
    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

    # --- Apify (labellisation multi-chaînes, optionnel) ---
    APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")

    # --- CoinGecko ---
    COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
    PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "60"))
    DEFAULT_VS_CURRENCY = os.getenv("DEFAULT_VS_CURRENCY", "usd")

    # --- Scraper blockchain.com ---
    SCRAPER_ENABLED = os.getenv("SCRAPER_ENABLED", "true").lower() == "true"
    SCRAPER_TIMEOUT_MS = int(os.getenv("SCRAPER_TIMEOUT_MS", "20000"))
    SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"