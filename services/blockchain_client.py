import http.client
import json
from typing import Any

from config import Config


class BlockchainAPIError(Exception):
    """Erreur remontée par l'API explorer-gateway-kt."""


class BlockchainInfoClient:
    """
    Client HTTP bas niveau pour api.blockchain.info (explorer-gateway-kt).
    Centralise les en-têtes navigateur et la sérialisation JSON.
    """

    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Origin": "https://www.blockchain.com",
        "Referer": "https://www.blockchain.com/",
    }

    def __init__(
        self,
        host: str = Config.BLOCKCHAIN_HOST,
        timeout: int = Config.BLOCKCHAIN_TIMEOUT,
    ):
        self.host = host
        self.timeout = timeout

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        conn = http.client.HTTPSConnection(self.host, timeout=self.timeout)
        body = json.dumps(payload)

        try:
            conn.request("POST", path, body=body, headers=self.DEFAULT_HEADERS)
            response = conn.getresponse()
            raw = response.read().decode("utf-8")

            if response.status != 200:
                raise BlockchainAPIError(
                    f"HTTP {response.status} sur {path} : {raw[:200]}"
                )

            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise BlockchainAPIError(
                    f"Réponse non-JSON sur {path} : {raw[:200]}"
                ) from exc
        except (http.client.HTTPException, OSError) as exc:
            raise BlockchainAPIError(f"Erreur réseau sur {path} : {exc}") from exc
        finally:
            conn.close()