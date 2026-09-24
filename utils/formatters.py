from datetime import datetime, timezone

WEI_PER_ETH = 10**18
SATOSHI_PER_BTC = 10**8


def wei_to_eth(value) -> float:
    """Convertit une valeur Wei (str ou int) en ETH (float)."""
    try:
        return int(value) / WEI_PER_ETH
    except (TypeError, ValueError):
        return 0.0


def satoshi_to_btc(value) -> float:
    """Convertit une valeur satoshi (str ou int) en BTC (float)."""
    try:
        return int(value) / SATOSHI_PER_BTC
    except (TypeError, ValueError):
        return 0.0


def timestamp_to_iso(ts) -> str | None:
    """
    Convertit un timestamp Unix en ISO 8601 UTC.
    Tolère :
      - secondes ou millisecondes (détection automatique)
      - valeurs non numériques, vides ou hors plage
    Retourne None en cas de problème, ne lève jamais d'exception.
    Compatible Windows (qui refuse fromtimestamp hors plage 1970–2038).
    """
    if ts is None:
        return None

    try:
        n = int(ts)
    except (TypeError, ValueError):
        return None

    if n <= 0:
        return None

    # Millisecondes → secondes
    if n > 1_000_000_000_000:
        n = n // 1000

    # Filtre de plausibilité (2009-01-01 → 2100-01-01)
    if n < 1_230_768_000 or n > 4_102_444_800:
        return None

    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None