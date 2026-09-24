import requests

from config import Config


class IdentityService:
    """
    Résolution de noms multi-sources avec fallback en cascade.

    Ordre de priorité :
      - ETH  : ENS → Etherscan Nametag → scraping blockchain.com
      - BTC  : tag local (blockchain.info/tags) → scraping blockchain.com
      - BCH  : tag local → scraping blockchain.com

    N'écrit PAS en base : c'est le rôle du repository et de la route.
    Retourne toujours un dict {"name": str | None, "source": str | None}.
    """

    def __init__(self, w3=None, tag_service=None, scraper=None):
        self.w3 = w3
        self.tag_service = tag_service
        self.scraper = scraper

        # Initialisation ENS (optionnelle, seulement si un RPC est configuré)
        if self.w3 is None and Config.ETH_RPC_URL:
            try:
                from web3 import Web3
                self.w3 = Web3(Web3.HTTPProvider(Config.ETH_RPC_URL))
            except ImportError:
                self.w3 = None

    # ------------------------------------------------------------------
    # Point d'entrée unique
    # ------------------------------------------------------------------
    def resolve(self, chain: str, address: str) -> dict:
        if chain == "eth":
            # 1. ENS (décentralisé, source la plus fiable)
            name = self._resolve_ens(address)
            if name:
                return {"name": name, "source": "ens"}

            # 2. Etherscan Nametag (labels publics d'entités connues)
            name = self._resolve_etherscan_nametag(address)
            if name:
                return {"name": name, "source": "etherscan_nametag"}

            # 3. Scraping blockchain.com (dernier recours)
            if self.scraper and Config.SCRAPER_ENABLED:
                name = self.scraper.fetch_name("eth", address)
                if name:
                    return {"name": name, "source": "blockchain.com_scrape"}

        elif chain in ("btc", "bch"):
            # 1. Tag local (base blockchain.info/tags) — instantané
            if self.tag_service:
                tag = self.tag_service.lookup(address)
                if tag:
                    return {"name": tag, "source": "blockchain_info_tags"}

            # 2. Scraping blockchain.com — lent mais couvre plus d'adresses
            if self.scraper and Config.SCRAPER_ENABLED:
                name = self.scraper.fetch_name(chain, address)
                if name:
                    return {"name": name, "source": "blockchain.com_scrape"}

        return {"name": None, "source": None}

    # ------------------------------------------------------------------
    # Sources ETH
    # ------------------------------------------------------------------
    def _resolve_ens(self, address: str) -> str | None:
        """Résolution ENS inverse (address → name.eth)."""
        if not self.w3:
            return None
        try:
            return self.w3.ens.name(address)
        except Exception:
            return None

    def _resolve_etherscan_nametag(self, address: str) -> str | None:
        """Récupère le nametag public Etherscan (ex : 'Coinbase 10')."""
        if not Config.ETHERSCAN_API_KEY:
            return None
        try:
            r = requests.get(
                "https://api.etherscan.io/api",
                params={
                    "module": "metadata",
                    "action": "getlabel",
                    "address": address,
                    "apikey": Config.ETHERSCAN_API_KEY,
                },
                timeout=8,
            )
            r.raise_for_status()
            return r.json().get("result", {}).get("label")
        except (requests.RequestException, ValueError):
            return None