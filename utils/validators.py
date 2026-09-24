import re

# Ethereum / EVM
ETH_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Bitcoin : legacy (1/3) et bech32 (bc1)
BTC_RE = re.compile(
    r"^(bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$"
)

# Bitcoin Cash : format CashAddr (avec ou sans préfixe)
BCH_RE = re.compile(r"^(bitcoincash:)?[qp][a-z0-9]{41}$")


def detect_chain(address: str) -> str:
    """
    Retourne 'eth', 'btc', 'bch' ou 'unknown'.
    Ordre important : BCH avant BTC pour éviter que les adresses CashAddr
    ne tombent dans la regex BTC (elles ne matchent pas de toute façon,
    mais on garde l'ordre explicite).
    """
    address = (address or "").strip()
    if ETH_RE.match(address):
        return "eth"
    if BCH_RE.match(address):
        return "bch"
    if BTC_RE.match(address):
        return "btc"
    return "unknown"