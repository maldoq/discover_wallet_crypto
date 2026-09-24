import threading

from flask import Blueprint, current_app, jsonify

from services.blockchain_client import BlockchainAPIError
from services.database import get_connection
from utils.validators import detect_chain

bp = Blueprint("api", __name__, url_prefix="/api")


def _services():
    return current_app.extensions["services"]


# ----------------------------------------------------------------------
# Suivi en mémoire des résolutions en cours
# (évite de spawner plusieurs threads pour la même adresse quand le front
#  fait du polling)
# ----------------------------------------------------------------------
_resolving_lock = threading.Lock()
_resolving: set[str] = set()


def _mark_resolving(addr: str) -> bool:
    """Retourne True si on a pu réserver l'adresse, False si déjà en cours."""
    with _resolving_lock:
        if addr in _resolving:
            return False
        _resolving.add(addr)
        return True


def _unmark_resolving(addr: str) -> None:
    with _resolving_lock:
        _resolving.discard(addr)


# ----------------------------------------------------------------------
# Route principale
# ----------------------------------------------------------------------
@bp.route("/address/<path:address>")
def get_address(address: str):
    chain = detect_chain(address)
    if chain == "unknown":
        return jsonify({"error": "Format d'adresse non reconnu"}), 400

    services = _services()
    repo = services["repo"]

    # --- 1) Persistance : TOUJOURS enregistrer avant les appels réseau ---
    try:
        row = repo.upsert_seen(address, chain)
    except Exception:
        current_app.logger.exception("Erreur SQLite (upsert_seen)")
        return jsonify({"error": "Erreur base de données"}), 500

    # --- 2) Données on-chain ---
    try:
        if chain == "btc":
            info = services["btc"].get_address(address)
            # Transactions (best-effort : n'échoue pas si le endpoint tombe)
            try:
                info["transactions"] = services["btc"].get_transactions(
                    address, limit=20
                )
            except BlockchainAPIError as exc:
                current_app.logger.warning(
                    "Erreur transactions BTC : %s", exc
                )
                info["transactions"] = []

        elif chain == "bch":
            info = services["bch"].get_address(address)
            try:
                info["transactions"] = services["bch"].get_transactions(
                    address, limit=20
                )
            except BlockchainAPIError as exc:
                current_app.logger.warning(
                    "Erreur transactions BCH : %s", exc
                )
                info["transactions"] = []

        elif chain == "eth":
            info = services["eth"].get_address(address)

        else:
            return jsonify({"error": "Chaîne non supportée"}), 400
    except BlockchainAPIError as exc:
        current_app.logger.warning("Erreur blockchain : %s", exc)
        return jsonify({
            "error": "Erreur source blockchain",
            "detail": str(exc),
        }), 502

    # --- 3) Nom : lire le cache, sinon lancer la résolution en arrière-plan ---
    display_name = row.get("display_name") if row else None
    name_source = row.get("name_source") if row else None
    needs_resolve = repo.needs_resolution(address)

    # On lance une résolution seulement si :
    #  - pas de nom en cache
    #  - needs_resolution (pas tenté récemment)
    #  - aucune résolution déjà en cours pour cette adresse
    resolving_now = False
    if not display_name and needs_resolve:
        if _mark_resolving(address):
            resolving_now = True
            app = current_app._get_current_object()  # réf. forte pour le thread

            def resolve_in_background(addr: str, ch: str):
                try:
                    with app.app_context():
                        identity = services["identity"].resolve(ch, addr)
                        repo.set_name(addr, identity["name"], identity["source"])
                except Exception:
                    # IMPORTANT : en cas d'erreur technique, on ne marque PAS
                    # la résolution comme tentée. Elle sera retentée à la
                    # prochaine visite (name_resolution_attempted reste à 0).
                    app.logger.exception("Erreur résolution en arrière-plan")
                finally:
                    _unmark_resolving(addr)

            threading.Thread(
                target=resolve_in_background,
                args=(address, chain),
                daemon=True,
            ).start()

    info["display_name"] = display_name
    info["name_source"] = name_source
    info["name_resolving"] = bool(
        not display_name and (resolving_now or needs_resolve)
    )
    if row:
        info["first_seen"] = row.get("first_seen")
        info["last_seen"] = row.get("last_seen")

    # --- 4) Prix ---
    price = services["price"].get_price(chain)
    if price is not None:
        balance_key = {
            "btc": "balance_btc",
            "bch": "balance_bch",
            "eth": "balance_eth",
        }[chain]
        info["price_usd"] = price
        info["balance_usd"] = info.get(balance_key, 0.0) * price

    return jsonify(info)


# ----------------------------------------------------------------------
# Résolution synchrone (bouton « forcer la résolution »)
# ----------------------------------------------------------------------
@bp.route("/address/<path:address>/resolve", methods=["POST"])
def force_resolve(address: str):
    """
    Force la résolution de nom de manière SYNCHRONE.
    Peut prendre 3–15 s à cause du scraping.
    """
    chain = detect_chain(address)
    if chain == "unknown":
        return jsonify({"error": "Format d'adresse non reconnu"}), 400

    services = _services()
    repo = services["repo"]

    # S'assurer que l'adresse existe en base
    try:
        repo.upsert_seen(address, chain)
    except Exception:
        current_app.logger.exception("Erreur SQLite (upsert_seen)")
        return jsonify({"error": "Erreur base de données"}), 500

    try:
        identity = services["identity"].resolve(chain, address)
        repo.set_name(address, identity["name"], identity["source"])

        return jsonify({
            "address": address,
            "chain": chain,
            "display_name": identity["name"],
            "name_source": identity["source"],
            "found": identity["name"] is not None,
        })
    except Exception as exc:
        current_app.logger.exception("Erreur résolution manuelle")
        return jsonify({
            "error": "Erreur de résolution",
            "detail": str(exc),
        }), 500


# ----------------------------------------------------------------------
# Recherches récentes (pour le dropdown de suggestions)
# ----------------------------------------------------------------------
@bp.route("/addresses/recent")
def recent_addresses():
    repo = _services()["repo"]
    try:
        return jsonify(repo.list_recent(limit=5))
    except Exception:
        current_app.logger.exception("Erreur SQLite (list_recent)")
        return jsonify({"error": "Erreur base de données"}), 500


@bp.route("/addresses/pending")
def pending_addresses():
    repo = _services()["repo"]
    try:
        return jsonify(repo.list_pending(limit=50))
    except Exception:
        current_app.logger.exception("Erreur SQLite (list_pending)")
        return jsonify({"error": "Erreur base de données"}), 500


@bp.route("/debug/db")
def debug_db():
    """Diagnostic rapide de l'état de la base."""
    try:
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM addresses"
            ).fetchone()[0]
            rows = conn.execute(
                """
                SELECT address, chain, display_name, name_source,
                       name_resolution_attempted, last_seen
                  FROM addresses
                 ORDER BY last_seen DESC
                 LIMIT 5
                """
            ).fetchall()
        return jsonify({
            "total_addresses": count,
            "recent": [dict(r) for r in rows],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500