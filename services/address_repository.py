from datetime import datetime

from services.database import get_connection


class AddressRepository:
    """
    Persistance des adresses recherchées + cache de résolution de nom.

    Cycle de vie :
      1. upsert_seen()      -> enregistre l'adresse si nouvelle, met à jour last_seen
      2. needs_resolution() -> True si aucune résolution récente n'a été faite
      3. set_name()         -> stocke le nom trouvé (ou marque l'échec)
    """

    RETRY_AFTER_SECONDS = 24 * 3600  # 24h

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    def get(self, address: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM addresses WHERE address = ?",
                (address,),
            ).fetchone()
            return dict(row) if row else None

    def exists(self, address: str) -> bool:
        return self.get(address) is not None

    def needs_resolution(self, address: str) -> bool:
        row = self.get(address)
        if not row:
            return True
        if row["display_name"]:
            return False
        if not row["name_resolution_attempted"]:
            return True

        last = row["name_resolved_at"]
        if not last:
            return True

        try:
            last_dt = datetime.fromisoformat(last)
        except (TypeError, ValueError):
            return True

        return (datetime.utcnow() - last_dt).total_seconds() > self.RETRY_AFTER_SECONDS

    # ------------------------------------------------------------------
    # Écriture
    # ------------------------------------------------------------------
    def upsert_seen(self, address: str, chain: str) -> dict | None:
        """
        Insère l'adresse si elle n'existe pas, met à jour last_seen sinon.
        Utilise INSERT OR IGNORE + UPDATE pour une compatibilité maximale SQLite.
        """
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO addresses (address, chain) VALUES (?, ?)",
                (address, chain),
            )
            conn.execute(
                "UPDATE addresses SET last_seen = CURRENT_TIMESTAMP WHERE address = ?",
                (address,),
            )
            row = conn.execute(
                "SELECT * FROM addresses WHERE address = ?",
                (address,),
            ).fetchone()
            return dict(row) if row else None

    def set_name(self, address: str, name: str | None, source: str | None) -> None:
        """
        Enregistre le résultat d'une résolution.
        - Si `name` est None : marque la tentative sans stocker de nom
          (permettra un retry ultérieur).
        - Si `name` trouvé : stocke le nom et sa source.
        """
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE addresses
                   SET display_name              = ?,
                       name_source               = ?,
                       name_resolution_attempted = 1,
                       name_resolved_at          = CURRENT_TIMESTAMP
                 WHERE address = ?
                """,
                (name, source, address),
            )

    def list_recent(self, limit: int = 20) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT address, chain, display_name, name_source, last_seen
                  FROM addresses
                 ORDER BY last_seen DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_pending(self, limit: int = 50) -> list[dict]:
        """Adresses sans nom et jamais tentées."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT address, chain
                  FROM addresses
                 WHERE display_name IS NULL
                   AND name_resolution_attempted = 0
                 ORDER BY last_seen DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]