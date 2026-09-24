import time

import requests

from config import Config


class PriceService:
    CHAIN_TO_COIN = {
        "btc": "bitcoin",
        "bch": "bitcoin-cash",
        "eth": "ethereum",
    }

    def __init__(self, ttl: int = Config.PRICE_CACHE_TTL):
        self.ttl = ttl
        self._cache: dict[tuple[str, str], tuple[float, float]] = {}

    def get_price(self, chain: str, vs_currency: str = Config.DEFAULT_VS_CURRENCY):
        coin_id = self.CHAIN_TO_COIN.get(chain)
        if not coin_id:
            return None

        cache_key = (coin_id, vs_currency)
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and now - cached[1] < self.ttl:
            return cached[0]

        try:
            r = requests.get(
                Config.COINGECKO_URL,
                params={"ids": coin_id, "vs_currencies": vs_currency},
                timeout=8,
            )
            r.raise_for_status()
            price = r.json().get(coin_id, {}).get(vs_currency)
            if price is not None:
                self._cache[cache_key] = (price, now)
            return price
        except requests.RequestException:
            return None