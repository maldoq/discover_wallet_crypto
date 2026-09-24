import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import Config


SCHEMA = """
CREATE TABLE IF NOT EXISTS addresses (
    address                     TEXT PRIMARY KEY,
    chain                       TEXT NOT NULL,
    display_name                TEXT,
    name_source                 TEXT,
    name_resolution_attempted   INTEGER NOT NULL DEFAULT 0,
    name_resolved_at            TIMESTAMP,
    first_seen                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_addresses_chain ON addresses(chain);

CREATE TABLE IF NOT EXISTS btc_tags (
    address     TEXT PRIMARY KEY,
    tag         TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'blockchain.info',
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(db_path: Path | None = None) -> None:
    """Crée le fichier SQLite et les tables si nécessaire."""
    path = Path(db_path or Config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_connection(db_path: Path | None = None):
    """
    Context manager qui ouvre une connexion, commit en sortie propre,
    rollback en cas d'exception, et ferme toujours.
    """
    path = Path(db_path or Config.DB_PATH)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()