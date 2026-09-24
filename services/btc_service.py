from services.blockchain_client import BlockchainInfoClient
from utils.formatters import satoshi_to_btc, timestamp_to_iso


class BtcService:
    BALANCE_PATH = "/explorer-gateway-kt/btc/address"
    TRANSACTIONS_PATH = "/explorer-gateway-kt/btc/address/transactions"

    def __init__(self, client: BlockchainInfoClient):
        self.client = client

    # ------------------------------------------------------------------
    # Solde
    # ------------------------------------------------------------------
    def get_address(self, address: str) -> dict:
        raw = self.client.post(self.BALANCE_PATH, {"address": address})
        return self._normalize(address, raw)

    @staticmethod
    def _normalize(address: str, raw: dict) -> dict:
        confirmed_sat = raw.get("confirmed", 0) or 0
        unconfirmed_sat = raw.get("unconfirmed", 0) or 0
        received_sat = raw.get("received", 0) or 0

        return {
            "chain": "btc",
            "address": raw.get("address", address),
            "balance_btc": satoshi_to_btc(confirmed_sat),
            "pending_btc": satoshi_to_btc(unconfirmed_sat),
            "received_btc": satoshi_to_btc(received_sat),
            "balance_sat": confirmed_sat,
            "pending_sat": unconfirmed_sat,
            "received_sat": received_sat,
            "tx_count": raw.get("txCount", 0),
            "utxo_count": raw.get("utxo", 0),
        }

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    def get_transactions(
        self, address: str, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        raw = self.client.post(
            self.TRANSACTIONS_PATH,
            {"address": address, "limit": limit, "offset": offset},
        )
        return [
            self._normalize_tx(tx, address)
            for tx in raw.get("transactions", [])
        ]

    @staticmethod
    def _normalize_tx(tx: dict, address: str) -> dict:
        """
        Normalise une transaction BTC.

        Calcule :
          - la direction (in/out) relative à `address`
          - les montants reçus/envoyés par `address`
          - les champs `from`/`to` cohérents avec le front (detectDirection)
        """
        addr_lc = address.lower()
        inputs = tx.get("inputs", []) or []
        outputs = tx.get("outputs", []) or []

        # Sommes relatives à l'adresse interrogée
        received_sat = sum(
            (o.get("value") or 0)
            for o in outputs
            if (o.get("address") or "").lower() == addr_lc
        )
        sent_sat = sum(
            (i.get("value") or 0)
            for i in inputs
            if (i.get("address") or "").lower() == addr_lc
        )

        is_sender = any(
            (i.get("address") or "").lower() == addr_lc for i in inputs
        )
        is_receiver = any(
            (o.get("address") or "").lower() == addr_lc for o in outputs
        )

        # Détermination de from/to cohérente avec la direction
        if is_sender:
            from_addr = address
            to_addr = next(
                (
                    o.get("address")
                    for o in outputs
                    if o.get("address")
                    and o["address"].lower() != addr_lc
                ),
                None,
            )
        elif is_receiver:
            from_addr = next(
                (i.get("address") for i in inputs if i.get("address")),
                None,
            )
            to_addr = address
        else:
            # Cas rare : ni sender ni receiver (ne devrait pas arriver)
            from_addr = next(
                (i.get("address") for i in inputs if i.get("address")),
                None,
            )
            to_addr = next(
                (o.get("address") for o in outputs if o.get("address")),
                None,
            )

        # Valeur affichée : flux net absolu, avec fallback
        net_sat = received_sat - sent_sat
        value_sat = (
            abs(net_sat) if net_sat != 0 else (received_sat or sent_sat)
        )

        is_mempool = bool(tx.get("mempool"))

        return {
            "hash": tx.get("txId"),
            "block_number": tx.get("blockHeight"),
            "timestamp": tx.get("time"),
            "datetime": timestamp_to_iso(tx.get("time")),
            "from": from_addr,
            "to": to_addr,
            "value_btc": satoshi_to_btc(value_sat),
            "value_sat": value_sat,
            "received_btc": satoshi_to_btc(received_sat),
            "sent_btc": satoshi_to_btc(sent_sat),
            "net_btc": satoshi_to_btc(net_sat),
            "fee_btc": satoshi_to_btc(tx.get("fee", 0)),
            "fee_sat": tx.get("fee", 0),
            "size": tx.get("size"),
            "weight": tx.get("weight"),
            "rbf": tx.get("rbf"),
            "mempool": is_mempool,
            "confirmed": not is_mempool,
        }