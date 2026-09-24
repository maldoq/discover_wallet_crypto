"""
Télécharge les tags blockchain.info et les stocke dans SQLite.
Usage : python -m scripts.update_btc_tags

À exécuter périodiquement (cron, tâche planifiée…).
"""
import requests

from services.database import get_connection

TAGS_URL = "https://blockchain.info/tags"


def fetch_and_store_tags() -> int:
    try:
        r = requests.get(
            TAGS_URL,
            params={"format": "json", "limit": 10000},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        tags = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"Erreur de récupération : {e}")
        return 0

    with get_connection() as conn:
        for item in tags:
            addr = item.get("address")
            tag = item.get("tag")
            if addr and tag:
                conn.execute(
                    """
                    INSERT INTO btc_tags (address, tag) VALUES (?, ?)
                    ON CONFLICT(address) DO UPDATE SET
                        tag = excluded.tag,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (addr, tag),
                )

    print(f"{len(tags)} tags importés/mis à jour.")
    return len(tags)


if __name__ == "__main__":
    fetch_and_store_tags()