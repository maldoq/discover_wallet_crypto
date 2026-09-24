from datetime import datetime, timezone

from services.blockchain_client import BlockchainInfoClient
from utils.formatters import wei_to_eth


class EthService:
    PATH = "/explorer-gateway-kt/eth/address"
    NETWORK = "ETH"

    def __init__(self, client: BlockchainInfoClient):
        self.client = client

    def get_address(
        self, address: str, page: int = 0, size: int = 20
    ) -> dict:
        payload = {
            "network": self.NETWORK,
            "address": address,
            "page": page,
            "size": size,
        }
        raw = self.client.post(self.PATH, payload)
        return self._normalize(address, raw)

    @classmethod
    def _normalize(cls, address: str, raw: dict) -> dict:
        return {
            "chain": "eth",
            "address": raw.get("address", address),
            "balance_eth": wei_to_eth(raw.get("balance", "0")),
            "balance_wei": raw.get("balance", "0"),
            "nonce": raw.get("nonce"),
            "tx_count": raw.get("transactionCount"),
            "internal_tx_count": raw.get("internalTransactionCount"),
            "total_sent_eth": wei_to_eth(raw.get("totalSent", "0")),
            "total_received_eth": wei_to_eth(raw.get("totalReceived", "0")),
            "total_fees_eth": wei_to_eth(raw.get("totalFees", "0")),
            "page": raw.get("page", 0),
            "transactions": [
                cls._normalize_tx(tx) for tx in raw.get("transactions", [])
            ],
        }

    @staticmethod
    def _normalize_tx(tx: dict) -> dict:
        ts = tx.get("timestamp")
        dt_iso = EthService._ts_to_iso(ts)

        return {
            "hash": tx.get("hash"),
            "block_number": tx.get("blockNumber"),
            "timestamp": ts,
            "datetime": dt_iso,
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value_eth": wei_to_eth(tx.get("value", "0")),
            "value_wei": tx.get("value", "0"),
            "fee_eth": wei_to_eth(tx.get("fee", "0")),
            "gas_price": tx.get("gasPrice"),
            "gas_used": tx.get("gasUsed"),
            "gas_limit": tx.get("gasLimit"),
            "nonce": tx.get("nonce"),
            "success": tx.get("success"),
            "state": tx.get("state"),
            "type": tx.get("type"),
            "error": tx.get("error"),
        }

    @staticmethod
    def _ts_to_iso(ts) -> str | None:
        """
        Convertit un timestamp en ISO 8601 UTC.
        Tolère :
          - secondes ou millisecondes
          - valeurs non numériques, vides ou hors plage
        Retourne None en cas de problème, sans jamais lever d'exception.
        """
        if ts is None:
            return None

        try:
            n = int(ts)
        except (TypeError, ValueError):
            return None

        if n <= 0:
            return None

        # Détection millisecondes : au-delà de 10^12, c'est clairement
        # en millisecondes (10^12 secondes = ~an 33658).
        if n > 1_000_000_000_000:
            n = n // 1000

        # Filtre de sécurité : on refuse tout ce qui n'est pas plausible
        # (avant 2009 pour ETH, ou après l'an 2100).
        # 1230768000 = 2009-01-01, 4102444800 = 2100-01-01
        if n < 1_230_768_000 or n > 4_102_444_800:
            return None

        try:
            return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            # Windows peut refuser certaines dates proches des bornes.
            return None