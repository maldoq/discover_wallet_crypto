import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5000"))

    # --- Blockchain.info explorer-gateway-kt ---
    BLOCKCHAIN_HOST = os.getenv("BLOCKCHAIN_HOST", "api.blockchain.info")
    BLOCKCHAIN_TIMEOUT = int(os.getenv("BLOCKCHAIN_TIMEOUT", "15"))

    # --- SQLite ---
    DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "explorer.db")))

    # --- Ethereum RPC (ENS, optionnel) ---
    ETH_RPC_URL = os.getenv("ETH_RPC_URL", "")

    # --- Etherscan (nametags, optionnel) ---
    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

    # --- CoinGecko ---
    COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
    PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "60"))
    DEFAULT_VS_CURRENCY = os.getenv("DEFAULT_VS_CURRENCY", "usd")

    # --- Scraper ---
    SCRAPER_ENABLED = os.getenv("SCRAPER_ENABLED", "true").lower() == "true"
    SCRAPER_TIMEOUT_MS = int(os.getenv("SCRAPER_TIMEOUT_MS", "20000"))
    SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"

    # --- Limites ---
    MAX_TX_PER_REQUEST = int(os.getenv("MAX_TX_PER_REQUEST", "20"))
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))