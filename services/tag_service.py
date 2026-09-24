from services.database import get_connection


class TagService:
    """
    Lookup local des tags BTC (base blockchain.info/tags).
    Aucun appel réseau : instantané et robuste.
    """

    def lookup(self, address: str) -> str | None:
        try:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT tag FROM btc_tags WHERE address = ?",
                    (address,),
                ).fetchone()
                return row["tag"] if row else None
        except Exception:
            return None